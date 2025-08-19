import json
import time
from pathlib import Path

import librosa
import numpy as np

from dancer.src.music_player import MusicPlayer
from src.logging_utils import Logger
from src.settings import Settings

from mimetic.src.threads.blossom_sender import BlossomSenderThread



class BeatDetector:

    def __init__(self, logger: Logger, settings: Settings):
        self.logger = logger
        self.settings = settings
        self.current_music_path: str
        self.current_music_duration: float
        self.MusicPlayer = MusicPlayer(logger)
        self.is_running = False
        self.analysis_interval = 5
        self.current_sequence = None
        self.blossom_sender_thread = BlossomSenderThread(host=self.host, port=self.port, logger=self.logger)



    def change_music(self, music_path: str):
        self.current_music_path = music_path
        self.current_music_duration = librosa.get_duration(filename=music_path)
        self.logger(f"[Dancer] Now playing: {Path(music_path).name} ({self.current_music_duration:.1f}s)", level="info")
        MusicPlayer.play(music_path)
        self.analyse_music(music_path)

    def analyse_music(self, music_path: str) -> dict:
        current_time = 0.0


        try:
            while self.is_running and current_time < self.current_music_duration:
                segment_duration = min(self.analysis_interval, self.current_music_duration - current_time)
                sequence = self.analyze_music_segment(music_path=music_path, offset=current_time,
                                                      duration=segment_duration)

                if sequence != self.current_sequence:
                    duration = self.get_sequence_duration(sequence)
                    if duration is not None:
                        payload = {"sequence": sequence, "duration": duration}
                        self.blossom_sender_thread.send(payload)
                        self.current_sequence = sequence
                        self.logger(f"[Dancer] Mood -> '{sequence}', ({duration:.2f})s", level="debug")
                    else:
                        self.logger(f"[Dancer] Could not find duration for '{sequence}'", level="warning")

                time.sleep(segment_duration)
                current_time += segment_duration
        except Exception as e:
            pass

    def analyze_music_segment(self, music_path, offset, duration):
        y, sr = librosa.load(music_path, offset=offset, duration=duration)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        energy = float(np.sum(np.abs(y)) / y.size)
        tempo_scalar = float(tempo)
        self.logger(f"[Dancer] Segment @ {offset:.1f}s - BPM: {tempo_scalar:.2f}, Energy: {energy:.4f}", level="debug")
        return "happy" if tempo_scalar > 100 and energy > 0.1 else "sad"

    def get_sequence_duration(self, sequence):
        try:
            with open(f"blossom_public/src/sequences/woody/{sequence}_sequence.json", "r") as file:
                sequence_json = json.load(file)
            last_frame = sequence_json["frame_list"][-1]
            last_millis = last_frame["millis"]
            return float(last_millis) / 1000.0
        except Exception as e:
            self.logger(f"[ERROR] Failed to get sequence duration: {e}", level="critical")
        return 2.0
