import os
import time
from pathlib import Path
from typing import Literal

import librosa
import numpy as np
import requests
import sounddevice as sd


import json

from dancer.src.beat_detector import BeatDetector
from src.logging_utils import Logger
from src.threads.blossom_sender import BlossomSenderThread


class Dancer:
    def __init__(self, music_dir: str, logger: Logger, analysis_interval: float = 5.0):
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
        self.logger = logger
        self.beat_detector = BeatDetector(logger=logger)
        self.blossom_one_sender = self.blossom_two_sender = None
        self.is_sending_one = self.is_sending_two = False




    def start(self, blossom_sender: BlossomSenderThread):
        """Start the dancer and continuously adjust mood based on the music."""
        self.logger("[Dancer] Launching Dancer...", level="info")
        blossom_sender.start()
        self.is_running = True

        self.beat_detector.analyse_microphone()

        blossom_sender.stop()



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

