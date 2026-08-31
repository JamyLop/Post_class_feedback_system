# 小程序端实施计划

> 版本：v0.2 / 2026-08-31 / 状态：评审修订版（待确认后实施）
> 关联文档：`PRODUCT.md` `PROGRESS.md` `README.md` `frontend/src/router/index.js` `backend/app/api/student_cases.py`

---

## 1. 背景与目标

### 1.1 现状
- Web 端已具备高三一生一案核心闭环：`诊断证据 → 班主任确认维护总案/学科方案 → 日周月任务 → 执行记录 → 校级督查 → 阶段复盘 → 家长只读查看`（`README.md:7`）。
- 后端 `backend/app/api/student_cases.py` 已提供总案、学科方案、任务、打卡、复盘、版本、进度、导出等接口，权限按 `admin/deyu_director/teacher/parent` 严格分离（`PRODUCT.md:9`）。
- 前端 `frontend` 为 Vue3 + Vite + Element Plus + Pinia（`README.md:20`），已验证家长只读、班主任全量管理的角色模型。
- 缺口：家长是最终查看对象（`PROGRESS.md:13`），但当前家长仅有 Web 只读入口，无移动端；学生、班主任也缺乏移动端轻量入口。

### 1.2 小程序目标
1. **家长移动端只读查看**——已发布版本的总案、学科方案、任务执行、督查复盘，清晰可读。
2. **学生移动端只读+作业闭环**——查看作业/分数/反馈；在后端补齐“仅本人、仅可见状态”的自查权限后，查看自己的一生一案（不参与录入）。
3. **教师移动端轻量办公**——待办提醒、打卡补录、督查提交，不做复杂编辑。
4. 复用现有后端鉴权与业务接口，不另起数据孤岛；与 Web 端保持一致的 `CASE_STATUSES` 状态机。

### 1.3 非目标（本期不做）
- DOCX 导出、批量导入/导出、班级管理、AI 草稿生成，保留在 Web 端。
- 小程序内直接编辑总案正文、学科方案五段式长文本（复杂表单留 Web）。

---

## 2. 用户与场景

| 角色 | 常量 | 小程序核心场景 | 权限来源 |
|---|---|---|---|
| 家长 | `parent` (`backend/app/models/user.py:13`) | 查看子女列表 → 查看已确认总案详情 → 查看学科方案/任务时间轴/复盘记录 → 接收状态变更通知 | `PARENT_VISIBLE_STATUSES` + `StudentGuardian` 关联 (`backend/app/services/student_case_service.py`) |
| 学生 | `student` | 查看作业/提交结果/周考月报/学情分析 → 只读查看自己的一生一案 | 作业接口可复用；一生一案当前会被 `require_case_access` 拒绝，P1 新增“仅 `case.student_id == current_user.id`”的自查权限 |
| 班主任 | `teacher` + `is_head_teacher` | 查看待办/班级进展 → 快速打卡 → 提交班主任层级复盘 | `backend/app/api/student_cases.py:72` `_head_teacher` |
| 德育主任 | `deyu_director` | 查看待审列表 → 提交德育督查 | `backend/app/api/student_cases.py:627` `review_level=deyu` 仅德育主任 |
| 校长 | `admin` | 查看全校进展 → 提交校级督查 | `backend/app/api/student_cases.py:625` `school/principal` 仅 admin |

> 设计原则沿用 `PRODUCT.md:26`：先呈现状态与下一步行动，再展开完整材料；角色操作明确分离。

---

## 3. 技术选型

### 3.1 推荐方案：uni-app + Vue3 + Vite + Pinia

| 维度 | 选择 | 理由 |
|---|---|---|
| 框架 | uni-app (Vue3) | 团队已是 Vue3+Pinia+Axios（`frontend/package.json:15`），可复用 `frontend/src/api/*`、`stores/auth.js` 思想与代码 |
| UI | `wd-ui` / `uni-ui` + 自写原子组件 | 禁用 Element Plus（体积大、不适配小程序）；风格克制、信息密度高，符合 `PRODUCT.md:17` 品牌气质 |
| 网络 | 自封装 `request`（拦截器复刻 `frontend/src/api/index.js:10`） | 统一注入 `Authorization: Bearer JWT`，401 自动回登录页 |
| 图表 | `echarts` 小程序版 / `ucharts` | Web 端已用 `echarts@6.1.0`，移动端按需轻量化 |
| 构建 | Vite + `pages.json` 分包 | 主包 < 2MB，分包按角色拆分 |

