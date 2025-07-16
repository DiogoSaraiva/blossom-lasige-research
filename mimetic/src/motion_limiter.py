import time
import numpy as np

class MotionLimiter:
    def __init__(self, alpha_map=None, rate_hz=10, threshold=2.0):
        self.alpha_map = alpha_map or {
            "x": 0.3,  # pitch
            "y": 0.2,  # roll
            "z": 0.1,  # yaw
            "h": 0.3,  # height
            "e": 0.2   # ears
        }
        self.smoothed = {
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
            "h": 50.0,
            "e": 70.0
        }
        self.last_sent = 0
        self.min_interval = 1.0 / rate_hz
        self.threshold = threshold
        self.last_data = self.smoothed.copy()

    @staticmethod
    def to_six_unit_range(value, min_val, max_val):
        """Maps a value in [min_val, max_val] to [0, 6] linearly."""
        return np.clip((value - min_val) / (max_val - min_val), 0.0, 1.0) * 6.0

    def smooth_and_scale(self, key, value):
        smoothed = self._smooth(key, value)

        match key:
            case "x" | "y":
                return self.to_six_unit_range(np.clip(smoothed, -150, 150), -150, 150)
            case "z":
                return self.to_six_unit_range(np.clip(smoothed, -40, 40), 0, 100)
            case "h":
                return self.to_six_unit_range(np.clip(smoothed, 0, 100), 0, 100)
            case "e":
                return self.to_six_unit_range(np.clip(smoothed, 50, 130), 50, 130)
            case _:
                return smoothed


    def smooth(self, key, value):
        match key:
            case "x" | "y":
                return self.smooth_and_scale("x", value)
            case "z":
                return self.smooth_and_scale("z", value)
            case "h":
                return self.smooth_and_scale("h", value)
            case "e":
                return self.smooth_and_scale("e", value)

    def _smooth(self, key, value):
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
