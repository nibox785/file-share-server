import socket
import ssl
import json
import os

class TCPFileClient:
    """Client để test TCP server (upload/download file)"""
    
    def __init__(self, host='localhost', port=9000, use_ssl=False):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.socket = None
    
    def connect(self, timeout: float = 10.0):
        """Kết nối đến server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            
            if self.use_ssl:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE  # Chỉ dùng cho test
                self.socket = context.wrap_socket(self.socket, server_hostname=self.host)
                print(f"Connected to {self.host}:{self.port} with SSL")
            else:
                print(f"Connected to {self.host}:{self.port}")
            
            self.socket.connect((self.host, self.port))
            return True
            
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def upload_file(self, filepath, progress_cb=None):
        """Upload file lên server"""
        try:
            if not os.path.exists(filepath):
                print(f"File not found: {filepath}")
                return False
            
            filename = os.path.basename(filepath)
            filesize = os.path.getsize(filepath)
            
            # Gửi request upload
            request = {
                'command': 'UPLOAD',
                'filename': filename,
                'filesize': filesize
            }
            self.socket.send(json.dumps(request).encode('utf-8'))
            
            # Nhận response
            response = json.loads(self.socket.recv(1024).decode('utf-8'))
            if response.get('status') != 'ok':
                print(f"Server rejected: {response.get('message')}")
                return False
            
            # Gửi file data
            print(f"Uploading {filename} ({filesize} bytes)...")
            sent = 0
            with open(filepath, 'rb') as f:
                while sent < filesize:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    self.socket.send(chunk)
                    sent += len(chunk)
                    if progress_cb:
                        progress_cb(sent, filesize)
                    else:
                        print(f"Progress: {sent}/{filesize} bytes ({sent*100//filesize}%)", end='\r')
            
            print()  # New line
            
            # Nhận kết quả
            result = json.loads(self.socket.recv(1024).decode('utf-8'))
            if result.get('status') == 'success':
                print(f"Upload successful: {result.get('message')}")
                return True
            else:
                print(f"Upload failed: {result.get('message')}")
                return False
                
        except Exception as e:
            print(f"Upload error: {e}")
            return False
    
    def download_file(self, filename, save_path=None, progress_cb=None):
        """Download file từ server"""
        try:
            # Gửi request download
            request = {
                'command': 'DOWNLOAD',
                'filename': filename
            }
            self.socket.send(json.dumps(request).encode('utf-8'))
            
            # Nhận thông tin file
            response = json.loads(self.socket.recv(1024).decode('utf-8'))
            if response.get('status') != 'ok':
                print(f"Download failed: {response.get('message')}")
                return False
            
            filesize = response.get('filesize')
            print(f" Downloading {filename} ({filesize} bytes)...")
            
            # Gửi confirm
            self.socket.send(b'READY')
            
            # Nhận file data
            save_path = save_path or f"downloaded_{filename}"
            received = 0
            with open(save_path, 'wb') as f:
                while received < filesize:
                    chunk = self.socket.recv(min(4096, filesize - received))
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)
                    if progress_cb:
                        progress_cb(received, filesize)
                    else:
                        print(f"Progress: {received}/{filesize} bytes ({received*100//filesize}%)", end='\r')
            
            print()  # New line
            
            if received == filesize:
                print(f"Download successful: {save_path}")
                return True
            else:
                print(f"Download incomplete: {received}/{filesize} bytes")
                return False
                
        except Exception as e:
            print(f"Download error: {e}")
            return False
    
    def list_files(self):
        """Liệt kê các file trên server"""
        try:
            request = {'command': 'LIST'}
            self.socket.send(json.dumps(request).encode('utf-8'))
            
            response = json.loads(self.socket.recv(4096).decode('utf-8'))
            if response.get('status') == 'success':
                files = response.get('files', [])
                print(f"\nFiles on server ({response.get('count')} files):")
                for i, file in enumerate(files, 1):
                    print(f"  {i}. {file}")
                return files
            else:
                print(f"List failed: {response.get('message')}")
                return []
                
        except Exception as e:
            print(f"List error: {e}")
            return []
    
    def close(self):
        """Đóng kết nối"""
        if self.socket:
            self.socket.close()
            print("👋 Disconnected")

# Test script
if __name__ == "__main__":
    print("=== TCP File Transfer Client ===\n")
    
    default_host = 'localhost'
    print("Using default host: localhost")
    
    # Nhập host (or use default)
    host_input = input(f"Server IP [{default_host}]: ").strip()
    host = host_input if host_input else default_host
    
    # Chọn SSL hay không
    use_ssl = input("Use SSL? (y/n) [n]: ").lower() == 'y'
    port = 9001 if use_ssl else 9000
    
    client = TCPFileClient(host=host, port=port, use_ssl=use_ssl)
    
    if not client.connect():
        print("\nCannot connect to server!")
        print(f"\nTroubleshooting:")
        print(f"1. Is server running? Check {host}:8000")
        print(f"2. Is firewall open? Check port {port}")
        print(f"3. Are you in the same network?")
        print(f"4. Try ping: ping {host}")
        exit(1)
    
    try:
        while True:
            print("\n--- Menu ---")
            print("1. Upload file")
            print("2. Download file")
            print("3. List files")
            print("4. Exit")
            
            choice = input("Choose: ")
            
            if choice == '1':
                filepath = input("Enter file path to upload: ")
                client.upload_file(filepath)
            
            elif choice == '2':
                filename = input("Enter filename to download: ")
                client.download_file(filename)
            
            elif choice == '3':
                client.list_files()
            
            elif choice == '4':
                break
            
            else:
                print("Invalid choice")
    
    finally:
        client.close()