**备选**：Taro Vue3（同等可用），不推荐原生小程序（与现有 Vue 体系完全割裂，维护成本高）。

### 3.2 与 Web 的代码复用策略
- `frontend/src/api/studentCases.js` 等接口定义直接移植为 `miniprogram/src/api/studentCases.js`，仅替换 `http` 适配层（`wx.request`）。
- 后端是权限与状态机的唯一权威；小程序只保留展示映射，不依赖客户端常量实施权限。接口类型优先由 OpenAPI 生成，避免手工复制后漂移。
- 不强行 mono-repo 共享组件，样式与交互按移动端重写。

---

## 4. 总体架构

```
┌─────────────┐      wx.login(code)       ┌──────────────┐      jscode2session      ┌──────────┐
│ 微信客户端   │ ───────────────────────→ │  miniprogram │ ───────────────────────→ │ 微信服务 │
└─────────────┘                          │  (uni-app)   │ ←────────────────────── │          │
       │  wx.request + JWT                └──────┬───────┘     openid/unionid       └──────────┘
       │  Authorization: Bearer <token>          │
       │                                         ▼
       │                                 ┌──────────────┐
       └────────────────────────────────→│   backend    │
                                         │ FastAPI      │  复用 /api/auth/*, /api/student-cases/*,
                                         │ PostgreSQL   │       /api/assignments/*, /api/feedback/* 等
                                         └──────────────┘
```

- 登录后全链路继续使用 JWT（`backend/app/auth/router.py:31` `create_access_token`），小程序与 Web 共享同一套 `get_current_user` 依赖。
- 鉴权失败 401 统一回登录页（复刻 `frontend/src/api/index.js:23` 逻辑）。

---

## 5. 后端改造（估 4-6 个工作日）

### 5.1 数据模型
首版建议新增独立身份绑定表 `user_external_identities`，避免把微信身份直接耦合到 `users`：
- `id` / `user_id` / `provider`（固定 `wechat_miniprogram`）/ `app_id`
- `subject_id`（微信 `openid`）/ `unionid NULL` / `bound_at` / `last_login_at`
- 唯一约束：`(provider, app_id, subject_id)`；同一系统用户是否允许绑定多个微信身份由业务约束决定

若确认系统长期只有一个小程序，也可简化为在 `users` 表新增 `wx_openid/wx_unionid/wx_bound_at`，但迁移前必须记录这一约束。

手机号如需作为登录身份，应放在用户身份域并完成唯一性与验证流程，不与 `CaseStudentProfile.parent_phone`（学生档案联系方式）混用。

`StudentGuardian` 已可支撑一对多子女绑定，无需改表。

### 5.2 新增接口

| 方法 | 路径 | 说明 | 鉴权 |
|---|---|---|---|
| `POST` | `/api/auth/wx-login` | 入参 `code`，服务端调微信 `jscode2session`；已绑定则签发 JWT，未绑定只返回一次性 `bind_ticket`（有效期 5 分钟），不信任客户端提交的 `openid` | 无 |
| `POST` | `/api/auth/wx-bind` | 入参 `bind_ticket` + “现有账号密码”或“邀请码注册资料”；事务内校验一次性票据、账号状态、角色和唯一绑定约束，成功后签发 JWT | 无（依赖一次性票据） |
| `POST` | `/api/auth/wx-unbind` | 解绑（需已登录） | JWT |
| `GET` | `/api/auth/me` | 已有（`backend/app/auth/router.py:35`），小程序启动时校验会话 | JWT |
| `GET` | `/api/auth/me/children` | 返回当前家长真实绑定的子女关系及各子女最新可见总案摘要；没有已发布总案的子女也必须返回 | `parent` JWT |

