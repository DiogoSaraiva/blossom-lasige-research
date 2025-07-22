import time
from threading import Lock

class ResultBuffer:
    def __init__(self):
        self.buffer = {}
        self.lock = Lock()

    def add(self, kind, result, timestamp):
        with self.lock:
            if timestamp not in self.buffer:
                self.buffer[timestamp] = {}
            self.buffer[timestamp][kind] = result

    def get_if_complete(self, timestamp):
        with self.lock:
            if timestamp in self.buffer:
                res = self.buffer[timestamp]
                if "face" in res and "pose" in res:
                    del self.buffer[timestamp]
                    return res["face"], res["pose"]
            return None, None

    def get_latest_complete(self, max_delay_ms=200):
        now = int(time.time() * 1000)
        with self.lock:
            for ts in sorted(self.buffer.keys()):
                if now - ts > max_delay_ms:
                    del self.buffer[ts]
                    continue
                res = self.buffer[ts]
                if "face" in res and "pose" in res:
                    del self.buffer[ts]
                    return res["face"], res["pose"]
        return None, None
