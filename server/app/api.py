import uuid
import itertools
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, status, Form
from typing import List, Dict

# 修改这一行
# 从新的 schemas.py 导入 Pydantic 模型
from .schemas import (
    TaskStatusResponse, DetailedComparisonResponse, ComparisonResultItem, QueryHistoryResponse
)
# 从 models.py 导入 SQLAlchemy 模型
from .models import CodeSubmission, QueryHistory, HistoryResult
from .core import calculate_similarity, generate_detailed_diff
from .database import SessionLocal

import hashlib

# 模拟数据库/任务存储
tasks_db: Dict[str, Dict] = {}

router = APIRouter()


# 替换旧的 run_check_and_save
def run_check_and_save(task_id: str, description: str, folder_name: str, files_content: Dict[str, str]):
    """【已修改】后台运行“文件夹互查”，并保存包括文件夹名的历史记录。"""
    # ... (函数内部的计算逻辑保持不变) ...
    filenames = list(files_content.keys())
    results_list = []
    detailed_results = {}
    for i, (file1, file2) in enumerate(itertools.combinations(filenames, 2)):
        code1 = files_content[file1]
        code2 = files_content[file2]
        similarity = calculate_similarity(code1, code2)
        result_id = f"{task_id}-{i}"
        results_list.append(ComparisonResultItem(result_id=result_id, file1=file1, file2=file2, similarity=similarity))
        detailed_results[result_id] = generate_detailed_diff(file1, code1, file2, code2)
    results_list.sort(key=lambda x: x.similarity, reverse=True)

    db = SessionLocal()
    try:
        # 【修改】保存历史记录时，加入 folder_name 和 special_file_name
        new_history_entry = QueryHistory(
            query_type='文件夹互查',
            description=description,
            folder_name=folder_name,
            special_file_name='-' # 互查模式没有特殊文件，用'-'表示
        )
        db.add(new_history_entry)
        # ... (后续的 db.commit() 等逻辑保持不变) ...
        db.commit()
        db.refresh(new_history_entry)
        for res in results_list:
            db_result = HistoryResult(history_id=new_history_entry.id, result_id=res.result_id, file1=res.file1, file2=res.file2, similarity=res.similarity)
            db.add(db_result)
        db.commit()
        print(f"新历史记录 (ID: {new_history_entry.id}) 已存入数据库。")
    finally:
        db.close()
    tasks_db[task_id]['status'] = 'completed'
    tasks_db[task_id]['summary_results'] = results_list
    tasks_db[task_id]['detailed_results'] = detailed_results

