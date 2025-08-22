import os
import time
from pathlib import Path
from typing import Literal

import librosa
import numpy as np
import requests
import sounddevice as sd


import json

from src.logging_utils import Logger
from src.threads.blossom_sender import BlossomSenderThread


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
        self.blossom_one_sender = None
        self.blossom_two_sender = None
        self.is_sending_one = False
        self.is_sending_two = False


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

    def start(self, blossom_sender: BlossomSenderThread):
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



    def stop(self, blossom_sender: BlossomSenderThread):
        """Stop the dancer and shut down the sender thread."""
        if not self.is_running:
            return

        self.is_running = False
        try:
            blossom_sender.stop()
            blossom_sender.join(timeout=1.0)
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
                if self.is_sending_one:
                    self.blossom_one_sender.send(sequence)
                if self.is_sending_two:
                    self.blossom_two_sender.send(sequence)



            else:
                self.logger(f"[Dancer] Mood unchanged: '{sequence}'", level="debug")

        self.logger("[Dancer] Dancer stopped.", level="info")

    def update_sender(self, number: Literal["one", "two"], blossom_sender: BlossomSenderThread | None):
        setattr(self, f"blossom_{number}_sender", blossom_sender)


    def start_sending(self, blossom_sender: BlossomSenderThread, number: Literal["one", "two"]):
        if getattr(self, f"is_sending_{number}"):
            self.logger(f"[Dancer] Sending already enabled for Blossom {number}.", level="warning")
            return
        setattr(self, f"is_sending_{number}", True)
        blossom_sender.start()


    def stop_sending(self, blossom_sender: BlossomSenderThread, number: Literal["one", "two"]):
        if not getattr(self, f"is_sending_{number}"):
            self.logger(f"[Dancer] Sending not enabled for Blossom {number}.", level="warning")
            return
        setattr(self, f"is_sending_{number}", False)
        blossom_sender.stop()
        blossom_sender.join()

