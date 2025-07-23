import datetime
import os
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QTableWidgetItem
from PyQt6.QtCore import QThread, pyqtSlot
from PyQt6.QtGui import QAction

from client.ui.main_window_ui import UiMainWindow
from client.threads.worker import AnalysisWorker


class MainWindow(QMainWindow, UiMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui(self)
        self.setWindowTitle("Sonar - Code Plagiarism Detection")

        self._create_menu_bar()
        self._setup_results_table()
        self.connect_signals()
        self.display_login_time()

        self.btn_start_analysis_mode1.setEnabled(False)
        self.btn_start_analysis_mode2.setEnabled(False)
        self.thread = None

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件")
        start_pairwise_action: QAction = QAction("开始两两互查...", self)
        start_pairwise_action.triggered.connect(self.select_pairwise_directory)
        file_menu.addAction(start_pairwise_action)
        start_one_to_many_action: QAction = QAction("开始一对多查重...", self)
        start_one_to_many_action.triggered.connect(self.select_one_to_many_file)
        file_menu.addAction(start_one_to_many_action)
        file_menu.addSeparator()
        exit_action: QAction = QAction("退出", self)
        exit_action.setShortcut("Cmd+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        view_menu = menu_bar.addMenu("视图")
        go_home_action: QAction = QAction("回到主页", self)
        go_home_action.triggered.connect(self.go_to_home_page)
        view_menu.addAction(go_home_action)
        go_dashboard_action: QAction = QAction("查看查重看板", self)
        go_dashboard_action.triggered.connect(self.go_to_dashboard_page)
        view_menu.addAction(go_dashboard_action)
        help_menu = menu_bar.addMenu("帮助")
        about_action: QAction = QAction("关于 Sonar", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _setup_results_table(self):
        self.table_history.setColumnCount(3)
        self.table_history.setHorizontalHeaderLabels(["文件1", "文件2", "相似度"])
        self.table_history.setColumnWidth(0, 250)
        self.table_history.setColumnWidth(1, 250)
        self.table_history.setColumnWidth(2, 100)

    def connect_signals(self):
        self.pushButton.clicked.connect(lambda: self.change_mode(0))
        self.pushButton_2.clicked.connect(lambda: self.change_mode(1))
        self.btn_select_folder.clicked.connect(self.select_pairwise_directory)
        self.btn_select_folder_2.clicked.connect(self.select_one_to_many_file)
        self.btn_select_folder_3.clicked.connect(self.select_one_to_many_directory)
        self.btn_start_analysis_mode1.clicked.connect(self.start_analysis)
        self.btn_start_analysis_mode2.clicked.connect(self.start_analysis)
        self.home.clicked.connect(self.go_to_home_page)
        self.btn_back.clicked.connect(self.go_to_dashboard_page)
        self.table_history.cellDoubleClicked.connect(self.go_to_details_page)

    def display_login_time(self):
        current_time = datetime.datetime.now()
        time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
        self.label_login_time_2.setText(f"登录时间：{time_str}")

    def change_mode(self, index):
        self.stackedWidget.setCurrentIndex(index)

    def select_pairwise_directory(self):
        self.change_mode(0)
        folder_path = QFileDialog.getExistingDirectory(self, "选择要进行互查的代码文件夹")
        if folder_path:
            self.le_folder_path.setText(folder_path)
            self.btn_start_analysis_mode1.setEnabled(True)

    def select_one_to_many_file(self):
        self.change_mode(1)
        file_path, _ = QFileDialog.getOpenFileName(self, "选择基准代码文件", "", "Python Files (*.py)")
        if file_path:
            self.le_folder_path_2.setText(file_path)
            self.update_one_to_many_analysis_button_state()

    def select_one_to_many_directory(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择要进行对比的代码文件夹")
        if folder_path:
            self.le_folder_path_3.setText(folder_path)
            self.update_one_to_many_analysis_button_state()

    def update_one_to_many_analysis_button_state(self):
        base_file_ok = bool(self.le_folder_path_2.text())
        compare_dir_ok = bool(self.le_folder_path_3.text())
        self.btn_start_analysis_mode2.setEnabled(base_file_ok and compare_dir_ok)

    def start_analysis(self):
        current_mode = self.stackedWidget.currentIndex()
        file_paths = []
        try:
            if current_mode == 0:
                dir_path = self.le_folder_path.text()
                if not dir_path: raise ValueError("请先选择一个文件夹。")
                file_paths = [os.path.join(dir_path, f) for f in os.listdir(dir_path) if f.endswith('.py')]
            else:
                # 1对多模式，也发送一个文件列表给后端
                base_file = self.le_folder_path_2.text()
                compare_dir = self.le_folder_path_3.text()
                if not base_file or not compare_dir: raise ValueError("请选择基准文件和对比文件夹。")
                # 注意：这里我们仍将所有文件作为列表发送，后端api.py中的/check接口可以处理
                file_paths.append(base_file)
                dir_files = [os.path.join(compare_dir, f) for f in os.listdir(compare_dir) if f.endswith('.py')]
                file_paths.extend(dir_files)

            if len(file_paths) < 2:
                raise ValueError("需要至少两个 Python 文件才能进行比较。")

        except Exception as e:
            QMessageBox.warning(self, "输入错误", str(e))
            return

        self.btn_start_analysis_mode1.setEnabled(False)
        self.btn_start_analysis_mode2.setEnabled(False)

        self.thread: QThread = QThread()
        # 创建 Worker 时不再需要传递 api_client
        worker = AnalysisWorker(file_paths)
        worker.moveToThread(self.thread)

        worker.progress.connect(self.statusbar.showMessage)
        worker.success.connect(self.on_analysis_success)
        worker.error.connect(self.on_analysis_error)
        worker.finished.connect(self.thread.quit)
        worker.finished.connect(worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.started.connect(worker.run)
        self.thread.start()

    @pyqtSlot(list)
    def on_analysis_success(self, results):
        self.statusbar.showMessage(f"分析完成！找到 {len(results)} 个相似对。", 5000)
        self.populate_results_table(results)
        self.go_to_dashboard_page()
        self.btn_start_analysis_mode1.setEnabled(True)
        self.update_one_to_many_analysis_button_state()

    @pyqtSlot(str)
    def on_analysis_error(self, error_message):
        QMessageBox.critical(self, "分析出错", error_message)
        self.statusbar.showMessage(f"分析出错。", 5000)
        self.btn_start_analysis_mode1.setEnabled(True)
        self.update_one_to_many_analysis_button_state()

    def populate_results_table(self, results: list):
        self.table_history.setRowCount(0)
        for row, item in enumerate(results):
            self.table_history.insertRow(row)
            self.table_history.setItem(row, 0, QTableWidgetItem(item.get('file1')))
            self.table_history.setItem(row, 1, QTableWidgetItem(item.get('file2')))
            similarity = item.get('similarity', 0)
            self.table_history.setItem(row, 2, QTableWidgetItem(f"{similarity:.2%}"))

    def go_to_home_page(self):
        self.main_stack.setCurrentIndex(0)

    def go_to_dashboard_page(self):
        self.main_stack.setCurrentIndex(1)

    def go_to_details_page(self, row, _column):
        file1 = self.table_history.item(row, 0).text()
        file2 = self.table_history.item(row, 1).text()
        QMessageBox.information(self, "详情", f"您选择了查看 {file1} 和 {file2} 的详细对比。\n（此处将加载详细对比页面）")
        self.main_stack.setCurrentIndex(2)

    def _show_about_dialog(self):
        QMessageBox.about(self, "关于 Sonar", "<h2>Sonar - 代码相似度检测工具</h2><p>版本 1.0</p>")