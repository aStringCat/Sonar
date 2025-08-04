from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

# --- SQLAlchemy Database Models ---

class CodeSubmission(Base):
    __tablename__ = "code_submissions"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    content = Column(Text)
    submitted_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    content_hash = Column(String(64), unique=True, index=True)

class QueryHistory(Base):
    """用于存储每一次查询任务的元数据"""
    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True, index=True)
    query_time = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    query_type = Column(String(50))
    folder_name = Column(String, nullable=True)
    special_file_name = Column(String, nullable=True)
    description = Column(Text)

class HistoryResult(Base):
    """用于存储某次历史任务下的具体比对结果"""
    __tablename__ = "history_results"

    id = Column(Integer, primary_key=True, index=True)
    history_id = Column(Integer, index=True)
    result_id = Column(String, unique=True)
    file1 = Column(String)
    file2 = Column(String)
    similarity = Column(Float)