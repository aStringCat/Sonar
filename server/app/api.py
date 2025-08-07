import itertools
import uuid
from typing import List, Dict

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, status, Form, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .core import calculate_similarity, generate_detailed_diff
from .database import SessionLocal, get_db
from .models import QueryHistory, HistoryResult, Setting
from .schemas import (
    TaskStatusResponse, DetailedComparisonResponse, ComparisonResultItem,
    QueryHistoryResponse, MarkPlagiarizedRequest, SimilarityThreshold
)

tasks_db: Dict[str, Dict] = {}

router = APIRouter()


def get_or_create_threshold(db: Session) -> float:
    db_setting = db.query(Setting).filter(Setting.key == "similarity_threshold").first()
    if not db_setting:
        db_setting = Setting(key="similarity_threshold", value="0.85")
        db.add(db_setting)
        db.commit()
        db.refresh(db_setting)
        return 0.85
    return float(db_setting.value)


# 替换旧的 run_check_and_save
def run_check_and_save(task_id: str, description: str, folder_name: str, files_content: Dict[str, str]):
    db = SessionLocal()
    try:
        threshold = get_or_create_threshold(db)
        filenames = list(files_content.keys())
        results_list = []
        detailed_results = {}

        for i, (file1, file2) in enumerate(itertools.combinations(filenames, 2)):
            code1 = files_content[file1]
            code2 = files_content[file2]
            similarity = calculate_similarity(code1, code2)
            is_plagiarized = similarity > threshold
            result_id = f"{task_id}-{i}"
            results_list.append(ComparisonResultItem(
                result_id=result_id, file1=file1, file2=file2,
                similarity=similarity, plagiarized=is_plagiarized
            ))
            detailed_results[result_id] = generate_detailed_diff(file1, code1, file2, code2)

        results_list.sort(key=lambda x: x.similarity, reverse=True)

        new_history_entry = QueryHistory(
            query_type='文件夹互查', description=description, folder_name=folder_name,
            special_file_name='-'
        )
        db.add(new_history_entry)
        db.commit()
        db.refresh(new_history_entry)

        for res in results_list:
            db_result = HistoryResult(
                history_id=new_history_entry.id, result_id=res.result_id,
                file1=res.file1, file2=res.file2, similarity=res.similarity,
                plagiarized=res.plagiarized
            )
            db.add(db_result)
        db.commit()
        print(f"新历史记录 (ID: {new_history_entry.id}) 已存入数据库。")

    finally:
        db.close()

    tasks_db[task_id]['status'] = 'completed'
    tasks_db[task_id]['summary_results'] = results_list
    tasks_db[task_id]['detailed_results'] = detailed_results


