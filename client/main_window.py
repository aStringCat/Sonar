from api_client import get_greeting_from_api

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QLineEdit, QLabel, QMessageBox
)
from PyQt6.QtCore import (QThread, QObject, pyqtSignal, pyqtSlot)


class Worker(QObject):
    finished = pyqtSignal()
    success = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, name_to_greet):
        super().__init__()
        self.name_to_greet = name_to_greet

    @pyqtSlot()
    def run(self):
        data, error_message = get_greeting_from_api(self.name_to_greet)

        if error_message:
            self.error.emit(error_message)
        else:
            message = data.get("message", "Received an invalid response from the API")
            self.success.emit(message)

        self.finished.emit()


# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PyQt6 + FastAPI Example (API Abstraction)")
        self.setGeometry(100, 100, 450, 200)

        # Create UI components
        self.central_widget = QWidget()
        self.layout = QVBoxLayout(self.central_widget)

        self.label_info = QLabel("Enter your name below and click the button:")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Fastapi")
        self.greet_button = QPushButton("Get Greeting From Backend")
        self.result_label = QLabel("Results will be shown here...")
        self.result_label.setStyleSheet("color: blue; font-style: italic;")

        self.layout.addWidget(self.label_info)
        self.layout.addWidget(self.name_input)
        self.layout.addWidget(self.greet_button)
        self.layout.addWidget(self.result_label)

        self.setCentralWidget(self.central_widget)

        self.greet_button.clicked.connect(self.call_backend_api)

        self.thread = None
        self.worker = None

    def call_backend_api(self):
        user_name = self.name_input.text().strip()
        if not user_name:
            user_name = "World"

        self.greet_button.setEnabled(False)
        self.result_label.setText("Contacting backend server...")

        self.thread = QThread()
        self.worker = Worker(user_name)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.success.connect(self.on_api_success)
        self.worker.error.connect(self.on_api_error)

        self.thread.start()

    @pyqtSlot(str)
    def on_api_success(self, message):
        self.result_label.setText(f"Backend Response: {message}")
        self.result_label.setStyleSheet("color: blue; font-style: italic;")
        self.greet_button.setEnabled(True)

    @pyqtSlot(str)
    def on_api_error(self, error_message):
        self.result_label.setText(f"Error: {error_message}")
        self.result_label.setStyleSheet("color: red; font-style: italic;")
        self.greet_button.setEnabled(True)

        QMessageBox.critical(self, "API Error", error_message)