# 替换旧的 /check 路由
@router.post("/check", response_model=TaskStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_plagiarism_check(
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        folder_name: str = Form(...) # 【新增】从表单接收文件夹名
):
    """【已修改】接收“文件夹互查”请求，并将文件夹名一同存入历史记录。"""
    # ... (函数顶部的逻辑不变) ...
    filenames = [file.filename for file in files]
    if len(filenames) != len(set(filenames)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate filenames are not allowed. Please provide files with unique names.")
    task_id = str(uuid.uuid4())
    files_content = {file.filename: (await file.read()).decode('utf-8') for file in files}

    final_description = f"文件夹 '{folder_name}' ({len(files_content)}个文件)"
    tasks_db[task_id] = {"status": "processing", "summary_results": None, "detailed_results": None}

    # 【修改】调用后台任务时，传入 folder_name
    background_tasks.add_task(run_check_and_save, task_id, final_description, folder_name, files_content)
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


# 替换旧的 run_one_to_many_check 函数
# 替换旧的 run_one_to_many_check
def run_one_to_many_check(task_id: str, description: str, folder_name: str, base_filename: str, base_file_content: str, other_files_content: Dict[str, str]):
    """【已修改】后台运行“一对多”查重，并保存包括文件夹和文件名的历史记录。"""
    # ... (计算逻辑不变) ...
    results_list = []
    detailed_results = {}
    for i, (other_filename, other_content) in enumerate(other_files_content.items()):
        similarity = calculate_similarity(base_file_content, other_content)
        result_id = f"{task_id}-{i}"
        results_list.append(ComparisonResultItem(result_id=result_id, file1=base_filename, file2=other_filename, similarity=similarity))
        detailed_results[result_id] = generate_detailed_diff(base_filename, base_file_content, other_filename, other_content)
    results_list.sort(key=lambda x: x.similarity, reverse=True)

    db = SessionLocal()
    try:
        # 【修改】保存历史记录时，加入 folder_name 和 special_file_name (即 base_filename)
        new_history_entry = QueryHistory(
            query_type='一对多比对',
            description=description,
            folder_name=folder_name,
            special_file_name=base_filename
        )
        # ... (后续的 db.add, db.commit 等逻辑不变) ...
        db.add(new_history_entry)
        db.commit()
        db.refresh(new_history_entry)
        for res in results_list:
            db_result = HistoryResult(history_id=new_history_entry.id, result_id=res.result_id, file1=res.file1, file2=res.file2, similarity=res.similarity)
            db.add(db_result)
        db.commit()
        print(f"新历史记录 (ID: {new_history_entry.id}) 已存入数据库。")
    finally:
        db.close()
    tasks_db[task_id]['status'] = 'completed'
    tasks_db[task_id]['summary_results'] = results_list
    tasks_db[task_id]['detailed_results'] = detailed_results


# 替换旧的 /check_one 路由
@router.post("/check_one", response_model=TaskStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_one_to_many_check(
        background_tasks: BackgroundTasks,
        base_file: UploadFile = File(...),
        other_files: List[UploadFile] = File(...),
        folder_name: str = Form(...) # 【新增】从表单接收文件夹名
):
    """【已修改】接收“一对多”请求，并将文件夹和文件名一同存入历史记录。"""
    # ... (函数顶部的逻辑不变) ...
    task_id = str(uuid.uuid4())
    base_file_content = (await base_file.read()).decode('utf-8')
    other_files_content = {file.filename: (await file.read()).decode('utf-8') for file in other_files}

    final_description = f"文件 '{base_file.filename}' vs 文件夹 '{folder_name}' ({len(other_files_content)}个文件)"
    tasks_db[task_id] = {"status": "processing", "summary_results": None, "detailed_results": None}

    # 【修改】调用后台任务时，传入 folder_name 和 base_file.filename
    background_tasks.add_task(run_one_to_many_check, task_id, final_description, folder_name, base_file.filename, base_file_content, other_files_content)
    return TaskStatusResponse(task_id=task_id, status="processing")

# --- 新增的历史记录接口 ---

# 修改这一行
@router.get("/history", response_model=List[QueryHistoryResponse])
async def get_all_history():
    """获取所有历史查询任务的列表，按时间倒序排列。"""
    db = SessionLocal()
    try:
        history_list = db.query(QueryHistory).order_by(QueryHistory.query_time.desc()).all()
        return history_list
    finally:
        db.close()


@router.get("/history/{history_id}", response_model=TaskStatusResponse)
async def get_history_detail(history_id: int):
    """根据历史ID获取该次任务的详细查重结果。"""
    db = SessionLocal()
    try:
        results = db.query(HistoryResult).filter(HistoryResult.history_id == history_id).order_by(
            HistoryResult.similarity.desc()).all()
        if not results:
            raise HTTPException(status_code=404, detail="未找到该历史记录的详细结果。")

        # 将数据库结果转换为前端期望的 Pydantic 模型列表
        response_results = [ComparisonResultItem.from_orm(res) for res in results]

        # 返回与实时查询完全相同的数据结构
        return TaskStatusResponse(
            task_id=f"history-{history_id}",
            status="completed",
            results=response_results
        )
    finally:
        db.close()