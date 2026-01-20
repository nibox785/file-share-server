from __future__ import annotations

import json
import socket
import struct
import threading
from typing import Optional

import sounddevice as sd


class VoiceCallClient:
    def __init__(
        self,
        host: str,
        port: int,
        room: str,
        username: str,
        sample_rate: int = 16000,
        channels: int = 1,
        sample_width: int = 2,
        chunk_frames: int = 1024,
        play_audio: bool = True,
        capture_audio: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.room = room
        self.username = username
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width
        self.chunk_frames = chunk_frames
        self.play_audio = play_audio
        self.capture_audio = capture_audio

        self._sock: Optional[socket.socket] = None
        self._running = False
        self._recv_thread: Optional[threading.Thread] = None
        self._input_stream: Optional[sd.RawInputStream] = None
        self._output_stream: Optional[sd.RawOutputStream] = None

    def _send_packet(self, payload: bytes) -> bool:
        if not self._sock:
            return False
        try:
            self._sock.sendall(struct.pack("!I", len(payload)) + payload)
            return True
        except Exception:
            return False

    def _recv_exact(self, size: int) -> bytes:
        data = b""
        while len(data) < size:
            chunk = self._sock.recv(size - len(data))
            if not chunk:
                return b""
            data += chunk
        return data

    def _recv_packet(self) -> bytes:
        header = self._recv_exact(4)
        if not header:
            return b""
        length = struct.unpack("!I", header)[0]
        if length <= 0:
            return b""
        return self._recv_exact(length)

    def _recv_loop(self):
        try:
            while self._running:
                data = self._recv_packet()
                if not data:
                    break
                if self.play_audio and self._output_stream:
                    self._output_stream.write(data)
        except Exception:
            pass

    def _on_audio(self, indata, frames, time, status):
        if not self._running or not self.capture_audio:
            return
        self._send_packet(bytes(indata))

    def start(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((self.host, self.port))

        join = json.dumps({"type": "join", "room": self.room, "username": self.username}).encode("utf-8")
        self._send_packet(join)

        self._running = True

        if self.play_audio:
            self._output_stream = sd.RawOutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                blocksize=self.chunk_frames,
            )
            self._output_stream.start()

        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()

        if self.capture_audio:
            self._input_stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                blocksize=self.chunk_frames,
                callback=self._on_audio,
            )
            self._input_stream.start()

    def stop(self):
        self._running = False
        try:
            if self._input_stream:
                self._input_stream.stop()
                self._input_stream.close()
        except Exception:
            pass
        try:
            if self._output_stream:
                self._output_stream.stop()
                self._output_stream.close()
        except Exception:
            pass
        try:
            if self._sock:
                self._sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            if self._sock:
                self._sock.close()
        except Exception:
            pass
        self._sock = None
