from pathlib import Path

from src.logging_utils import Logger


class MusicPlayer:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.current_music_path = None
        self.is_playing = False

    def change_music(self, music_path):
        self.logger(f"[MusicPlayer] Changing music path to: {music_path}...")
        self.current_music_path = music_path

    def play(self):
        self.is_playing = True
        self.logger(f"[MusicPlayer] Playing music: {Path(self.current_music_path).name}...", level="info")

    def stop(self):
        self.is_playing = False
