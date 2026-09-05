# 课后反馈系统 · 项目技术说明

> 面向开发者：本项目的架构设计、模块划分、数据模型、核心流程、异步任务、API 索引、权限与安全、开发测试与部署方式。
> 补充材料：业务方案见《课后反馈系统_具体实施计划.md》；进度与验收见 `PROGRESS.md`；部署实施见 `DEPLOYMENT.md`。

---

## 1. 系统概述

系统目标是打通「作业 → 提交 → 自动批改 → 教师复核 → 学情分析 → 课后反馈」的完整闭环，帮助教师把批改后的高频工作交给 AI，把精力留给复核与个性化反馈。

```
作业创建 → 学生提交 → OCR/结构化 → AI 批改 → 教师复核 → 学情更新 → 课后反馈
   ↑ 教师                                          ↓
   发布作业                                    学生查看反馈
```

开发期 AI 与 OCR 均使用 Mock 实现保证全链路可跑通，通过 Provider 抽象可平滑切换真实服务（DeepSeek OpenAI 兼容接口 / 第三方 OCR）。

## 2. 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 + Vite 8 + Element Plus + Pinia + Vue Router + Axios + ECharts |
| 后端 | Python 3.12 + FastAPI 0.115 + SQLAlchemy 2.0 + Alembic 1.14 + Celery 5.4 |
| 数据 | PostgreSQL 16 + Redis 7 |
| 存储 | 本地磁盘（默认）或 MinIO（可切换） |
| AI | OpenAI 兼容接口，DeepSeek（`LLM_PROVIDER=mock\)openai_compat`） |
| OCR | 第三方（开发期 Mock，接口预留给 baidu/aliyun/tencent） |
| 认证 | JWT + BCrypt，RBAC（admin / teacher / student） |

## 3. 整体架构

```
┌─────────────┐   HTTPS/404-SPA   ┌──────────────┐
│  浏览器 (Vue3)│ ───────────────► │   Nginx (web)  │
└─────────────┘                  ────────┬───────┘
                                         │ /api 反向代理
                              ┌──────────▼──────────┐
                              │  FastAPI (api)      │  ←─ Postgres  /api/ready 就绪检查
                              └──────┬──────────┬───┘
                                     │          │
                          ┌──────────▼─┐    ┌───▼──────────┐
                          │  PostgreSQL │    │  Redis       │   broker + result backend
                          └────────────┘    └───┬──────────┘
                                                │ 投递异步任务
                              ┌───────────▼───────────┐
                              │  Celery Worker        │  OCR → 批改 → 反馈
                              └───────────────────────┘
```

### 3.1 分层与模块（backend/app）

| 包 | 职责 |
| --- | --- |
| `api/` | HTTP 路由层（auth / users / classes / knowledge / questions / assignments / submissions / grading / analytics / feedback） |
| `auth/` | JWT 签发与校验，`get_current_user` / `require_roles` 依赖 |
| `core/` | 配置（pydantic-settings）、数据库 Session、Redis、JWT/哈希、结构化 JSONL 日志 |
| `models/` | SQLAlchemy ORM 模型（15 张表） |
| `schemas/` | Pydantic 请求/响应模型 |
| `grading/` | 批改引擎：`router` 按题型分发到 Rule / Hybrid / LLM 三套 Grader |
| `feedback/` | 反馈引擎：仅消费 Analytics 结构化结果生成 300 字反馈 |
| `analytics/` | 学情聚合：掌握度、趋势、薄弱点、重复错误、作业/班级分析 |
| `ai/` | LLM Provider 抽象（Mock / OpenAI 兼容） |
| `ocr/` | OCR Provider 抽象（Mock） |
| `storage/` | 文件存储抽象（local / minio） |
| `tasks/` | Celery 异步任务（OCR / 批改 / 反馈生成） |
| `seed.py` | 开发种子数据（账号 + 知识点树） |

### 3.2 前端（frontend/src）

- `api/`：按域拆分的 Axios 封装（auth / classes / assignments / questions / analytics / feedback / submissions）
- `stores/auth.js`：登录态与用户信息
- `router/index.js`：按角色守卫路由（teacher / student 两套布局）
- `views/teacher/`：班级学生、题库、作业、提交记录、复核中心、学情（学生/班级/作业分析）、课后反馈
- `views/student/`：我的作业、提交作答、提交结果（AI 批改）、我的学情、我的反馈
- `components/EChart.vue`：ECharts 通用图表封装

