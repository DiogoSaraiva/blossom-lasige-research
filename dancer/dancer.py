import json
import os
import threading
import time
from typing import Literal, Optional, Dict, List

from dancer.src.beat_detector import BeatDetector
from dancer.src.music_player import MusicPlayer
from src.logging_utils import Logger
from src.threads.blossom_sender import BlossomSenderThread


class Dancer:
    def __init__(self, music_dir: str, logger: Logger, mode: Literal["mic", "audio"], analysis_interval: float = 5.0, mic_sr = 22050):
        """
        :param music_dir: Path to the music directory
        :param logger: Logger instance for logging messages
        :param mode: Analysis mode, either "mic" or "audio"
        :param analysis_interval: Interval in seconds to re-analyze mood
        :param mic_sr: Microphone sample rate
        """
        self._run = None
        self._music_over = True
        self._music_schedule: List[Dict[str, str | float]] = []
        self._current_schedule_index = 0
        self._player_lock = None
        self._player_backend = None

        self.music_dir = music_dir
        self.analysis_interval = analysis_interval
        self.logger = logger
        self.mode = mode

        self.dancer_server_proc = None
        self.current_sequence: Optional[str] = None
        self.is_running = False

        self.beat_detector = BeatDetector(logger=logger, mic_sr=mic_sr, analysis_interval=analysis_interval)
        self.music_player = MusicPlayer(logger=logger)
        self.blossom_one_sender: Optional[BlossomSenderThread] = None
        self.blossom_two_sender: Optional[BlossomSenderThread] = None
        self.is_sending_one = False
        self.is_sending_two = False

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.resting_period = 0.01

        self._supported_extensions = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
        self._playlist: List[str] = []
        self._playlist_idx = -1
        self.loop_playlist = True

    def _refresh_playlist(self):
        """Refresh the playlist by loading all supported music files from the music directory."""
        try:
            files = [os.path.join(self.music_dir, f) for f in os.listdir(self.music_dir)]
            self._playlist = [p for p in files if os.path.splitext(p)[1].lower() in self._supported_extensions and os.path.isfile(p)]
            self._playlist.sort()
            self._playlist_idx = -1
            self.logger(f"[Dancer] Loaded {len(self._playlist)} tracks from '{self.music_dir}'.", level="info")
        except Exception as e:
            self._playlist = []
            self._playlist_idx = -1
            self.logger(f"[Dancer] Failed to load playlist: {e}", level="error")

    def _get_next_music_path(self) -> Optional[str]:
        """Return the path of the next track in the playlist, handling looping if enabled."""
        if not self._playlist:
            self._refresh_playlist()
            if not self._playlist:
                return None
        self._playlist_idx += 1
        if self._playlist_idx >= len(self._playlist):
            if self.loop_playlist:
                self._playlist_idx = 0
            else:
                return None
        return self._playlist[self._playlist_idx]

    def _main_loop(self):
        """
            Main loop of the Dancer. Plays music, analyzes mood, sends sequences to Blossoms,
            and sleeps cooperatively between iterations.
        """
        self.logger("[Dancer] Launching Dancer...", level="info")
        self.is_running = True
        while not self._stop_event.is_set() and self.is_running:
            if self._music_over and self.mode == "audio":
                next_music = self._get_next_music_path()
                if next_music:
                    self.change_music(next_music)
                    self.logger(f"[Dancer] Now playing: {os.path.basename(next_music)}", level="info")
                else:
                    self.logger("[Dancer] No tracks available. Waiting...", level="warning")
                    self._cooperative_sleep(0.5)
                    continue

            try:
                mood = self._run()
            except Exception as e:
                self.logger(f"[Dancer] Error in run loop: {e}", level="error")
                self._cooperative_sleep(self.resting_period)
                continue
            if not mood:
                self._cooperative_sleep(self.resting_period)
                continue

            sequence = mood.get("sequence")
            if not sequence:
                self._cooperative_sleep(self.resting_period)
                continue
            if sequence != self.current_sequence:
                duration_ms = self.get_sequence_duration_ms(sequence)
                if duration_ms is not None:
                    payload = {"sequence": sequence, "duration_ms": duration_ms}
                    if self.is_sending_one and self.blossom_one_sender:
                        self.blossom_one_sender.send(payload)
                    if self.is_sending_two and self.blossom_two_sender:
                        self.blossom_two_sender.send(payload)
                    self.current_sequence = sequence
                    self.logger(f"[Dancer] Mood -> '{sequence}', {duration_ms/1000:.2f}s", level="debug")
                else:
                    self.logger(f"[Dancer] Could not find duration for '{sequence}'", level="warning")

            seg = float(mood.get("mood_duration", self.analysis_interval))
            end_time = time.time() + max(0.0, seg - self.resting_period)
            while time.time() < end_time and not self._stop_event.is_set():
                self._cooperative_sleep(min(self.resting_period, end_time - time.time()))
            else:
                self._cooperative_sleep(self.resting_period)

        self.is_running = False
        self.logger("[Dancer] Loop ended.", level="debug")

    def start(self):
        """Start the Dancer thread and set the proper run method based on mode."""
        self.is_running = True
        self._run = self.run_for_mic if self.mode == "mic" else self.run_for_audio
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._main_loop, daemon=False)
            self._thread.start()
            self.logger("[Dancer] Thread started.", level="info")
        else:
            self.logger("[Dancer] Start called, but already running.", level="warning")

    def stop(self):
        """Stop the Dancer, halt music playback, and join the thread if alive."""
        self.logger("[Dancer] Stopping...", level="info")
        self.current_sequence = None
        self._stop_event.set()
        self.music_player.stop()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self.is_running = False

    def get_sequence_duration_ms(self, sequence: str) -> Optional[int]:
        """Return the duration in milliseconds of a given sequence from its JSON file."""
        try:
            with open(f"blossom_public/src/sequences/woody/{sequence}_sequence.json", "r") as file:
                sequence_json = json.load(file)
            last_frame = sequence_json["frame_list"][-1]
            return int(last_frame["millis"])
        except Exception as e:
            self.logger(f"[Dancer] Failed to get sequence duration: {e}", level="critical")
            return None

    def run_for_mic(self) -> Dict[str, str | float]:
        """Analyze mood using the microphone input."""
        return self.beat_detector.analyse_microphone()

    def run_for_audio(self) -> Optional[Dict[str, str | float]]:
        """Analyze mood based on currently playing audio tracks."""
        if not self._music_schedule:
            self._music_schedule = self.beat_detector.analyse_music()
            self._current_schedule_index = 0

        if self._current_schedule_index >= len(self._music_schedule):
            self._music_over = True
            self._music_schedule = []
            self._current_schedule_index = 0
            return None

        mood = self._music_schedule[self._current_schedule_index]
        self._current_schedule_index += 1
        return mood

    def update_sender(self, number: Literal["one", "two"], blossom_sender: Optional[BlossomSenderThread]):
        """Update the Blossom sender thread for the specified number (one or two)."""
        setattr(self, f"blossom_{number}_sender", blossom_sender)

    def start_sending(self, blossom_sender: BlossomSenderThread, number: Literal["one", "two"]):
        """Start sending sequences to a Blossom if not already sending."""
        if not (self.is_sending_one or self.is_sending_two):
            self.start()
        if getattr(self, f"is_sending_{number}"):
            self.logger(f"[Dancer] Sending already enabled for Blossom {number.capitalize()}.", level="warning")
            return
        self.update_sender(number, blossom_sender)
        setattr(self, f"is_sending_{number}", True)
        blossom_sender.start()


    def stop_sending(self, blossom_sender: BlossomSenderThread, number: Literal["one", "two"]):
        """Stop sending sequences to a Blossom and stop the thread if no other sending is active."""
        if not getattr(self, f"is_sending_{number}"):
            self.logger(f"[Dancer] Sending not enabled for Blossom {number.capitalize()}.", level="warning")
            return
        setattr(self, f"is_sending_{number}", False)
        blossom_sender.stop()
        blossom_sender.join()
        if not (self.is_sending_one or self.is_sending_two):
            self.stop()

    def change_music(self, music_path: str):
        """Change the currently playing music and reset the analysis schedule."""
        self.beat_detector.change_music(music_path)
        self.music_player.play(music_path)
        self._music_schedule = []
        self._current_schedule_index = 0
        self._music_over = False

    def _cooperative_sleep(self, seconds: float, step: float = 0.02):
        """
        Sleep in small steps to allow cooperative multitasking and early interruption.

        :param seconds: Total time to sleep
        :param step: Step size for each sleep iteration
        """
        end = time.time() + max(0.0, seconds)
        while (self.is_running and not self._stop_event.is_set()) and time.time() < end:
            time.sleep(max(step, end - time.time()))