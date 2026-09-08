# 一生一案学业发展管理系统

面向高三试点的学生学业发展管理系统，以学生总案、周测成绩、月度评定和过程任务为核心。

## 高三试点业务闭环

```
诊断证据 → 班主任确认并维护总案/学科方案 → 日周月任务 → 班主任记录执行过程 → 校级督查 → 阶段复盘 → 家长查看已发布版本
```

第一版只开放高三：先验证 5 名学生，再扩展到一个班，最后覆盖高三全年级。家长端作为最终阅读入口；初三、艺考班和生产部署不在本阶段范围内。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 + Vite + Element Plus + Pinia + Axios + ECharts |
| 后端 | Python + FastAPI + SQLAlchemy + Alembic |
| 数据 | PostgreSQL |

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

3. 启动前端：

```bash
cd frontend
npm install
npm run dev
```

4. 访问 http://localhost:5173

默认种子账号见 `backend/app/seed.py`。
