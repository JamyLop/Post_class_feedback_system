"""FastAPI 应用入口：注册中间件与全部路由。"""

from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin,
    analytics,
    assignments,
    case_tasks,
    classes,
    feedback,
    grading,
    knowledge,
    monthly_reports,
    points_reports,
    questions,
    submissions,
    student_cases,
    users,
    weekly_scores,
)
from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.database import engine
from app.core.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.middleware("http")
async def request_log(request: Request, call_next):
    """请求日志中间件：记录耗时与结果，异常时记录堆栈。"""
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request_failed method=%s path=%s", request.method, request.url.path
        )
        raise
    logger.info(
        "request_completed method=%s path=%s status=%s duration_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        round((time.perf_counter() - started) * 1000),
    )
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载全部业务路由（统一 /api 前缀）
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(classes.router, prefix=settings.api_prefix)
app.include_router(knowledge.router, prefix=settings.api_prefix)
app.include_router(questions.router, prefix=settings.api_prefix)
app.include_router(assignments.router, prefix=settings.api_prefix)
app.include_router(submissions.router, prefix=settings.api_prefix)
app.include_router(grading.router, prefix=settings.api_prefix)
app.include_router(analytics.router, prefix=settings.api_prefix)
app.include_router(feedback.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(case_tasks.router, prefix=settings.api_prefix)
app.include_router(student_cases.router, prefix=settings.api_prefix)
app.include_router(weekly_scores.router, prefix=settings.api_prefix)
app.include_router(points_reports.router, prefix=settings.api_prefix)
app.include_router(monthly_reports.router, prefix=settings.api_prefix)


@app.get("/api/health")
def health():
    """存活探针：进程存在即返回 ok。"""
    return {"status": "ok"}


@app.get("/api/ready")
def ready():
    """就绪探针：校验数据库可连接。"""
    from sqlalchemy import text

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=True,
        reload_dirs=["app"],
    )
