from pydantic import BaseModel, Field
from typing import List
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base # Corrected import
import datetime

# --- SQLAlchemy Models ---

Base = declarative_base()

class CodeSubmission(Base):
    __tablename__ = "code_submissions"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    content = Column(Text)
    submitted_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    # 增加一个哈希值用于快速去重，这是一个很好的实践
    content_hash = Column(String(64), unique=True, index=True)

# --- Models for Summary View ---

class ComparisonResultItem(BaseModel):
    """单对文件比较结果的摘要"""
    result_id: str = Field(..., description="唯一的结果ID，用于获取详情")
    file1: str
    file2: str
    similarity: float = Field(..., description="相似度得分 (0.0 to 1.0)")

class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    task_id: str
    status: str = Field(..., description="任务状态: processing, completed, or error")
    results: List[ComparisonResultItem] | None = None # 仅在 completed 时提供

# --- Models for Detailed View ---

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