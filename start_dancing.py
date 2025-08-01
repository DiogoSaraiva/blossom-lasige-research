import sounddevice as sd
import numpy as np
import time


def start_dancing(robot, duration=10):
    """
    Listen to the microphone, detect music mood and dance:
    - if happy/fast → play 'happy' sequence
    - if sad/slow  → play 'sad' sequence
    Args:
        robot: the robot to dance
        duration: how long to listen before deciding (seconds)
    """
    print("Listening to music...")

    sample_rate = 16000  # sampling rate
    seconds = duration

    try:
        # record audio from mic
        recording = sd.rec(int(seconds * sample_rate), samplerate=sample_rate, channels=1, dtype='float64')
        sd.wait()
    except Exception as e:
        print(f"Could not access microphone: {e}")
        return

    # simple mood detection: compute energy
    energy = np.linalg.norm(recording) / len(recording)
    print(f"Detected energy: {energy}")

    # choose mood based on threshold (adjust as needed)
    mood = "happy" if energy > 0.01 else "sad"

    print(f"Dancing with mood: {mood}")

    # stop current sequence if running
    if robot.seq_stop:
        robot.seq_stop.set()
        time.sleep(0.1)  # wait a bit for previous thread to stop

    # start new sequence
    seq_thread = robot.play_recording(mood, idler=False)
    return seq_thread
