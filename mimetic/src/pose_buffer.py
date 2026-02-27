import time
from threading import Lock

from src.logging_utils import Logger


class PoseBuffer:
    """
    Thread-safe buffer for storing and retrieving face and pose detection results.

    This class allows adding results (face or pose data) with timestamps, retrieving complete results
    when both face and pose data are available for a timestamp, and managing pose data separately.
    All buffer operations are protected by a lock for thread safety.

    Attributes:
        logger (Logger): Logger instance for logging messages.
        buffer (dict): Stores face and pose results by timestamp.
        pose_data_buffer (list): Stores tuples of (pose_data, timestamp).
        lock (Lock): Threading lock for synchronizing access.
    """

    def __init__(self, logger:Logger):
        """
        Initializes the ResultBuffer with an optional logger.

        Args:
            logger (Logger): Logger instance for logging messages.
        """
        self.logger = logger
        self.buffer = {}  # face + pose by timestamp
        self.pose_data_buffer = []  # array de (pose_data, timestamp)
        self.lock = Lock()
        self.last_pose_update_time: float = 0.0

    def add(self, kind: str, result: dict, timestamp: int):
        """
        Adds a result to the buffer.

        Args:
            kind (str): The type of result, either "face" or "pose_data".
            result (dict): The result data to add.
            timestamp (int): The timestamp associated with the result.

        Raises:
            ValueError: If kind is not "face" or "pose_data".
        """
        try:
            if kind not in ["face", "pose_data"]:
                raise ValueError(f"Invalid kind: {kind}. Must be 'face' or 'pose_data'")
            with self.lock:
                if kind == "pose_data":
                    self.pose_data_buffer.append((result, timestamp))
                    if len(self.pose_data_buffer) > 30:
                        self.pose_data_buffer = self.pose_data_buffer[-30:]
                    self.last_pose_update_time = time.time()
                else:
                    if timestamp not in self.buffer:
                        self.buffer[timestamp] = {}
                    self.buffer[timestamp][kind] = result
        except ValueError as e:
            self.logger(f"[ResultBuffer] ValueError: {e}", level="error")
        except TypeError as e:
            self.logger(f"[ResultBuffer] TypeError: {e}", level="error")
        except Exception as e:
            self.logger(f"[ResultBuffer] Unexpected error: {e}", level="error")

    def get_if_complete(self, timestamp: int):
        """
        Returns the face and pose results if both are present for the given timestamp.

        Args:
            timestamp (int): The timestamp to check in the buffer.

        Returns:
            tuple: (face_result, pose_result) if both are present, otherwise (None, None).
        """
        with self.lock:
            if timestamp in self.buffer:
                res = self.buffer[timestamp]
                if "face" in res and "pose" in res:
                    del self.buffer[timestamp]
                    return res["face"], res["pose"]
            return None, None

    def get_latest_complete(self, max_delay_ms=200):
        """
        Returns the latest complete face and pose results from the buffer.

        Args:
            max_delay_ms (int, optional): Maximum delay in milliseconds to consider a result complete.

        Returns:
            tuple: (face_result, pose_result) if available, otherwise (None, None).

        Raises:
            TypeError: If max_delay_ms is not an integer.
            ValueError: If max_delay_ms is negative.
        """
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

    def is_pose_fresh(self, max_age: float = 0.2) -> bool:
        """Returns True if pose data was updated within the last max_age seconds."""
        with self.lock:
            return self.last_pose_update_time > 0 and (time.time() - self.last_pose_update_time) < max_age

    def get_latest_pose_data(self):
        """
        Returns the latest pose data and its timestamp from the pose data buffer.

        Returns:
            tuple: (pose_data, timestamp) if available, otherwise (None, None).
        """
        try:
            with self.lock:
                if not self.pose_data_buffer:
                    return None, None
                return self.pose_data_buffer[-1]  # last (result, timestamp)
        except Exception as e:
            self.logger(f"[ResultBuffer] Error getting latest pose data: {e}", level="error")
            return None, None

    def clear(self):
        """
        Clears the buffer and pose data buffer.

        This method removes all entries from both buffers, effectively resetting them.
        """
        with self.lock:
            self.buffer.clear()
            self.pose_data_buffer.clear()