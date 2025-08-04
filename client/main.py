import sys
from PyQt6.QtWidgets import QApplication
from client.windows.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        with open('style.qss', 'r', encoding='utf-8') as f:
            style_sheet = f.read()
        app.setStyleSheet(style_sheet)
        print("样式加载成功！")
    except FileNotFoundError:
        print("警告: 未找到 style.qss 文件，将使用默认样式。")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())