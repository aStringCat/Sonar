import uuid
import itertools
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, status
from typing import List, Dict

from .models import TaskStatusResponse, DetailedComparisonResponse, ComparisonResultItem, CodeSubmission
from .core import calculate_similarity, generate_detailed_diff
from .database import SessionLocal

import hashlib

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

    # 将本次提交的代码存入数据库
    db = SessionLocal()
    try:
        for filename, content in files_content.items():
            # 计算哈希值
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            # 检查是否已存在
            exists = db.query(CodeSubmission).filter(CodeSubmission.content_hash == content_hash).first()
            if not exists:
                db_submission = CodeSubmission(
                    filename=filename,
                    content=content,
                    content_hash=content_hash
                )
                db.add(db_submission)
        db.commit()
    finally:
        db.close()

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


def run_one_to_many_check(task_id: str, base_filename: str, base_file_content: str, other_files_content: Dict[str, str]):
    """
    【已修改】后台运行的“一对多”查重函数。
    比较一个基准文件和多个其他文件。
    """
    results = []
    detailed_results = {}

    # 遍历所有“其他文件”，逐一与基准文件比较
    for i, (other_filename, other_content) in enumerate(other_files_content.items()):
        similarity = calculate_similarity(base_file_content, other_content)
        result_id = f"{task_id}-{i}"

        results.append(
            ComparisonResultItem(result_id=result_id, file1=base_filename, file2=other_filename, similarity=similarity)
        )
        detailed_results[result_id] = generate_detailed_diff(base_filename, base_file_content, other_filename, other_content)

    results.sort(key=lambda x: x.similarity, reverse=True)

    # 更新任务状态和结果
    tasks_db[task_id]['status'] = 'completed'
    tasks_db[task_id]['summary_results'] = results
    tasks_db[task_id]['detailed_results'] = detailed_results


# 替换旧的 /check_one 路由
@router.post("/check_one", response_model=TaskStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_one_to_many_check(
        background_tasks: BackgroundTasks,
        base_file: UploadFile = File(..., description="一份基准代码文件"),
        other_files: List[UploadFile] = File(..., description="多份需要进行对比的代码文件")
):
    """
    【已修改】接收一个基准文件和多份对比文件，与文件夹内所有文件进行比较。
    """
    task_id = str(uuid.uuid4())

    # 读取文件内容
    base_file_content = (await base_file.read()).decode('utf-8')
    other_files_content = {file.filename: (await file.read()).decode('utf-8') for file in other_files}

    # 初始化任务状态
    tasks_db[task_id] = {"status": "processing", "summary_results": None, "detailed_results": None}

    # 启动后台任务，并传递正确的文件内容
    background_tasks.add_task(run_one_to_many_check, task_id, base_file.filename, base_file_content, other_files_content)

    return TaskStatusResponse(task_id=task_id, status="processing")
