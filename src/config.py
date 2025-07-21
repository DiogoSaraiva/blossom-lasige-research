import socket

MIMETIC_PORT = 8000
DANCER_PORT = 8001
MIRROR_VIDEO=True
PYTHON = ".venv/bin/python"

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

HOST = get_local_ip()


@staticmethod
def url_mimetic(path: str = "") -> str:
    return f"http://{HOST}:{MIMETIC_PORT}/{path.lstrip('/')}"

@staticmethod
def url_dancer(path: str = "") -> str:
    return f"http://{HOST}:{DANCER_PORT}/{path.lstrip('/')}"