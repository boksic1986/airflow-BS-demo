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

优先路线：在本地 Windows 通过 GitHub Release 下载官方 `docker-compose-linux-x86_64`，再用 `scp` 同步到 `fengxian`。如果本地 GitHub 下载需要代理，显式给 `curl.exe` 加 `--proxy socks5h://127.0.0.1:1080`；不要把代理配置写入仓库。

本地 PowerShell：

```powershell
$url = "https://github.com/docker/compose/releases/download/v2.24.7/docker-compose-linux-x86_64"
$local = "$env:TEMP\docker-compose-v2.24.7-linux-x86_64"
curl.exe -L --fail --retry 3 --proxy socks5h://127.0.0.1:1080 -o $local $url
scp $local fengxian:/tmp/docker-compose-v2.24.7-linux-x86_64
Remove-Item -LiteralPath $local -Force
```

远端 `fengxian`：

```bash
mkdir -p "$HOME/.docker/cli-plugins"
install -m 0755 \
  /tmp/docker-compose-v2.24.7-linux-x86_64 \
  "$HOME/.docker/cli-plugins/docker-compose"
rm -f /tmp/docker-compose-v2.24.7-linux-x86_64
docker compose version
```

备用路线：若本地无法访问 GitHub release asset，可使用国内 Docker CE 镜像下载 `docker-compose-plugin` deb 包，并只解包其中的 CLI plugin 二进制到用户目录。`fengxian` 是 Ubuntu 18.04，但 bionic 镜像只到 Compose 2.18.1；为了固定 `v2.24.7`，使用 focal 包解包二进制，不做系统级 dpkg/apt 安装。

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

- `fengxian` 直连 GitHub Release 容易受网络限制。
- 清华/中科大/交大 GitHub-release 路径对 `docker/compose/v2.24.7/docker-compose-linux-x86_64` 返回 404 或错误重定向。
- 清华、交大、阿里云 Docker CE `focal`/`jammy` 镜像可提供 `docker-compose-plugin_2.24.7`。

## 4. 初始化目录

```bash
mkdir -p <PROJECT_ROOT>
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

`fengxian` 当前端口约定：

```text
AIRFLOW_PORT=12958
FRONTEND_PORT=12959
BACKEND_PORT=8000
MAILHOG_WEB_PORT=8025
MAILHOG_SMTP_PORT=1025
```

Current frontend/backend browser access:

```text
FRONTEND_IMAGE=airflow-demo/frontend:0.1.0
BACKEND_CORS_ORIGINS=*
```

`frontend` now builds this repository's React app and serves it through Docker nginx. The browser API base defaults to `http://<current-host>:8000/api`; override with `window.__AIRFLOW_DEMO_CONFIG__.apiBaseUrl` or `VITE_API_BASE_URL` only when a reverse proxy is added.

Airflow admin 密码只写入未跟踪的 `.env`：

```text
AIRFLOW_ADMIN_USERNAME=admin
AIRFLOW_ADMIN_PASSWORD=<SECRET_FROM_ENV>
AIRFLOW_ADMIN_EMAIL=airflow-demo@example.com
```

Postgres 和 Redis 只在 Docker 网络内使用 `5432` / `6379`，不发布宿主机端口。

PGT-A v1 样本发现只允许扫描白名单路径。`fengxian` 默认：

```text
PGTA_DATA_ROOT=/data/project/CNV/PGT-A
PGTA_CONTAINER_DATA_ROOT=/data/project/CNV/PGT-A
INPUT_SCAN_ROOTS=/data/project/CNV/PGT-A/rawdata
PGTA_SNAKEMAKE9_BIN=/biosoftware/miniconda/envs/snakemake9_env/bin/snakemake
AIRFLOW_DAGS_ROOT=/opt/airflow/dags
```

backend 只读挂载 PGT-A 数据根目录，不上传或复制 5-6G FASTQ。

## 6. 检查 compose

```bash
docker compose config
docker compose config --images
```

项目自有镜像必须显式带 tag，不能依赖隐式 `latest`。当前项目镜像名应为：

```text
airflow-demo/backend:0.1.0
airflow-demo/frontend:0.1.0
```

