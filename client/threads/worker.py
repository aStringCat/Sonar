import time
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from client.api import client as api_client

class AnalysisWorker(QObject):
    """在后台线程中执行API请求和轮询的Worker"""
    finished = pyqtSignal()
    success = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, file_paths: list):
        super().__init__()
        self.file_paths = file_paths
        self.is_running = True

    @pyqtSlot()
    def run(self):
        """执行查重任务的主函数"""
        try:
            # 1. 提交查重任务
            self.progress.emit("正在提交文件到服务器...")
            # 直接调用模块中的函数
            task_data, err = api_client.start_check(self.file_paths)
            if err:
                raise Exception(err)
            if not task_data or 'task_id' not in task_data:
                raise Exception("服务器未能成功创建任务。")

            task_id = task_data['task_id']
            self.progress.emit(f"任务已创建 (ID: {task_id[:8]}...). 等待服务器处理...")

            # 2. 轮询任务结果
            attempts = 0
            max_attempts = 60  # 最多轮询30秒 (60 * 0.5s)
            while attempts < max_attempts and self.is_running:
                # 直接调用模块中的函数
                status_data, err = api_client.get_task_status(task_id)
                if err:
                    time.sleep(0.5)
                    attempts += 1
                    continue

                if status_data and status_data.get('status') == 'completed':
                    self.progress.emit("分析完成！")
                    self.success.emit(status_data.get('results', []))
                    self.finished.emit()
                    return

                time.sleep(0.5)
                attempts += 1

            if self.is_running:
                raise Exception("任务处理超时，请稍后再试。")

        except Exception as e:
            self.error.emit(str(e))
        finally:
            if self.is_running:
                self.finished.emit()

    def stop(self):
        self.is_running = False