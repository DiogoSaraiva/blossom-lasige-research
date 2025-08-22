import threading
import json
import threading
import time
from typing import Literal, Optional, List, Tuple

from dancer.src.beat_detector import BeatDetector
from src.logging_utils import Logger
from src.threads.blossom_sender import BlossomSenderThread


class Dancer:
    def __init__(self, music_dir: str, logger: Logger, mode: Literal["mic", "audio"], analysis_interval: float = 5.0, mic_sr = 22050):
        """
        :param music_dir: Path to the music directory
        :param analysis_interval: Interval in seconds to re-analyze mood
        """
        self._music_schedule: List[Tuple[float, float, str]] = []
        self._current_music_path = ""
        self._player_lock = None
        self._player_backend = None
        self.music_dir = music_dir
        self.analysis_interval = analysis_interval
        self.dancer_server_proc = None
        self.current_sequence = None
        self.is_running = False
        self.logger = logger
        self.beat_detector = BeatDetector(logger=logger, mic_sr= mic_sr)
        self.blossom_one_sender = self.blossom_two_sender = None
        self.is_sending_one = self.is_sending_two = False
        self.mode = mode
        self._thread = None
        self._stop_event = threading.Event()
        self._current_music_time = None

    def _main_loop(self):
        self.logger("[Dancer] Launching Dancer...", level="info")
        self.is_running = True
        run = self.run_for_mic if self.mode == "mic" else self.run_for_audio
        while self.is_running:
            sequence = run()
            if not sequence:
                time.sleep(0.02)
                continue
            if sequence != self.current_sequence:
                duration_ms = self.get_sequence_duration(sequence)
                if duration_ms is not None:
                    payload = {"sequence": sequence, "duration_ms": duration_ms}

                    if self.is_sending_one and self.blossom_one_sender:
                        self.blossom_one_sender.send(payload)
                    if self.is_sending_two and self.blossom_two_sender:
                        self.blossom_two_sender.send(payload)

                    self.current_sequence = sequence
                    self.logger(f"[BeatDetector] Mood -> '{sequence}', ({duration_ms:.2f})s", level="debug")
                else:
                    self.logger(f"[BeatDetector] Could not find duration for '{sequence}'", level="warning")
            time.sleep(0.01)

        self.logger("[Dancer] Loop ended.", level="debug")


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


    def get_sequence_duration_ms(self, sequence) -> Optional[int]:
        try:
            with open(f"blossom_public/src/sequences/woody/{sequence}_sequence.json", "r") as file:
                sequence_json = json.load(file)
            last_frame = sequence_json["frame_list"][-1]
            last_millis = last_frame["millis"]
            return last_millis
        except Exception as e:
            self.logger(f"[ERROR] Failed to get sequence duration: {e}", level="critical")
            return None

    def run_for_mic(self) -> str:
        return self.beat_detector.analyse_microphone()

    def run_for_audio(self) -> Optional[str]:
        if not self._music_schedule:
            if not self._current_music_path:
                return None
            self._music_schedule = self.beat_detector.analyse_music(self._current_music_path)

        for start, dur, mood in self._music_schedule:
            if start <= self._current_music_time < start + dur:
                self._current_music_time = start + dur
                return mood
            
        self._music_schedule = []
        self._current_music_time = 0.0
        return None

    def update_sender(self, number: Literal["one", "two"], blossom_sender: BlossomSenderThread | None):
        setattr(self, f"blossom_{number}_sender", blossom_sender)


    def start_sending(self, blossom_sender: BlossomSenderThread, number: Literal["one", "two"]):
        if getattr(self, f"is_sending_{number}"):
            self.logger(f"[Dancer] Sending already enabled for Blossom {number.capitalize()}.", level="warning")
            return
        setattr(self, f"is_sending_{number}", True)
        blossom_sender.start()


    def stop_sending(self, blossom_sender: BlossomSenderThread, number: Literal["one", "two"]):
        if not getattr(self, f"is_sending_{number}"):
            self.logger(f"[Dancer] Sending not enabled for Blossom {number.capitalize()}.", level="warning")
            return
        setattr(self, f"is_sending_{number}", False)
        blossom_sender.stop()
        blossom_sender.join()

