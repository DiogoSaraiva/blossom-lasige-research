import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from dancer.dancer import Dancer
from src.logging_utils import Logger

logger = Logger("../output/test.log", mode="system")
logger.set_system_log_level("debug")
dancer = Dancer(music_dir="../dancer/musics", logger=logger, mic_sr=22050, mode="audio")
dancer.start()

