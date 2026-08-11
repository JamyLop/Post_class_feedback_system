# 课后反馈系统

基于《课后反馈系统 —— 具体实施计划》的 MVP 实现。

## 业务闭环（第一阶段目标）

```
作业创建 → 学生提交 → OCR/结构化 → AI 批改 → 教师复核 → 学情更新 → 课后反馈
```

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 + Vite + Element Plus + Pinia + Axios + ECharts |
| 后端 | Python + FastAPI + SQLAlchemy + Alembic + Celery |
| 数据 | PostgreSQL + Redis |
| 存储 | MinIO |
| AI | OpenAI 兼容接口（开发期 mock） |
| OCR | 第三方（开发期 mock） |

## 目录结构

```
backend/     FastAPI 后端
frontend/    Vue3 前端
docker-compose.yml
```

## 快速启动

1. 启动基础设施：

```bash
docker compose up -d
```

2. 启动后端：

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

3. 启动 Celery worker：

```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

4. 启动前端：

```bash
cd frontend
npm install
npm run dev
```

5. 访问 http://localhost:5173

默认种子账号见 `backend/app/seed.py`。
