import subprocess
import time

import requests
from PyQt6.QtCore import QThread

from src.config import HOST, PYTHON, MIMETIC_PORT, DANCER_PORT


class BlossomServerLauncher(QThread):
    def __init__(self, logger, ports: dict = None, blossom_type: str = "mimetic"):
        super().__init__()
        self.logger = logger
        self.ports = ports or {'mimetic': MIMETIC_PORT, 'dancer': DANCER_PORT}
        self.server_proc = None
        self.success = False
        self.blossom_type = blossom_type

    def wait_for_server_ready(self, timeout=10.0, interval=0.5):
        url = f"http://{HOST}:{self.ports[self.blossom_type]}/"
        self.logger(f"Waiting for Blossom server at {url}...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                r = requests.get(url)
                if r.status_code == 200:
                    self.logger(f"Blossom server on port {self.ports[self.blossom_type]} is ready.")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(interval)
        self.logger(f"Timeout: Blossom server on port {self.ports[self.blossom_type]} not responding.", level="error")
        return False

    def run(self):
        try:
            self.logger(f"Launching blossom_public/mimetic.py ({self.blossom_type.upper()})...")
            self.server_proc = subprocess.Popen([
                PYTHON, "blossom_public/mimetic.py",
                "--host", HOST,
                "--port", str(self.ports[self.blossom_type]),
                "--browser-disable"

            ], stdin=subprocess.PIPE)

            if not self.wait_for_server_ready():
                self.logger(f"Blossom server ({self.blossom_type.upper()}) failed to start.", level="error")
                if self.server_proc: self.server_proc.terminate()
                return

            self.success = True
            self.logger(f"Blossom server ({self.blossom_type.upper()}) started successfully.")
        except Exception as e:
            self.logger(f"Exception while starting Blossom server: {e}", level="error")
