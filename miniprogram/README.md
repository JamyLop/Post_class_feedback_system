# 一生一案 小程序端

> 基于 uni-app + Vue3 + Vite + Pinia，复用 `frontend/src/api/*` 与后端 `/api/*` 权限模型。品牌与交互遵循 `PRODUCT.md` 与 `docs/miniprogram-plan.md`。

## 目录

```
miniprogram/
  src/
    pages/login, pages/index            # 主包
    subParent/children, caseDetail     # 家长分包 P0
    subStudent/assignments, myCase     # 学生分包 P1
    subTeacher/todo, checkin, reviewCreate # 教师轻量 P2
    api/ (auth, studentCases, assignments)
    stores/auth.js
    utils/request.js (wx.request + 401 拦截)
    components/CaseStatusTag, Timeline, EmptyState
    pages.json (分包) / manifest.json / App.vue / main.js
```

## 快速开始

```bash
cd miniprogram
npm install
# H5 预览
npm run dev
# 微信小程序构建（需 HBuilderX 或 uni CLI）
npm run build:mp-weixin
```

在微信开发者工具中导入 `dist/mp-weixin`（或 `dist/build/mp-weixin` 取决于 CLI 版本）。

环境变量：`VITE_API_BASE=http://localhost:8000/api`（见 `.env.example`）。

## 后端联调

- 微信登录：`POST /api/auth/wx-login` 需 `WX_APPID/WX_SECRET`，开发期支持 mock（`WX_MOCK=true` 时 `code` 以 `mock:` 前缀透传 openid）。
- 绑定：`POST /api/auth/wx-bind` 消费一次性 `bind_ticket`（5min）。
- 家长子女：`GET /api/auth/me/children` 返回真实 `StudentGuardian` 关系及最新可见档案摘要。

## 验收

- 主包/单分包 < 2MB
- 家长仅见 `PARENT_VISIBLE_STATUSES`，越权 `case_id` 403
- 健康与监护人字段按矩阵脱敏
- 教师可在手机完成一次打卡与督查，审计可查