当前对外端口应渲染为：

```text
airflow-api-server: 12958 -> 8080
frontend: 12959 -> 80
backend: 8000 -> 8000
mailhog: 1025 -> 1025, 8025 -> 8025
```

backend 镜像构建时先使用仓库内 `backend/pip.conf` 的国内 PyPI 源配置，并在镜像内 `/opt/venv` 安装依赖。不要在 `fengxian` 宿主机系统 Python 上裸跑 `pip install`；若将来确实需要宿主机 Python 辅助脚本，必须先创建虚拟环境：

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
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

先初始化 Airflow metadata DB 和 admin 用户：

```bash
docker compose -f docker-compose.yaml up airflow-init
```

再启动基础服务：

```bash
docker compose -f docker-compose.yaml up -d postgres redis mailhog backend frontend airflow-api-server airflow-scheduler airflow-worker
```

检查：

```bash
docker compose ps
docker compose logs --tail=100 airflow-scheduler
docker compose logs --tail=100 backend
```

## 9. 初始化数据库

`biodemo` 业务库和 Airflow metadata DB 共用同一个 Postgres 容器，但使用不同 database/user。先启动 Postgres，再运行可重复的 one-shot 初始化服务：

```bash
docker compose -f docker-compose.yaml up -d postgres
docker compose -f docker-compose.yaml run --rm biodemo-db-init
```

然后用 backend 容器执行 Alembic migration：

```bash
docker compose -f docker-compose.yaml run --rm backend alembic upgrade head
```

如果 backend 服务已经在运行，使用 `exec`，避免 `run` 创建新 backend 容器时和宿主机 `8000` 端口映射冲突：

```bash
docker compose -f docker-compose.yaml exec -T backend alembic upgrade head
```

验证核心表：

```bash
docker compose -f docker-compose.yaml exec -T postgres \
  psql -U "$POSTGRES_USER" -d biodemo \
  -c '\dt'
```

`.env` 必须包含 `BIODEMO_DB`、`BIODEMO_USER`、`BIODEMO_PASSWORD`、`DATABASE_URL`。不要在命令输出或文档中打印真实密码。

## 10. Airflow 初始化

推荐使用 one-shot 初始化服务：

```bash
docker compose -f docker-compose.yaml up airflow-init
```

验证用户列表：

```bash
docker compose -f docker-compose.yaml exec airflow-api-server airflow users list
```

如需创建用户，必须使用 `.env` 中变量，不在文档写密码。

## 11. 健康检查

```bash
curl http://<SERVER_HOST>:8000/api/health
curl http://<SERVER_HOST>:8000/api/health/db
curl http://<SERVER_HOST>:8000/api/health/airflow
curl http://<SERVER_HOST>:12958/health
curl http://<SERVER_HOST>:12959/
curl http://<SERVER_HOST>:8025/
```

`fengxian` 宿主机已探测到系统 nginx，可作为后续反向代理候选，但当前 airflow-demo 未配置宿主机 nginx，也不应在没有单独计划时修改或 reload nginx。

```bash
/usr/sbin/nginx -v
```

已探测版本：

```text
nginx version: nginx/1.14.0 (Ubuntu)
```

### 11.1 PGT-A frontend run detail smoke

T050/T057 验收启动 `postgres redis backend frontend airflow-api-server airflow-scheduler airflow-worker`，不运行新的 PGT-A DAG。前端访问 `12959`，Airflow UI 仍访问 `12958`。

```bash
docker compose -f docker-compose.yaml config --quiet
docker compose -f docker-compose.yaml build backend frontend
docker build --target test -f frontend/Dockerfile frontend
docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q
docker compose -f docker-compose.yaml up -d postgres redis backend frontend airflow-api-server airflow-scheduler airflow-worker
curl -fsS http://127.0.0.1:12959/
curl -fsS 'http://127.0.0.1:8000/api/runs?pipeline=pgta&limit=5&offset=0'
curl -fsS http://127.0.0.1:8000/api/runs/PGTA_20260703_054712_501D8B/rules
curl -fsS 'http://127.0.0.1:8000/api/runs/PGTA_20260703_054712_501D8B/logs?stream=metadata&tail=2'
curl -fsS http://127.0.0.1:8000/api/runs/PGTA_20260703_054712_501D8B/artifacts
docker compose -f docker-compose.yaml down
```

