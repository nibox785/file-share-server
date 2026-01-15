"""TCP File Transfer Server (threaded, SSL-ready)

This module provides `start_tcp_server(use_ssl: bool)` that the FastAPI
app imports and starts as threads on startup.
"""

import socket
import ssl
import json
import threading
import os
from pathlib import Path
from typing import Tuple

from app.core.config import settings

UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

BUFFER_SIZE = 4096


def _send_json(conn: socket.socket, obj: dict):
    try:
        conn.sendall(json.dumps(obj).encode('utf-8'))
    except Exception:
        pass


def _recv_json(conn: socket.socket) -> dict:
    """Receive a short JSON control message from conn."""
    try:
        data = conn.recv(BUFFER_SIZE)
        if not data:
            return {}
        return json.loads(data.decode('utf-8'))
    except Exception:
        return {}


def handle_client(conn: socket.socket, addr: Tuple[str, int]):
    print(f"Client connected: {addr}")
    try:
        req = _recv_json(conn)
        if not req:
            print("Empty request or protocol error")
            return

        cmd = req.get('command')

        if cmd == 'UPLOAD':
            filename = req.get('filename')
            filesize = int(req.get('filesize', 0))
            if not filename or filesize <= 0:
                _send_json(conn, {'status': 'error', 'message': 'Invalid upload request'})
                return

            _send_json(conn, {'status': 'ok'})

            save_path = UPLOAD_DIR / filename
            received = 0

            with open(save_path, 'wb') as f:
                while received < filesize:
                    chunk = conn.recv(min(BUFFER_SIZE, filesize - received))
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)

            if received == filesize:
                print(f"Uploaded {filename} ({filesize} bytes) from {addr}")
                _send_json(conn, {'status': 'success', 'message': 'Uploaded'})
            else:
                print(f"Incomplete upload {filename}: {received}/{filesize}")
                _send_json(conn, {'status': 'error', 'message': 'Incomplete upload'})

        elif cmd == 'DOWNLOAD':
            filename = req.get('filename')
            file_path = UPLOAD_DIR / filename
            if not file_path.exists():
                _send_json(conn, {'status': 'error', 'message': 'Not found'})
                return

            filesize = file_path.stat().st_size
            _send_json(conn, {'status': 'ok', 'filesize': filesize})

            # Wait for READY
            ready = conn.recv(16)
            if not ready or ready.strip() != b'READY':
                print("Client not ready for download")
                return

            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    conn.sendall(chunk)

            print(f"Sent {filename} ({filesize} bytes) to {addr}")

        elif cmd == 'LIST':
            files = [f.name for f in UPLOAD_DIR.iterdir() if f.is_file()]
            _send_json(conn, {'status': 'success', 'count': len(files), 'files': files})

        else:
            _send_json(conn, {'status': 'error', 'message': 'Unknown command'})

    except Exception as e:
        print(f"Error handling client {addr}: {e}")
        try:
            _send_json(conn, {'status': 'error', 'message': str(e)})
        except Exception:
            pass
    finally:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        conn.close()
        print(f"Client disconnected: {addr}")


def start_tcp_server(use_ssl: bool = False, host: str = None, port: int = None):
    """Start a threaded TCP file server.

    Args:
        use_ssl: If True, load TLS cert/key and serve on SSL port.
        host: optional bind host (default from settings)
        port: optional port override (default from settings)
    """
    host = host or settings.TCP_HOST
    if use_ssl:
        port = port or settings.TCP_SSL_PORT
    else:
        port = port or settings.TCP_PORT

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(5)

    context = None
    if use_ssl:
        # Ensure certs exist
        if not (os.path.exists(settings.SSL_CERT_FILE) and os.path.exists(settings.SSL_KEY_FILE)):
            print("SSL certs not found; cannot start SSL server")
            sock.close()
            return
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(settings.SSL_CERT_FILE, settings.SSL_KEY_FILE)

    print(f"TCP Server listening on {host}:{port} (SSL={use_ssl})")

    try:
        while True:
            conn, addr = sock.accept()

            if use_ssl and context:
                try:
                    conn = context.wrap_socket(conn, server_side=True)
                except ssl.SSLError as e:
                    print(f"SSL handshake failed from {addr}: {e}")
                    conn.close()
                    continue

            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("TCP server stopping")
    except Exception as e:
        print(f"TCP server error: {e}")
    finally:
        sock.close()


if __name__ == '__main__':
    import argparse

    p = argparse.ArgumentParser(description='TCP File Server')
    p.add_argument('--port', type=int, default=None)
    p.add_argument('--ssl', action='store_true')
    args = p.parse_args()

    start_tcp_server(use_ssl=args.ssl, port=args.port)