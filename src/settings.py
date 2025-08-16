from dataclasses import dataclass
from PyQt6.QtCore import QSettings

from src.utils import get_local_ip, compact_timestamp


@dataclass
class Settings:
    host: str = get_local_ip()
    mimetic_port: int = 8001
    dancer_port: int = 8002
    mirror_video: bool = True
    target_fps: float = 30
    output_directory: str = "./output"
    flip_blossom: bool = True
    left_threshold: float = 0.45
    right_threshold: float = 0.55
    study_id: str = compact_timestamp()


class SettingManager:
    ORG = "LASIGE"
    APP = "BlossomResearch"

    def __init__(self):
        self.qs = QSettings(self.ORG, self.APP)

    def load(self) -> Settings:
        settings = Settings()
        settings.host = self.qs.value("host", settings.host, str)
        settings.mimetic_port = int(self.qs.value("mimetic_port", settings.mimetic_port))
        settings.dancer_port = int(self.qs.value("dancer_port", settings.dancer_port))
        settings.mirror_video = self.qs.value("mirror_video", settings.mirror_video)
        settings.target_fps = int(self.qs.value("target_fps", settings.target_fps))
        settings.output_directory = self.qs.value("output_directory", settings.output_directory)
        settings.flip_blossom = self.qs.value("flip_blossom", settings.flip_blossom)
        settings.left_threshold = float(self.qs.value("left_threshold", settings.left_threshold))
        settings.right_threshold = float(self.qs.value("right_threshold", settings.right_threshold))

        return settings

    def save(self, settings: Settings):
        self.qs.setValue("host", settings.host)
        self.qs.setValue("mimetic_port", settings.mimetic_port)
        self.qs.setValue("dancer_port", settings.dancer_port)
        self.qs.setValue("mirror_video", settings.mirror_video)
        self.qs.setValue("target_fps", settings.target_fps)
        self.qs.setValue("output_directory", settings.output_directory)
        self.qs.setValue("flip_blossom", settings.flip_blossom)
        self.qs.setValue("left_threshold", settings.left_threshold)
        self.qs.setValue("right_threshold", settings.right_threshold)
        self.qs.sync()




