import json
from datetime import datetime
from pathlib import Path

def print_logger(message, *args, **kwargs):
    print(message)

class Logger:
    def __init__(self, output_path: str, mode: str="pose", level: str=None, print_to_terminal: bool = False):
        """
        Initializes the Logger.
        :param output_path: Path to save the log file.
        :param mode: Logging mode, either "pose" or "system".
        :param level: Logging level for system logs (default is "info").
        :param print_to_terminal: If True, logs will be printed to the terminal instead of saving to a file.
        :type output_path: str
        :type mode: str
        :type level: str
        :type print_to_terminal: bool
        """
        self.log_level = level or "info"
        self.entries = []
        self.output_path = Path(output_path)
        self.print_to_terminal = print_to_terminal

        if print_to_terminal:
            self.log = print_logger
        elif mode == "pose":
            self.log = self._log_pose
        elif mode == "system":
            self.log = self._log_system
        else:
            raise ValueError(f"Invalid logger mode: {mode}")

    def _log_pose(self, data: dict):
        """
        Logs pose data to the log file.
        :param data: Pose data to log, must be a dictionary.
        :type data: dict
        """
        if not isinstance(data, dict):
            print("[Logger] Invalid pose log data (must be dict)")
            return
        entry = {
            "timestamp": datetime.now().isoformat(),
            "data": data.copy()
        }
        self.entries.append(entry)

    def _log_system(self, message: str, level: str="info"):
        """
        Logs system messages to the log file.
        :param message: Message to log, can be a string or a dictionary.
        :type message: str or dict
        :param level: Logging level, one of "debug", "info", "warning", "error", "critical".
        :type level: str
        """
        levels = {
            "debug": 0,
            "info": 1,
            "warning": 2,
            "error": 3,
            "critical": 4
        }
        if levels.get(level, 1) >= levels.get(self.log_level, 1):
            entry = {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "data": message
            }
            self.entries.append(entry)

    def save_log(self):
        """
        Saves the logged entries to the specified output path in JSON format.
        If there are no entries, it prints a message indicating that there is no data to save.
        """
        if not self.entries:
            print(f"[Logger] No data to save for {self.output_path.name}.")
            return
        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_path, "w") as f:
                json.dump(self.entries, f, indent=2)
            print(f"[Logger] Log saved to: {self.output_path}")
        except Exception as e:
            print(f"[Logger] Failed to save log to {self.output_path}: {e}")

    def __call__(self, message: str or dict, level: str=None):
        """
        Calls the logger to log a message or data.
        If print_to_terminal is True, it prints the message to the terminal.
        If the log is set to system mode, it logs the message with the specified level.
        If the log is set to pose mode, it logs the data as pose data.
        :param message: Message or data to log, can be a string or a dictionary.
        :type message: str or dict
        :param level: Logging level, one of "debug", "info", "warning", "error", "critical".
        :type level: str
        """
        if self.print_to_terminal:
            print_logger(message, level=level)
        elif self.log == self._log_system:
            self._log_system(message, level=(level or self.log_level))
        else:
            self._log_pose(message)

    def set_system_log_level(self, level: str):
        if level not in ["debug", "info", "warning", "error", "critical"]:
            raise ValueError(f"Invalid logging level: {level}")
        self.log_level = level
        print(f"[Logger] Log level set to: {level}")