# 一生一案学业发展管理系统

学生学业发展管理系统，以**学生总案、周测成绩、月度评定、过程任务**为核心。

业务闭环：

```
诊断证据 → 班主任确认并维护总案/学科方案 → 日周月任务 → 班主任记录执行过程 → 校级督查 → 阶段复盘 → 家长查看已发布版本
```


## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 + Vite + Element Plus + Pinia + Vue Router + Axios + ECharts |
| 小程序 | uni-app + Vue 3 + Vite + Pinia（`miniprogram/`，微信端家长/学生/教师轻量入口） |
| 后端 | Python + FastAPI + SQLAlchemy + Alembic + Pydantic Settings |
| 数据/基础设施 | PostgreSQL 16 + Redis 7 + MinIO（开发）/ OSS（生产） |
| 异步任务 | Celery + Redis（生产 `worker` 服务） |
| AI/OCR | OpenAI 兼容 LLM 接口 + 通义 qwen-vl-ocr，均支持 `mock` 模式本地联调 |

## 目录结构

```
backend/               FastAPI 后端
  app/
    main.py            应用入口（中间件、CORS、/api/health、/api/ready）
    api/               业务路由：admin、users、classes、student_cases、
    │                  case_tasks、weekly_scores、points_reports、
    │                  monthly_reports、storage_files
    auth/              登录鉴权（含微信 wx-login / wx-bind）
    models/            User、Class、StudentCase、WeeklyScore、MonthlyReport 等
    core/              config / database / security / rate_limit / pagination
    tasks/             Celery 异步任务
    ai/ ocr/ grading/  LLM / OCR / 批改相关
    seed.py            开发种子数据
  migrations/          Alembic 迁移脚本
  requirements.txt
frontend/              Vue3 管理端
  src/
    api/               后端 /api/* 封装
    views/             admin / deyu / teacher / subject / consultant /
    │                  student / parent + Login / Register
    router/ stores/ layouts/ components/
miniprogram/           小程序端（家长分包 P0 / 学生分包 P1 / 教师轻量 P2）
docs/                  miniprogram-plan.md 等文档
deploy/                nginx.conf + production-secrets.example.env
docker-compose.yml     开发基础设施：postgres + redis + minio
docker-compose.prod.yml  生产：postgres + redis + api + worker + web
.env.example           环境变量模板（根目录 / backend / miniprogram 各一份）
```

## 快速启动（开发）

### 1. 启动基础设施

```bash
docker compose up -d
# postgres :5432 / redis :6379 / minio :9000（控制台 :9001）
# 默认账号：pfs / pfs，minio root 密码 pfs123456
```

### 2. 启动后端

```bash
cp .env.example .env   # 按需修改 SECRET_KEY、LLM/OCR Key、WX_APPID 等
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

- 接口前缀：`http://localhost:8000/api`
- 存活探针：`GET /api/health` → `{"status":"ok"}`
- 就绪探针：`GET /api/ready` → 校验数据库连接，失败返回 503
- Swagger 文档：`http://localhost:8000/docs`

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

前端通过 `VITE_API_BASE=http://localhost:8000/api` 指向后端（见根目录 `.env.example`）。

### 4. 小程序（可选）

```bash
cd miniprogram
npm install
npm run dev        # H5 预览
npm run build:mp-weixin  # 构建微信小程序，再用微信开发者工具导入 dist 对应目录
```

详见 `miniprogram/README.md` 与 `docs/miniprogram-plan.md`。

## 环境变量

以 `.env.example` 为准，关键项：

| 变量 | 说明 | 默认 |
| --- | --- | --- |
| `APP_NAME` | 应用名 | 一生一案学业发展管理系统 |
| `DATABASE_URL` | Postgres 连接 | `postgresql+psycopg://pfs:pfs@localhost:5432/pfs` |
| `REDIS_URL` / `CELERY_*` | Redis / Celery | `redis://localhost:6379/...` |
| `STORAGE_BACKEND` | `local`（开发）/ `minio` / `oss`（生产） | `local` |
| `LLM_PROVIDER` | `mock` / `openai_compat` | `mock` |
| `OCR_PROVIDER` | `mock` / `qwen` | `mock` |
| `WX_APPID` / `WX_SECRET` / `WX_MOCK` | 微信登录，开发期 `WX_MOCK=true` 可用 `mock:` 前缀透传 openid | — |
| `VITE_API_BASE` | 前端指向的后端地址 | `http://localhost:8000/api` |

生产环境启动即强校验（`backend/app/core/config.py`）：必须 `DEBUG=false`、`SECRET_KEY` ≥ 32 位随机值、`CORS_ORIGINS` 为明确域名列表。

## 默认种子账号

执行 `python -m app.seed`（幂等，已有则跳过）：

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `admin123` | 系统管理员 |
| `deyu1` | `deyu123` | 德育主任 |
| `teacher1` | `teacher123` | 班主任（初二(1)班） |
| `subject1` | `subject123` | 任课老师（数学） |
| `consultant1` | `consultant123` | 咨询老师 |
| `student1` / `student2` / `student3` | `student123` | 学生 |

种子数据见 `backend/app/seed.py`。

## 接口概览

统一前缀 `/api`（注册见 `backend/app/main.py`）：

- `auth`：账号登录、微信 `wx-login` / `wx-bind`、`me/children`（家长子女）
- `users` / `admin` / `classes`：用户、班级、任课关系管理
- `student_cases`：学生总案（含家长可见版本 `PARENT_VISIBLE_STATUSES` 越权 403）
- `case_tasks`（+ stage）：日周月任务、打卡、督查
- `weekly_scores` / `points_reports`：周测成绩与积分报表
- `monthly_reports`：月度评定
- `storage_files`：附件上传（本地 / MinIO / OSS，注意 `MAX_UPLOAD_BYTES` 默认 10MB）

## 生产部署

```bash
cp deploy/production-secrets.example.env .env.prod  # 填入真实 SECRET_KEY、密码、域名、CORS 等
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

生产包含 `api`（`alembic upgrade head` 后启动 uvicorn）、`worker`（celery）、`web`（前端构建 + nginx，见 `deploy/nginx.conf`，需自备 `deploy/certs/` 证书）。健康检查依赖 `/api/ready`。

## 测试

```bash
cd backend
pytest            # 配置见 pytest.ini
```

## 常见问题

- **后端连不上数据库**：先确认 `docker compose ps` 中 postgres healthy，再检查 `DATABASE_URL` 主机是 `localhost`（本地直连）还是 `postgres`（compose 内服务名）。
- **前端 401 / CORS 报错**：检查 `VITE_API_BASE` 与后端 `CORS_ORIGINS` 是否包含当前前端地址。
- **微信登录失败**：开发期确认 `WX_MOCK=true`；生产需配置真实 `WX_APPID/WX_SECRET`。
- **附件过大**：调整 `MAX_UPLOAD_BYTES`；生产确认 OSS bucket / endpoint / key 配置正确。
