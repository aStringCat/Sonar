from pydantic import BaseModel, Field
from typing import List, Optional
import datetime


class ComparisonResultItem(BaseModel):
    """单对文件比较结果的摘要"""
    result_id: str = Field(..., description="唯一的结果ID，用于获取详情")
    file1: str
    file2: str
    similarity: float = Field(..., description="相似度得分 (0.0 to 1.0)")
    # 【新增】抄袭标记字段
    plagiarized: bool = Field(False, description="是否被标记为抄袭")

    class Config:
        from_attributes = True


class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    task_id: str
    status: str = Field(..., description="任务状态: processing, completed, or error")
    results: Optional[List[ComparisonResultItem]] = None  # 仅在 completed 时提供


class CodeLine(BaseModel):
    """带状态的单行代码"""
    line_num: int
    text: str
    status: str = Field(..., description="代码行状态: similar, unique")


class FileDetail(BaseModel):
    """包含带状态代码行的文件详情"""
    name: str
    lines: List[CodeLine]


class DetailedComparisonResponse(BaseModel):
    """用于高亮显示的详细比对结果"""
    file1_details: FileDetail
    file2_details: FileDetail


class QueryHistoryResponse(BaseModel):
    """用于API响应的历史记录Pydantic模型"""
    id: int
    query_time: datetime.datetime
    query_type: str
    description: str
    folder_name: Optional[str] = None
    special_file_name: Optional[str] = None

    class Config:
        from_attributes = True


class MarkPlagiarizedRequest(BaseModel):
    """手动标记抄袭的请求体"""
    plagiarized: bool


class SimilarityThreshold(BaseModel):
    """相似度阈值的模型"""
    threshold: float
