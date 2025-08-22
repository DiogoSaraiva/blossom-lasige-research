from pathlib import Path
from typing import Optional, Dict

import librosa
import numpy as np
import sounddevice as sd

from dancer.src.music_player import MusicPlayer
from src.logging_utils import Logger


class BeatDetector:

    def __init__(self, logger: Logger, sr: int):
        self.logger = logger
        self.current_music_path: str = ""
        self.current_music_duration: float = 0.0
        self.MusicPlayer = MusicPlayer(logger)
        self.is_running = False
        self.analysis_interval = 5
        self.current_sequence = None
        self.blossom_one_sender = self.blossom_two_sender = None
        self.is_sending_one = self.is_sending_two = False
        self.sr = sr

    def change_music(self, music_path: str):
        self.current_music_path = music_path
        self.current_music_duration = librosa.get_duration(filename=music_path)
        self.logger(f"[BeatDetector] Now playing: {Path(music_path).name} ({self.current_music_duration:.1f}s)", level="info")
        self.analyse_music(music_path)

    def analyse_music(self, music_path: str) -> Dict[float, str]:
        current_time = 0.0
        result = {}
        try:
            while current_time < self.current_music_duration:
                segment_duration = min(self.analysis_interval, self.current_music_duration - current_time)
                sequence = self.analyze_music_segment(music_path=music_path, offset=current_time,
                                                      duration=segment_duration)

                current_time += segment_duration
                result[current_time] = sequence
        except Exception as e:
            self.logger(f"[BeatDetector] Exception while analysing music: {e}", level="error")

        return result

    def analyze_music_segment(self, music_path, offset, duration) -> str:
        y, sr = librosa.load(music_path, offset=offset, duration=duration)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        energy = float(np.sum(np.abs(y)) / y.size)
        tempo_scalar = float(tempo)
        self.logger(f"[BeatDetector] Segment @ {offset:.1f}s - BPM: {tempo_scalar:.2f}, Energy: {energy:.4f}", level="debug")
        return "happy" if tempo_scalar > 100 and energy > 0.1 else "sad"


    def analyse_microphone(self) -> Optional[str]:
        """
        Continuously capture audio from the microphone and detect mood changes.
        Runs until self.is_running = False
        """
        self.logger(f"[BeatDetector] Starting microphone analysis loop...", level="info")
        self.current_sequence = None

        # Record audio for analysis_interval seconds
        recording = sd.rec(int(self.analysis_interval * self.sr), samplerate=self.sr, channels=1, dtype="float32")
        sd.wait()

        # Process audio
        y = recording.flatten()
        tempo, _ = librosa.beat.beat_track(y=y, sr=self.sr)
        energy = np.mean(np.abs(y))

        # Detect mood
        if tempo > 100 and energy > 0.1:
            sequence = "happy"
        else:
            sequence = "sad"

        # Only update if mood changes
        if sequence != self.current_sequence:
            self.current_sequence = sequence
            self.logger(f"[BeatDetector] Mood changed -> '{sequence}'", level="info")

            return sequence

        else:
            self.logger(f"[BeatDetector] Mood unchanged: '{sequence}'", level="debug")

        self.logger("[BeatDetector] BeatDetector stopped.", level="info")
        return None