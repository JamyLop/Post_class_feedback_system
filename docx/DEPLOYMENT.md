# 生产部署

阶段 6 使用 `docker-compose.prod.yml` 部署 PostgreSQL、Redis、FastAPI、Celery Worker 和 Nginx。

## 准备

1. 从 `.env.example` 创建服务器本地 `.env`，设置强随机 `SECRET_KEY`、数据库密码和 DeepSeek 的 `LLM_API_KEY`。
2. 使用 `LLM_PROVIDER=openai_compat`、`LLM_BASE_URL=https://api.deepseek.com`、`LLM_MODEL=deepseek-v4-flash`。
3. 将证书保存为 `deploy/certs/fullchain.pem` 和 `deploy/certs/privkey.pem`。证书目录已忽略，禁止提交私钥。
4. 部署前执行 PostgreSQL 完整备份，并验证备份可读取。

## 启动与验证

```powershell
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
curl.exe -fsS https://你的域名/api/ready
```

随后用教师和学生账号完成一次真实闭环：提交、批改、教师确认、生成反馈、编辑发布、学生查看。`/api/health` 只表示进程存活，数据库就绪以 `/api/ready` 为准。

日志写入 `logs/app.jsonl` 对应的容器卷，只记录调用元数据，不记录密钥或原始学生答案。
