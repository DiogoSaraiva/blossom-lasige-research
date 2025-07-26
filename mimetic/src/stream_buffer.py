import time
from threading import Lock

from mimetic.src.logging_utils import Logger


class ResultBuffer:
    """
    A thread-safe buffer for storing results from face and pose detection.
    This class allows for adding results with a timestamp, retrieving complete results
    when both face and pose data are available, and managing pose data separately.
    It uses a lock to ensure thread safety when accessing the buffer.
    :param logger: Logger instance for logging messages (optional).
    :type logger: Logger
    :raises TypeError: If logger is not an instance of Logger or None.
    :raises ValueError: If logger is not None and does not have a log method.
    :raises Exception: If an unexpected error occurs during initialization.
    :type logger: Logger
    """
    def __init__(self, logger:Logger=None):
        """
        Initializes the ResultBuffer with an optional logger.
        The ResultBuffer is designed to store results from face and pose detection,
        allowing for thread-safe addition and retrieval of results based on timestamps.
        :param logger: Logger instance for logging messages (optional).
        :type logger: Logger
        """
        self.logger = logger
        self.buffer = {}  # face + pose by timestamp
        self.pose_data_buffer = []  # array de (pose_data, timestamp)
        self.lock = Lock()

    def add(self, kind: str, result: dict, timestamp: int):
        """
        Adds a result to the buffer.
        :param kind: The type of result, either "face" or "pose_data".
        :type kind: str
        :param result: The result data to add, should be a dictionary.
        :type result: dict
        :param timestamp: The timestamp associated with the result.
        :type timestamp: int

        """
        try:
            with self.lock:
                if kind == "pose_data":
                    self.pose_data_buffer.append((result, timestamp))
                    if len(self.pose_data_buffer) > 30:
                        self.pose_data_buffer = self.pose_data_buffer[-30:]
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
        if kind not in ["face", "pose_data"]:
            raise ValueError(f"Invalid kind: {kind}. Must be 'face' or 'pose_data'")

    def get_if_complete(self, timestamp: int):
        """
        Returns the face and pose results if both are present for the given timestamp.
        If not, returns None for both.
        :param timestamp: The timestamp to check in the buffer.
        :type timestamp: int
        :return: A tuple containing the face and pose results if both are present, otherwise (None, None).
        :rtype: tuple (dict, dict)
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
        If no complete results are found within the specified delay, returns None for both.
        :param max_delay_ms: Maximum delay in milliseconds to consider a result complete.
        :type max_delay_ms: int
        :return: A tuple containing the latest face and pose results if available, otherwise (None, None).
        :rtype: tuple (dict, dict)
        :raises TypeError: If max_delay_ms is not an integer.
        :raises ValueError: If max_delay_ms is negative.
        :raises Exception: If an unexpected error occurs while accessing the buffer.
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

    def get_latest_pose_data(self):
        """
        Returns the latest pose data and its timestamp from the pose data buffer.
        If the buffer is empty, returns None for both.
        :return: A tuple containing the latest pose data and its timestamp, or (None, None) if the buffer is empty.
        :rtype: tuple (dict, int)
        :raises Exception: If an unexpected error occurs while accessing the pose data buffer.
        """
        try:
            with self.lock:
                if not self.pose_data_buffer:
                    return None, None
                return self.pose_data_buffer[-1]  # último (result, timestamp)
        except Exception as e:
            self.logger(f"[ResultBuffer] Error getting latest pose data: {e}", level="error")
            return None, None

    def clear(self):
        """
        Clears the buffer and pose data buffer.
        This method removes all entries from both buffers, effectively resetting them.
        :raises Exception: If an unexpected error occurs while clearing the buffers.
        """
        with self.lock:
            self.buffer.clear()
            self.pose_data_buffer.clear()
