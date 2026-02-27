from pathlib import Path
from typing import Optional
import threading

import numpy as np
import librosa
import sounddevice as sd

from src.logging_utils import Logger


class MusicPlayer:
    def __init__(self, logger: Logger, target_sr: int = 22050):
        """
        Initialize the MusicPlayer.

        :param logger: Logger instance for logging messages
        :param target_sr: Target sampling rate for audio playback
        """
        self.logger = logger
        self.current_music_path: Optional[str] = None
        self.is_running: bool = False
        self._target_sr = int(target_sr)

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def play(self, music_path: str):
        """
        Play an audio file in a separate thread. Stops any currently playing audio.

        :param music_path: Path to the audio file to play
        """
        self.stop()

        self.current_music_path = music_path
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=False)
        self.logger("[MusicPlayer] Starting thread", level="debug")
        self._thread.start()

    def stop(self):
        """
        Stop the current audio playback and terminate the playback thread.
        """
        self._stop_event.set()
        try:
            sd.stop()
        except Exception as e:
            self.logger(f"[MusicPlayer] Exception raised: {e}", level="error")
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        if self.is_running:
            self.logger("[MusicPlayer] Stopped.", level="info")
        self.is_running = False

    def _worker(self):
        """
        Worker thread that handles the actual audio playback.
        Loads the audio file using librosa and plays it with sounddevice.
        """
        path = self.current_music_path
        if not path:
            return
        try:
            y, sr = librosa.load(path, sr=self._target_sr, mono=True)
            if y.size == 0:
                self.logger(f"[MusicPlayer] Empty audio: {Path(path).name}", level="warning")
                return

            if self._stop_event.is_set():
                return

            sd.default.channels = 1
            self.logger(f"[MusicPlayer] Playing: {Path(path).name}", level="info")
            self.is_running = True

            sd.play(y.astype(np.float32, copy=False), sr)
            while not self._stop_event.is_set() and sd.get_stream().active:
                sd.wait()
            sd.stop()

        except Exception as e:
            self.logger(f"[MusicPlayer] Playback error on '{Path(path).name}': {e}", level="error")
        finally:
            self.is_running = False