import argparse
import time
import requests
import librosa
from src.config import HOST, DANCER_PORT


def analyze_music(file_path):
    """
    Analyze the music file to determine mood (happy/sad)
    based on tempo (BPM) and average energy.
    """
    y, sr = librosa.load(file_path)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    energy = sum(abs(y)) / len(y)

    print(f"[INFO] Estimated BPM: {tempo:.2f}")
    print(f"[INFO] Average energy: {energy:.4f}")

    if tempo > 100 and energy > 0.1:
        return 'happy'
    else:
        return 'sad'


def send_sequence(sequence_str):
    """
    Send the selected sequence to the dancer server via HTTP POST.
    """
    url = f"http://{HOST}:{DANCER_PORT}/sequence"
    print(f"[INFO] Sending sequence to {url}: {sequence_str}")

    try:
        response = requests.post(url, data=sequence_str)
        if response.status_code == 200:
            print("[SUCCESS] Sequence sent successfully!")
        else:
            print(f"[ERROR] Received status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to send sequence: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Blossom dancing controller")
    parser.add_argument("--music", type=str, required=True,
                        help="Path to the music file (e.g., mp3 or wav)")
