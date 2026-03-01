import src.resources_rc  # noqa: F401 — registers :/icon/blossom.png
from src.main_window import MainWindow
from PyQt6.QtWidgets import QApplication
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Blossom LASIGE Research")
    app.setDesktopFileName("blossom-lasige-research")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())