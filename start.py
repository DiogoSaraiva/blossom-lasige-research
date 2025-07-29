import subprocess
import time
import requests
from src.config import HOST, MIMETIC_PORT, DANCER_PORT, PYTHON

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

# Wait for both to be ready
if not wait_for_server_ready(MIMETIC_PORT) or not wait_for_server_ready(DANCER_PORT):
    mimetic_server_proc.terminate()
    dancer_server_proc.terminate()
    exit("One or both servers failed to start.")

# Launch mimetic controller
print("Launching mimetic/start.py...")
mimetic_proc = subprocess.Popen(["python3", "mimetic/start.py"])

# Launch dancer controller
print("Launching dancer/start.py...")
dancer_proc = subprocess.Popen(["python3", "dancer/start.py"])

try:
    print("\n Press [q] then [Enter] at any time to stop all processes.\n")
    while True:
        user_input = input()
        if user_input.strip().lower() == "q":
            print("Stopping all processes...")
            break
except KeyboardInterrupt:
    print("Interrupted manually.")

# Clean up all processes with status verification
for proc in [mimetic_proc, mimetic_server_proc, dancer_proc, dancer_server_proc]:
    if proc.poll() is None:
        proc.terminate()
    proc.wait()