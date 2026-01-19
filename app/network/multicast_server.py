import socket
import struct
import time
import os
import wave
from app.core.config import settings

try:
    import sounddevice as sd
    HAS_SD = True
except Exception:
    HAS_SD = False

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
    
    def start(self, audio_file="static/audio/sample.wav", source: str = "auto"):
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

            # Decide source
            if source == "auto":
                source = "mic" if HAS_SD else "wav"

            if source == "mic":
                if not HAS_SD:
                    print("sounddevice not available. Falling back to dummy stream.")
                    self.stream_dummy_audio()
                else:
                    self.stream_microphone()
            elif source == "wav":
                if not os.path.exists(audio_file):
                    print(f"Audio file not found: {audio_file}")
                    print("   Creating dummy audio stream...")
                    self.stream_dummy_audio()
                else:
                    self.stream_wav_file(audio_file)
            else:
                self.stream_dummy_audio()
                
        except Exception as e:
            print(f"Multicast server error: {e}")
        finally:
            self.stop()
    
    def stream_wav_file(self, audio_file):
        """Stream file WAV thật (PCM)"""
        try:
            with wave.open(audio_file, "rb") as wf:
                channels = wf.getnchannels()
                rate = wf.getframerate()
                width = wf.getsampwidth()
                print(f"WAV format: {channels}ch, {rate}Hz, {width*8}bit")

                if channels != settings.RADIO_CHANNELS or rate != settings.RADIO_SAMPLE_RATE or width != settings.RADIO_SAMPLE_WIDTH:
                    print("⚠️  WAV format differs from RADIO_* settings; playback might be distorted.")

                chunk_frames = settings.RADIO_CHUNK_FRAMES
                chunk_count = 0

                while self.running:
                    data = wf.readframes(chunk_frames)
                    if not data:
                        wf.rewind()
                        print("Looping audio...")
                        continue

                    self.sock.sendto(data, (self.multicast_group, self.port))
                    chunk_count += 1
                    if chunk_count % 100 == 0:
                        print(f"Sent {chunk_count} chunks")

                    time.sleep(chunk_frames / float(rate))
        except Exception as e:
            print(f"Error streaming WAV audio: {e}")

    def stream_microphone(self):
        """Stream live microphone audio (PCM int16)"""
        if not HAS_SD:
            print("sounddevice not installed. Cannot stream microphone.")
            return

        rate = settings.RADIO_SAMPLE_RATE
        channels = settings.RADIO_CHANNELS
        frames = settings.RADIO_CHUNK_FRAMES

        try:
            with sd.RawInputStream(
                samplerate=rate,
                channels=channels,
                dtype="int16",
                blocksize=frames,
            ) as stream:
                print("🎙️  Live microphone streaming started")
                chunk_count = 0
                while self.running:
                    data, _ = stream.read(frames)
                    if data:
                        self.sock.sendto(data, (self.multicast_group, self.port))
                        chunk_count += 1
                        if chunk_count % 100 == 0:
                            print(f"Streaming mic... ({chunk_count} packets)")
        except Exception as e:
            print(f"Error streaming microphone: {e}")
    
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
    server.start(audio_file, source=settings.RADIO_SOURCE)