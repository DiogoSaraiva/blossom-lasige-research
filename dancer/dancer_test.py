import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dancer.dancer import Dancer
from src.logging_utils import Logger

logger = Logger("logs/test.log", level="debug")
dancer = Dancer(host="127.0.0.1", port=5000, music_dir="blossom-lasige-research/dancer/musics", logger=logger)
dancer.start()