已验证的 T050/T057 frontend smoke：

```text
frontend: http://127.0.0.1:12959/ returned React HTML
backend tests: 31 passed
frontend tests: 2 passed
PGTA_20260703_054712_501D8B rules: all=success, collect_run_metadata=success
Airflow health: metadatabase healthy, scheduler healthy
```

## 12. PGT-A server-path project smoke

T022/T024 验收只创建项目，不触发 Airflow DAG，不运行 Snakemake。先启动 Postgres/backend 并完成 biodemo 初始化和 Alembic migration。

扫描候选样本：

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/input/scan \
  -H 'Content-Type: application/json' \
  -d '{"pipeline":"pgta","rawdata_root":"/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28","max_samples":5}'
```

用扫描结果中的 1-2 个样本创建 run：

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/runs \
  -H 'Content-Type: application/json' \
  -d @/tmp/pgta-create-run.json
```

验收：

```text
analysis_run.status = created
analysis_run.dag_run_id is null
sample rows contain fq1/fq2 server paths
shared/runs/<analysis_id>/config/samples.selected.tsv exists
shared/runs/<analysis_id>/config/request.json exists
```

后续使用 submit action 触发 Airflow `bio_pgta`。

## 13. PGT-A submit smoke

T027/T035/T045 验收把已存在的 `created` PGT-A run 提交到 Airflow。当前 `bio_pgta` 支持 `metadata`、`dryrun_cnv` 和 `invalid_target` 三个受控 target；不跑真实 CNV、mapping、baseline QC 或 qsub。

先确认配置、测试和 DAG import：

```bash
docker compose -f docker-compose.yaml config --quiet
docker compose -f docker-compose.yaml build backend
docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q
docker compose -f docker-compose.yaml run --rm --no-deps --entrypoint env \
  airflow-scheduler PYTHONPYCACHEPREFIX=/tmp/pycache \
  python -m py_compile /opt/airflow/dags/bio_pgta.py /opt/airflow/dags/pgta_metadata_runner.py
docker compose -f docker-compose.yaml run --rm --no-deps --entrypoint python \
  airflow-scheduler -m unittest discover -s /opt/airflow/dags/tests -v
```

启动所需服务：

```bash
docker compose -f docker-compose.yaml up -d postgres redis
docker compose -f docker-compose.yaml run --rm biodemo-db-init
docker compose -f docker-compose.yaml up airflow-init
docker compose -f docker-compose.yaml run --rm backend alembic upgrade head
docker compose -f docker-compose.yaml up -d backend airflow-api-server airflow-scheduler airflow-worker
```

提交已有 `created` run：

```bash
analysis_id=<PGTA_CREATED_ANALYSIS_ID>
curl -fsS -X POST \
  "http://127.0.0.1:8000/api/runs/${analysis_id}/actions/submit"
```

验收 Airflow 和产物：

```bash
docker compose -f docker-compose.yaml exec -T airflow-scheduler \
  airflow dags list | grep bio_pgta
docker compose -f docker-compose.yaml exec -T airflow-scheduler \
  airflow dags list-runs -d bio_pgta --output json
find "shared/runs/${analysis_id}" -maxdepth 4 -type f | sort
head -5 "shared/runs/${analysis_id}/logs/run_metadata.tsv"
```

biodemo DB 中该 run 应更新为 `submitted` 且 `dag_run_id` 非空。Airflow success/failed 状态回写需要显式调用 `sync-airflow`。

已验证的 fengxian smoke：

```text
analysis_id: PGTA_20260702_171533_9A85B1
dag_run_id: manual__PGTA_20260702_171533_9A85B1
Airflow state: success
metadata artifact: shared/runs/PGTA_20260702_171533_9A85B1/logs/run_metadata.tsv
```

