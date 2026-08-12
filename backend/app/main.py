from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    assignments,
    classes,
    grading,
    knowledge,
    questions,
    submissions,
    users,
)
from app.auth.router import router as auth_router
from app.core.config import settings
from app.storage import serve_file


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(classes.router, prefix=settings.api_prefix)
app.include_router(knowledge.router, prefix=settings.api_prefix)
app.include_router(questions.router, prefix=settings.api_prefix)
app.include_router(assignments.router, prefix=settings.api_prefix)
app.include_router(submissions.router, prefix=settings.api_prefix)
app.include_router(grading.router, prefix=settings.api_prefix)


@app.get("/api/storage/files/{path:path}")
def storage_file(path: str):
    return serve_file(path)


@app.get("/api/health")
def health():
    return {"status": "ok"}
