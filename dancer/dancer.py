import os
import threading
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
    def __init__(self, music_dir: str, logger: Logger, mode: Literal["mic", "audio"], analysis_interval: float = 5.0, sr = 22050):
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
        self.beat_detector = BeatDetector(logger=logger, sr = sr)
        self.blossom_one_sender = self.blossom_two_sender = None
        self.is_sending_one = self.is_sending_two = False
        self.mode = mode
        self._thread = None
        self._stop_event = threading.Event()

    def _main_loop(self):
        run = self.run_for_mic if self.mode == "mic" else self.run_for_audio
        self.logger("[Dancer] Launching Dancer...", level="info")
        while self.is_running:
            sequence = run()
            if sequence != self.current_sequence:
                duration = self.get_sequence_duration(sequence)
                if duration is not None:
                    payload = {"sequence": sequence, "duration": duration}

                    if self.is_sending_one:
                        self.blossom_one_sender.send(payload)
                    if self.is_sending_two:
                        self.blossom_two_sender.send(payload)

                    self.current_sequence = sequence
                    self.logger(f"[BeatDetector] Mood -> '{sequence}', ({duration:.2f})s", level="debug")
                else:
                    self.logger(f"[BeatDetector] Could not find duration for '{sequence}'", level="warning")

        self.is_running = True

        self.beat_detector.analyse_microphone()


    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._main_loop, daemon=True)
            self._thread.start()
            self.logger("[Dancer] Thread started.", level="info")
        else:
            self.logger("[Dancer] Start called, but already running.", level="warning")

    def stop(self):
        self.logger("[Dancer] Stopping...", level="info")
        self.current_sequence = None
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join()
        self.is_running = False


    def get_sequence_duration(self, sequence):
        try:
            with open(f"blossom_public/src/sequences/woody/{sequence}_sequence.json", "r") as file:
                sequence_json = json.load(file)
            last_frame = sequence_json["frame_list"][-1]
            last_millis = last_frame["millis"]
            return float(last_millis) / 1000.0
        except Exception as e:
            self.logger(f"[ERROR] Failed to get sequence duration: {e}", level="critical")
        return None


    def run_for_mic(self) -> str:
        return self.beat_detector.analyse_microphone()

    def run_for_audio(self) -> str:
        """
        Run analysis for all songs in music_dir and return the last detected sequence.
        """
        music_dir_path = Path(self.music_dir)

        if not music_dir_path.exists() or not music_dir_path.is_dir():
            self.logger(f"[Dancer] Music directory not found: {self.music_dir}", level="error")
            return ""

        last_sequence = ""
        for music_path in music_dir_path.glob("*.mp3"):
            self.logger(f"[Dancer] Analyzing music file: {music_path.name}", level="info")
            sequences = self.beat_detector.analyse_music(str(music_path))
            if sequences:
                last_sequence = list(sequences.values())[-1]

        return last_sequence

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

