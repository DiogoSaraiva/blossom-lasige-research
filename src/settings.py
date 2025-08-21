from dataclasses import dataclass, field
from typing import Dict

from PyQt6.QtCore import QSettings

from src.utils import get_local_ip, compact_timestamp


@dataclass
class Settings:
    # Base
    study_id: str = compact_timestamp()
    host: str = get_local_ip()
    blossom_one_device: str = "/dev/ttyACM0"
    blossom_two_device: str = "/dev/ttyACM1"
    blossom_one_port: int = 8001
    blossom_two_port: int = 8002
    mirror_video: bool = True
    flip_blossom: bool = True
    output_directory: str = "./output"

    # Gaze Tracking
    left_threshold: float = 0.45
    right_threshold: float = 0.55

    # Mimetic
    alpha_map: Dict[str, float] = field(default_factory=lambda: {"x": 0.4, "y": 0.4, "z": 0.4, "h": 0.2, "e": 0.2})
    send_rate: int = 5
    send_threshold: float = 2.0
    target_fps: int = 30

    # Dancer
    music_directory: str = "./dancer/musics"
    analysis_interval: float = 5.0



class SettingManager:
    ORG = "LASIGE"
    APP = "BlossomResearch"

    def __init__(self):
        self.qs = QSettings(self.ORG, self.APP)

    def load(self) -> Settings:
        settings = Settings()

        # Base
        settings.study_id = self.qs.value("study_id")
        settings.host = self.qs.value("host", settings.host, str)
        settings.blossom_one_port = int(self.qs.value("blossom_one_port", settings.blossom_one_port))
        settings.blossom_two_port = int(self.qs.value("blossom_two_port", settings.blossom_two_port))
        settings.mirror_video = self.qs.value("mirror_video", settings.mirror_video)
        settings.flip_blossom = self.qs.value("flip_blossom", settings.flip_blossom)
        settings.output_directory = self.qs.value("output_directory", settings.output_directory)

        settings.blossom_one_device = self.qs.value("blossom_one_device", settings.blossom_one_device)
        settings.blossom_two_device = self.qs.value("blossom_two_device", settings.blossom_two_device)

        # Gaze Tracking
        settings.left_threshold = float(self.qs.value("left_threshold", settings.left_threshold))
        settings.right_threshold = float(self.qs.value("right_threshold", settings.right_threshold))

        # Mimetic
        settings.alpha_map = {"x": self.qs.value("x", 0.2), "y": self.qs.value("y", 0.2), "z": self.qs.value("z", 0.2),
                              "h": self.qs.value("h", 0.2), "e": self.qs.value("e", 0.2)}

        settings.send_rate = int(self.qs.value("send_rate", settings.send_rate))
        settings.send_threshold = float(self.qs.value("send_threshold", settings.send_threshold))
        settings.target_fps = int(self.qs.value("target_fps", settings.target_fps))

        # Dancer
        settings.music_directory = self.qs.value("music_directory", settings.music_directory)
        settings.analysis_interval = float(self.qs.value("analysis_interval", settings.analysis_interval))

        return settings

    def save(self, settings: Settings):
        # Base
        self.qs.setValue("study_id", settings.study_id)
        self.qs.setValue("blossom_one_device", settings.blossom_one_device)
        self.qs.setValue("blossom_two_device", settings.blossom_two_device)
        self.qs.setValue("host", settings.host)
        self.qs.setValue("blossom_one_port", settings.blossom_one_port)
        self.qs.setValue("blossom_two_port", settings.blossom_two_port)
        self.qs.setValue("mirror_video", settings.mirror_video)
        self.qs.setValue("flip_blossom", settings.flip_blossom)
        self.qs.setValue("output_directory", settings.output_directory)


        # Gaze Tracking
        self.qs.setValue("left_threshold", settings.left_threshold)
        self.qs.setValue("right_threshold", settings.right_threshold)

        # Mimetic
        self.qs.setValue("alpha_map", settings.alpha_map)
        self.qs.setValue("send_threshold", settings.send_threshold)
        self.qs.setValue("send_rate", settings.send_rate)
        self.qs.setValue("target_fps", settings.target_fps)

        # Dancer
        self.qs.setValue("music_directory", settings.music_directory)
        self.qs.setValue("analysis_interval", settings.analysis_interval)

        self.qs.sync()




