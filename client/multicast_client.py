"""
Multicast Radio Client - Nhận stream audio từ server
Client tham gia multicast group để nghe "Radio Station"
"""

import socket
import struct
import sys
import time

try:
    import sounddevice as sd
    HAS_SD = True
except Exception:
    HAS_SD = False

class MulticastRadioClient:
    """
    Multicast Client - Nhận Radio Stream
    Tham gia multicast group để nhận audio từ server
    """
    
    def __init__(self, group='224.1.1.1', port=5007):
        self.multicast_group = group
        self.port = port
        self.sock = None
        self.running = False
    
    def join_group(self):
        """
        Tham gia multicast group
        """
        try:
            # Tạo UDP socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            
            # Cho phép reuse address (để nhiều client cùng máy có thể join)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind đến port multicast
            # Windows: bind đến '' (empty string) 
            # Linux/Mac: bind đến multicast group
            if sys.platform == 'win32':
                self.sock.bind(('', self.port))
            else:
                self.sock.bind((self.multicast_group, self.port))
            
            # Join multicast group
            mreq = struct.pack('4sl', socket.inet_aton(self.multicast_group), socket.INADDR_ANY)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            
            print(f"Joined multicast group: {self.multicast_group}:{self.port}")
            print(f"Listening for radio stream...")
            print(f"   Press Ctrl+C to stop\n")
            
            return True
            
        except Exception as e:
            print(f"Error joining multicast group: {e}")
            return False
    
    def receive_stream(self, save_to_file=None, duration_seconds=None, play_audio=True, sample_rate=16000, channels=1):
        """
        Nhận stream từ server
        
        Args:
            save_to_file: Đường dẫn file để lưu (nếu muốn lưu)
            duration_seconds: Thời gian nhận (None = vô hạn)
        """
        if not self.sock:
            print("Not connected. Call join_group() first.")
            return
        
        self.running = True
        received_bytes = 0
        packet_count = 0
        start_time = time.time()
        
        file_handle = None
        if save_to_file:
            try:
                file_handle = open(save_to_file, 'wb')
                print(f"Saving stream to: {save_to_file}")
            except Exception as e:
                print(f"Warning: Cannot save to file: {e}")

        audio_stream = None
        if play_audio and HAS_SD:
            try:
                audio_stream = sd.RawOutputStream(
                    samplerate=sample_rate,
                    channels=channels,
                    dtype="int16"
                )
                audio_stream.start()
                print("🔊 Live audio playback enabled")
            except Exception as e:
                print(f"Audio playback disabled: {e}")
                audio_stream = None
        elif play_audio and not HAS_SD:
            print("sounddevice not installed. Live playback disabled.")
        
        try:
            while self.running:
                # Check duration
                if duration_seconds:
                    elapsed = time.time() - start_time
                    if elapsed >= duration_seconds:
                        print(f"\nDuration reached: {duration_seconds}s")
                        break
                
                # Set timeout để có thể check Ctrl+C
                self.sock.settimeout(1.0)
                
                try:
                    data, addr = self.sock.recvfrom(4096)
                    
                    if data:
                        received_bytes += len(data)
                        packet_count += 1
                        
                        # Live playback (PCM)
                        if audio_stream:
                            try:
                                audio_stream.write(data)
                            except Exception:
                                pass

                        # Lưu vào file nếu có
                        if file_handle:
                            file_handle.write(data)
                        
                        # Hiển thị progress
                        if packet_count % 50 == 0:
                            elapsed = time.time() - start_time
                            rate = received_bytes / elapsed / 1024 if elapsed > 0 else 0
                            print(f"Receiving... {received_bytes/1024:.1f} KB ({rate:.1f} KB/s) - {packet_count} packets", end='\r')
                            
                except socket.timeout:
                    # Timeout - check if still running
                    continue
                    
        except KeyboardInterrupt:
            print(f"\n\nStopped by user")
        finally:
            if audio_stream:
                try:
                    audio_stream.stop()
                    audio_stream.close()
                except Exception:
                    pass
            if file_handle:
                file_handle.close()
                print(f"Saved {received_bytes/1024:.1f} KB to {save_to_file}")
            
            self.running = False
            elapsed = time.time() - start_time
            print(f"\nSummary:")
            print(f"   Total received: {received_bytes/1024:.1f} KB")
            print(f"   Packets: {packet_count}")
            print(f"   Duration: {elapsed:.1f}s")
            if elapsed > 0:
                print(f"   Avg rate: {received_bytes/elapsed/1024:.1f} KB/s")
    
    def leave_group(self):
        """Rời khỏi multicast group"""
        if self.sock:
            try:
                # Leave multicast group
                mreq = struct.pack('4sl', socket.inet_aton(self.multicast_group), socket.INADDR_ANY)
                self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
                self.sock.close()
                print(f"Left multicast group: {self.multicast_group}")
            except Exception as e:
                print(f"Error leaving group: {e}")
            finally:
                self.sock = None

    def stop(self):
        """Dừng nhận stream"""
        self.running = False
        self.leave_group()
    
    def __enter__(self):
        self.join_group()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.leave_group()


def interactive_mode():
    """Chế độ tương tác với menu"""
    print("=" * 60)
    print("  MULTICAST RADIO CLIENT")
    print("  Listen to radio stream from File Share Network")
    print("=" * 60)
    print()
    
    # Cấu hình kết nối
    group = input("Multicast Group [224.1.1.1]: ").strip() or '224.1.1.1'
    port = input("Port [5007]: ").strip()
    port = int(port) if port else 5007
    
    print()
    print("Options:")
    print("  1. Listen only (stream to console)")
    print("  2. Listen and save to file")
    print("  3. Listen for specific duration")
    print()
    
    choice = input("Choose option [1]: ").strip() or '1'
    
    save_file = None
    duration = None
    
    if choice == '2':
        save_file = input("Save to file [received_stream.mp3]: ").strip() or 'received_stream.mp3'
    elif choice == '3':
        duration = input("Duration in seconds [30]: ").strip()
        duration = int(duration) if duration else 30
        save_file = input("Save to file (optional): ").strip() or None
    
    print()
    
    # Start client
    with MulticastRadioClient(group=group, port=port) as client:
        client.receive_stream(save_to_file=save_file, duration_seconds=duration, play_audio=True)


if __name__ == "__main__":
    interactive_mode()