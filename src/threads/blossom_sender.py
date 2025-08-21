import threading
import time
from typing import Literal

import requests
from queue import Queue, Empty, Full

from src.logging_utils import Logger

class BlossomSenderThread(threading.Thread):
    """
    Thread responsible for sending pose data payloads to a Blossom server via HTTP POST requests.
    Manages a queue of payloads, rate-limits requests, and provides thread-safe start/stop mechanisms.

    Args:
        host (str): Blossom server hostname or IP address.
        port (int): Blossom server port.
        max_queue (int): Maximum number of payloads to queue.
        min_interval (float): Minimum interval (in seconds) between sends.
        logger (Logger, optional): Logger instance for logging events.
    """
    def __init__(self, logger:Logger, mode: Literal["mimetic", "dancer"], host="localhost", port: int=8000, max_queue:int=32, min_interval:float=0.1):
        """
        Initialize the BlossomSenderThread.

        Args:
            host (str): Blossom server hostname or IP address.
            port (int): Blossom server port.
            max_queue (int): Maximum number of payloads to queue.
            min_interval (float): Minimum interval (in seconds) between sends.
            logger (Logger): Logger instance for logging events.
        """
        super().__init__()
        self.logger = logger
        self.queue = Queue(maxsize=max_queue)
        self.is_running = True
        self.host = host
        self.port = port
        self.min_interval = min_interval
        self.last_send_time = 0
        self.mode = mode
        self.last_sequence = None

    def run(self):
        """
        Main thread loop for sending payloads to the Blossom server.

        Continuously checks the queue for new payloads and sends them to the server,
        respecting the minimum interval between sends. Handles errors and logs events.
        """
        self.logger(f"[BlossomSender] Thread started (mode: {self.mode})", level="info")
        try:
            while self.is_running:
                try:
                    payload = self.queue.get(timeout=0.1)
                    if payload is None:
                        break
                    now = time.time()
                    if now - self.last_send_time < self.min_interval:
                        time.sleep(self.min_interval - (now - self.last_send_time))
                    try:
                        requests.post(f"http://{self.host}:{self.port}/position", json=payload, timeout=1)
                        x = payload.get("x", 0)
                        y = payload.get("y", 0)
                        z = payload.get("z", 0)
                        h = payload.get("h", 0)
                        duration = payload.get("duration_ms", 0) / 1000
                        self.logger(
                            f"Sent -> Pitch: {x:.3f}, Roll: {y:.3f}, Yaw: {z:.3f}, Height: {h:.3f}, Duration: {duration:.2f}s")
                        self.last_send_time = time.time()
                    except requests.RequestException as e:
                        self.logger(f"[BlossomSender] Error sending: {e}", level="error")
                except Empty:
                    continue
        except Exception as e:
            import traceback
            self.logger(f"[BlossomSender] CRASHED: {e} \n {traceback.format_exc()}", level="critical")

    def _cooperative_sleep(self, seconds: float, step: float = 0.02):
        """Sleep in small steps so stop() can interrupt quickly."""
        end = time.time() + max(0.0, seconds)
        while self.is_running and time.time() < end:
            time.sleep(min(step, end - time.time()))

    def send(self, payload: dict):
        """
        Queue a payload to be sent to the Blossom server.

        Args:
            payload (dict): Dictionary containing the data to send.
        """
        if self.mode == "mimetic":
            if not self.queue.full():
                self.queue.put_nowait(payload)
            else:
                self.logger("[BlossomSender] Queue is full, dropping payload", level="warning")
        else:
            pass #TODO

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