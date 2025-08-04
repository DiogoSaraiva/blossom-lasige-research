import subprocess
import time
import requests
import sys
import librosa
from src.config import HOST, MIMETIC_PORT, DANCER_PORT

def wait_for_server_ready(port, timeout=10.0, interval=0.5):
    url = f"http://{HOST}:{port}/"
    print(f"Waiting for Blossom server at {url}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            r = requests.get(url)
            if r.status_code == 200:
                print(f"Blossom server on port {port} is ready.")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(interval)
    print(f"Timeout: Blossom server on port {port} not responding.")
    return False

def analisar_musica(file_path):
    y, sr = librosa.load(file_path)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    energy = sum(abs(y)) / len(y)

    print(f"BPM estimado: {tempo:.2f}")
    print(f"Energia média: {energy:.4f}")

    if tempo > 100 and energy > 0.1:
        return 'happy'
    else:
        return 'sad'

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❗ Uso: python start_dancing.py caminho/para/musica.mp3")
        sys.exit(1)

    music_file = sys.argv[1]
    mood = analisar_musica(music_file)

    # Define as sequências conforme quiseres
    happy_seq = "dance1 dance2 dance3"
    sad_seq = "dance4 dance5 dance6"

    sequence = happy_seq if mood == 'happy' else sad_seq
    print(f"🎵 Detetada música '{mood}' → sequência: {sequence}")

    # Launch DANCER server
    print("Launching blossom_public/start.py (DANCER)...")
    dancer_server_proc = subprocess.Popen([
        "python3", "blossom_public/start.py",
        "--host", HOST,
        "--port", str(DANCER_PORT),
        "--browser-disable"
    ])

    # Launch MIMETIC server
    print("Launching blossom_public/start.py (MIMETIC)...")
    mimetic_server_proc = subprocess.Popen([
        "python3", "blossom_public/start.py",
        "--host", HOST,
        "--port", str(MIMETIC_PORT),
        "--browser-disable"
    ])

    # Wait for servers
    if not wait_for_server_ready(MIMETIC_PORT) or not wait_for_server_ready(DANCER_PORT):
        mimetic_server_proc.terminate()
        dancer_server_proc.terminate()
        exit("One or both servers failed to start.")

    # Launch mimetic controller
    print("Launching mimetic/start.py...")
    mimetic_proc = subprocess.Popen(["python3", "mimetic/start.py"])

    # Launch dancer controller passando a sequência como argumento
    print("Launching dancer/start.py...")
    dancer_proc = subprocess.Popen([
        "python3", "dancer/start.py", "--sequence", sequence
    ])

    try:
        print("\n Press [q] then [Enter] at any time to stop all processes.\n")
        while True:
            user_input = input()
            if user_input.strip().lower() == "q":
                print("Stopping all processes...")
                break
    except KeyboardInterrupt:
        print("Interrupted manually.")

    # Clean up
    for proc in [mimetic_proc, mimetic_server_proc, dancer_proc, dancer_server_proc]:
        if proc.poll() is None:
            proc.terminate()
        proc.wait()
