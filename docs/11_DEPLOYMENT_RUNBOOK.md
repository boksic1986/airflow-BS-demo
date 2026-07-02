# 11 部署 Runbook

## 1. 前置检查

```bash
whoami
pwd
uname -a
df -h
free -h
docker --version
docker compose version
python --version
node --version || true
which qsub || true
which qstat || true
```

把非敏感结果写入 `SERVER_INFO.md`。

## 2. 初始化目录

```bash
mkdir -p <PROJECT_ROOT>
mkdir -p <SHARED_ROOT>/uploads
mkdir -p <SHARED_ROOT>/runs
mkdir -p <SHARED_ROOT>/reports
mkdir -p <SHARED_ROOT>/logs
```

## 3. 配置环境变量

从 `.env.example` 创建 `.env`：

```bash
cp .env.example .env
```

不得提交 `.env`。

## 4. 检查 compose

```bash
docker compose config
```

## 5. 启动服务

```bash
docker compose up -d
```

检查：

```bash
docker compose ps
docker compose logs --tail=100 airflow-scheduler
docker compose logs --tail=100 backend
```

## 6. 初始化数据库

示例：

```bash
docker compose exec backend alembic upgrade head
```

实际命令以 backend 实现为准。

## 7. Airflow 初始化

示例：

```bash
docker compose exec airflow-api-server airflow users list
```

如需创建用户，必须使用 `.env` 中变量，不在文档写密码。

## 8. 健康检查

```bash
curl http://<SERVER_HOST>:8000/api/health
curl http://<SERVER_HOST>:8080/health
```

## 9. Smoke test

建议命令：

```bash
python scripts/submit_mock_run.py --pipeline wes_qsub --sample-sheet examples/samples/wes_mock.tsv
```

或通过前端提交 mock sample sheet。

## 10. 查看日志

```bash
docker compose logs --tail=200 backend
docker compose logs --tail=200 airflow-scheduler
docker compose logs --tail=200 airflow-worker
```

Run 日志：

```bash
find <SHARED_ROOT>/runs/<analysis_id>/logs -type f | sort
```

## 11. 停止服务

安全停止：

```bash
docker compose down
```

禁止默认使用：

```bash
docker compose down -v
```

除非明确需要删除 volume 且已备份。

## 12. 回滚

```bash
git status
git log --oneline -5
# 使用 git revert 优先于 reset --hard
```

服务回滚：

```bash
docker compose down
git checkout <known-good-commit>
docker compose up -d --build
```

DB migration 回滚必须先确认不会丢数据。

## 13. 常见故障

### Airflow scheduler 起不来

检查：

- Postgres 是否 healthy。
- AIRFLOW_UID 是否正确。
- dags 是否 import error。

### DAG 不出现

检查：

```bash
docker compose exec airflow-scheduler airflow dags list-import-errors
```

### Backend 无法触发 Airflow

检查：

- `AIRFLOW_BASE_URL` 是否是容器内可访问地址。
- Airflow API auth 配置。
- backend logs。

### qsub 提交失败

检查：

- `which qsub`。
- queue 名称。
- qsub 参数是否符合服务器调度系统。
- demo 用户是否有提交权限。

### 前端无法访问 backend

检查：

- 前端构建时 API base URL。
- CORS 配置。
- host port 映射。
