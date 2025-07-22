from fastapi import FastAPI
from app.api import router
from app.database import create_db_and_tables

create_db_and_tables()

app = FastAPI(
    title="Python 代码查重工具 API",
    description="一个用于课程作业抄袭检测的后端服务。",
    version="1.0.0"
)

# 包含API路由
app.include_router(router, prefix="/api", tags=["Plagiarism Checker"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "欢迎使用代码查重API! 请访问 /docs 查看API文档。"}