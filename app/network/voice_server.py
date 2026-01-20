"""Simple TCP voice call relay server.

Protocol:
- Client sends a length-prefixed JSON join message:
  {"type": "join", "room": "room1", "username": "user1"}
- Then client streams audio frames as length-prefixed raw bytes.
- Server relays raw audio frames to other clients in the same room.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
from typing import Dict, Set, Tuple

from app.core.config import settings


def _recv_exact(conn: socket.socket, size: int) -> bytes:
    data = b""
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk:
            return b""
        data += chunk
    return data


def _recv_packet(conn: socket.socket) -> bytes:
    header = _recv_exact(conn, 4)
    if not header:
        return b""
    length = struct.unpack("!I", header)[0]
    if length <= 0:
        return b""
    return _recv_exact(conn, length)


def _send_packet(conn: socket.socket, payload: bytes) -> bool:
    try:
        conn.sendall(struct.pack("!I", len(payload)) + payload)
        return True
    except Exception:
        return False


def _recv_join(conn: socket.socket) -> Dict[str, str] | None:
    raw = _recv_packet(conn)
    if not raw:
        return None
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    if data.get("type") != "join":
        return None
    if not data.get("room"):
        return None
    return data


class VoiceRoomRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rooms: Dict[str, Set[socket.socket]] = {}

    def add(self, room: str, conn: socket.socket) -> None:
        with self._lock:
            self._rooms.setdefault(room, set()).add(conn)

    def remove(self, room: str, conn: socket.socket) -> None:
        with self._lock:
            if room in self._rooms and conn in self._rooms[room]:
                self._rooms[room].remove(conn)
                if not self._rooms[room]:
                    del self._rooms[room]

    def peers(self, room: str) -> Set[socket.socket]:
        with self._lock:
            return set(self._rooms.get(room, set()))


ROOMS = VoiceRoomRegistry()


def handle_client(conn: socket.socket, addr: Tuple[str, int]):
    room = None
    try:
        join = _recv_join(conn)
        if not join:
            return
        room = join.get("room")
        ROOMS.add(room, conn)
        print(f"Voice client joined {room}: {addr}")

        while True:
            data = _recv_packet(conn)
            if not data:
                break
            for peer in ROOMS.peers(room):
                if peer is conn:
                    continue
                _send_packet(peer, data)
    except Exception as exc:
        print(f"Voice client error {addr}: {exc}")
    finally:
        if room:
            ROOMS.remove(room, conn)
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        conn.close()
        print(f"Voice client disconnected: {addr}")


def start_voice_server(host: str | None = None, port: int | None = None):
    host = host or settings.TCP_HOST
    port = port or settings.VOICE_PORT

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(20)

    print(f"Voice Server listening on {host}:{port}")

    try:
        while True:
            conn, addr = sock.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("Voice server stopping")
    except Exception as exc:
        print(f"Voice server error: {exc}")
    finally:
        sock.close()
