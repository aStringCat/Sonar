import requests
import os
from typing import List, Dict, Any, Tuple

BASE_URL = "http://127.0.0.1:8000/api"


def start_check(file_paths: List[str], folder_name: str) -> Tuple[Dict[str, Any] | None, str | None]:
    """【已修改】开始一个多文件互查任务，并发送文件夹名。"""
    files_to_send = []
    # 【新增】准备要发送的表单数据
    data = {'folder_name': folder_name}
    try:
        for path in file_paths:
            files_to_send.append(('files', (os.path.basename(path), open(path, 'rb'), 'text/plain')))
        if not files_to_send:
            return None, "没有提供任何文件。"
        with requests.Session() as session:
            # 【修改】在请求中加入 data
            response = session.post(f"{BASE_URL}/check", files=files_to_send, data=data, timeout=30)
            response.raise_for_status()
        return response.json(), None
    # ... (except 和 finally 块保持不变) ...
    except requests.exceptions.Timeout:
        return None, "请求超时。请检查网络或后端服务是否正在运行。"
    except requests.exceptions.ConnectionError:
        return None, "连接错误。无法连接到后端服务。"
    except requests.exceptions.RequestException as e:
        return None, f"网络请求失败: {e}"
    finally:
        for _, (_, f, _) in files_to_send:
            f.close()


def start_one_to_many_check(base_file_path: str, other_file_paths: List[str], folder_name: str) -> Tuple[
    Dict[str, Any] | None, str | None]:
    """【已修改】开始一个一对多查重任务，并发送文件夹和文件名。"""
    files_to_send = []
    # 【新增】准备要发送的表单数据
    data = {'folder_name': folder_name}
    try:
        files_to_send.append(('base_file', (os.path.basename(base_file_path), open(base_file_path, 'rb'), 'text/plain')))
        for path in other_file_paths:
            files_to_send.append(('other_files', (os.path.basename(path), open(path, 'rb'), 'text/plain')))
        if len(files_to_send) < 2:
            return None, "至少需要一个基准文件和一个对比文件。"
        with requests.Session() as session:
            # 【修改】在请求中加入 data
            response = session.post(f"{BASE_URL}/check_one", files=files_to_send, data=data, timeout=60)
            response.raise_for_status()
        return response.json(), None
    # ... (except 和 finally 块保持不变) ...
    except requests.exceptions.RequestException as e:
        return None, f"网络请求失败: {e}"
    finally:
        for _, file_tuple in files_to_send:
            file_obj = file_tuple[1]
            if file_obj:
                file_obj.close()



def get_task_status(task_id: str) -> Tuple[Dict[str, Any] | None, str | None]:
    """根据任务ID获取查重结果。"""
    try:
        with requests.Session() as session:
            response = session.get(f"{BASE_URL}/check/{task_id}", timeout=10)
            response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        return None, f"获取任务状态失败: {e}"

def get_comparison_details(result_id: str) -> Tuple[Dict[str, Any] | None, str | None]:
    """根据结果ID获取详细的代码比对数据。"""
    try:
        with requests.Session() as session:
            response = session.get(f"{BASE_URL}/comparison/{result_id}", timeout=10)
            response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        return None, f"获取比对详情失败: {e}"

def get_history_list() -> Tuple[List[Dict[str, Any]] | None, str | None]:
    """获取所有历史查询任务的列表。"""
    try:
        with requests.Session() as session:
            response = session.get(f"{BASE_URL}/history", timeout=10)
            response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        return None, f"获取历史记录列表失败: {e}"

def get_history_detail(history_id: int) -> Tuple[Dict[str, Any] | None, str | None]:
    """根据历史ID获取该次任务的详细查重结果。"""
    try:
        with requests.Session() as session:
            response = session.get(f"{BASE_URL}/history/{history_id}", timeout=10)
            response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        return None, f"获取历史详情失败: {e}"