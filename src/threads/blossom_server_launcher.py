import os
import subprocess
import time
from typing import Literal

import requests
from PyQt6.QtCore import QThread

class BlossomServerLauncher(QThread):
    def __init__(self, logger, host, port: int, number: Literal["one", "two"], usb: str):
        super().__init__()
        self.logger = logger
        self.host = host
        self.port = port
        self.usb = usb
        self.server_proc = None
        self.success = False
        self.number = number
        self.init_allowed = True
        self.url = f"http://{self.host}:{self.port}/"

    def wait_for_server_ready(self, timeout=10.0, interval=0.5) -> bool:
        self.logger(f"[BlossomLauncher] Waiting for Blossom server at {self.url}...", level="info")
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.init_allowed:
                return False
            try:
                r = requests.get(self.url)
                if r.status_code == 200:
                    self.logger(f"[BlossomLauncher] Blossom server at {self.url} is ready.")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(interval)

        self.logger(f"[BlossomLauncher] Timeout: Blossom server at {self.url} not responding.", level="error")
        return False

    def kill_if_using(self, mode:Literal["port", "device"]):
        """
        Kills all processes listening on a given TCP port.
        Logs each kill.
        """
        try:
            if mode == "port":
                result = subprocess.run(["lsof", "-t", f"-i:{self.port}"], capture_output=True, text=True, check=False)
            else:
                result = subprocess.run(["lsof", "-t", self.usb], capture_output=True, text=True, check=False)
            pids = [p.strip() for p in result.stdout.splitlines() if p.strip()]

            if not pids:
                return

            for pid in pids:
                try:
                    self.logger(f"[BlossomLauncher] {mode.capitalize()} {self.port if mode == 'port' else self.usb} in use by PID {pid}. Killing...", level="warning")
                    os.kill(int(pid), 9)  # SIGKILL
                except Exception as e:
                    self.logger(f"[BlossomLauncher] Failed to kill PID {pid}: {e}", level="error")

        except FileNotFoundError:
            self.logger("[BlossomLauncher] lsof not installed. Cannot check ports.", level="error")
        except Exception as e:
            self.logger(f"[BlossomLauncher] Error while checking/killing {mode} {self.port if mode == 'port' else self.usb}: {e}", level="error")

    def run(self):
        try:
            self.logger(f"[BlossomLauncher]  Launching blossom_public/start.py ({self.number.upper()} at {self.url})...", level="info")
            self.kill_if_using(mode="port")
            self.kill_if_using(mode="device")
            self.server_proc = subprocess.Popen([
                "python", "blossom_public/start.py",
                "--host", self.host,
                "--port", str(self.port),
                "--browser-disable",
                "--usb-port", self.usb

            ], stdin=subprocess.PIPE)

            if not self.wait_for_server_ready() and self.init_allowed:
                self.logger(f"[BlossomLauncher] Blossom server ({self.number.upper()}) failed to start at {self.url}.", level="error")
                if self.server_proc: self.server_proc.terminate()
                return
            if not self.init_allowed:
                if self.server_proc:
                    self.server_proc.terminate()
                return
            self.success = True
            self.logger(f"[BlossomLauncher] Blossom server ({self.number.upper()}) started successfully at {self.url}.")
        except Exception as e:
            self.logger(f"[BlossomLauncher] Exception while starting Blossom server at {self.url}: {e}", level="error")
            if self.server_proc:
                self.server_proc.terminate()
