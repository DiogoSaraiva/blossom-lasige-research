import time
import numpy as np

from src.logging_utils import Logger

class MotionLimiter:
    """
    A class to limit and smooth motion data for pose estimation.

    Attributes:
        logger (Logger): Logger instance for logging messages.
        alpha_map (dict): Mapping of keys to smoothing factors.
        smoothed (dict): Stores the last smoothed value for each key.
        last_sent (float): Timestamp of the last sent update.
        min_interval (float): Minimum interval between updates (in seconds).
        threshold (float): Minimum change required to trigger an update.
        last_data (dict): Last sent smoothed values.
        values (dict): Stores the last value for each key.
    """

    def __init__(self, logger: Logger, alpha_map: dict=None, send_rate: int=5, threshold: float=2.0, ):
        self.logger = logger
        # Higher alpha value - Less filtered, lower time to respond
        # Less alpha value - More filtered, higher time to respond
        self.alpha_map = alpha_map or {
            "x": 0.4,  # pitch
            "y": 0.4,  # roll
            "z": 0.4,  # yaw
            "h": 0.2,  # height
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
        self.min_interval = 1.0 / send_rate
        self.threshold = threshold
        self.last_data = self.smoothed.copy()
        self.values = {}

    def smooth(self, key: str, value: float) -> float | None:
        """
        Applies exponential smoothing to the value and returns the result.
        Does not scale or normalize the result.

        Args:
            key (str): One of "x", "y", "z", "h", "e"
            value (float): The input value (in degrees or 0-100 for h/e)

        Returns:
            float or None: Smoothed value or None if input is invalid.
        """
        if value is None:
            return None
        alpha = self.alpha_map.get(key, 0.3)
        prev = self.smoothed.get(key, 0.0)
        smoothed = alpha * value + (1 - alpha) * prev
        self.smoothed[key] = smoothed
        return smoothed

    def should_send(self, keys: list) -> tuple[bool, float | None]:
        """
        Determines if an update should be sent based on change threshold and time interval.

        Args:
            keys (list): Keys to check (e.g., ["x", "y", "z", "h"])

        Returns:
            tuple: (should_send (bool), duration (float in seconds or None))
        """
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

    def last(self, key: str) -> float:
        """
        Returns the last value for a given key.

        Args:
            key (str): Key to retrieve.

        Returns:
            float: Last value for the key, or 0 if not found.
        """
        return self.values.get(key, 0)