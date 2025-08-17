import sys
import os
import subprocess
import time
import requests
import librosa
import select
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from src.config import HOST, DANCER_PORT


class Dancer:
    def __init__(self, music_path, analysis_interval=5):
        """
        :param music_path: Path to the music file
        :param analysis_interval: Interval in seconds to re-analyze mood
        """
        self.music_path = music_path
        self.analysis_interval = analysis_interval
        self.dancer_server_proc = None
        self.current_mood = None
        self.is_running = False

    def wait_for_server_ready(self, port, timeout=10.0, interval=0.5):
        """Wait for the Blossom/Dancer server to be ready."""
        url = f"http://{HOST}:{port}/"
        print(f"[INFO] Waiting for Blossom server at {url}...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                r = requests.get(url)
                if r.status_code == 200:
                    print(f"[INFO] Blossom server on port {port} is ready.")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(interval)
        print(f"[ERROR] Timeout: Blossom server on port {port} not responding.")
        return False

    def analyze_music_segment(self, offset, duration):
        """Analyze a segment of the music starting at `offset` for `duration` seconds."""
        y, sr = librosa.load(self.music_path, offset=offset, duration=duration)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        energy = sum(abs(y)) / len(y)

        print(f"[INFO] Segment @ {offset:.1f}s - BPM: {tempo:.2f}, Energy: {energy:.4f}")
        return 'happy' if tempo > 100 and energy > 0.1 else 'sad'

    def send_sequence(self, sequence_str):
        """Send sequence to the Dancer server."""
        url = f"http://{HOST}:{DANCER_PORT}/sequence"
        print(f"[INFO] Sending sequence to {url}: {sequence_str}")

        try:
            response = requests.post(url, data=sequence_str)
            if response.status_code == 200:
                print("[SUCCESS] Sequence sent successfully!")
                return True
            else:
                print(f"[ERROR] Received status code {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to send sequence: {e}")
            return False

    def start(self):
        """Start the dancer and continuously adjust mood based on the music."""
        print("[INFO] Launching DANCER server...")
        self.dancer_server_proc = subprocess.Popen([
            "python3", "blossom_public/start.py",
            "--host", HOST,
            "--port", str(DANCER_PORT),
            "--browser-disable"
        ])

        if not self.wait_for_server_ready(DANCER_PORT):
            self.stop()
            sys.exit("[ERROR] DANCER server failed to start.")

        self.is_running = True
        music_duration = librosa.get_duration(filename=self.music_path)
        offset = 0

        print("\n[INFO] Type 'STOP DANCING' and press Enter to stop the robot.\n")

        try:
            while self.is_running and offset < music_duration:
                mood = self.analyze_music_segment(offset, self.analysis_interval)

                if mood != self.current_mood:
                    self.current_mood = mood
                    self.send_sequence(mood)

                offset += self.analysis_interval
                time.sleep(self.analysis_interval)

                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    command = sys.stdin.readline().strip().upper()
                    if command == "STOP DANCING":
                        print("[INFO] Stop command received.")
                        break

        except KeyboardInterrupt:
            print("\n[INFO] Interrupted manually.")
        finally:
            self.stop()

    def stop(self):
        """Stop the dancer and shut down the server."""
        self.is_running = False
        if self.dancer_server_proc:
            print("[INFO] Shutting down DANCER server...")
            self.dancer_server_proc.terminate()
            self.dancer_server_proc.wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Blossom dancing controller with live mood detection")
    parser.add_argument("--music", type=str, required=True, help="Path to the music file (e.g., mp3 or wav)")
    parser.add_argument("--interval", type=int, default=5, help="Analysis interval in seconds")
    args = parser.parse_args()

    dancer = Dancer(music_path=args.music, analysis_interval=args.interval)
    dancer.start()
