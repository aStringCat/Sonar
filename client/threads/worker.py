import time
import os
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from client.api import client as api_client
from typing import Dict, List


class Worker(QObject):
    finished = pyqtSignal()
    success = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, mode: int, paths: Dict[str, str], names: Dict[str, str] = None):
        super().__init__()
        self.mode = mode
        self.paths = paths
        self.names = names if names is not None else {}  # 【新增】接收文件名
        self.is_running = True

    @pyqtSlot()
    def run(self):
        try:
            self.progress.emit("正在提交文件到服务器...")
            task_data = None
            err = None
            if self.mode == 0:
                dir_path = self.paths.get('directory')
                if not dir_path or not os.path.isdir(dir_path):
                    raise Exception("无效的文件夹路径。")
                file_paths = [os.path.join(dir_path, f) for f in os.listdir(dir_path) if f.endswith('.py')]
                if len(file_paths) < 2:
                    raise Exception("文件夹内至少需要两个Python文件才能进行互查。")

                # 【修改】传递文件夹名
                folder_name = self.names.get('folder_name', os.path.basename(dir_path))
                task_data, err = api_client.start_check(file_paths, folder_name=folder_name)

            elif self.mode == 1:
                base_file = self.paths.get('base_file')
                compare_dir = self.paths.get('compare_dir')
                if not base_file or not os.path.isfile(base_file):
                    raise Exception("无效的基准文件路径。")
                if not compare_dir or not os.path.isdir(compare_dir):
                    raise Exception("无效的对比文件夹路径。")
                other_files = [os.path.join(compare_dir, f) for f in os.listdir(compare_dir) if f.endswith('.py')]
                if not other_files:
                    raise Exception("对比文件夹内没有任何Python文件。")

                # 【修改】传递文件夹名
                folder_name = self.names.get('folder_name', os.path.basename(compare_dir))
                task_data, err = api_client.start_one_to_many_check(base_file, other_files, folder_name=folder_name)

            # ... (后续的轮询逻辑保持不变) ...
            if err:
                raise Exception(err)
            if not task_data or 'task_id' not in task_data:
                raise Exception("服务器未能成功创建任务。")
            task_id = task_data['task_id']
            self.progress.emit(f"任务已创建 (ID: {task_id[:8]}...). 等待服务器处理...")
            attempts = 0
            max_attempts = 120
            while attempts < max_attempts and self.is_running:
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

class HistoryWorker(QObject):
    """一个专门用于从后台获取历史记录列表的 Worker。"""
    finished = pyqtSignal()
    success = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    @pyqtSlot()
    def run(self):
        """执行网络请求并发送结果信号。"""
        try:
            history_list, err = api_client.get_history_list()
            if err:
                raise Exception(err)
            self.success.emit(history_list)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()