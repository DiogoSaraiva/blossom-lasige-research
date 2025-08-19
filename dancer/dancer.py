import os
import time
from pathlib import Path

import librosa
import numpy as np
import requests
import sounddevice as sd


import json

from src.logging_utils import Logger
from mimetic.src.threads.blossom_sender import BlossomSenderThread


class Dancer:
    def __init__(self, host: str, port: int, music_dir: str, logger: Logger, blossom_sender: BlossomSenderThread = None, analysis_interval: float = 5.0):
        """
        :param music_dir: Path to the music directory
        :param analysis_interval: Interval in seconds to re-analyze mood
        """
        self._player_lock = None
        self._player_backend = None
        self.music_dir = music_dir
        self.analysis_interval = analysis_interval
        self.dancer_server_proc = None
        self.current_sequence = None
        self.is_running = False
        self.host = host
        self.port = port
        self.logger = logger
        self.blossom_sender_thread = blossom_sender or BlossomSenderThread(host=self.host, port=self.port, logger = self.logger, mode = "sequence")


    def analyse_music(self, music_path: str):
        """Analyse music file in segments and send mood-based sequences."""
        music_duration = librosa.get_duration(path=music_path)
        current_time = 0.0

        self.logger(f"[Dancer] Now playing: {Path(music_path).name} ({music_duration:.1f}s)", level="info")

        try:
            while self.is_running and current_time < music_duration:
                segment_duration = min(self.analysis_interval, music_duration - current_time)
                sequence = self.analyze_music_segment(music_path=music_path, offset=current_time,
                                                      duration=segment_duration)

                if sequence != self.current_sequence:
                    duration = self._get_sequence_duration(sequence)
                    if duration is not None:
                        payload = {"sequence": sequence, "duration": duration}
                        self.blossom_sender_thread.send(payload)
                        self.current_sequence = sequence
                        self.logger(f"[Dancer] Mood -> '{sequence}', ({duration:.2f})s", level="debug")

                current_time += segment_duration
                time.sleep(segment_duration)
        except Exception as e:
            pass

    def start(self):
        """Start the dancer and continuously adjust mood based on the music."""
        self.logger("[Dancer] Launching Dancer...", level="info")
        self.blossom_sender_thread.start()
        self.is_running = True

        for music_file in os.listdir(self.music_dir):
            if not self.is_running:
                break

            music_file_path = os.path.join(self.music_dir, music_file)
            self.analyse_music(music_file_path)

        self.stop()

    def send_sequence(self, sequence_str: str) -> bool:
        """Send sequence directly to the Dancer server (bypassing BlossomSenderThread)."""
        url = f"http://{self.host}:{self.port}/sequence"
        self.logger(f"[Dancer] Sending sequence to {url}: {sequence_str}", level="info")

        try:
            response = requests.post(url, data=sequence_str)
            if response.status_code == 200:
                self.logger(f"[Dancer] Sequence '{sequence_str}' sent successfully!", level="debug")
                return True
            else:
                self.logger(f"[Dancer] Received status code {response.status_code}", level="error")
                return False
        except requests.exceptions.RequestException as e:
            self.logger(f"[ERROR] Failed to send sequence '{sequence_str}': {e}", level="error")
            return False

    def stop(self):
        """Stop the dancer and shut down the sender thread."""
        if not self.is_running:
            return

        self.is_running = False
        try:
            self.blossom_sender_thread.stop()
            self.blossom_sender_thread.join(timeout=1.0)
        except Exception as e:
            self.logger(f"[Dancer] Error stopping sender thread: {e}", level="error")

        self.logger("[Dancer] Stopped.", level="info")


    def _stop_music(self):
        pass

    def _get_sequence_duration(self, sequence: str) -> float:
        """Return sequence duration in seconds (mock for now)."""
        if sequence == "happy":
            return 3.0
        elif sequence == "sad":
            return 5.0
        else:
            return 0.0



    def analyze_music_segment(self, music_path: str, offset: float, duration: float) -> str:
        """Analyze a segment of the music and return mood as sequence name."""
        y, sr = librosa.load(music_path, offset=offset, duration=duration)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        energy = np.mean(np.abs(y))

        self.logger(f"[Dancer] Segment @ {offset:.1f}s - BPM: {tempo:.2f}, Energy: {energy:.4f}", level="debug")

        if tempo > 100 and energy > 0.1:
            return "happy"
        else:
            return "sad"

    def analyse_microphone(self, sr: int = 22050):
        """
        Continuously capture audio from the microphone and detect mood changes.
        Runs until self.is_running = False
        """
        self.logger(f"[DancerMic] Starting microphone analysis loop...", level="info")
        self.is_running = True
        self.current_sequence = None

        while self.is_running:
            # Record audio for analysis_interval seconds
            recording = sd.rec(int(self.analysis_interval * sr), samplerate=sr, channels=1, dtype="float32")
            sd.wait()

            # Process audio
            y = recording.flatten()
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            energy = np.mean(np.abs(y))

            # Detect mood
            if tempo > 100 and energy > 0.1:
                sequence = "happy"
            else:
                sequence = "sad"

            # Only update if mood changes
            if sequence != self.current_sequence:
                self.current_sequence = sequence
                self.logger(f"[Dancer] Mood changed -> '{sequence}'", level="info")

                # Send to Blossom
                self.blossom_sender_thread.send({"sequence": sequence, "duration": self.analysis_interval})

            else:
                self.logger(f"[Dancer] Mood unchanged: '{sequence}'", level="debug")

        self.logger("[Dancer] Dancer stopped.", level="info")
