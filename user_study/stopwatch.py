import sys
import time
import termios
import tty
import select

POLL_SLEEP = 0.005
HOLD_GRACE = 0.18

class RawTerminal:
    def __enter__(self):
        self.fd = sys.stdin.fileno()
        self.old = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)  # ler sem Enter
        return self
    def __exit__(self, exc_type, exc, tb):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)
        return False

def get_key_nonblock(timeout=0.0):
    dr, _, _ = select.select([sys.stdin], [], [], timeout)
    if dr:
        ch = sys.stdin.read(1)
        return ch.lower() if ch else None
    return None

class TimeCounter:
    def __init__(self):
        self.time_mimic = 0.0
        self.time_dancer = 0.0
        self.active = None
        now = time.monotonic()
        self.last_loop = now
        self.last_key  = now
        self.running = True

    def _credit(self, dt: float):
        if self.active == 'm':
            self.time_mimic += dt
        elif self.active == 'd':
            self.time_dancer += dt

    def add_to(self, mode: str):
        self.active = mode
        print(f"→ Active: {'Mimetic' if mode=='m' else 'Dancer '} | "
              f"M={self.time_mimic:.3f}s D={self.time_dancer:.3f}s")

    def reset(self):
        self.time_mimic = 0.0
        self.time_dancer = 0.0
        now = time.monotonic()
        self.last_loop = now
        self.last_key = now
        self.active = None
        print("- Reset: M=0.000s, D=0.000s")

    def loop(self):
        print("RAW input mode active. Keys: [m]=Mimetic  [d]=Dancer  [r]=reset  [q]=quit")
        print("Each key sums the time between loops to the chosen category.")
        with RawTerminal():
            try:
                while self.running:
                    now = time.monotonic()
                    dt = now - self.last_loop
                    self.last_loop = now

                    if self.active is not None and (now - self.last_key) <= HOLD_GRACE:
                        self._credit(dt)

                    while True:
                        key = get_key_nonblock(0.0)
                        if key is None:
                            break
                        self.last_key = now
                        if key == 'q':
                            self.running = False
                        elif key == 'r':
                            self.reset()
                        elif key in ('m', 'd'):
                            self.add_to(key)

                    time.sleep(POLL_SLEEP)

            except KeyboardInterrupt:
                self.running = False

        print("\n--- Final result ---")
        print(f"Time Mimetic: {self.time_mimic:.3f} s")
        print(f"Time Dancer:  {self.time_dancer:.3f} s")

if __name__ == "__main__":
    TimeCounter().loop()
