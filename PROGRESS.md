# 开发进度记录

> 更新日期：2026-08-11
> 依据：《课后反馈系统 —— 具体实施计划.md》

## 当前进度：阶段 0-2 已完成 ✅

### 阶段 0：项目初始化 ✅
- [x] git 仓库初始化
- [x] 根目录 `docker-compose.yml`（PostgreSQL 16 / Redis 7 / MinIO，供部署参考）
- [x] `.env.example` / `.env` 配置
- [x] `backend/`（FastAPI）+ `frontend/`（Vue3 + Vite）骨架

> 本机开发环境未使用 Docker，改用本机服务：
> - PostgreSQL 18（本地服务，已建库 `pfs`/用户 `pfs`）
> - Redis 3.2（本地 `D:\Redis-x64-3.2.100`，端口 6379）
> - 文件存储：`STORAGE_BACKEND=local`（本地磁盘 `backend/local_storage/`，经 `/api/storage/files/` 访问），MinIO 后端接口已预留，配置 `STORAGE_BACKEND=minio` 即可切换

### 阶段 1：基础框架 + 数据模型 ✅（对应实施计划第 1 周）
后端：
- [x] FastAPI + SQLAlchemy 2.0 + Alembic + JWT + RBAC（admin/teacher/student）
- [x] 13 张核心表全部建好：users、classes、class_students、assignments、assignment_questions、questions、knowledge_points、question_knowledge_points、submissions、submission_answers
- [x] API：`/auth/login`、`/auth/me`、classes CRUD + 学生、assignments CRUD + publish + 加题、questions CRUD、knowledge-points（含 tree）
- [x] seed 脚本：admin/admin123、teacher1/teacher123、student1-3/student123，初中数学知识点树

前端（教师端）：
- [x] 登录页、教师布局
- [x] 班级管理、学生管理（搜索 + 批量添加）
- [x] 作业列表、新建作业、作业详情（添加题目/发布）、题库（建题 + 知识点树绑定）

### 阶段 2：学生提交模块 ✅（对应实施计划第 2 周）
后端：
- [x] `submissions` / `submission_answers` 表
- [x] 文本提交（逐题答案）+ 图片/PDF 上传（本地存储）
- [x] `POST /api/assignments/{id}/submit`、`GET /api/submissions/{id}`、`GET /api/assignments/{id}/submissions`
- [x] Celery + Redis 异步任务（`ocr_submission`，当前接 Mock OCR，状态 processing → submitted）

前端：
- [x] 学生端：我的作业、作业详情（文本逐题作答 / 图片 PDF 上传）、提交记录
- [x] 教师端：作业提交记录列表（状态 + 文件查看）

## 验收结果（已实测通过）

全链路 API 冒烟测试通过：
```
教师登录 → 建班 → 加学生 → 建知识点 → 建题 → 建作业 → 加题 → 发布
→ 学生登录 → 查看作业 → 文本提交 ✓ → 教师查看提交列表 ✓
→ 学生图片上传 ✓（本地存储 + /api/storage/files 访问 200）
→ Celery worker 执行 Mock OCR 任务成功 ✓（processing → submitted）
```
前端构建通过，Vite dev server（5174）+ `/api` 代理连通。

## 本机启动方式

```bash
# 1. 数据库/Redis 需已启动（见上）
# 2. 后端（backend 目录）
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
# 3. Celery worker（backend 目录）
.venv/Scripts/python -m celery -A app.tasks.celery_app worker --loglevel=info -P solo
# 4. 前端（frontend 目录）
npm run dev   # http://localhost:5174
```

## 后续计划（阶段 3-6）

- [ ] 阶段 3：OCR Mock→AI 批改引擎（GradingRouter / RuleGrader / HybridGrader / LLMGrader）+ Celery 异步批改 + 结构化输出校验（对应第 3 周）
- [ ] 阶段 4：教师复核系统（改分/评语/确认/重试/标记异常，确认后写入 student_knowledge_records）（对应第 4 周）
- [ ] 阶段 5：学情分析（掌握度计算、student_knowledge_stats、ECharts 学生/班级学情）（对应第 5 周）
- [ ] 阶段 6：Feedback Engine（结构化数据 → LLM 生成课后反馈）、异常处理/日志、部署（对应第 6 周）

## 已知技术选型（与用户确认）
- 异步任务：Celery + Redis
- LLM：OpenAI 兼容接口（开发期 `LLM_PROVIDER=mock`）
- OCR：先 Mock，后接真实第三方
