from src.main_window import MainWindow
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
import os
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blossom.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())