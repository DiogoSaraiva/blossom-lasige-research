import sys
import os
import subprocess
import time
import requests
import argparse
import librosa
import select

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.config import HOST, DANCER_PORT

####  comentario

def wait_for_server_ready(port, timeout=10.0, interval=0.5):
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


def analyze_music(file_path):
    """Analyze music to determine mood (happy/sad)."""
    y, sr = librosa.load(file_path)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    energy = sum(abs(y)) / len(y)

    print(f"[INFO] Estimated BPM: {tempo:.2f}")
    print(f"[INFO] Average energy: {energy:.4f}")

    return 'happy' if tempo > 100 and energy > 0.1 else 'sad'


def send_sequence(sequence_str):
    """Send sequence to the dancer server."""
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Blossom dancing controller")
    parser.add_argument("--music", type=str, required=True,
                        help="Path to the music file (e.g., mp3 or wav)")
    args = parser.parse_args()

    # Start the DANCER server
    print("[INFO] Launching DANCER server...")
    dancer_server_proc = subprocess.Popen([
        "python3", "blossom_public/start.py",
        "--host", HOST,
        "--port", str(DANCER_PORT),
        "--browser-disable"
    ])

    # Wait for server to be ready
    if not wait_for_server_ready(DANCER_PORT):
        dancer_server_proc.terminate()
        sys.exit("[ERROR] DANCER server failed to start.")

    # Music analysis
    mood = analyze_music(args.music)
    print(f"[RESULT] Music mood detected: {mood}")

    print("\n[INFO] Type 'STOP DANCING' and press Enter to stop the robot.\n")

    try:
        while True:
            if send_sequence(mood):
                print(f"[INFO] Waiting for sequence '{mood}' to finish...")
                time.sleep(5)  # Adjust to sequence length
            else:
                print("[WARN] Sequence not sent, retrying in 2 seconds...")
                time.sleep(2)

            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                command = sys.stdin.readline().strip().upper()
                if command == "STOP DANCING":
                    print("[INFO] Stop command received. Exiting...")
                    break

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted manually. Stopping robot.")
    finally:
        print("[INFO] Shutting down DANCER server...")
        dancer_server_proc.terminate()
        dancer_server_proc.wait()
