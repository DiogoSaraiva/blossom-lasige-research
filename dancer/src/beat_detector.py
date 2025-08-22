from pathlib import Path
from typing import Optional, Dict, Tuple, List

import librosa
import numpy as np
import sounddevice as sd

from src.logging_utils import Logger


class BeatDetector:

    def __init__(self, logger: Logger, mic_sr: int = 22050, analysis_interval: float = 5.0):
        self.logger = logger
        self.current_music_path: str = ""
        self.current_music_duration: float = 0.0
        self.analysis_interval = analysis_interval
        self.current_sequence = None
        self.mic_sr = mic_sr

    def change_music(self, music_path: str):
        self.current_music_path = music_path
        self.current_music_duration = librosa.get_duration(filename=music_path)

    def analyse_music(self, music_path: Optional[str] = None) -> List[Tuple[float, float, str]]:
        if music_path:
            self.change_music(music_path)
        if not self.current_music_path:
            return []

        schedule: List[Tuple[float, float, str]] = []
        current_time = 0.0
        try:
            while current_time < self.current_music_duration - 1e-6:
                segment_duration = min(self.analysis_interval, self.current_music_duration - current_time)
                sequence = self.analyze_music_segment(
                    music_path=self.current_music_path,
                    offset=current_time,
                    duration=segment_duration,
                )
                schedule.append((current_time, float(segment_duration), sequence))
                current_time += float(segment_duration)
        except Exception as e:
            self.logger(
                f"[BeatDetector] Exception while analysing music - {Path(self.current_music_path).name}: {e}",
                level="error",
            )

        return schedule

    def analyze_music_segment(self, music_path, offset, duration) -> str:
        y, sr = librosa.load(music_path, offset=offset, duration=duration)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        energy = float(np.sum(np.abs(y)) / y.size)
        self.logger(f"[BeatDetector] Segment @ {offset:.1f}s - BPM: {float(tempo):.2f}, Energy: {energy:.4f}", level="debug")
        return "happy" if float(tempo) > 100 and energy > 0.1 else "sad"

    def analyse_microphone(self) -> Optional[str]:
        """
        Continuously capture audio from the microphone and detect mood changes.
        Runs until self.is_running = False
        """
        # Record audio for analysis_interval seconds
        recording = sd.rec(int(self.analysis_interval * self.mic_sr), samplerate=self.mic_sr, channels=1, dtype="float32")
        sd.wait()

        # Process audio
        y = recording.flatten()
        tempo, _ = librosa.beat.beat_track(y=y, sr=self.mic_sr)
        energy = np.mean(np.abs(y))

        # Detect mood
        if float(tempo) > 100 and energy > 0.1:
            sequence = "happy"
        else:
            sequence = "sad"

        # Only update if mood changes
        if sequence != self.current_sequence:
            self.current_sequence = sequence
            self.logger(f"[BeatDetector] Mood changed -> '{sequence}'", level="info")

            return sequence

        self.logger(f"[BeatDetector] Mood unchanged: '{sequence}'", level="debug")
        return None