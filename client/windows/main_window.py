import datetime
import os
import json  # 【新增】导入json模块

import qtawesome as qta
from PyQt6 import QtCore, QtWidgets
# 【新增】导入 QDoubleSpinBox, QCheckBox, QWidget, QHBoxLayout
from PyQt6.QtCore import QThread, pyqtSlot, Qt, QTimer
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QTableWidget, QHeaderView, QDoubleSpinBox, QCheckBox, \
    QWidget, QHBoxLayout

from client.threads.worker import Worker, HistoryWorker
# 【修改】导入 client
from client.api import client
from client.ui.main_window_ui import Ui_MainWindow


def _format_code_to_html(file_details: dict) -> str:
    if not file_details or 'lines' not in file_details: return "<code>无法加载代码。</code>"
    filename = file_details.get('name', 'Unknown File')
    html = f"<h3>{filename}</h3><pre><code>"
    for line in file_details['lines']:
        text = line.get('text', '').replace('<', '&lt;').replace('>', '&gt;')
        line_num = line.get('line_num', '')
        status = line.get('status', 'unique')
        if status == 'similar':
            html += f"<span style='background-color: #FFD700;'>{line_num: >4}: {text}</span>\n"
        else:
            html += f"{line_num: >4}: {text}\n"
    html += "</code></pre>"
    return html


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.m_Position = None
        self.m_flag = None
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # --- UI元素和逻辑初始化 ---
        self._setup_new_ui_elements()  # 调用一个新函数来创建和布局新UI控件
        self.threshold_update_timer = QTimer(self)  # 创建一个计时器，用于延迟更新阈值
        self.threshold_update_timer.setSingleShot(True)
        self.threshold_update_timer.setInterval(1000)  # 延迟1秒

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drag_start_pos = None

        self.connect_signals()
        self.display_login_time()
        self.ui.btn_start_analysis_mode1.setEnabled(False)
        self.ui.btn_start_analysis_mode2.setEnabled(False)

        self.thread = None
        self.worker = None
        self.history_thread = None
        self.history_worker = None

        self._setup_window_icons()
        self.load_initial_threshold()  # 程序启动时加载阈值

    def _setup_new_ui_elements(self):
        """【全新】创建一个函数，专门用于初始化所有新增的UI控件。"""
        # 1. 创建阈值设置控件
        self.threshold_label = QtWidgets.QLabel("相似度阈值:", self.ui.page)
        self.threshold_spinbox = QDoubleSpinBox(self.ui.page)
        self.threshold_spinbox.setRange(0.0, 1.0)
        self.threshold_spinbox.setSingleStep(0.05)
        self.threshold_spinbox.setDecimals(2)
        self.threshold_spinbox.setValue(0.85)  # 默认值

        # 2. 创建导出按钮
        self.export_button = QtWidgets.QPushButton("导出抄袭项", self.ui.page)

        # 3. 创建一个新的水平布局来容纳这些新控件
        new_controls_layout = QHBoxLayout()
        new_controls_layout.addWidget(self.threshold_label)
        new_controls_layout.addWidget(self.threshold_spinbox)
        new_controls_layout.addStretch()  # 添加伸缩项，把导出按钮推到右边
        new_controls_layout.addWidget(self.export_button)

        # 4. 将这个新布局插入到主页面 (page) 的现有垂直布局的某个位置
        # 我们把它插在 “详情” 标签 (label_2) 的上方
        page_layout = self.ui.page.layout()
        if page_layout:
            page_layout.insertLayout(2, new_controls_layout)  # 插入到第3个位置（索引为2）

        # 5. 初始化历史记录页面（保持不变）
        self.history_table: QTableWidget = QTableWidget()
        existing_layout = self.ui.page_3.layout()
        if existing_layout is not None:
            while existing_layout.count():
                item_to_remove = existing_layout.takeAt(0)
                widget_to_remove = item_to_remove.widget()
                if widget_to_remove is not None: widget_to_remove.deleteLater()
        existing_layout.addWidget(self.history_table)
        self.history_table.setColumnCount(3)
        self.history_table.setHorizontalHeaderLabels(['查询时间', '类型', '描述'])
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.verticalHeader().setVisible(False)
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

    def display_login_time(self):
        self.ui.label_login_time_2.setText(f"登录时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def connect_signals(self):
        """【已修改】连接所有信号，包括新增的控件。"""
        # 窗口控制按钮
        self.ui.pushButton_4.clicked.connect(self.showMinimized)
        self.ui.pushButton_5.clicked.connect(self.toggle_maximize_restore)
        self.ui.pushButton_6.clicked.connect(self.close)

        # 模式切换
        self.ui.pushButton.clicked.connect(lambda: self.change_mode(0))
        self.ui.pushButton_2.clicked.connect(lambda: self.change_mode(1))

        # 文件/文件夹选择
        self.ui.btn_select_folder.clicked.connect(self.select_pairwise_directory)
        self.ui.btn_select_folder_2.clicked.connect(self.select_one_to_many_file)
        self.ui.btn_select_folder_3.clicked.connect(self.select_one_to_many_directory)

        # 分析按钮
        self.ui.btn_start_analysis_mode1.clicked.connect(self.start_analysis)
        self.ui.btn_start_analysis_mode2.clicked.connect(self.start_analysis)

        # 页面跳转
        self.ui.home.clicked.connect(self.go_to_home_page)
        self.ui.btn_back.clicked.connect(self.go_to_home_page)
        self.ui.pushButton_7.clicked.connect(self.go_to_home_page)
        self.ui.pushButton_3.clicked.connect(self.show_history_page)

        # 表格点击
        self.ui.table_history.cellClicked.connect(self.go_to_details_page)
        self.history_table.cellClicked.connect(self.on_history_item_clicked)

        # --- 【新增】连接新控件的信号 ---
        self.threshold_spinbox.valueChanged.connect(self.on_threshold_changed)
        self.threshold_update_timer.timeout.connect(self.update_threshold_on_server)
        self.export_button.clicked.connect(self.export_plagiarized_items)

    def load_initial_threshold(self):
        """【全新】程序启动时从服务器加载阈值。"""
        threshold, err = client.get_similarity_threshold()
        if err:
            self.ui.statusbar.showMessage(f"加载阈值失败: {err}", 5000)
        elif threshold is not None:
            # 临时断开信号连接，避免在设置初始值时触发更新
            self.threshold_spinbox.valueChanged.disconnect(self.on_threshold_changed)
            self.threshold_spinbox.setValue(threshold)
            self.threshold_spinbox.valueChanged.connect(self.on_threshold_changed)
            self.ui.statusbar.showMessage(f"成功加载相似度阈值: {threshold:.2f}", 3000)

    def on_threshold_changed(self):
        """【全新】当用户修改SpinBox时，重启计时器。"""
        self.threshold_update_timer.start()

    def update_threshold_on_server(self):
        """【全新】计时器到期后，真正将新阈值发送到服务器。"""
        new_value = self.threshold_spinbox.value()
        self.ui.statusbar.showMessage(f"正在更新阈值为 {new_value:.2f}...")
        success, err = client.set_similarity_threshold(new_value)
        if err:
            self.ui.statusbar.showMessage(f"更新失败: {err}", 5000)
            QMessageBox.warning(self, "错误", f"更新阈值失败: {err}")
        else:
            self.ui.statusbar.showMessage(f"阈值已成功更新为 {new_value:.2f}", 3000)

    def select_pairwise_directory(self):
        folder_path = QFileDialog.getExistingDirectory(self, "请选择要进行互查的代码文件夹")
        if folder_path:
            self.ui.le_folder_path.setText(folder_path)
            self.ui.btn_start_analysis_mode1.setEnabled(True)

    def select_one_to_many_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "请选择基准代码文件", "", "Python Files (*.py)")
        if file_path:
            self.ui.le_folder_path_2.setText(file_path)
            self.update_one_to_many_analysis_button_state()

    def select_one_to_many_directory(self):
        folder_path = QFileDialog.getExistingDirectory(self, "请选择要进行对比的代码文件夹")
        if folder_path:
            self.ui.le_folder_path_3.setText(folder_path)
            self.update_one_to_many_analysis_button_state()

    def update_one_to_many_analysis_button_state(self):
        base_ok = bool(self.ui.le_folder_path_2.text())
        compare_ok = bool(self.ui.le_folder_path_3.text())
        self.ui.btn_start_analysis_mode2.setEnabled(base_ok and compare_ok)

    def change_mode(self, index):
        self.ui.stackedWidget.setCurrentIndex(index)

    def start_analysis(self):
        current_mode = self.ui.stackedWidget.currentIndex()
        paths, names = {}, {}
        if current_mode == 0:
            folder_path = self.ui.le_folder_path.text()
            paths['directory'] = folder_path
            names['folder_name'] = os.path.basename(folder_path)
        else:
            paths['base_file'] = self.ui.le_folder_path_2.text()
            folder_path = self.ui.le_folder_path_3.text()
            paths['compare_dir'] = folder_path
            names['folder_name'] = os.path.basename(folder_path)
        self.ui.btn_start_analysis_mode1.setEnabled(False)
        self.ui.btn_start_analysis_mode2.setEnabled(False)
        self.ui.statusbar.showMessage("正在分析中，请稍候...")
        self.thread = QThread()
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
        """分析成功后，处理包含抄袭标记的结果，并添加复选框。"""
        print("分析成功，结果为:", results)
        self.ui.statusbar.showMessage("分析完成！", 5000)
        self.ui.main_stack.setCurrentIndex(0)

        # 增加一列“是否抄袭”
        self.ui.table_history.setRowCount(0)
        self.ui.table_history.setColumnCount(4)
        self.ui.table_history.setHorizontalHeaderLabels(['文件1', '文件2', '相似度', '是否抄袭'])

        if not results:
            self.ui.table_history.setRowCount(1)
            item = QtWidgets.QTableWidgetItem("未找到有相似度的文件。")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ui.table_history.setItem(0, 0, item)
            self.ui.table_history.setSpan(0, 0, 1, 4)
            return

        self.ui.table_history.setRowCount(len(results))
        for row, res_item in enumerate(results):
            file1 = res_item.get('file1', '')
            file2 = res_item.get('file2', '')
            similarity = res_item.get('similarity', 0.0)
            result_id = res_item.get('result_id', '')
            is_plagiarized = res_item.get('plagiarized', False)

            item_file1 = QtWidgets.QTableWidgetItem(file1)
            item_file2 = QtWidgets.QTableWidgetItem(file2)
            item_similarity = QtWidgets.QTableWidgetItem(f"{similarity:.2%}")
            item_similarity.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 将 result_id 存储在第一列的自定义数据角色中
            item_file1.setData(Qt.ItemDataRole.UserRole, result_id)

            self.ui.table_history.setItem(row, 0, item_file1)
            self.ui.table_history.setItem(row, 1, item_file2)
            self.ui.table_history.setItem(row, 2, item_similarity)

            # --- 添加复选框 ---
            checkbox = QCheckBox()
            checkbox.setChecked(is_plagiarized)
            # 使用 lambda 来捕获当前的 result_id 和 checkbox 实例
            checkbox.stateChanged.connect(
                lambda state, rid=result_id: self.on_mark_changed(rid, state == Qt.CheckState.Checked.value)
            )
            # QTableWidget 需要一个 QWidget 来容纳 checkbox，并使其居中
            cell_widget = QWidget()
            layout = QHBoxLayout(cell_widget)
            layout.addWidget(checkbox)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            self.ui.table_history.setCellWidget(row, 3, cell_widget)
            # --- 复选框添加结束 ---

        header = self.ui.table_history.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.ui.btn_start_analysis_mode1.setEnabled(True)
        self.ui.btn_start_analysis_mode2.setEnabled(True)

    def on_mark_changed(self, result_id: str, is_checked: bool):
        """当用户点击复选框时，调用API更新后端的标记。"""
        self.ui.statusbar.showMessage(f"正在更新标记 (ID: {result_id[:8]}...)...", 2000)
        err = client.update_plagiarism_mark(result_id, is_checked)
        if err:
            QMessageBox.warning(self, "更新失败", err)
            self.ui.statusbar.showMessage(f"更新标记失败！", 5000)
        else:
            self.ui.statusbar.showMessage(f"标记已更新。", 3000)

    @pyqtSlot(str)
    def on_analysis_error(self, error_message):
        self.ui.statusbar.showMessage(f"分析出错: {error_message}", 5000)
        QMessageBox.critical(self, "分析出错", error_message)
        self.ui.btn_start_analysis_mode1.setEnabled(True)
        self.ui.btn_start_analysis_mode2.setEnabled(True)

    def go_to_home_page(self):
        self.ui.main_stack.setCurrentIndex(0)

    def go_to_details_page(self, row, column):
        """如果点击的是复选框列，则不跳转。"""
        if column == 3:  # 如果点击的是第4列（复选框），则不执行任何操作
            return
        item = self.ui.table_history.item(row, 0)
        if not item: return
        result_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not result_id: return

        details, err = client.get_comparison_details(result_id)
        if err:
            QMessageBox.critical(self, "获取详情出错", err)
            return
        if not details:
            QMessageBox.information(self, "提示", "未找到详细的比对数据。")
            return

        self.ui.te_code_file1.setHtml(_format_code_to_html(details.get('file1_details', {})))
        self.ui.te_code_file2.setHtml(_format_code_to_html(details.get('file2_details', {})))
        self.ui.main_stack.setCurrentIndex(2)

    def show_history_page(self):
        self.ui.statusbar.showMessage("正在加载历史记录...")
        self.ui.pushButton_3.setEnabled(False)
        self.history_thread = QThread()
        self.history_worker = HistoryWorker()
        self.history_worker.moveToThread(self.history_thread)
        self.history_thread.started.connect(self.history_worker.run)
        self.history_worker.finished.connect(self.history_thread.quit)
        self.history_worker.finished.connect(self.history_worker.deleteLater)
        self.history_thread.finished.connect(self.history_thread.deleteLater)
        self.history_worker.success.connect(self.on_history_load_success)
        self.history_worker.error.connect(self.on_history_load_error)
        self.history_thread.start()

    @pyqtSlot(list)
    def on_history_load_success(self, history_list):
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(['查询时间', '类型', '查询文件夹', '基准文件', '描述'])
        header = self.history_table.horizontalHeader()
        for i in range(5): header.setSectionResizeMode(i,
                                                       QHeaderView.ResizeMode.ResizeToContents if i < 2 else QHeaderView.ResizeMode.Stretch)

        self.history_table.setRowCount(0)
        if history_list:
            self.history_table.setRowCount(len(history_list))
            for row, item in enumerate(history_list):
                item_time = QtWidgets.QTableWidgetItem(item.get('query_time', '').split('.')[0].replace('T', ' '))
                item_time.setData(Qt.ItemDataRole.UserRole, item.get('id'))
                self.history_table.setItem(row, 0, item_time)
                self.history_table.setItem(row, 1, QtWidgets.QTableWidgetItem(item.get('query_type', '')))
                self.history_table.setItem(row, 2, QtWidgets.QTableWidgetItem(item.get('folder_name', 'N/A')))
                self.history_table.setItem(row, 3, QtWidgets.QTableWidgetItem(item.get('special_file_name', 'N/A')))
                self.history_table.setItem(row, 4, QtWidgets.QTableWidgetItem(item.get('description', '')))
            self.ui.statusbar.showMessage(f"成功加载 {len(history_list)} 条历史记录。", 5000)
        else:
            self.ui.statusbar.showMessage("没有找到历史记录。", 5000)

        self.ui.main_stack.setCurrentIndex(1)
        self.ui.pushButton_3.setEnabled(True)

    @pyqtSlot(str)
    def on_history_load_error(self, error_message):
        QMessageBox.critical(self, "加载失败", f"无法加载历史记录: {error_message}")
        self.ui.statusbar.showMessage("加载历史记录失败！", 5000)
        self.ui.pushButton_3.setEnabled(True)

    def on_history_item_clicked(self, row, _column):
        item = self.history_table.item(row, 0)
        if not item: return
        history_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not history_id: return

        self.ui.statusbar.showMessage(f"正在加载历史记录 {history_id} 的详情...")
        details, err = client.get_history_detail(history_id)
        if err:
            QMessageBox.critical(self, "错误", f"无法加载历史详情: {err}")
            self.ui.statusbar.showMessage(f"加载详情失败", 5000)
            return

        if 'results' in details:
            self.on_analysis_success(details['results'])
        else:
            print("错误：历史详情数据格式不正确。")

    def export_plagiarized_items(self):
        """导出所有被标记为抄袭的项目。"""
        self.ui.statusbar.showMessage("正在导出抄袭项...")
        results, err = client.export_plagiarized()
        if err:
            QMessageBox.critical(self, "导出失败", err)
            self.ui.statusbar.showMessage("导出失败！", 5000)
            return

        if not results:
            QMessageBox.information(self, "提示", "当前没有被标记为抄袭的项目可供导出。")
            self.ui.statusbar.showMessage("无项目可导出。", 3000)
            return

        # 弹出文件保存对话框
        save_path, _ = QFileDialog.getSaveFileName(self, "保存导出结果", "plagiarized_results.json",
                                                   "JSON Files (*.json)")
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=4, ensure_ascii=False)
                self.ui.statusbar.showMessage(f"成功导出到 {save_path}", 5000)
                QMessageBox.information(self, "导出成功", f"所有标记为抄袭的项目已成功导出到:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"无法将文件写入磁盘: {e}")
                self.ui.statusbar.showMessage("保存文件失败！", 5000)

    # --- 窗口拖动和最大化/最小化/关闭的函数 (保持不变) ---
    def toggle_maximize_restore(self):
        if self.isMaximized():
            self.showNormal()
            self.ui.pushButton_5.setIcon(qta.icon('fa5s.window-maximize', color='#A3A4A8'))
        else:
            self.showMaximized()
            self.ui.pushButton_5.setIcon(qta.icon('fa5s.window-restore', color='#A3A4A8'))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.isMaximized():
            self.m_flag = True
            self.m_Position = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, mouse_event):
        if self.m_flag:
            self.move(mouse_event.globalPosition().toPoint() - self.m_Position)
            mouse_event.accept()

    def mouseReleaseEvent(self, mouse_event):
        self.m_flag = False

    def _setup_window_icons(self):
        self.ui.pushButton_4.setIcon(qta.icon('fa5s.window-minimize', color='#A3A4A8'))
        self.ui.pushButton_6.setIcon(qta.icon('fa5s.times', color='#A3A4A8'))
        self.ui.pushButton_5.setIcon(qta.icon('fa5s.window-maximize', color='#A3A4A8'))
