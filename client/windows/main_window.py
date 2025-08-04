from PyQt6 import QtGui, QtCore, QtWidgets
import os
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QVBoxLayout
from PyQt6.QtCore import QThread, QObject, pyqtSignal, pyqtSlot, Qt
import datetime
from client.ui.main_window_ui import Ui_MainWindow
# 修改这一行
from client.threads.worker import Worker, HistoryWorker

# 修改这一行，加入 QTableWidget, QHeaderView
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QVBoxLayout, QTableWidget, QHeaderView
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon
import qtawesome as qta
# --- Main_window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # 【修正后】的代码块，解决了布局冲突和属性错误
        # --- 初始化历史记录页面 ---
        # 1. 创建一个新的表格控件
        self.history_table = QTableWidget()

        # 2. 从UI文件中获取 page_3 已有的布局
        existing_layout = self.ui.page_3.layout()

        # 3. 清空该布局中所有旧的占位控件，确保我们有一个干净的页面
        if existing_layout is not None:
            while existing_layout.count():
                # 逐一移除旧控件并标记为删除
                item_to_remove = existing_layout.takeAt(0)
                widget_to_remove = item_to_remove.widget()
                if widget_to_remove is not None:
                    widget_to_remove.deleteLater()

        # 4. 将我们的新历史表格添加到这个【已清空】的布局中
        existing_layout.addWidget(self.history_table)

        # 5. 设置历史表格的样式
        self.history_table.setColumnCount(3)
        self.history_table.setHorizontalHeaderLabels(['查询时间', '类型', '描述'])
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.verticalHeader().setVisible(False)
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        # --- 初始化代码结束 ---

        # 移除原生的标题栏和边框
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        # 让窗口背景透明
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # 初始化一个用于窗口拖动的变量
        self._drag_start_pos = None

        # 现在调用 connect_signals 时, self.history_table 已经存在
        self.connect_signals()
        self.display_login_time()
        # 默认禁用，选择文件夹/文件后才启用
        self.ui.btn_start_analysis_mode1.setEnabled(False)
        self.ui.btn_start_analysis_mode2.setEnabled(False)

        self.thread = None
        self.worker = None
        # 初始化历史记录相关的线程变量
        self.history_thread = None
        self.history_worker = None

        self._setup_window_icons()

    def display_login_time(self):
        current_time = datetime.datetime.now()
        time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
        self.ui.label_login_time_2.setText(f"登录时间：{time_str}")

    def connect_signals(self):
        self.ui.pushButton_4.clicked.connect(self.showMinimized)
        self.ui.pushButton_5.clicked.connect(self.toggle_maximize_restore)
        self.ui.pushButton_6.clicked.connect(self.close)

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
        self.ui.btn_back.clicked.connect(self.go_to_home_page)  # "返回结果列表" 按钮

        # --- 【新增的】侧边栏跳转按钮 ---
        self.ui.pushButton_7.clicked.connect(self.go_to_home_page)  # "代码查重" 侧边栏按钮

        # --- 表格点击跳转 ---
        self.ui.table_history.cellClicked.connect(self.go_to_details_page)

        # --- 历史记录相关按钮 ---
        self.ui.pushButton_3.clicked.connect(self.show_history_page)  # "历史记录" 侧边栏按钮
        self.history_table.cellClicked.connect(self.on_history_item_clicked)  # 点击历史记录条目

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
        names = {}  # 【新增】用于存放文件/文件夹名

        if current_mode == 0:
            folder_path = self.ui.le_folder_path.text()
            paths['directory'] = folder_path
            names['folder_name'] = os.path.basename(folder_path)  # 从路径中提取文件夹名
        else:
            paths['base_file'] = self.ui.le_folder_path_2.text()
            folder_path = self.ui.le_folder_path_3.text()
            paths['compare_dir'] = folder_path
            names['folder_name'] = os.path.basename(folder_path)  # 从路径中提取文件夹名

        self.ui.btn_start_analysis_mode1.setEnabled(False)
        self.ui.btn_start_analysis_mode2.setEnabled(False)
        self.ui.statusbar.showMessage("正在分析中，请稍候...")

        self.thread = QThread()
        # 【修改】将 names 传递给 Worker
        self.worker = Worker(current_mode, paths, names)
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
        """
        【已修改】分析成功后的处理函数。
        增加了在表格中存储 result_id 的逻辑。
        """
        print("分析成功，结果为:", results)
        self.ui.statusbar.showMessage("分析完成！", 5000)

        self.ui.main_stack.setCurrentIndex(0)

        self.ui.table_history.setRowCount(0)
        self.ui.table_history.setColumnCount(3)
        self.ui.table_history.setHorizontalHeaderLabels(['文件1', '文件2', '相似度'])

        if not results:
            self.ui.table_history.setRowCount(1)
            item = QtWidgets.QTableWidgetItem("未找到有相似度的文件。")
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.ui.table_history.setItem(0, 0, item)
            self.ui.table_history.setSpan(0, 0, 1, 3)
            return

        self.ui.table_history.setRowCount(len(results))
        for row, res_item in enumerate(results):
            file1 = res_item.get('file1', '')
            file2 = res_item.get('file2', '')
            similarity = res_item.get('similarity', 0.0)
            result_id = res_item.get('result_id', '')  # 获取 result_id

            item_file1 = QtWidgets.QTableWidgetItem(file1)
            item_file2 = QtWidgets.QTableWidgetItem(file2)
            item_similarity = QtWidgets.QTableWidgetItem(f"{similarity:.2%}")

            # 【关键】将 result_id 存储在第一列的自定义数据角色中
            # Qt.ItemDataRole.UserRole 是一个安全的位置，用于存储不显示但需要引用的数据
            item_file1.setData(QtCore.Qt.ItemDataRole.UserRole, result_id)

            item_similarity.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

            self.ui.table_history.setItem(row, 0, item_file1)
            self.ui.table_history.setItem(row, 1, item_file2)
            self.ui.table_history.setItem(row, 2, item_similarity)

        self.ui.table_history.resizeColumnsToContents()
        header = self.ui.table_history.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

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
        """
        【已实现】当用户点击表格行时，获取详情并高亮显示。
        """
        # 从第一列的单元格中取出我们之前存储的 result_id
        item = self.ui.table_history.item(row, 0)
        if not item:
            return
        result_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not result_id:
            print("错误：无法获取此行的 result_id。")
            return

        print(f"用户点击了第 {row + 1} 行，result_id 为: {result_id}，准备获取详情...")

        # 调用API获取详细比对数据
        from client.api import client as api_client  # 局部导入避免循环引用
        details, err = api_client.get_comparison_details(result_id)

        if err:
            QMessageBox.critical(self, "获取详情出错", err)
            return
        if not details:
            QMessageBox.information(self, "提示", "未找到详细的比对数据。")
            return

        # 处理并显示 file1 的代码
        file1_details = details.get('file1_details', {})
        self.ui.te_code_file1.setHtml(self._format_code_to_html(file1_details))

        # 处理并显示 file2 的代码
        file2_details = details.get('file2_details', {})
        self.ui.te_code_file2.setHtml(self._format_code_to_html(file2_details))

        # 跳转到详情页 (page_2, 索引为2)
        self.ui.main_stack.setCurrentIndex(2)

    def _format_code_to_html(self, file_details: dict) -> str:
        """一个辅助函数，用于将带状态的代码行列表转换为高亮的HTML。"""
        if not file_details or 'lines' not in file_details:
            return "<code>无法加载代码。</code>"

        html_lines = []
        # 添加文件名作为标题
        filename = file_details.get('name', 'Unknown File')
        html_lines.append(f"<h3>{filename}</h3>")

        # 使用 pre 标签保持代码格式
        html_lines.append("<pre><code>")
        for line in file_details['lines']:
            text = line.get('text', '').replace('<', '&lt;').replace('>', '&gt;')  # HTML转义
            line_num = line.get('line_num', '')
            status = line.get('status', 'unique')

            # 根据状态决定是否高亮
            if status == 'similar':
                html_lines.append(f"<span style='background-color: #FFD700;'>{line_num: >4}: {text}</span>")
            else:
                html_lines.append(f"{line_num: >4}: {text}")

        html_lines.append("</code></pre>")
        return "\n".join(html_lines)


    def toggle_maximize_restore(self):

        if self.isMaximized():
            self.showNormal()
            self.ui.pushButton_5.setIcon(qta.icon('fa5s.window-maximize', color='#A3A4A8'))
        else:
            self.showMaximized()
            self.ui.pushButton_5.setIcon(qta.icon('fa5s.window-restore', color='#A3A4A8'))

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.isMaximized() == False:
            self.m_flag = True
            self.m_Position = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, mouse_event):
        if QtCore.Qt.LeftButton and self.m_flag:
            self.move(mouse_event.globalPos() - self.m_Position)
            mouse_event.accept()

    def mouseReleaseEvent(self, mouse_event):
        self.m_flag = False

    def toggle_maximize_restore(self):
        """
        切换窗口的最大化和正常尺寸状态。
        """
        if self.isMaximized():
            self.showNormal()
        else:

            self.showMaximized()

    def _setup_window_icons(self):
        self.ui.pushButton_4.setIcon(qta.icon('fa5s.window-minimize', color='#A3A4A8'))
        self.ui.pushButton_6.setIcon(qta.icon('fa5s.times', color='#A3A4A8'))
        self.ui.pushButton_5.setIcon(qta.icon('fa5s.window-maximize', color='#A3A4A8'))

    def show_history_page(self):
        """【已修改】槽函数：启动一个后台线程来获取并显示历史记录列表。"""
        print("正在启动后台线程获取历史记录...")
        self.ui.statusbar.showMessage("正在加载历史记录，请稍候...")

        # 禁用按钮，防止重复点击
        self.ui.pushButton_3.setEnabled(False)

        # 创建并启动后台线程
        self.history_thread = QThread()
        self.history_worker = HistoryWorker()
        self.history_worker.moveToThread(self.history_thread)

        # 连接信号和槽
        self.history_thread.started.connect(self.history_worker.run)
        self.history_worker.finished.connect(self.history_thread.quit)
        self.history_worker.finished.connect(self.history_worker.deleteLater)
        self.history_thread.finished.connect(self.history_thread.deleteLater)
        self.history_worker.success.connect(self.on_history_load_success)
        self.history_worker.error.connect(self.on_history_load_error)

        self.history_thread.start()

    def on_history_item_clicked(self, row, column):
        """槽函数：当用户点击某条历史记录时，获取其详细结果"""
        item = self.history_table.item(row, 0)
        if not item:
            return

        history_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not history_id:
            print(f"错误：无法从第 {row + 1} 行获取 history_id")
            return

        print(f"用户点击了历史记录 ID: {history_id}，正在获取详细结果...")
        self.ui.statusbar.showMessage(f"正在加载历史记录 {history_id} 的详情...")

        from client.api import client as api_client
        details, err = api_client.get_history_detail(history_id)

        if err:
            QMessageBox.critical(self, "错误", f"无法加载历史详情: {err}")
            self.ui.statusbar.showMessage(f"加载详情失败", 5000)
            return

        # 【代码复用】我们直接调用处理实时结果的 on_analysis_success 函数
        # 因为后端返回的历史详情和实时查询结果的格式是完全一样的！
        if 'results' in details:
            self.on_analysis_success(details['results'])
        else:
            print("错误：历史详情数据格式不正确。")

    @pyqtSlot(list)
    def on_history_load_success(self, history_list):
        """【已修改】当历史记录成功加载后，填充包含新列的表格。"""
        # 【修改】设置5列
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(['查询时间', '类型', '查询文件夹', '基准文件', '描述'])

        # 调整列宽
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        self.history_table.setRowCount(0)

        if history_list:
            self.history_table.setRowCount(len(history_list))
            for row, item in enumerate(history_list):
                history_id = item.get('id')
                query_time_str = item.get('query_time', '').split('.')[0].replace('T', ' ')
                query_type = item.get('query_type', '')
                description = item.get('description', '')
                # 【新增】获取新字段
                folder_name = item.get('folder_name', 'N/A')
                special_file = item.get('special_file_name', 'N/A')

                item_time = QtWidgets.QTableWidgetItem(query_time_str)
                item_type = QtWidgets.QTableWidgetItem(query_type)
                item_folder = QtWidgets.QTableWidgetItem(folder_name)
                item_special = QtWidgets.QTableWidgetItem(special_file)
                item_desc = QtWidgets.QTableWidgetItem(description)

                item_time.setData(QtCore.Qt.ItemDataRole.UserRole, history_id)

                self.history_table.setItem(row, 0, item_time)
                self.history_table.setItem(row, 1, item_type)
                # 【新增】插入新列的数据
                self.history_table.setItem(row, 2, item_folder)
                self.history_table.setItem(row, 3, item_special)
                self.history_table.setItem(row, 4, item_desc)

            self.ui.statusbar.showMessage(f"成功加载 {len(history_list)} 条历史记录。", 5000)
        else:
            self.ui.statusbar.showMessage("没有找到历史记录。", 5000)

        self.ui.main_stack.setCurrentIndex(1)
        self.ui.pushButton_3.setEnabled(True)

    @pyqtSlot(str)
    def on_history_load_error(self, error_message):
        """【新增】槽函数：当加载历史记录失败时，显示错误信息。"""
        QMessageBox.critical(self, "加载失败", f"无法加载历史记录: {error_message}")
        self.ui.statusbar.showMessage("加载历史记录失败！", 5000)
        self.ui.pushButton_3.setEnabled(True)  # 重新启用按钮


