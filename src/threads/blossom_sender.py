import threading
import time
from queue import Queue, Empty, Full
from typing import Literal

import requests

from src.logging_utils import Logger


class BlossomSenderThread(threading.Thread):
    def __init__(self, logger: Logger, mode: Literal["mimetic", "dancer"], host="localhost", port: int = 8000, max_queue: int = 32, min_interval: float = 0.1):
        super().__init__(daemon=True)
        self.logger = logger
        self.queue = Queue(maxsize=max_queue or (32 if mode == "mimetic" else 4))
        self.is_running = True
        self.host = host
        self.port = port
        self.min_interval = float(min_interval)
        self.mode = mode
        self.is_running = True
        self.last_send_time = 0.0
        self.last_sequence = None

    def run(self):
        self.logger(f"[BlossomSender] Thread started (mode: {self.mode})", level="info")
        try:
            while self.is_running:
                try:
                    payload = self.queue.get(timeout=0.1)
                except Empty:
                    continue
                if payload is None:
                    break

                # rate limit
                now = time.time()
                dt = now - self.last_send_time
                if dt < self.min_interval:
                    self._cooperative_sleep(self.min_interval - dt)

                try:
                    if self.mode == "mimetic":
                        requests.post(f"http://{self.host}:{self.port}/position", json=payload, timeout=1)
                        self.last_send_time = time.time()
                        x = payload.get("x", 0)
                        y = payload.get("y", 0)
                        z = payload.get("z", 0)
                        h = payload.get("h", 0)
                        duration = payload.get("duration_ms", 0) / 1000
                        self.logger(
                            f"Sent -> Pitch: {x:.3f}, Roll: {y:.3f}, Yaw: {z:.3f}, Height: {h:.3f}, Duration: {duration:.2f}s", level="debug")
                    else:
                        sequence = payload.get("sequence")
                        duration_ms = payload.get("duration_ms", 0)
                        if not sequence or duration_ms <= 0:
                            self.logger("[BlossomSender] Invalid sequence payload", level="warning")
                            continue

                        if sequence != self.last_sequence:
                            requests.post(f"http://{self.host}:{self.port}/sequence", data=sequence, timeout=2)
                            self.last_sequence = sequence
                            self.last_send_time = time.time()
                            self._cooperative_sleep(duration_ms / 1000.0)
                            self.last_sequence = None
                        else:
                            pass

                except requests.RequestException as e:
                    self.logger(f"[BlossomSender] Error sending: {e}", level="error")

        except Exception as e:
            import traceback
            self.logger(f"[BlossomSender] CRASHED: {e} \n {traceback.format_exc()}", level="critical")

    def _cooperative_sleep(self, seconds: float, step: float = 0.02):
        end = time.time() + max(0.0, seconds)
        while self.is_running and time.time() < end:
            time.sleep(min(step, end - time.time()))

    def send(self, payload: dict):
        if self.mode == "mimetic":
            if not self.queue.full():
                self.queue.put_nowait(payload)
            else:
                self.logger("[BlossomSender] Queue full, dropping pose", level="warning")
        else:
            if not self.queue.full():
                self.queue.put_nowait(payload)
            else:
                self.logger("[BlossomSender] Queue full, dropping pose", level="warning")

    def stop(self):
        """
        Stop the thread and clear the queue.

        Signals the thread to stop, unblocks the queue, and clears any remaining payloads.
        """
        self.is_running = False
        try:
            self.queue.put_nowait(None)  # unblock queue.get()
        except Full:
            pass
        with self.queue.mutex:
            self.queue.queue.clear()
        self.logger("[BlossomSender] Thread stopped", level="info")