@router.post("/check", response_model=TaskStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_plagiarism_check(
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        folder_name: str = Form(...)
):
    filenames = [file.filename for file in files]
    if len(filenames) != len(set(filenames)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Duplicate filenames are not allowed. Please provide files with unique names.")
    task_id = str(uuid.uuid4())
    files_content = {file.filename: (await file.read()).decode('utf-8') for file in files}

    final_description = f"文件夹 '{folder_name}' ({len(files_content)}个文件)"
    tasks_db[task_id] = {"status": "processing", "summary_results": None, "detailed_results": None}

    background_tasks.add_task(run_check_and_save, task_id, final_description, folder_name, files_content)
    return TaskStatusResponse(task_id=task_id, status="processing")


@router.get("/check/{task_id}", response_model=TaskStatusResponse)
async def get_check_status(task_id: str):
    """根据任务ID查询查重结果。"""
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task['status'] == 'completed':
        return TaskStatusResponse(task_id=task_id, status='completed', results=task['summary_results'])
    return TaskStatusResponse(task_id=task_id, status='processing')


@router.get("/comparison/{result_id}", response_model=DetailedComparisonResponse)
async def get_comparison_detail(result_id: str):
    """根据结果ID获取两份代码的详细比对，用于高亮显示。"""
    try:
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


# 替换旧的 run_one_to_many_check
def run_one_to_many_check(task_id: str, description: str, folder_name: str, base_filename: str,
                          base_file_content: str, other_files_content: Dict[str, str]):
    """后台运行“一对多”查重，并根据阈值自动标记和保存。"""
    db = SessionLocal()
    try:
        threshold = get_or_create_threshold(db)
        results_list = []
        detailed_results = {}

        for i, (other_filename, other_content) in enumerate(other_files_content.items()):
            similarity = calculate_similarity(base_file_content, other_content)
            is_plagiarized = similarity > threshold
            result_id = f"{task_id}-{i}"
            results_list.append(ComparisonResultItem(
                result_id=result_id, file1=base_filename, file2=other_filename,
                similarity=similarity, plagiarized=is_plagiarized
            ))
            detailed_results[result_id] = generate_detailed_diff(base_filename, base_file_content, other_filename,
                                                                 other_content)

        results_list.sort(key=lambda x: x.similarity, reverse=True)

        new_history_entry = QueryHistory(
            query_type='一对多比对', description=description, folder_name=folder_name,
            special_file_name=base_filename
        )
        db.add(new_history_entry)
        db.commit()
        db.refresh(new_history_entry)

        for res in results_list:
            db_result = HistoryResult(
                history_id=new_history_entry.id, result_id=res.result_id,
                file1=res.file1, file2=res.file2, similarity=res.similarity,
                plagiarized=res.plagiarized
            )
            db.add(db_result)
        db.commit()
        print(f"新历史记录 (ID: {new_history_entry.id}) 已存入数据库。")

    finally:
        db.close()

    tasks_db[task_id]['status'] = 'completed'
    tasks_db[task_id]['summary_results'] = results_list
    tasks_db[task_id]['detailed_results'] = detailed_results


@router.post("/check_one", response_model=TaskStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_one_to_many_check(
        background_tasks: BackgroundTasks,
        base_file: UploadFile = File(...),
        other_files: List[UploadFile] = File(...),
        folder_name: str = Form(...)
):
    task_id = str(uuid.uuid4())
    base_file_content = (await base_file.read()).decode('utf-8')
    other_files_content = {file.filename: (await file.read()).decode('utf-8') for file in other_files}

    final_description = f"文件 '{base_file.filename}' vs 文件夹 '{folder_name}' ({len(other_files_content)}个文件)"
    tasks_db[task_id] = {"status": "processing", "summary_results": None, "detailed_results": None}

    background_tasks.add_task(run_one_to_many_check, task_id, final_description, folder_name, base_file.filename,
                              base_file_content, other_files_content)
    return TaskStatusResponse(task_id=task_id, status="processing")


@router.get("/history", response_model=List[QueryHistoryResponse])
async def get_all_history(db: Session = Depends(get_db)):
    """获取所有历史查询任务的列表，按时间倒序排列。"""
    history_list = db.query(QueryHistory).order_by(QueryHistory.query_time.desc()).all()
    return history_list


@router.get("/history/{history_id}", response_model=TaskStatusResponse)
async def get_history_detail(history_id: int, db: Session = Depends(get_db)):
    """根据历史ID获取该次任务的详细查重结果，包含抄袭标记。"""
    results = db.query(HistoryResult).filter(HistoryResult.history_id == history_id).order_by(
        HistoryResult.similarity.desc()).all()
    if not results:
        raise HTTPException(status_code=404, detail="未找到该历史记录的详细结果。")
    response_results = [ComparisonResultItem.model_validate(res) for res in results]
    return TaskStatusResponse(task_id=f"history-{history_id}", status="completed", results=response_results)


@router.put("/results/{result_id}/mark", status_code=status.HTTP_204_NO_CONTENT)
async def mark_result_as_plagiarized(result_id: str, request: MarkPlagiarizedRequest, db: Session = Depends(get_db)):
    """根据 result_id 手动更新一个结果的抄袭标记。"""
    db_result = db.query(HistoryResult).filter(HistoryResult.result_id == result_id).first()
    if not db_result:
        raise HTTPException(status_code=404, detail="Result not found")
    db_result.plagiarized = request.plagiarized
    db.commit()
    return


@router.get("/settings/similarity_threshold", response_model=SimilarityThreshold)
async def get_similarity_threshold(db: Session = Depends(get_db)):
    """获取当前的相似度阈值。"""
    threshold_value = get_or_create_threshold(db)
    return SimilarityThreshold(threshold=threshold_value)


@router.post("/settings/similarity_threshold", response_model=SimilarityThreshold)
async def set_similarity_threshold(threshold: SimilarityThreshold, db: Session = Depends(get_db)):
    """设置新的相似度阈值。"""
    db_setting = db.query(Setting).filter(Setting.key == "similarity_threshold").first()
    if not db_setting:
        db_setting = Setting(key="similarity_threshold")
        db.add(db_setting)
    db_setting.value = str(threshold.threshold)
    db.commit()
    return threshold


@router.get("/export/plagiarized")
async def export_plagiarized_results(db: Session = Depends(get_db)):
    """导出所有被标记为抄袭的记录。"""
    plagiarized_items = db.query(HistoryResult).filter(HistoryResult.plagiarized == True).all()
    return JSONResponse(content=[ComparisonResultItem.model_validate(item).model_dump() for item in plagiarized_items])
