import json
from datetime import datetime
from pathlib import Path


class Logger:
    def __init__(self, output_path, mode="pose"):
        """
        :param output_path: path to JSON log file
        :param mode: 'pose' or 'system'
        """
        self.entries = []
        self.output_path = Path(output_path)

        if mode == "pose":
            self.log = self._log_pose
        elif mode == "system":
            self.log = self._log_system
        else:
            raise ValueError(f"Invalid logger mode: {mode}")

    def _log_pose(self, data: dict):
        if not isinstance(data, dict):
            print("[Logger] Invalid pose log data (must be dict)")
            return
        entry = data.copy()
        entry["timestamp"] = datetime.now().isoformat()
        self.entries.append(entry)

    def _log_system(self, message):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "data": message
        }
        self.entries.append(entry)

    def save_log(self):
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

    def __call__(self, message):
        self.log(message)