已知边界：`run_metadata.tsv` 中 `git_branch` / `git_commit` 字段在当前 Airflow 容器内显示 git permission error，但 metadata target 和 DAG run 已成功；后续如需干净 provenance，可单独修正 PGT-A metadata rule 的 git 调用环境。

### T045/T084 dry-run 与 failure smoke

`dryrun_cnv` run 通过前端 target 下拉或 API 创建，submit 后 `bio_pgta` 会生成 CNV 配置方向的 run-local `config.yaml`，并执行：

```bash
snakemake --snakefile /opt/pipelines/PGT_A/Snakefile \
  --cores 1 --printshellcmds --configfile <workdir>/config.yaml --dry-run
```

验收：

```bash
analysis_id=<PGTA_DRYRUN_ANALYSIS_ID>
curl -fsS -X POST "http://127.0.0.1:8000/api/runs/${analysis_id}/actions/sync-airflow"
curl -fsS "http://127.0.0.1:8000/api/runs/${analysis_id}/logs?stream=stdout&tail=50"
curl -fsS "http://127.0.0.1:8000/api/runs/${analysis_id}/artifacts"
```

期望 `status=success`，stdout/stderr 存在，`config/pgta_run_config.json` 可见，且没有真实 CNV 结果写回 PGT-A 流程目录。

`invalid_target` run 只用于 failure smoke。submit 后 Snakemake 会收到 `__airflow_demo_invalid_target__` 并自然失败。验收：

```bash
analysis_id=<PGTA_INVALID_ANALYSIS_ID>
curl -fsS -X POST "http://127.0.0.1:8000/api/runs/${analysis_id}/actions/sync-airflow"
curl -fsS "http://127.0.0.1:8000/api/runs/${analysis_id}/logs?stream=stderr&tail=100"
curl -fsS "http://127.0.0.1:8000/api/runs/${analysis_id}"
```

期望 `status=failed`，`error_summary` 非空，并包含 stderr 路径和最后 100 行错误内容。

## 14. PGT-A diagnostics smoke

T025/T062 验收不重新运行 PGT-A；复用已有 Airflow DAG run，同步状态并读取日志/产物。

同步成功 run：

```bash
analysis_id=PGTA_20260702_171533_9A85B1
curl -fsS -X POST \
  "http://127.0.0.1:8000/api/runs/${analysis_id}/actions/sync-airflow"
```

验收：

```text
status = success
error_summary = null
```

读取日志和 artifact：

```bash
curl -fsS \
  "http://127.0.0.1:8000/api/runs/${analysis_id}/logs?stream=metadata&tail=3"
curl -fsS \
  "http://127.0.0.1:8000/api/runs/${analysis_id}/logs?stream=stderr&tail=5"
curl -fsS \
  "http://127.0.0.1:8000/api/runs/${analysis_id}/artifacts"
```

同步历史失败 run：

```bash
analysis_id=PGTA_20260702_171200_A68C19
curl -fsS -X POST \
  "http://127.0.0.1:8000/api/runs/${analysis_id}/actions/sync-airflow"
```

验收：

```text
status = failed
error_summary is not null
```

缺失日志验收可以使用未提交 run：

```bash
curl -sS -o /tmp/missing-log.json -w '%{http_code}\n' \
  "http://127.0.0.1:8000/api/runs/PGTA_20260702_162531_74CE91/logs?stream=stdout"
cat /tmp/missing-log.json
```

期望 HTTP 404，错误码为 `LOG_NOT_FOUND`。

## 15. PGT-A Airflow-only Snakemake 9 logger/event smoke

该 smoke 验证 Airflow UI/CLI 直接触发 PGT-A metadata，并通过 Snakemake 9 logger plugin 在 Airflow task log/XCom 中展示状态。默认只写 JSONL；若 DAG conf 传入 `backend_event_url=http://backend:8000/api/events/snakemake`，rule/job 事件会同步 POST 到 FastAPI 并 upsert 到 biodemo `snakemake_rule_event`。

前置检查：

