import os
from datetime import datetime
import socket
from typing import Optional


def resource_path(relative_path: str) -> str:
    """Return the absolute path to a project resource.

    Works in normal dev mode and inside an AppImage (where PYTHONPATH points
    to $APPDIR/usr/src, so __file__ resolves within the mounted image).
    """
    # Project root is one level up from src/
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)


def compact_timestamp() -> str:
    """
    Generates a compact timestamp for use in file/folder names.

    Returns:
        str: Timestamp in the format YYYYMMDD-HHMMSSmmm
    """
    now = datetime.now()
    return now.strftime("%Y%m%d-%H%M%S") + f"{int(now.microsecond / 1000):03d}"

def get_local_ip() -> Optional[str]:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()
