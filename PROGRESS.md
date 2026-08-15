# 开发进度记录

> 更新日期：2026-08-12
> 依据：《课后反馈系统 —— 具体实施计划.md》

## 当前进度：阶段 0-6 已完成 ✅ + 安全基线 ✅

### 管理员控制台 + 注册功能 ✅（阶段 6 之后新增）
后端：
- [x] 新表 `invite_codes`（Alembic 迁移 `a1b2c3d4e5f6`）：code 唯一、role(teacher/student)、status(active/used/disabled)、过期时间、使用者
- [x] `POST /auth/register` 公开注册：仅限 teacher/student，必须携带未使用且在有效期内的邀请码；角色不匹配/已用/停用/过期返回 400，用户名重复 409；注册成功即消费邀请码（行锁防并发重复使用）
- [x] `app/api/admin.py` 管理员专属接口（仅 admin）：
  - `GET /admin/stats` 系统概览（用户数/教师/学生/管理员/班级/作业/提交数）
  - `POST /admin/invite-codes` 生成邀请码（随机 8 位，可设有效期）
  - `GET /admin/invite-codes` 邀请码列表（可按角色过滤）
  - `POST /admin/invite-codes/{id}/disable` 停用邀请码
  - `DELETE /admin/users/{id}` 删除无关联数据的用户；有提交/班级/邀请码关联返回 409 提示禁用；禁止删除自己

前端：
- [x] 公开注册页 `/register`（角色选择 + 邀请码 + 用户名/姓名/密码/确认密码），登录页加注册入口
- [x] 专属 `AdminLayout` + 管理员三页：系统概览仪表盘、用户管理（角色筛选/新建/编辑/启禁用/删除）、邀请码管理（生成/过滤/复制/停用）
- [x] admin 登录首页改为 `/admin/dashboard`；`/register` 纳入公开路由

验收结果：新增 `tests/test_register_admin.py` 15 个用例全绿（注册成功/角色/邀请码/过期/重复/并发消费/权限/删除），后端全量 `pytest` 64 个通过；前端 `npm run build` 通过；Alembic 实库迁移应用成功。

### 阶段 6：课后反馈 + 异常处理 + 部署 ✅（对应实施计划第 6 周）
后端：
- [x] `feedback_reports` 持久化：匿名结构化输入快照、AI 原文、教师终稿、状态、模型、耗时和 Token 用量
- [x] Feedback Engine：仅消费 Analytics 结构化结果，生成 300 字以内的单次作业反馈与学生周报
- [x] Celery `generate_feedback_report`：超时沿用 LLM 客户端配置，失败最多重试 2 次，耗尽后落库 `failed`
- [x] 教师生成、编辑、发布；学生只可查看已发布反馈；教师数据严格按自己班级隔离
- [x] 结构化 JSONL 日志：HTTP、LLM、OCR、批改任务、反馈任务的耗时/模型/Token/失败/重试元数据
- [x] `/api/ready` 数据库就绪检查；OCR 空结果与任务异常进入重试/失败状态

前端：
- [x] 教师课后反馈页：班级/学生/作业筛选，单次反馈与周报生成，编辑、发布、失败状态展示
- [x] 学生课后反馈页：仅展示教师已发布终稿

部署：
- [x] FastAPI、Celery Worker、PostgreSQL、Redis、Nginx 的生产 Docker Compose
- [x] Nginx HTTPS、SPA 回退和 API 反向代理；证书和 `.env` 均排除出镜像/Git
- [x] DeepSeek OpenAI 兼容配置，当前模型 `deepseek-v4-flash`

验收结果：阶段 6 专项测试 4 个通过；完整后端测试 49 个、前端生产构建、Alembic 实库迁移、`/api/ready` 和 DeepSeek 真实 Feedback Engine 调用均通过。生产 Compose 配置校验通过；本机 Docker Engine 未启动，因此容器镜像构建与 HTTPS 实机启动待部署环境验证。