```bash
docker compose -f docker-compose.yaml config --quiet
docker compose -f docker-compose.yaml run --rm --no-deps --entrypoint /biosoftware/miniconda/envs/snakemake9_env/bin/python \
  airflow-scheduler /opt/airflow/dags/tests/test_snakemake_logger_plugin.py -v
PYTHONPATH=/home/jiucheng/project/airflow-demo/dags \
  /biosoftware/miniconda/envs/snakemake9_env/bin/snakemake --help | grep -- --logger-airflow-demo-analysis-id
```

Airflow import 检查：

```bash
docker compose -f docker-compose.yaml run --rm airflow-scheduler airflow dags list-import-errors
docker compose -f docker-compose.yaml run --rm airflow-scheduler airflow dags list | grep bio_pgta_airflow
```

手工创建 manifest 后触发：

```bash
analysis_id=PGTA_AIRFLOW_<YYYYMMDD_HHMMSS>
mkdir -p "shared/runs/${analysis_id}/config"
# 写入 shared/runs/${analysis_id}/config/samples.selected.tsv
chmod -R a+rwX "shared/runs/${analysis_id}"
docker compose -f docker-compose.yaml exec -T airflow-scheduler \
  airflow dags trigger \
  --run-id "manual__${analysis_id}" \
  --conf "$(cat /tmp/${analysis_id}.json)" \
  bio_pgta_airflow
```

在 stdin bash 脚本中连续执行 `docker compose exec` 时，给 exec 命令追加 `</dev/null`，避免 compose/容器进程吞掉后续脚本内容。

可选 backend event smoke：

```bash
analysis_id=<PGTA_CREATED_ANALYSIS_ID>
run_id="manual__${analysis_id}_events"
conf="$(ANALYSIS_ID="$analysis_id" python3 - <<'PY'
import json
import os

aid = os.environ["ANALYSIS_ID"]
print(json.dumps({
    "analysis_id": aid,
    "workdir": f"/data/airflow-demo/runs/{aid}",
    "sample_sheet_path": f"/data/airflow-demo/runs/{aid}/config/samples.selected.tsv",
    "target": "metadata",
    "email_to": None,
    "backend_event_url": "http://backend:8000/api/events/snakemake",
}, separators=(",", ":")))
PY
)"
docker compose -f docker-compose.yaml exec -T airflow-scheduler \
  airflow dags trigger bio_pgta_airflow --run-id "$run_id" --conf "$conf" </dev/null
```

验收：

```text
Airflow dag_run state = success
shared/runs/<analysis_id>/logs/run_metadata.tsv exists
shared/runs/<analysis_id>/logs/events/snakemake_events.jsonl exists and is non-empty
shared/runs/<analysis_id>/logs/events/snakemake_rule_summary.tsv exists and is non-empty
collect_snakemake_events task log includes event count and status counts
collect_snakemake_events XCom includes snakemake_event_summary
if backend_event_url configured: GET /api/runs/<analysis_id>/rules returns rule rows
```

已验证的 fengxian smoke：

```text
analysis_id: PGTA_AIRFLOW_20260703_074844
dag_run_id: manual__PGTA_AIRFLOW_20260703_074844
Airflow state: success
run_metadata.tsv: 11 lines
snakemake_events.jsonl: 22 lines
XCom status_counts: {'info': 15, 'progress': 2, 'running': 2, 'started': 1, 'success': 2}
```

已验证的 T026/T043 backend event smoke：

```text
analysis_id: PGTA_20260703_054712_501D8B
dag_run_id: manual__PGTA_20260703_054712_501D8B_events
Airflow state: success
run_metadata.tsv: 11 lines
snakemake_events.jsonl: 22 lines
snakemake_rule_summary.tsv: 29 lines
GET /api/runs/<analysis_id>/rules: all=success, collect_run_metadata=success
```

## 16. 查看日志

```bash
docker compose logs --tail=200 backend
docker compose logs --tail=200 airflow-scheduler
docker compose logs --tail=200 airflow-worker
```

Run 日志：

```bash
find <SHARED_ROOT>/runs/<analysis_id>/logs -type f | sort
```

## 17. 停止服务

安全停止：

```bash
docker compose down
```

禁止默认使用：

```bash
docker compose down -v
```

除非明确需要删除 volume 且已备份。

## 18. 回滚

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

## 19. 常见故障

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
