from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# 使用SQLite数据库，数据库文件将存放在项目根目录的 a.db 文件中
DATABASE_URL = "sqlite:///./a.db"

engine = create_engine(
    DATABASE_URL,
    # 这个参数只在SQLite中需要，用于允许多线程共享同一个连接
    connect_args={"check_same_thread": False}
)

# 创建SessionLocal类，其实例将是实际的数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_db_and_tables():
    # 创建在模型中定义的所有表
    Base.metadata.create_all(bind=engine)