### 5.3 配置
- `.env` 新增 `WX_APPID` / `WX_SECRET`（不入库，不提交）。
- 微信 `jscode2session` 失败需有 mock 开关（开发期同 `README.md:23` 的 OpenAI/OCR mock 思路）。Mock 仅允许测试环境显式开启；生产缺少配置或请求失败时必须关闭登录并记录脱敏错误，禁止自动回退 Mock。

### 5.4 权限与脱敏
- 复用 `require_case_access` / `require_case_manager` 的服务端权限边界，但新增小程序响应 DTO，不能把 `_detail` 原样返回给所有角色。
- 家长端查询强制 `status IN PARENT_VISIBLE_STATUSES`，不可绕过。
- 学生端 P1 新增 `STUDENT_VISIBLE_STATUSES`，并强制 `case.student_id == current_user.id`；未实现前不开放学生总案入口。
- 家长响应不得包含 `guardian_accounts`、其他监护人用户名/手机号和内部审核信息；学生响应默认不包含监护人联系方式与健康明细。
- 当前 `_mask_health_for_viewer` 只在 `health_visible=false` 时对非校长隐藏，实施前需由产品确认字段矩阵，并用后端测试固化，不能只在前端隐藏。
- `/wx-bind`、`/wx-unbind`、绑定冲突和失败尝试写入审计日志；日志不得记录 `code`、`session_key`、`WX_SECRET`、完整手机号或 JWT。

---

## 6. 小程序工程结构

```
miniprogram/
  src/
    pages/                 # 主包
      login/index.vue          # 微信一键登录 + 手机号/邀请码绑定
      index/index.vue          # 角色分发首页（复刻 frontend/src/router/roleHome.js）
      webview/index.vue        # 可选：内嵌 H5 兜底
    subParent/             # 分包 - 家长（主战场）
      children/index.vue       # 真实子女列表  ← GET /auth/me/children（含暂无可见总案的子女）
      caseDetail/index.vue     # 总案详情（总览/学科方案/任务/复盘 Tab，只读）← GET /student-cases/{id}
      taskDetail/index.vue     # 任务时间轴 ← tasks + task_checkins
      reviewDetail/index.vue   # 督查复盘详情
    subStudent/            # 分包 - 学生
      assignments/index.vue    # 作业列表  ← /api/assignments
      assignmentDetail/index.vue
      analytics/index.vue      # 学情/分数  ← /api/analytics, /api/weekly-scores
      myCase/index.vue         # 只读一生一案
    subTeacher/            # 分包 - 教师轻量
      todo/index.vue           # 待办/班级进展 ← GET /student-cases/progress
      checkin/index.vue        # 快速打卡  ← POST /student-cases/tasks/{id}/checkins
      reviewCreate/index.vue   # 提交督查  ← POST /{case_id}/reviews
    api/
      index.js                 # wx.request 封装 + 拦截器
      auth.js                  # wxLogin / wxBind / getMe
      studentCases.js          # 移植 frontend/src/api/studentCases.js
      assignments.js
    stores/
      auth.js                  # Pinia，存储 token/user/role
    components/
      CaseStatusTag.vue
      Timeline.vue
      EmptyState.vue
    static/
    App.vue
    pages.json                 # 分包路由 + tabBar
    manifest.json
  .env.example
  README.md
```

`pages.json` 分包示例：`subParent` / `subStudent` / `subTeacher` 独立分包，主包目标 < 1.5MB；CI/构建验收同时检查主包和单个分包均不超过 2MB。

---

## 7. 页面与交互要点

### 7.1 登录/绑定
- 优先 `wx.login` 静默登录 → 调 `/wx-login` → 已绑直接进首页。
- 未绑：引导选择“绑定已有账号”或“使用邀请码注册”，连同 `/wx-login` 返回的一次性 `bind_ticket` 提交 `/wx-bind`。
- 小程序新绑定链路不创建默认密码账号；存量默认密码账号只有在验证原密码并完成改密后才能绑定。

