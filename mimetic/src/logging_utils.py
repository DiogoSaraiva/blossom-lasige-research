from datetime import datetime
from pathlib import Path
import json


class Logger:
    def __init__(self, output_path):
        self.entries = []
        self.output_path = Path(output_path)

    def log(self, data: dict):
        if "timestamp" not in data:
            data["timestamp"] = datetime.now().isoformat()
        self.entries.append(data)

    def save_log(self):
        if not self.entries:
            print("[WARNING] No data to save.")
            return
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "w") as f:
            json.dump(self.entries, f, indent=2)
        print(f"[INFO] JSON log saved to {self.output_path}")
