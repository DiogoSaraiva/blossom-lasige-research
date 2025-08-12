import sys

from src.utils import get_local_ip

MIMETIC_PORT = 8000
DANCER_PORT = 8001
MIRROR_VIDEO=True
PYTHON = sys.executable
TARGET_FPS = 30
OUTPUT_FOLDER = "./output"
HOST = get_local_ip()
FLIP_BLOSSOM = True
LEFT_THRESHOLD = 0.45
RIGHT_THRESHOLD = 0.55

def url_mimetic(path: str = "") -> str:
    return f"http://{HOST}:{MIMETIC_PORT}/{path.lstrip('/')}"

def url_dancer(path: str = "") -> str:
    return f"http://{HOST}:{DANCER_PORT}/{path.lstrip('/')}"