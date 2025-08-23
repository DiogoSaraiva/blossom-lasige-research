import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dancer.dancer import Dancer
from src.logging_utils import Logger

logger = Logger("logs/test.log", mode="system")
logger.set_system_log_level("debug")
dancer = Dancer(music_dir="dancer/musics", logger=logger, mic_sr=22050, mode="audio")
dancer.start()

