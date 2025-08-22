import json
import time
from pathlib import Path

import librosa
import numpy as np

from dancer.src.music_player import MusicPlayer
from src.logging_utils import Logger
from src.settings import Settings
import sounddevice as sd


from src.threads.blossom_sender import BlossomSenderThread



class BeatDetector:

    def __init__(self, logger: Logger):
        self.logger = logger
        self.current_music_path: str = ""
        self.current_music_duration: float = 0.0
        self.MusicPlayer = MusicPlayer(logger)
        self.is_running = False
        self.analysis_interval = 5
        self.current_sequence = None
        self.blossom_one_sender = self.blossom_two_sender = None
        self.is_sending_one = self.is_sending_two = False



    def change_music(self, music_path: str):
        self.current_music_path = music_path
        self.current_music_duration = librosa.get_duration(filename=music_path)
        self.logger(f"[Dancer] Now playing: {Path(music_path).name} ({self.current_music_duration:.1f}s)", level="info")
        self.analyse_music(music_path)

    def analyse_music(self, music_path: str, blossom_sender: BlossomSenderThread) -> dict:
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
                        blossom_sender.send(payload)
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