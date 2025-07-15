import time
import numpy as np

class MotionLimiter:
    def __init__(self, alpha_map=None, rate_hz=10, threshold=2.0):
        # Custom smoothing factor (alpha) per axis
        self.alpha_map = alpha_map or {
            "x": 0.3,  # pitch
            "y": 0.2,  # roll
            "z": 0.1,  # yaw
            "h": 0.3,  # height
            "e": 0.2   # ears
        }
        # Initial smoothed values
        self.smoothed = {
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
            "h": 50.0,
            "e": 70.0
        }
        # State for rate limiting and change detection
        self.last_sent = 0
        self.min_interval = 1.0 / rate_hz
        self.threshold = threshold
        self.last_data = self.smoothed.copy()

    def smooth(self, key, value):
        alpha = self.alpha_map.get(key, 0.3)
        prev = self.smoothed.get(key, 0.0)
        smoothed = alpha * value + (1 - alpha) * prev
        self.smoothed[key] = smoothed
        return smoothed

    def should_send(self, keys):
        now = time.time()
        if now - self.last_sent < self.min_interval:
            return False, None

        max_change = max(abs(self.smoothed[k] - self.last_data[k]) for k in keys)
        if max_change > self.threshold:
            self.last_sent = now
            self.last_data = {k: self.smoothed[k] for k in keys}
            duration = np.clip(max_change / 100.0, 0.1, 0.4)
            return True, duration

        return False, None
