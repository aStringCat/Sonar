# app/api.py (最终修复版)

import uuid
import itertools
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, status
from typing import List, Dict

from .models import TaskStatusResponse, DetailedComparisonResponse, ComparisonResultItem
from .core import calculate_similarity, generate_detailed_diff

# 模拟数据库/任务存储
tasks_db: Dict[str, Dict] = {}

router = APIRouter()


def run_check(task_id: str, files_content: Dict[str, str]):
    """
    这是在后台运行的实际查重函数。
    """
    filenames = list(files_content.keys())
    results = []
    detailed_results = {}

    for i, (file1, file2) in enumerate(itertools.combinations(filenames, 2)):
        code1 = files_content[file1]
        code2 = files_content[file2]

        similarity = calculate_similarity(code1, code2)
        result_id = f"{task_id}-{i}"

        results.append(
            ComparisonResultItem(result_id=result_id, file1=file1, file2=file2, similarity=similarity)
        )
        detailed_results[result_id] = generate_detailed_diff(file1, code1, file2, code2)

    results.sort(key=lambda x: x.similarity, reverse=True)

    # 更新任务状态和结果
    tasks_db[task_id]['status'] = 'completed'
    tasks_db[task_id]['summary_results'] = results
    tasks_db[task_id]['detailed_results'] = detailed_results


@router.post("/check", response_model=TaskStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_plagiarism_check(
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(..., description="需要查重的多个Python代码文件")
):
    """
    接收批量代码文件，启动后台查重任务，并立即返回任务ID。
    """
    filenames = [file.filename for file in files]
    if len(filenames) != len(set(filenames)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate filenames are not allowed. Please provide files with unique names."
        )

    task_id = str(uuid.uuid4())
    files_content = {file.filename: (await file.read()).decode('utf-8') for file in files}

    tasks_db[task_id] = {"status": "processing", "summary_results": None, "detailed_results": None}

    background_tasks.add_task(run_check, task_id, files_content)

    return TaskStatusResponse(task_id=task_id, status="processing")


@router.get("/check/{task_id}", response_model=TaskStatusResponse)
async def get_check_status(task_id: str):
    """
    根据任务ID查询查重结果。
    """
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task['status'] == 'completed':
        return TaskStatusResponse(task_id=task_id, status='completed', results=task['summary_results'])

    return TaskStatusResponse(task_id=task_id, status='processing')


@router.get("/comparison/{result_id}", response_model=DetailedComparisonResponse)
async def get_comparison_detail(result_id: str):
    """
    根据结果ID获取两份代码的详细比对，用于高亮显示。
    """
    try:
        # 【最终修复】使用 rsplit 从右边分割，确保正确提取完整的UUID
        task_id, _ = result_id.rsplit('-', 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid result_id format")

    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if 'detailed_results' not in task or not task.get('detailed_results'):
        raise HTTPException(status_code=404, detail="Detailed results not available for this task.")

    detail = task['detailed_results'].get(result_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Comparison detail not found")

    return DetailedComparisonResponse(**detail)