## 4. 数据模型（15 张表）

Alembic 迁移链：`f8adfaa7edf4`(init) → `86e937410e61`(批改) → `d363eb9469eb`(唯一约束) → `00e2fdc191e0`(学习轨迹) → `8cede53c312e`(掌握度聚合) → `4e4d9f8a2b6c`(反馈报告)

```
users ──< classes ──< class_students ──> users(student)
 │        │(teacher_id)
 │        └──< assignments ──< assignment_questions >── questions ──< question_knowledge_points >── knowledge_points(self parent)
 │                                                                        │
 │                                                                        ▼
 └──< submissions ──< submission_answers ──1:1── grading_results          student_knowledge_records (确认时写入)
        │student_id          │(question_id)        │                      │
        └──assignments       └──questions          ├── grading_prompt_versions(参考)
                                      │             │                      ▼
                                      │             ▼              student_knowledge_stats (聚合)
                                      └─ student_knowledge_records
feedback_reports (student_id, class_id, assignment_id?, report_type=assignment|weekly)
```

| 表 | 关键字段 / 说明 |
| --- | --- |
| `users` | username / password_hash / role（admin,teacher,student）/ status |
| `classes` | name / grade / teacher_id |
| `class_students` | 联合主键 (class_id, student_id) |
| `knowledge_points` | 树形（parent_id）；code 唯一 |
| `questions` | 题型 6 种：single_choice / multiple_choice / judge / fill / calculation / short_answer；grading_rule JSON |
| `question_knowledge_points` | (question_id, kp_id, weight) 多对多 |
| `assignments` | status=draft \| published \| closed \| archived；due_at 截止时间 |
| `assignment_questions` | (assignment_id, question_id, question_order) |
| `submissions` | content_type=text \| image \| pdf；status 状态机见 §6 |
| `submission_answers` | student_answer / ocr_text / is_correct / score / max_score |
| `grading_results` | 批改结果：grading_type(rule/ai/hybrid)、ai_score、confidence、error_type、teacher_score、teacher_comment、status |
| `grading_prompt_versions` | prompt 版本快照（审计用） |
| `student_knowledge_records` | 原始学习轨迹，教师确认批改时写入（先清后写按 学生/作业/题目） |
| `student_knowledge_stats` | (student_id, knowledge_point_id) 唯一；correct/wrong/mastery_score/trend |
| `feedback_reports` | input_snapshot、ai_content、final_content、模型/Token/耗时元数据、status、published_at |

## 5. 记忆与学情数据流

```
教师确认单题/一键确认
        │  写入
        ▼
student_knowledge_records  ──增量重算──►  student_knowledge_stats
        │                                     │ 读接口直接读聚合表（有轨迹无聚合时全量兜底重算）
        └──► 学情 API 按班级隔离输出           ▼
                                  反馈引擎快照（弱项 TOP3 + 重复错误）
```

- 掌握度公式：`mastery_score = correct / (correct + wrong)`
- 趋势：按作业正确率分前后两半比较，阈值 `0.1`，输出 `up / down / stable / new`
- 成绩分布桶：`ge90 / ge80 / ge70 / ge60 / lt60`

## 6. 提交与批改状态机

```
submission： submitted ──► processing ──► ai_graded ──► teacher_reviewed（全部确认后）
                    │           │              │            │
                    └───────────┴──── 失败: failed（可重触发）

grading： pending ──► ai_completed ──► confirmed
                │          └─────────► manual_review（confidence < 0.70 强制人工复核）
                └────────── 解析失败 → 降级 manual_review（error_type=parse_failed）
```

- 文本提交：`submitted → auto 投递批改任务`；图片/PDF：先 OCR（`ocr_submission`）完成后再触发批改
- 批改任务幂等：`SELECT ... FOR UPDATE` 行锁 + 状态判断，只批改一次
- 置信度策略：`≥0.85` 正常展示；`0.70~0.85` 提示重点检查；`<0.70` 状态置为 `manual_review`
- 防护：已 `teacher_reviewed` / 存在已确认批改 → 提交 `409`；`due_at` 过期 → `409`

## 7. 批改引擎按题型分发

