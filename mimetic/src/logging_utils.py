import json
from datetime import datetime
from pathlib import Path

def print_logger(message, *args, **kwargs):
    """
    Prints a log message to the terminal.

    Args:
        message (str): The message to print.
        *args: Additional positional arguments.
        **kwargs: Additional keyword arguments.
    """
    print(message)

class Logger:
    """
    Logger class for saving and printing logs in pose or system mode.

    Attributes:
        log_level (str): Logging level for system logs.
        entries (list): List of log entries.
        output_path (Path): Path to save the log file.
        print_to_terminal (bool): If True, logs are printed to the terminal.
        log (callable): Logging function based on mode and output.
    """

    def __init__(self, output_path: str, mode: str="pose", level: str=None, print_to_terminal: bool = False):
        """
        Initializes the Logger.

        Args:
            output_path (str): Path to save the log file.
            mode (str, optional): Logging mode, either "pose" or "system". Default is "pose".
            level (str, optional): Logging level for system logs. Default is "info".
            print_to_terminal (bool, optional): If True, logs are printed to the terminal. Default is False.
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

        Args:
            data (dict): Pose data to log.
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

        Args:
            message (str or dict): Message to log.
            level (str, optional): Logging level ("debug", "info", "warning", "error", "critical"). Default is "info".
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
        If there are no entries, prints a message indicating that there is no data to save.
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

        Args:
            message (str or dict): Message or data to log.
            level (str, optional): Logging level ("debug", "info", "warning", "error", "critical").
        """
        if self.print_to_terminal:
            print_logger(message, level=level)
        elif self.log == self._log_system:
            self._log_system(message, level=(level or self.log_level))
        else:
            self._log_pose(message)

    def set_system_log_level(self, level: str):
        """
        Sets the logging level for system logs.

        Args:
            level (str): Logging level ("debug", "info", "warning", "error", "critical").

        Raises:
            ValueError: If the provided level is not valid.
        """
        if level not in ["debug", "info", "warning", "error", "critical"]:
            raise ValueError(f"Invalid logging level: {level}")
        self.log_level = level
        print(f"[Logger] Log level set to: {level}")