### 阶段 5：学情分析 ✅（对应实施计划第 5 周）
后端：
- [x] 新表 `student_knowledge_stats`（掌握度聚合表，(学生,知识点) 唯一；Alembic 迁移 `8cede53c312e`）
- [x] `app/analytics/` 聚合服务：`recompute_student_stats` 按原始轨迹重算；`mastery_score = correct/(correct+wrong)`；趋势按前后半段正确率切分（up/down/stable/new）
- [x] 教师确认批改（单题确认 / confirm-all）后自动增量重算该学生受影响知识点的掌握度
- [x] 读接口兜底：学生有轨迹无聚合行时自动全量重算；`POST /students/{id}/knowledge-stats/recompute` 教师可手动重算
- [x] API：
  - `GET /students/{id}/knowledge-stats` 学生知识点掌握度
  - `GET /students/{id}/weak-points?top_n&min_records` 薄弱知识点 TOP N
  - `GET /students/{id}/learning-trend` 成绩趋势（按已确认作业得分率）
  - `GET /students/{id}/repeated-errors` 重复错误类型聚合
  - `GET /assignments/{id}/analysis` 单次作业分析（平均分/分布/各题正确率/薄弱点/共性错误）
  - `GET /classes/{id}/analytics` 班级学情（平均分/成绩分布/知识点正确率/薄弱排行/共性错误/未提交学生）
- [x] 权限：学生仅能看自己；教师查询学生学情必须指定自己班级，所有统计按作业班级隔离；admin 全量

前端（ECharts）：
- [x] 通用图表组件 `components/EChart.vue`
- [x] 教师端学生学情页：班级+学生筛选、成绩趋势折线、知识点掌握度条形图、薄弱点 TOP5、重复错误
- [x] 教师端班级学情页：平均分/提交数、成绩分布、知识点整体正确率、班级薄弱排行、共性错误、未提交学生
- [x] 教师端单次作业分析页：作业列表"分析"入口、平均分/及格率/题目数卡片、成绩分布、各题正确率、本作业薄弱点、错误类型
- [x] 学生端我的学情页：个人趋势 + 掌握度 + 薄弱点

验收结果：`pytest` 45 个用例全绿（`test_analytics.py` 10 个，覆盖跨班级隔离、未提交学生、趋势、正确率和重复错误），前端 `npm run build` 通过；本机端到端冒烟通过：学生提交 → AI 批改 → 教师 confirm-all → knowledge-stats/weak-points/learning-trend/repeated-errors/assignment-analysis/class-analytics 均返回正确数据。

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
# 2. 后端（backend 目录，开发端口 8002）
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload
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

### 安全基线 ✅（阶段 4 完成后加固，前后端全链路联调通过）
后端：
- [x] 学生看不到标准答案：`GET /assignments`、`GET /assignments/{id}`、`GET /assignments/{id}/questions` 学生视角 `standard_answer=null`，且学生不能查看未发布作业
- [x] 匿名打不开题库：`GET /questions`、`GET /questions/{id}` 需 admin/teacher（401）；`get_question` 修复 ORM 序列化 500
- [x] 作业文件鉴权：`/api/storage/files/...` 移入 submissions 路由，仅提交者/任课教师/admin 可读（学生 403 隔离、匿名 401）
- [x] 教师越权封堵：教师查看他人作业详情/题目、管理教师/管理员账号均 403（users 接口教师仅可管理学生）
- [x] 复核后不能覆盖提交：已 teacher_reviewed/completed 或有已确认批改 → 提交 409
- [x] 截止后不能提交：`due_at` 过期 → 409
- [x] 上传加固：10MB 大小限制（413）、PDF/图片魔数校验（400）、本地存储路径穿越修复
- [x] Broker 故障降级：异步任务投递失败时提交保留并标记 failed，不再 500

前端：
- [x] 文件下载改为带 Authorization 的 blob 下载（`openSubmissionFile`），学生/教师端同步改造

联调验证：教师建作业 → 学生提交 → AI 批改 → 教师复核全链路通过；5 项安全检查实测全部符合预期（学生不见答案、匿名 401、教师 403、复核后 409、截止后 409）。

## 后续计划

- [ ] 使用 1 名教师、10~20 名学生、3~5 次真实作业开展 MVP 试用，收集教师修改率与学生可理解度

## 已知技术选型（与用户确认）
- 异步任务：Celery + Redis
- LLM：OpenAI 兼容接口（开发期 `LLM_PROVIDER=mock`）
- OCR：先 Mock，后接真实第三方
