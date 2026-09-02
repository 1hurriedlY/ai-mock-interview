"""FastAPI 应用入口：CORS、路由注册、启动建表。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .database import init_db
from .routers import admin, auth, export, history, industry, interview, project, resume

app = FastAPI(title="模拟面试 AI 助手", version="0.1.0")

# 允许前端本地开发地址跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(resume.router, prefix="/api/resume", tags=["简历"])
app.include_router(interview.router, prefix="/api/interview", tags=["面试"])
app.include_router(history.router, prefix="/api/history", tags=["历史"])
app.include_router(industry.router, prefix="/api/industry", tags=["行业调研"])
app.include_router(project.router, prefix="/api/project", tags=["项目渠道"])
app.include_router(export.router, prefix="/api/report", tags=["报告导出"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理"])


@app.on_event("startup")
def on_startup() -> None:
    """启动时建表（MySQL/Redis 未就绪时记录警告但不崩溃）。"""
    try:
        init_db()
    except Exception as exc:
        # 不阻塞启动，日志里提示
        import logging

        logging.getLogger(__name__).warning("数据库建表失败（请确认 MySQL 已启动）：%s", exc)


@app.get("/api/health")
def health() -> dict:
    """健康检查：返回服务与 Redis 状态。"""
    from .redis_client import redis_client

    return {"status": "ok", "redis": redis_client.available}
