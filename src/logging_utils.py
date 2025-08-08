import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional


def print_logger(message, level, *args, **kwargs):
    colors = {
        "debug": "\033[90m",
        "info": "\033[92m",
        "warning": "\033[93m",
        "error": "\033[91m",
        "critical": "\033[1;91m",
        "reset": "\033[0m",
    }
    color = colors.get(level, colors["info"])
    reset = colors["reset"]
    print(f"{color}[{level.upper()}] {message}{reset}", *args, **kwargs)


class Logger:
    def __init__(self, output_path: str, mode: Literal["pose", "system"] = "pose", level: Optional[str] = None, print_to_terminal: bool = True,):
        self.log_level = (level or "info").lower()
        self.output_path = Path(output_path)
        self.print_to_terminal = print_to_terminal

        if mode == "pose":
            self.log = self._log_pose
        elif mode == "system":
            self.log = self._log_system

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.output_path.exists():
            self.output_path.touch()
        self._lock = threading.Lock()

    # ---------- append helpers ----------

    def _append_entry(self, entry: dict):
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        with self._lock:
            try:
                with open(self.output_path, "a", encoding="utf-8") as f:
                    f.write(line)  # sem flush/fsync para performance
            except Exception as e:
                print(f"[Logger] Failed to write to log file: {e}")

    def _log_system(self, message: str, level: str = "info"):
        levels = {"debug": 0, "info": 1, "warning": 2, "error": 3, "critical": 4}
        level = (level or "info").lower()

        if levels.get(level, 1) >= levels.get(self.log_level, 1):
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": level,
                "data": message,
            }
            self._append_entry(entry)
            if self.print_to_terminal:
                print_logger(message, level)

    def _log_pose(self, data: dict):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "data": data.copy(),
        }
        self._append_entry(entry)

    def __call__(self, message: str | dict, level: str = None):
        if self.log == self._log_system:
            self._log_system(message, level=(level or self.log_level))
        else:
            self._log_pose(message)

    def set_system_log_level(self, level: str):
        valid = ["debug", "info", "warning", "error", "critical"]
        if level not in valid:
            raise ValueError(f"Invalid logging level: {level}")
        self.log_level = level
        print(f"[Logger] Log level set to: {level}")
