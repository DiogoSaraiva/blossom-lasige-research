from pathlib import Path
from typing import Dict, List

import librosa
import numpy as np
import sounddevice as sd

from src.logging_utils import Logger
from dancer.src.dance_sequences import dance_sequence_from_data

class BeatDetector:

    def __init__(self, logger: Logger, mic_sr: int = 22050, analysis_interval: float = 5.0):
        """
        Initialize the BeatDetector.

        :param logger: Logger instance for logging messages
        :param mic_sr: Sampling rate for microphone input
        :param analysis_interval: Duration of each music segment to analyze (in seconds)
        """
        self.logger = logger
        self.current_music_path: str = ""
        self.current_music_duration: float = 0.0
        self.analysis_interval = analysis_interval
        self.mic_sr = mic_sr


    def change_music(self, music_path: str):
        """
        Change the current music track and calculate its duration.

        :param music_path: Path to the new music file
        """
        self.current_music_path = music_path
        self.current_music_duration = librosa.get_duration(path=music_path)

    def analyse_music(self) -> List[Dict[str, str | float]]:
        """
        Analyze the entire music track by splitting it into segments
        and detecting tempo and energy for each segment.

        :return: List of dictionaries containing 'sequence' and 'mood_duration' per segment
        """
        schedule: List[Dict[str, str | float]] = []
        current_time = 0.0
        try:
            while current_time < self.current_music_duration:
                segment_duration = min(self.analysis_interval, self.current_music_duration - current_time)
                sequence = self.analyze_music_segment(offset=current_time, duration=segment_duration)
                schedule.append({"sequence": sequence, "mood_duration": segment_duration})
                current_time += segment_duration
        except Exception as e:
            self.logger(f"[BeatDetector] Exception while analysing music - {Path(self.current_music_path).name}: {e}", level="error")

        return schedule

    def analyze_music_segment(self, offset, duration) -> str:
        """
        Analyze a segment of the current music track to detect tempo and energy.

        :param offset: Start time of the segment in seconds
        :param duration: Duration of the segment in seconds
        :return: Dance sequence name based on detected tempo and energy
        """
        y, sr = librosa.load(self.current_music_path, offset=offset, duration=duration, mono=True)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        energy = float(np.sum(np.abs(y)) / y.size)
        self.logger(f"[BeatDetector] Segment @ {offset:.1f}s - BPM: {float(tempo):.2f}, Energy: {energy:.4f}", level="debug")
        return dance_sequence_from_data(tempo=float(tempo), energy=energy)

    def analyse_microphone(self) -> Dict[str, str | float]:
        """
        Continuously capture audio from the microphone and detect mood changes.
        """
        # Record audio for analysis_interval seconds
        recording = sd.rec(frames=int(self.analysis_interval * self.mic_sr), samplerate=self.mic_sr, channels=1, dtype="float32")
        sd.wait()

        # Process audio
        y = recording.flatten()
        tempo, _ = librosa.beat.beat_track(y=y, sr=self.mic_sr)
        energy = float(np.mean(np.abs(y)))

        # Detect mood
        sequence = dance_sequence_from_data(tempo=float(tempo), energy=energy)

        self.logger(f"[BeatDetector] Tempo: {float(tempo):.2f} - Energy: {energy:.4f}", level="debug")

        return {"sequence": sequence, "mood_duration": self.analysis_interval}