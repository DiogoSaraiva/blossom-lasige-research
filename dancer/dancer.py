import sys
import os
import subprocess
import time
import requests
import librosa
import select

from src.logging_utils import Logger


class Dancer:
    def __init__(self, host: str, port: int, music_dir: str, logger: Logger, analysis_interval: float = 5):
        """
        :param music_path: Path to the music file
        :param analysis_interval: Interval in seconds to re-analyze mood
        """
        self.music_dir = music_dir
        self.analysis_interval = analysis_interval
        self.dancer_server_proc = None
        self.current_mood = None
        self.is_running = False
        self.host = host
        self.port = port
        self.logger = logger

    def wait_for_server_ready(self, port, timeout=10.0, interval=0.5):
        """Wait for the Blossom/Dancer server to be ready."""
        url = f"http://{self.host}:{self.port}/"
        self.logger(f"[INFO] Waiting for Blossom server at {url}...", level="info")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                r = requests.get(url)
                if r.status_code == 200:
                    self.logger(f"[INFO] Blossom server on port {port} is ready.", level="debug")
                    return True
            except requests.exceptions.RequestException as e:
                self.logger(f"[ERROR] Blossom server on port {port} is not ready: {e}", level="warning")
            time.sleep(interval)
        self.logger(f"[ERROR] Timeout: Blossom server on port {port} not responding.", level="error")
        return False

    def analyze_music_segment(self, music_path, offset, duration):
        """Analyze a segment of the music starting at `offset` for `duration` seconds."""
        y, sr = librosa.load(music_path, offset=offset, duration=duration)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        energy = sum(abs(y)) / len(y)

        print(f"[INFO] Segment @ {offset:.1f}s - BPM: {tempo:.2f}, Energy: {energy:.4f}")
        return 'happy' if tempo > 100 and energy > 0.1 else 'sad'

    def send_sequence(self, sequence_str):
        """Send sequence to the Dancer server."""
        url = f"http://{self.host}:{self.host}/sequence"
        print(f"[INFO] Sending sequence to {url}: {sequence_str}")

        try:
            response = requests.post(url, data=sequence_str)
            if response.status_code == 200:
                self.logger(f"[Dancer] Sequence '{sequence_str}' sent successfully!", level="debug")
                return True
            else:
                self.logger(f"[Dancer] Received status code {response.status_code}", level="error")
                return False
        except requests.exceptions.RequestException as e:
            self.logger(f"[ERROR] Failed to send sequence '{sequence_str}': {e}", level="error")
            return False

    def start(self):
        """Start the dancer and continuously adjust mood based on the music."""
        print("[INFO] Launching DANCER server...")
        self.dancer_server_proc = subprocess.Popen([
            "python3", "blossom_public/start.py",
            "--host", self.host,
            "--port", str(self.port),
            "--browser-disable"
        ])

        try:
            self.wait_for_server_ready(self.port)
        except Exception as e:
            self.logger(f"[ERROR] Failed to start DANCER server: {e}", level="critical")
        finally:
            self.stop()


        self.is_running = True
        for music_file in os.listdir(self.music_dir):
            music_file = os.path.join(self.music_dir, music_file)
            self.analyse_music(music_file)


    def stop(self):
        """Stop the dancer and shut down the server."""
        self.is_running = False
        if self.dancer_server_proc:
            self.logger("[INFO] Shutting down DANCER server...", level="info")
            self.dancer_server_proc.terminate()
            self.dancer_server_proc.wait()

    def analyse_music(self, music_path: str):
        music_duration = librosa.get_duration(filename=music_path)
        offset = 0

        try:
            while self.is_running and offset < music_duration:
                mood = self.analyze_music_segment(music_path=music_path, offset=offset, duration=self.analysis_interval)

                if mood != self.current_mood:
                    self.current_mood = mood
                    self.send_sequence(mood)

                offset += self.analysis_interval
                time.sleep(self.analysis_interval)

        except KeyboardInterrupt:
            self.logger("\n[INFO] Interrupted manually.", level="warning")
        finally:
            self.stop()

