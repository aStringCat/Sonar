from PyQt6.QtWidgets import QMainWindow, QMessageBox, QFileDialog
from PyQt6.QtCore import QThread, QObject, pyqtSignal, pyqtSlot, QTimer
import datetime
from main_window_ui import Ui_MainWindow

class Worker(QObject):
    finished = pyqtSignal()
    success = pyqtSignal(list)  # 假设成功后返回一个结果列表，还没写
    error = pyqtSignal(str)

    def __init__(self, mode, paths):
        super().__init__()
        self.mode = mode
        self.paths = paths

    @pyqtSlot()
    def run(self):
        print(f"开始执行查重任务...")
        print(f"模式: {'两两互查' if self.mode == 0 else '一对多'}")
        print(f"路径: {self.paths}")

        #


        self.finished.emit()

# --- Main_window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.connect_signals()
        self.display_login_time()
        # 默认禁用，选择文件夹/文件后才启用
        self.ui.btn_start_analysis_mode1.setEnabled(False)
        self.ui.btn_start_analysis_mode2.setEnabled(False)

        self.thread = None
        self.worker = None

    def display_login_time(self):
        current_time = datetime.datetime.now()
        time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
        self.ui.label_login_time_2.setText(f"登录时间：{time_str}")

    def connect_signals(self):
        # 0代表互查模式，1代表一对多模式
        self.ui.pushButton.clicked.connect(lambda: self.change_mode(0))  # 文件夹内互查
        self.ui.pushButton_2.clicked.connect(lambda: self.change_mode(1))  # 一对多

        self.ui.btn_select_folder.clicked.connect(self.select_pairwise_directory)  # 互查模式-选择文件夹
        self.ui.btn_select_folder_2.clicked.connect(self.select_one_to_many_file)  # 一对多-选择文件
        self.ui.btn_select_folder_3.clicked.connect(self.select_one_to_many_directory)  # 一对多-选择文件夹

        # --- 开始分析按钮 ---
        self.ui.btn_start_analysis_mode1.clicked.connect(self.start_analysis)
        self.ui.btn_start_analysis_mode2.clicked.connect(self.start_analysis)

        # --- 页面跳转按钮 ---
        self.ui.home.clicked.connect(self.go_to_home_page)  # "返回主页" 按钮
        self.ui.btn_back.clicked.connect(self.go_to_dashboard_page)  # "返回结果列表" 按钮

        # --- 表格点击跳转 ---
        self.ui.table_history.cellClicked.connect(self.go_to_details_page)

    def select_pairwise_directory(self):
        """两两互查选择文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "请选择要进行互查的代码文件夹")
        if folder_path:
            self.ui.le_folder_path.setText(folder_path)
            self.ui.btn_start_analysis_mode1.setEnabled(True)  # 选择后启用分析按钮

    def select_one_to_many_file(self):
        """一对多选择基准文件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "请选择基准代码文件", "", "Python Files (*.py)")
        if file_path:
            self.ui.le_folder_path_2.setText(file_path)
            self.update_one_to_many_analysis_button_state()  # 检查是否可以启用分析按钮

    def select_one_to_many_directory(self):
        """一对多选择对比文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "请选择要进行对比的代码文件夹")
        if folder_path:
            self.ui.le_folder_path_3.setText(folder_path)
            self.update_one_to_many_analysis_button_state()  # 检查是否可以启用分析按钮

    def update_one_to_many_analysis_button_state(self):
        base_file_ok = bool(self.ui.le_folder_path_2.text())
        compare_dir_ok = bool(self.ui.le_folder_path_3.text())
        self.ui.btn_start_analysis_mode2.setEnabled(base_file_ok and compare_dir_ok)

    def change_mode(self, index):
        self.ui.stackedWidget.setCurrentIndex(index)
        print(f"切换到模式: {index}")

    def start_analysis(self):
        current_mode = self.ui.stackedWidget.currentIndex()
        paths = {}

        if current_mode == 0:
            paths['directory'] = self.ui.le_folder_path.text()
        else:
            paths['base_file'] = self.ui.le_folder_path_2.text()
            paths['compare_dir'] = self.ui.le_folder_path_3.text()

        # 禁用交互按钮，防止重复点击
        self.ui.btn_start_analysis_mode1.setEnabled(False)
        self.ui.btn_start_analysis_mode2.setEnabled(False)
        self.ui.statusbar.showMessage("正在分析中，请稍候...")


        self.thread = QThread()
        self.worker = Worker(current_mode, paths)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.success.connect(self.on_analysis_success)
        self.worker.error.connect(self.on_analysis_error)

        self.thread.start()

    @pyqtSlot(list)
    def on_analysis_success(self, results):
        print("分析成功，结果为:", results)
        self.ui.statusbar.showMessage("分析完成！", 5000)  

        # 填充显示表格，待完成
        

        # 跳转到结果看板页面 (page_3, 索引为1)
        self.go_to_dashboard_page()
        # 启用分析按钮
        self.ui.btn_start_analysis_mode1.setEnabled(True) 
        self.ui.btn_start_analysis_mode2.setEnabled(True)

    @pyqtSlot(str)
    def on_analysis_error(self, error_message):
        self.ui.statusbar.showMessage(f"分析出错: {error_message}", 5000)
        QMessageBox.critical(self, "分析出错", error_message)
        # 启用分析按钮
        self.ui.btn_start_analysis_mode1.setEnabled(True)
        self.ui.btn_start_analysis_mode2.setEnabled(True)

    def go_to_home_page(self):
        self.ui.main_stack.setCurrentIndex(0)

    def go_to_dashboard_page(self):
        self.ui.main_stack.setCurrentIndex(1)

    def go_to_details_page(self, row, column):
        print(f"用户点击了历史记录的第 {row + 1} 行，准备跳转到详情页...")

        # 这里只实现跳转，还要加载详情等
        self.ui.main_stack.setCurrentIndex(2)
