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

## 2. fengxian 代码镜像

服务器目录只作为 GitHub 镜像，不直接开发或提交。

首次同步：

```bash
test -d /home/jiucheng/project/airflow-demo
find /home/jiucheng/project/airflow-demo -mindepth 1 -maxdepth 1 | head
git clone git@github.com:boksic1986/airflow-BS-demo.git /home/jiucheng/project/airflow-demo
```

如果目录非空且不是 Git 仓库，先停止并确认/备份，不覆盖。

后续更新：

```bash
cd /home/jiucheng/project/airflow-demo
git pull --ff-only
```

## 3. Docker Compose v2 用户级准入

在 `fengxian` 只安装用户级 Docker CLI plugin，不升级系统 Docker，不安装 legacy `docker-compose` v1。

优先使用国内 Docker CE 镜像下载 `docker-compose-plugin` deb 包，并只解包其中的 CLI plugin 二进制到用户目录。`fengxian` 是 Ubuntu 18.04，但 bionic 镜像只到 Compose 2.18.1；为了固定 `v2.24.7`，使用 focal 包解包二进制，不做系统级 dpkg/apt 安装。

```bash
mkdir -p "$HOME/.docker/cli-plugins"
tmpdir="$(mktemp -d)"
curl -fL \
  "https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/ubuntu/dists/focal/pool/stable/amd64/docker-compose-plugin_2.24.7-1~ubuntu.20.04~focal_amd64.deb" \
  -o "$tmpdir/docker-compose-plugin.deb"
dpkg-deb -x "$tmpdir/docker-compose-plugin.deb" "$tmpdir/extract"
install -m 0755 \
  "$tmpdir/extract/usr/libexec/docker/cli-plugins/docker-compose" \
  "$HOME/.docker/cli-plugins/docker-compose"
rm -rf "$tmpdir"
docker compose version
```

验收输出应为：

```text
Docker Compose version v2.24.7
```

已探测但不作为优先路线：

- GitHub Release 直连容易受网络限制。
- 清华/中科大/交大 GitHub-release 路径对 `docker/compose/v2.24.7/docker-compose-linux-x86_64` 返回 404 或错误重定向。
- 清华、交大、阿里云 Docker CE `focal`/`jammy` 镜像可提供 `docker-compose-plugin_2.24.7`。

## 4. 初始化目录

```bash
mkdir -p <PROJECT_ROOT>
mkdir -p <SHARED_ROOT>/uploads
mkdir -p <SHARED_ROOT>/runs
mkdir -p <SHARED_ROOT>/reports
mkdir -p <SHARED_ROOT>/logs
```

## 5. 配置环境变量

从 `.env.example` 创建 `.env`：

```bash
cp .env.example .env
```

不得提交 `.env`。

## 6. 检查 compose

```bash
docker compose config
```

## 7. 最小启动验收

第一轮只启动基础容器和 backend health，不启动 Airflow、frontend 功能页或 PGT-A。

```bash
docker compose up -d postgres redis mailhog backend
curl http://127.0.0.1:8000/api/health
docker compose down
```

期望 health：

```json
{"status":"ok"}
```

禁止使用 `docker compose down -v` 作为默认停止方式。

## 8. 启动完整服务

```bash
docker compose up -d
```

检查：

```bash
docker compose ps
docker compose logs --tail=100 airflow-scheduler
docker compose logs --tail=100 backend
```

## 9. 初始化数据库

示例：

```bash
docker compose exec backend alembic upgrade head
```

实际命令以 backend 实现为准。

## 10. Airflow 初始化

示例：

```bash
docker compose exec airflow-api-server airflow users list
```

如需创建用户，必须使用 `.env` 中变量，不在文档写密码。

## 11. 健康检查

```bash
curl http://<SERVER_HOST>:8000/api/health
curl http://<SERVER_HOST>:8080/health
```

## 12. Smoke test

建议命令：

```bash
python scripts/submit_mock_run.py --pipeline wes_qsub --sample-sheet examples/samples/wes_mock.tsv
```

或通过前端提交 mock sample sheet。

## 13. 查看日志

```bash
docker compose logs --tail=200 backend
docker compose logs --tail=200 airflow-scheduler
docker compose logs --tail=200 airflow-worker
```

Run 日志：

```bash
find <SHARED_ROOT>/runs/<analysis_id>/logs -type f | sort
```

## 14. 停止服务

安全停止：

```bash
docker compose down
```

禁止默认使用：

```bash
docker compose down -v
```

除非明确需要删除 volume 且已备份。

## 15. 回滚

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

## 16. 常见故障

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
