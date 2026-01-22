import socket
import struct
import time
import os
import wave
import threading
import audioop
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
        self.audio_file = settings.RADIO_AUDIO_FILE
        self.source = settings.RADIO_SOURCE
        self._lock = threading.Lock()
        self._change_requested = False
    
    def start(self, audio_file: str = None, source: str = "auto"):
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
            if audio_file:
                self.audio_file = audio_file
            self.source = source or self.source
            print(f"   Audio: {self.audio_file}")
            
            self.running = True

            while self.running:
                with self._lock:
                    source = self.source
                    audio_file = self.audio_file
                    self._change_requested = False

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

                if not self.running:
                    break
                
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
                rate_state = None
                target_rate = settings.RADIO_SAMPLE_RATE
                target_channels = settings.RADIO_CHANNELS
                target_width = settings.RADIO_SAMPLE_WIDTH

                while self.running:
                    if self._change_requested:
                        return
                    data = wf.readframes(chunk_frames)
                    if not data:
                        wf.rewind()
                        print("Looping audio...")
                        continue

                    # Normalize WAV to configured output format (PCM int16, mono, target sample rate)
                    out = data
                    out_width = width
                    out_channels = channels
                    out_rate = rate

                    if out_width != target_width:
                        out = audioop.lin2lin(out, out_width, target_width)
                        out_width = target_width

                    if out_channels != target_channels:
                        # Downmix to mono if needed
                        out = audioop.tomono(out, out_width, 0.5, 0.5) if out_channels > 1 else out
                        out_channels = target_channels

                    if out_rate != target_rate:
                        out, rate_state = audioop.ratecv(
                            out,
                            out_width,
                            out_channels,
                            out_rate,
                            target_rate,
                            rate_state,
                        )
                        out_rate = target_rate

                    self.sock.sendto(out, (self.multicast_group, self.port))
                    chunk_count += 1
                    if chunk_count % 100 == 0:
                        print(f"Sent {chunk_count} chunks")

                    # Sleep based on output frames to keep realtime pace
                    out_frames = len(out) / float(out_width * out_channels) if out_width and out_channels else chunk_frames
                    time.sleep(out_frames / float(out_rate))
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
                    if self._change_requested:
                        return
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
                if self._change_requested:
                    return
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

    def request_source(self, source: str, audio_file: str | None = None):
        with self._lock:
            if audio_file:
                self.audio_file = audio_file
            if source:
                self.source = source
            self._change_requested = True

_RADIO_SERVER: MulticastRadioServer | None = None


def start_multicast_server(audio_file: str = None):
    """Helper function để start multicast server"""
    global _RADIO_SERVER
    server = MulticastRadioServer()
    _RADIO_SERVER = server
    server.start(audio_file or settings.RADIO_AUDIO_FILE, source=settings.RADIO_SOURCE)


def set_radio_source(source: str, audio_file: str | None = None) -> bool:
    if _RADIO_SERVER:
        _RADIO_SERVER.request_source(source, audio_file=audio_file)
        return True
    return False