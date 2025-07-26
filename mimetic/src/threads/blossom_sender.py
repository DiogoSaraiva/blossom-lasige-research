import threading
import time
import requests
from queue import Queue, Empty, Full

from mimetic.src.logging_utils import Logger


class BlossomSenderThread(threading.Thread):
    def __init__(self, host="localhost", port: int=8000, max_queue:int=32, min_interval:float=0.1, logger:Logger=None):
        super().__init__()
        self.logger = logger
        self.queue = Queue(maxsize=max_queue)
        self.running = True
        self.host = host
        self.port = port
        self.min_interval = min_interval
        self.last_send_time = 0

    def run(self):
        """
        Run the thread to send data to the Blossom server.
        This method continuously checks the queue for new payloads and sends them to the server.
        It respects the minimum interval between sending to avoid overwhelming the server.
        If the queue is empty, it will wait briefly before checking again.
        If an error occurs during sending, it logs the error.
        """
        self.logger("[BlossomSender] Thread started", level="info")
        try:
            while self.running:
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
            self.logger(f"[BlossomSenderThread] CRASHED: {e}", level="critical")
        self.logger("[BlossomSender] Thread stopped", level="info")

    def send(self, payload: dict):
        """
        Send a payload to the Blossom server if the queue is not full.
        :param payload: Dictionary containing the data to send.
        :type payload: dict

        """
        if not self.queue.full():
            self.queue.put_nowait(payload)
        else:
            self.logger("[BlossomSender] Queue is full, dropping payload", level="warning")

    def stop(self):
        """
        Stop the thread and clear the queue.
        """

        self.running = False
        try:
            self.queue.put_nowait(None)  # unblock queue.get()
        except Full:
            pass
        with self.queue.mutex:
            self.queue.queue.clear()