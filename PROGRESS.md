# 开发进度记录

> 更新日期：2026-08-12
> 依据：《课后反馈系统 —— 具体实施计划.md》

## 当前进度：阶段 0-4 已完成 ✅

### 阶段 0：项目初始化 ✅
- [x] git 仓库初始化
- [x] 根目录 `docker-compose.yml`（PostgreSQL 16 / Redis 7 / MinIO，供部署参考）
- [x] `.env.example` / `.env` 配置
- [x] `backend/`（FastAPI）+ `frontend/`（Vue3 + Vite）骨架

> 本机开发环境未使用 Docker，改用本机服务：
> - PostgreSQL 18（本地服务，已建库 `pfs`/用户 `pfs`）
> - Redis 3.2（本地 `D:\Redis-x64-3.2.100`，端口 6379；本机未装为服务，开发时手动启动 `redis-server.exe --port 6379`）
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

### 阶段 3：OCR Mock→AI 批改引擎 ✅（对应实施计划第 3 周）
后端：
- [x] 新表 `grading_results` + `grading_prompt_versions`（Alembic 迁移 `86e937410e61`）
- [x] `app/grading/`：GradingRouter / RuleGrader / HybridGrader / LLMGrader / validator / prompts / schemas / base
  - RuleGrader：单选/多选/判断题，规则比对，不调 LLM（成本控制）
  - HybridGrader：填空题，规则优先 + LLM 部分分
  - LLMGrader：计算/简答题，LLM 结构化输出
- [x] 结构化输出 Pydantic 校验：JSON 解析失败重试 1 次，仍失败降级人工复核（error_type=parse_failed）
- [x] 置信度策略：`confidence>=0.85` 正常展示；`0.70~0.85` 提示重点检查；`<0.70` 强制人工复核（status=manual_review）
- [x] MockLLMProvider 升级为启发式批改（基于答案相似度），返回与真实 LLM 一致的结构化 JSON
- [x] Celery `grade_submission` 异步批改任务；文本提交自动触发，image/pdf 提交 OCR 完成后触发
- [x] Grading API：`POST /submissions/{id}/grade`、`GET /submissions/{id}/grading`、`POST /gradings/{id}/retry`

前端：
- [x] 学生端提交结果页展示 AI 批改（每题得分/对错/AI评语/置信度标签）
- [x] 教师端提交记录：批改结果抽屉（题目/学生答案/标准答案/得分/错误类型/AI评语）+ 单题重新批改

顺带修复：
- [x] `create_question`/`get_question` 返回 `knowledge_points` 为 ORM 对象导致 500 的既有 bug

## 验收结果（已实测通过）

阶段 1-2 全链路 API 冒烟测试通过（见上一版记录）。

阶段 3 端到端冒烟测试通过（六种题型作业，文本提交）：
```
教师建班加学生 → 建题（单选/判断/填空/计算/简答，绑定知识点）→ 建作业 → 发布
→ 学生文本提交 → Celery 自动批改（submitted → ai_graded）
→ GET /grading 返回：
  单选 对 10/10  rule  conf=1.0
  判断 对 10/10  rule  conf=1.0
  填空 部分 6/10  hybrid conf=0.6  → status=manual_review（<0.70 强制复核 ✓）
  计算 部分 18.4/20 ai   conf=0.78 → ai_completed（0.70~0.85 提示重点检查 ✓）
  简答 对 20/20  ai   conf=0.92  → ai_completed（≥0.85 正常 ✓）
  总分 64.4/70
→ 单题 retry 同步重新批改 ✓
```
前端 `npm run build` 通过。

## 本机启动方式

```bash
# 0. 启动 Redis（本机未注册为服务）
D:\Redis-x64-3.2.100\Redis-x64-3.2.100\redis-server.exe --port 6379
# 1. 数据库需已启动（PostgreSQL 本地服务）
# 2. 后端（backend 目录）
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
# 3. Celery worker（backend 目录）
.venv/Scripts/python -m celery -A app.tasks.celery_app worker --loglevel=info -P solo
# 4. 前端（frontend 目录）
npm run dev   # http://localhost:5174
```

### 阶段 4：教师复核系统 ✅（对应实施计划第 4 周）
后端：
- [x] 新表 `student_knowledge_records`（原始学习轨迹，确认时写入；Alembic 迁移 `00e2fdc191e0`）
- [x] `GET /api/reviews` 复核队列（`review_status=pending|confirmed`，可按作业过滤；教师仅见自己作业的提交，含进度 confirmed_count/answer_count）
- [x] `PUT /api/gradings/{id}/confirm` 单题确认（可覆盖分数/评语，分数缺省沿用 AI；校验 0~满分；同步 answer 并写入知识点记录）
- [x] `POST /api/gradings/{id}/flag` 标记异常（必填原因，前缀【标记异常】，保持待复核）
- [x] `POST /api/submissions/{id}/confirm-all` 作业级一键确认（未确认题沿用 AI 分数）
- [x] 确认后：该题 grading.status=confirmed、reviewed_at=now；整份全部确认 → submission.status=teacher_reviewed
- [x] 知识点记录按 (学生,作业,题目) 先清后写，重复确认不产生重复数据

前端：
- [x] 教师复核中心页（待复核/已确认 Tab + 作业过滤 + 进度条）
- [x] 逐题复核页：左侧题号导航（上一题/下一题）、题目/学生答案/标准答案/AI结果/错误点/置信度展示、教师改分/评语、确认本题、标记异常、重新AI批改、确认全部批改

验收结果：`pytest` 27 个用例全绿（新增 `test_teacher_review.py` 7 个），前端 `npm run build` 通过。

## 后续计划（阶段 5-6）

- [ ] 阶段 5：学情分析（掌握度计算、student_knowledge_stats、ECharts 学生/班级学情）（对应第 5 周）
- [ ] 阶段 6：Feedback Engine（结构化数据 → LLM 生成课后反馈）、异常处理/日志、部署（对应第 6 周）

## 已知技术选型（与用户确认）
- 异步任务：Celery + Redis
- LLM：OpenAI 兼容接口（开发期 `LLM_PROVIDER=mock`）
- OCR：先 Mock，后接真实第三方