| 题型 | 处理器 | 说明 |
| --- | --- | --- |
| single_choice / multiple_choice / judge | `RuleGrader` | 规则比对，不调用 LLM（成本控制） |
| fill | `HybridGrader` | 规则优先 + LLM 判定部分分 |
| calculation / short_answer | `LLMGrader` | LLM 结构化输出（JSON），Pydantic 校验 |

LLM 输出 JSON 解析失败自动重试 1 次，仍失败落 `manual_review`。
批改、反馈均记录：模型名、prompt/completion/total tokens、耗时、重试次数（结构化 JSONL 日志）。

## 8. 异步任务（Celery）

| 任务 | 触发时机 | 行为 |
| --- | --- | --- |
| `ocr_submission` | 图片/PDF 提交 | OCR 后触发批改；OCR 空结果进入重试/失败 |
| `grade_submission` | 文本提交 / OCR 完成 | 逐题分发批改；`max_retries=2` 耗尽落 `failed` |
| `generate_feedback_report` | 教师点生成 | 只用结构化快照生成反馈；失败重试 2 次后落 `failed` |

- Broker/Result 使用独立 Redis DB（0/1/2）
- `acks_late=True`，软限 270s / 硬限 300s
- Broker 故障降级：异步投递失败时提交保留并标记 `failed`，不 500

## 9. API 索引（统一前缀 `/api`）

后端启动后可在 `http://localhost:8000/docs` 查看 OpenAPI 全量接口与请求体示例。

### 认证与用户
| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | `/auth/login` | 公开 | 登录，返回 JWT |
| GET | `/auth/me` | 登录 | 当前用户 |
| POST/GET | `/users` | admin/teacher | 创建/列表（教师仅学生） |
| GET/PUT | `/users/{id}` | 登录/管理 | 详情、更新 |

### 班级与学生
| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| CRUD | `/classes` | teacher/admin | 班级管理 |
| POST/GET | `/classes/{id}/students` | teacher/admin | 添加/列表学生 |

### 知识点与题库
| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST/GET | `/knowledge-points` | teacher/admin | 知识点管理 |
| GET | `/knowledge-points/tree` | 登录 | 知识点树 |
| CRUD | `/questions` | teacher/admin | 试卷库（学生不可见） |

### 作业与提交
| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| CRUD | `/assignments` | teacher/admin | 作业管理 |
| POST | `/assignments/{id}/publish` | teacher | 发布；学生视角 `standard_answer=null` |
| POST/GET | `/assignments/{id}/questions` | teacher/student* | 加题/看题（学生不返回答案） |
| POST | `/assignments/{id}/submit` | 学生 | 文本/图片/PDF 提交 |
| GET | `/assignments/{id}/submissions` | teacher | 提交列表 |
| GET | `/submissions/{id}` | 本人/教师/admin | 提交详情 |
| GET | `/storage/files/{path}` | 本人/教师/admin | 文件下载（鉴权 + blob） |

### 批改与复核
| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | `/submissions/{id}/grade` | 教师 | 手动重批 |
| GET | `/submissions/{id}/grading` | 本人/教师 | 批改结果 |
| POST | `/gradings/{id}/retry` | 教师 | 单题重新 AI 批改 |
| GET | `/reviews` | 教师 | 复核队列（可按作业过滤，含进度） |
| PUT | `/gradings/{id}/confirm` | 教师 | 单题确认（可覆盖分数/评语） |
| POST | `/gradings/{id}/flag` | 教师 | 标记异常（必填原因） |
| POST | `/submissions/{id}/confirm-all` | 教师 | 一键确认整份 |