### 7.2 家长端（P0）
- **子女列表**：展示 `student_name/class_name/latest_case_status`；区分“尚未绑定子女”和“已绑定子女但暂无已发布总案”两种空状态。
- **总案详情**：顶部状态胶囊（`draft/pending_confirmation/executing/...`）+ 负责人 + 更新时间；Tab：总览（`overall_problem/admission_target/current_summary`）、学科方案（按 `subject` 分组，展示 `problem_location/cause_analysis/...`）、任务执行（`CaseTask` + `TaskCheckin` 时间轴）、督查复盘（`CaseReview` 列表）。
- 只读：所有编辑按钮、输入框不渲染；健康字段遵守 `_mask_health_for_viewer`。
- 分享：P0 不分享敏感学情摘要；后续如开放转发，仅携带详情响应体中的 `case_id/version` 作为定位信息，不把它们当访问凭证。落地页必须重新鉴权，并处理未登录、无监护关系和版本已更新。

### 7.3 学生端（P1）
- 作业列表/详情/提交结果复刻 `frontend/src/views/student/*` 轻量化。
- 分数/反馈图表简化为卡片+趋势线。
- 一生一案入口仅在后端学生自查权限、状态过滤和脱敏测试通过后展示。

### 7.4 教师端（P2）
- 待办页聚合 `GET /student-cases/progress` 的 `overdue_tasks/long_unreviewed`。
- 打卡页支持扫码选学生/任务，复用 `POST /student-cases/tasks/{id}/checkins` 的完成度驱动状态机（`backend/app/api/student_cases.py:605`）。
- 督查提交页按 `review_level` 自动限权。

### 7.5 通用
- 长文本保证全宽阅读，不截断（沿用 `PROGRESS.md:28` 已修复的策略）。
- 状态不单靠颜色区分，配文字与图标（`PRODUCT.md:36` WCAG AA）。
- 尊重 `prefers-reduced-motion` 的等价小程序动效降级。

### 7.6 角色字段矩阵（实施前锁定）

| 字段类别 | 家长 | 学生 | 班主任 | 学科教师 | 德育主任 | 校长 |
|---|---|---|---|---|---|---|
| 已发布总案/学科方案/任务/复盘 | 只读 | 仅本人、只读 | 管理本班 | 只读负责学科 | 只读+德育督查 | 只读+校级督查 |
| 监护人账号/手机号 | 不返回其他监护人信息 | 不返回 | 按业务需要 | 不返回 | 不返回 | 按管理需要 |
| 健康明细 | 待产品确认，默认最小披露 | 默认不返回 | 受 `health_visible` 控制 | 默认不返回 | 受控 | 可见 |
| 内部审计/绑定信息 | 不返回 | 不返回 | 不返回密钥类信息 | 不返回 | 按职责 | 按职责 |

最终权限由后端实施，客户端只负责隐藏无权限入口。

---

## 8. 接口复用清单

| 小程序调用 | 后端接口 | 备注 |
|---|---|---|
| `listStudentCases` | `GET /student-cases` | 家长自动加 `PARENT_VISIBLE_STATUSES` 过滤 |
| `getStudentCase` | `GET /student-cases/{id}` | 详情聚合（`_detail`） |
| `getMyChildren` | `GET /auth/me/children`（新增） | 真实子女关系列表，包含暂无可见总案的子女 |
| `getFamilyCases` | `GET /student-cases/children` | 家长当前可见的总案列表，不等同于完整子女列表 |
| `getCaseProgress` | `GET /student-cases/progress` | 教师待办 |
| `getCaseVersions` | `GET /student-cases/{id}/versions` | 可选，家长查看历史 |
| `checkinCaseTask` | `POST /student-cases/tasks/{id}/checkins` | 教师打卡 |
| `createCaseReview` | `POST /{case_id}/reviews` | 教师督查 |
| `listCaseCycles` | `GET /student-cases/cycles` | 筛选周期 |
| `login/getMe` | `POST /auth/login`, `GET /auth/me` | 兜底账号密码登录 |
| 新增 | `POST /auth/wx-login`, `POST /auth/wx-bind` | 小程序专属；使用一次性 `bind_ticket`，客户端不提交可信 `openid` |

作业、反馈、周考、月报等沿用 `frontend/src/api/assignments.js` 等对应后端模块。

---

## 9. 分期与里程碑

