import sys
from PyQt6.QtWidgets import QApplication
from client.views.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Sonar")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())