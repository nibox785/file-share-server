import socket
import struct
import time
import os
from app.core.config import settings

class MulticastRadioServer:
    """
    Multicast Server - Radio Station
    Stream audio file đến nhiều client cùng lúc
    """
    
    def __init__(self, group=None, port=None):
        self.multicast_group = group or settings.MULTICAST_GROUP
        self.port = port or settings.MULTICAST_PORT
        self.sock = None
        self.running = False
    
    def start(self, audio_file="static/audio/sample.mp3"):
        """
        Bắt đầu phát audio qua multicast
        
        Args:
            audio_file: Đường dẫn file audio để stream
        """
        try:
            # Tạo UDP socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Set TTL (Time To Live) cho multicast packets
            ttl = struct.pack('b', 1)  # TTL = 1 (chỉ trong mạng local)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
            
            print(f"Multicast Radio Server started")
            print(f"   Group: {self.multicast_group}:{self.port}")
            print(f"   Audio: {audio_file}")
            
            self.running = True
            
            # Kiểm tra file audio tồn tại
            if not os.path.exists(audio_file):
                print(f"Audio file not found: {audio_file}")
                print(f"   Creating dummy audio stream...")
                self.stream_dummy_audio()
            else:
                self.stream_audio_file(audio_file)
                
        except Exception as e:
            print(f"Multicast server error: {e}")
        finally:
            self.stop()
    
    def stream_audio_file(self, audio_file):
        """Stream file audio thật"""
        chunk_size = 4096  # 4KB chunks
        
        try:
            with open(audio_file, 'rb') as f:
                chunk_count = 0
                
                while self.running:
                    chunk = f.read(chunk_size)
                    
                    if not chunk:
                        # Hết file, quay lại đầu (loop)
                        f.seek(0)
                        print("Looping audio...")
                        continue
                    
                    # Gửi chunk qua multicast
                    self.sock.sendto(chunk, (self.multicast_group, self.port))
                    chunk_count += 1
                    
                    # Log mỗi 100 chunks
                    if chunk_count % 100 == 0:
                        print(f"Sent {chunk_count} chunks ({chunk_count * chunk_size / 1024:.1f} KB)")
                    
                    # Delay để control bitrate (tùy chỉnh)
                    time.sleep(0.01)  # 10ms delay
                    
        except Exception as e:
            print(f"Error streaming audio: {e}")
    
    def stream_dummy_audio(self):
        """Stream dữ liệu giả (để test khi không có file audio)"""
        try:
            chunk_count = 0
            
            while self.running:
                # Tạo dummy data (sine wave hoặc random)
                dummy_data = b'\x00' * 1024  # 1KB of silence
                
                # Gửi qua multicast
                self.sock.sendto(dummy_data, (self.multicast_group, self.port))
                chunk_count += 1
                
                if chunk_count % 100 == 0:
                    print(f"Streaming... ({chunk_count} packets)")
                
                time.sleep(0.1)  # 100ms delay
                
        except Exception as e:
            print(f"Error streaming dummy audio: {e}")
    
    def stop(self):
        """Dừng server"""
        self.running = False
        if self.sock:
            self.sock.close()
            print("🛑 Multicast Radio Server stopped")

def start_multicast_server(audio_file="static/audio/sample.mp3"):
    """Helper function để start multicast server"""
    server = MulticastRadioServer()
    server.start(audio_file)