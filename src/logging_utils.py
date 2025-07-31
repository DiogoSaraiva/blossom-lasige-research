import json
from datetime import datetime
from pathlib import Path


def print_logger(message, level, *args, **kwargs):
    colors = {
        "debug": "\033[90m",
        "info": "\033[92m",
        "warning": "\033[93m",
        "error": "\033[91m",
        "critical": "\033[1;91m",
        "reset": "\033[0m"
    }

    color = colors.get(level, colors["info"])
    reset = colors["reset"]

    print(f"{color}[{level.upper()}] {message}{reset}", *args, **kwargs)


class Logger:
    """
    Logger class for saving and printing logs in pose or system mode.

    Attributes:
        log_level (str): Logging level for system logs.
        output_path (Path): Path to save the log file.
        log (callable): Logging function based on mode and output.
    """

    def __init__(self, output_path: str, mode: str = "pose", level: str = None, print_to_terminal: bool = True):
        self.log_level = level or "info"
        self.output_path = Path(output_path)
        self.print_to_terminal = print_to_terminal

        if mode == "pose":
            self.log = self._log_pose
        elif mode == "system":
            self.log = self._log_system
        else:
            raise ValueError(f"[Logger] Invalid mode: {mode}")

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.output_path.exists():
            with open(self.output_path, "w") as f:
                json.dump([], f)

    def _append_entry(self, entry: dict):
        try:
            with open(self.output_path, "r+", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = []
                except json.JSONDecodeError:
                    data = []

                data.append(entry)
                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()
        except Exception as e:
            print(f"[Logger] Failed to write to log file: {e}")

    def _log_system(self, message: str, level: str = "info"):
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
            self._append_entry(entry)
            if self.print_to_terminal:
                print_logger(message, level)

    def _log_pose(self, data: dict):
        if not isinstance(data, dict):
            print("[Logger] Invalid pose log data (must be dict)")
            return
        entry = {
            "timestamp": datetime.now().isoformat(),
            "data": data.copy()
        }
        self._append_entry(entry)

    def __call__(self, message: str or dict, level: str = None):
        if self.log == self._log_system:
            self._log_system(message, level=(level or self.log_level))
        else:
            self._log_pose(message)

    def set_system_log_level(self, level: str):
        valid_levels = ["debug", "info", "warning", "error", "critical"]
        if level not in valid_levels:
            raise ValueError(f"Invalid logging level: {level}")
        self.log_level = level
        print(f"[Logger] Log level set to: {level}")
