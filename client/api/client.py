import requests
import os
from typing import List, Dict, Any, Tuple

BASE_URL = "http://127.0.0.1:8000/api"


def start_check(file_paths: List[str]) -> Tuple[Dict[str, Any] | None, str | None]:
    """
    开始一个多文件互查任务。
    它接收一个文件路径列表，并将其发送到后端的 /check 端点。
    """
    files_to_send = []
    try:
        for path in file_paths:
            # 'files' 是FastAPI后端接收文件列表时预期的字段名
            files_to_send.append(('files', (os.path.basename(path), open(path, 'rb'), 'text/plain')))

        if not files_to_send:
            return None, "没有提供任何文件。"

        # 使用 with a session for potential connection reuse
        with requests.Session() as session:
            response = session.post(f"{BASE_URL}/check", files=files_to_send, timeout=30)
            response.raise_for_status()  # 如果请求失败 (例如 4xx 或 5xx), 则会抛出异常

        return response.json(), None

    except requests.exceptions.Timeout:
        return None, "请求超时。请检查网络或后端服务是否正在运行。"
    except requests.exceptions.ConnectionError:
        return None, "连接错误。无法连接到后端服务。"
    except requests.exceptions.RequestException as e:
        return None, f"网络请求失败: {e}"
    finally:
        # 确保所有打开的文件都被关闭
        for _, (_, f, _) in files_to_send:
            f.close()


def get_task_status(task_id: str) -> Tuple[Dict[str, Any] | None, str | None]:
    """根据任务ID获取查重结果。"""
    try:
        with requests.Session() as session:
            response = session.get(f"{BASE_URL}/check/{task_id}", timeout=10)
            response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        return None, f"获取任务状态失败: {e}"