| 阶段 | 周期 | 交付物 | 验收标准 |
|---|---|---|---|
| **P0 MVP** | 2 周 | 工程初始化 + 安全 wx-login/bind + 真实子女列表 + 家长总案详情只读（含任务/复盘时间轴） | 隔离测试账号完成登录/绑定/解绑；多子女及“暂无可见总案”正确；家长仅见 `PARENT_VISIBLE_STATUSES`；越权 case_id 返回 403；监护人账号、手机号和健康字段按矩阵脱敏；Web 与小程序构建、后端全量测试通过 |
| **P1** | 1.5 周 | 学生作业/分数/反馈只读 + 学生本人总案自查权限 + 微信订阅消息 | 学生只能查看本人及允许状态的总案；用户主动授权且模板可用时状态流转消息成功进入发送队列并可追踪结果 |
| **P2** | 1.5 周 | 教师待办/快速打卡/移动督查提交 + 分享海报 | 班主任可在手机完成一次打卡与督查提交，审计日志 `case_audit_logs` 可查 |
| **P3** | 1 周 | H5 兜底、按班级分享、生产部署与监控 | `docker-compose.prod.yml` 新增 H5 静态服务；线上 5 名试点家长可用 |

> 人力假设：1 名全栈。P0 完成后即邀请 2-3 名家长内测，再进入 P1/P2。

---

## 10. 测试与验收

- 后端：新增 `backend/tests/test_wx_auth.py` 与角色字段脱敏/学生自查测试；覆盖伪造或过期 `bind_ticket`、重复消费、并发绑定、禁用账号、跨角色冲突、越权 case_id；从 `backend` 目录执行全量 `pytest -q` 串行通过。
- Web：执行 `npm --prefix frontend run build`，确认既有 Web 端不回归。
- 小程序：执行 `npm --prefix miniprogram run build:mp-weixin`，检查主包/单分包体积；微信开发者工具真机调试 + 体验版分发。
- 真机覆盖：未绑定、绑定已有账号、邀请码注册、重复绑定、解绑、401 过期回登、多子女、无已发布总案、健康信息及监护人信息脱敏。
- 人工核对：首批 5 名学生的学科方案字段与 Web 端一致（`PROGRESS.md:90` 仍需人工抽检的延续）。

---

## 11. 风险与待决策

| 风险/问题 | 影响 | 建议 |
|---|---|---|
| 一个微信绑多子女 | 家长常见 | 支持一对多，`StudentGuardian` 已支持 |
| 邀请码 vs 短信验证码 | 决定绑定链路 | 建议首版沿用邀请码（复用现有 `InviteCode`），二期再接短信 |
| 伪造 `openid` 或重复使用绑定凭据 | 账号接管 | 客户端不直接提交可信 `openid`；使用短时、一次性、签名 `bind_ticket`，事务内消费并记录审计 |
| 微信身份被其他账号占用 | 绑定失败 | 对 `(provider, app_id, subject_id)` 建唯一约束，冲突返回 409；不能只依赖 `username` 唯一约束 |
| 订阅消息未经授权或额度耗尽 | 无法通知 | 在明确用户点击动作后申请订阅；记录授权结果，采用 outbox、幂等键、重试和失败可观测机制，不把“必达”作为无条件验收 |
| DOCX 导出在小程序不可用 | 家长期望 | 用分享海报/图片替代，明确提示“完整文档请在电脑端导出” |
| 微信审核（教育类目、隐私协议） | 上线阻塞 | 提前准备《隐私政策》《用户信息收集说明》，`health_visible` 相关字段需在隐私协议中声明 |
| 未提交改动较多（`PROGRESS.md:121`） | 合并冲突 | 小程序与后端改动分分支，Alembic 迁移单独提交 |

---

## 12. 后续工作

1. 确认 uni-app 选型、单一 UI 组件库、绑定方式（首版建议“已有账号密码 + 邀请码注册”）及角色字段矩阵。
2. 先编写微信认证与隐私权限测试，再新建分支 `feat/miniprogram-auth` 实现身份表、迁移和安全绑定接口；后端认证与权限改造按 4-6 个工作日估算。
3. 初始化 `miniprogram/` 工程并提交骨架（含 `pages.json` 分包、`api/index.js` 拦截器、`stores/auth.js`、构建体积检查）。
4. 按 P0 交付家长只读闭环，使用 2-3 名家长的隔离测试数据完成体验版内测；通过后再进入学生端和订阅消息。
