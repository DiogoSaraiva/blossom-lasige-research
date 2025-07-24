import threading
import time
import requests
from queue import Queue, Empty

class BlossomSenderThread(threading.Thread):
    def __init__(self, host="localhost", port=8000, max_queue=32, min_interval=0.1):
        super().__init__()
        self.queue = Queue(maxsize=max_queue)
        self.running = True
        self.host = host
        self.port = port
        self.min_interval = min_interval
        self.last_send_time = 0

    def run(self):
        print("[BlossomSender] Thread started")
        try:
            while self.running:
                try:
                    payload = self.queue.get(timeout=0.1)
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
                        print(
                            f"Sent -> Pitch: {x:.3f}, Roll: {y:.3f}, Yaw: {z:.3f}, Height: {h:.3f}, Duration: {duration:.2f}s")
                        self.last_send_time = time.time()
                    except requests.RequestException as e:
                        print(f"[BlossomSender] Error sending: {e}")
                except Empty:
                    continue
        except Exception as e:
            print(f"[BlossomSenderThread] CRASHED: {e}")
        print("[BlossomSender] Thread stopped")

    def send(self, payload: dict):
        if not self.queue.full():
            self.queue.put_nowait(payload)

    def stop(self):
        self.running = False
        with self.queue.mutex:
            self.queue.queue.clear()