### 学情分析
| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/students/{id}/knowledge-stats` | 本人/教师 | 知识点掌握度 |
| GET | `/students/{id}/weak-points` | 本人/教师 | 薄弱点 TOP N |
| GET | `/students/{id}/learning-trend` | 本人/教师 | 成绩趋势 |
| GET | `/students/{id}/repeated-errors` | 本人/教师 | 重复错误 |
| POST | `/students/{id}/knowledge-stats/recompute` | 教师 | 手动重算 |
| GET | `/assignments/{id}/analysis` | 教师 | 单次作业分析 |
| GET | `/classes/{id}/analytics` | 教师 | 班级学情 |

### 课后反馈
| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | `/students/{id}/feedback/generate` | 教师 | 生成单次/周报反馈（异步） |
| GET | `/students/{id}/feedback` | 教师 | 学生反馈列表 |
| GET | `/students/{id}/feedback-report` | 学生 | 仅已发布反馈 |
| PUT | `/feedback/{report_id}` | 教师 | 编辑终稿 |
| POST | `/feedback/{report_id}/publish` | 教师 | 发布（学生可见） |

### 运维
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 进程存活 |
| GET | `/ready` | 数据库就绪检查（生产健康检查用） |

## 10. 权限与安全基线

- **RBAC**：`require_roles` 包裹路由；学生/教师/admin 三类角色
- **隐私**：学生视角所有接口不回传 `standard_answer`；学生不可见未发布作业；教师数据严格按自己班级隔离
- **越权封堵**：教师查看他人作业/管理教师账号 → 403；学生读他人文件 → 403；匿名 → 401
- **上传加固**：10MB 上限（413）、PDF/图片魔数校验（400）、本地存储路径穿越修复
- **提交合规**：复核完成后或超截止时间后不可再提交（409）
- **密钥管理**：`.env`、证书目录均 `gitignore` 且被 `.dockerignore` 排除；生产须强随机 `SECRET_KEY`
- **日志**：只记调用元数据（耗时/模型/Token/失败/重试），不记密钥与原始学生答案

## 11. 外部服务扩展点

| 抽象 | Mock 实现 | 生产实现 | 切换方式 |
| --- | --- | --- | --- |
| LLM | `MockLLMProvider`（启发式相似度评分） | `OpenAICompatProvider`（DeepSeek） | `LLM_PROVIDER` |
| OCR | `MockOcrProvider` | 待接入（baidu/aliyun/tencent） | `OCR_PROVIDER` |
| 存储 | `LocalStorage` | MinIO | `STORAGE_BACKEND` |

## 12. 配置项（`.env`）

| 变量 | 说明 |
| --- | --- |
| `APP_ENV` / `DEBUG` / `CORS_ORIGINS` | 环境与跨域 |
| `SECRET_KEY` / `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT 密钥与有效期 |
| `DATABASE_URL` | PostgreSQL 连接串 |
| `REDIS_URL` / `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis / Celery 三个 DB |
| `STORAGE_BACKEND` / `MAX_UPLOAD_BYTES` / `MINIO_*` | 文件存储 |
| `LLM_PROVIDER` / `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | AI 配置（默认 mock，生产 DeepSeek） |
| `OCR_PROVIDER` | mock |

## 13. 本地开发启动

前置：PostgreSQL（建库 `pfs`/用户 `pfs`）、Redis（`redis-server.exe --port 6379`）。

```bash
# 1. 后端
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed                                  # 种子账号与知识点树
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 2. Celery worker（另开终端）
cd backend
.venv/Scripts/python -m celery -A app.tasks.celery_app worker --loglevel=info -P solo

# 3. 前端（另开终端）
cd frontend
npm install
npm run dev                                         # http://localhost:5173
```

种子账号：`admin/admin123`、`teacher1/teacher123`、`student1..3/student123`。

## 14. 测试

```bash
cd backend
.venv/Scripts/python -m pytest                       # 全部用例
.venv/Scripts/python -m pytest tests/test_analytics.py -k "class"  # 按用例过滤
```

- 测试基座：`conftest.py` + `helpers.py`（内存/临时库、Mock provider）
- 覆盖：认证授权（`test_authz`）、提交流程与安全（`test_grading_pipeline`、`test_grading_api`、`test_submission_security`）、教师复核（`test_teacher_review`）、学情聚合（`test_analytics`）、反馈（`test_feedback`）

前端构建校验：

```bash
cd frontend && npm run build
```

## 15. 生产部署（概要）

详见 `DEPLOYMENT.md`。核心：

- `docker-compose.prod.yml` 编排 Postgres、Redis、FastAPI、Celery Worker、Nginx（HTTPS + SPA 回退）
- API 容器启动即 `alembic upgrade head`；健康检查用 `/api/ready`
- 证书放 `deploy/certs/`（已 gitignore）；镜像不携带 `.env` 与证书，运行时注入
- 部署前必须做 PostgreSQL 完整备份并验证可读