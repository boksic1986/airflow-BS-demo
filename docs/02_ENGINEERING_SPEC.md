# 02 工程规范

## 1. 仓库结构

```text
airflow-demo/
  docker-compose.yaml          # Docker Compose service skeleton
  .env.example                 # non-secret example environment
  dags/                       # Airflow DAGs
  backend/                    # FastAPI app
  frontend/                   # React app
  snakemake_runner/           # Dockerized Snakemake 9 + cluster-generic runner
  pipelines/
    common/                   # common wrappers/scripts
    wes/
      workflow/Snakefile
      config/
    nipt_qsub/
    nipt_docker/
  profiles/qsub/              # Snakemake cluster-generic profile
  shared/                     # local demo volume, usually gitignored
  docs/
  .agents/skills/
```

## 2. Python 规范

- Python 版本：由 `SERVER_INFO.md` 补齐，建议 3.11 或 3.12。
- 后端使用 FastAPI + SQLAlchemy 2.0 + Alembic。
- 当前最小后端入口：`backend/app/main.py`。
- 当前 API：`GET /api/health`、`GET /api/health/db`、`GET /api/health/airflow`、`POST /api/input/scan`、`POST /api/runs`、`GET /api/runs`、`GET /api/runs/{analysis_id}`、`GET /api/runs/{analysis_id}/samples`、logs/artifacts/rules/QC 查询和 submit/sync/reanalyze actions。
- T022/T024 阶段不上传 FASTQ，不上传 sample sheet；backend 只扫描白名单服务器路径、保存 R1/R2 路径并创建 selected manifest。
- backend Docker 镜像先复制 `backend/pip.conf` 配置国内 PyPI 源，再在 `/opt/venv` 创建虚拟环境并安装依赖。
- 远端宿主机如需临时 Python 工具，必须先建 venv 再安装依赖；不要在系统 Python 或用户全局 site-packages 裸装。
- 类型注解优先。
- 业务错误返回结构化 JSON。
- 日志使用标准 logging，禁止 print 密码/token。

## 2.1 Docker Compose 骨架

第一轮 Compose 骨架只保证基础运行面可渲染和最小服务可启动，不代表 Airflow DAG、biodemo migration 或 PGT-A runner 已经完成。

| Service | Host port | Container IP | Current role |
|---|---:|---|---|
| backend | 8000 | `172.30.10.20` | FastAPI health, biodemo DB, Airflow client, PGT-A server-path scan/run creation, WES mock lifecycle, diagnostics, rules, QC |
| frontend | 12959 | `172.30.10.30` | React PGT-A/WES mock run workspace served by Docker nginx |
| airflow-api-server | 12958 | `172.30.10.10` | Airflow web/api using project image `airflow-demo/airflow:0.1.0` |
| airflow-scheduler | n/a | `172.30.10.11` | Airflow scheduler using project image `airflow-demo/airflow:0.1.0` |
| airflow-worker | n/a | `172.30.10.12` | Airflow worker can run PGT-A direct tasks and WES mock qsub Snakemake |
| postgres | internal | `172.30.10.40` | Airflow metadata DB plus separate biodemo business DB |
| redis | internal | `172.30.10.50` | Airflow Celery broker |
| mailhog | 1025/8025 | `172.30.10.60` | demo SMTP/web UI |
| snakemake-runner | n/a | dynamic | run-only Snakemake 9.23.1 + cluster-generic executor for WES/NIPT mock profile smoke |

Fixed Docker network:

```text
subnet: 172.30.10.0/24
gateway: 172.30.10.1
```

Project-owned images must use explicit tags. Do not rely on implicit `latest`.

```text
backend image: airflow-demo/backend:0.1.0
frontend image: airflow-demo/frontend:0.1.0
airflow image: airflow-demo/airflow:0.1.0
snakemake runner image: airflow-demo/snakemake-runner:0.1.0
```

## 3. Frontend 规范

- React + TypeScript。
- API client 独立封装。
- 状态颜色统一：success/running/failed/warn/skipped。
- 日志查看组件必须支持大日志分页或 tail，不一次性加载巨大文件。
- 所有用户输入在前后端都要校验。

Current T050/T051/T054/T056/T057 frontend v1:

- `frontend/` is a Vite React + TypeScript app.
- Docker image tag is `airflow-demo/frontend:0.1.0`; nginx only serves the built SPA.
- The first screen is the PGT-A/WES mock run workspace, not a landing page.
- It consumes backend APIs for run list/detail, samples, logs, artifacts, rules, QC, explicit Airflow sync, PGT-A scan/create/submit, and WES mock create/submit/reanalysis.
- It does not implement login, independent log viewer page, MultiQC report viewer, or custom Airflow Web plugin yet.

## 4. Airflow 规范

- DAG 文件放 `dags/`。
- 每个 pipeline 一个主 DAG：`bio_wes_qsub`、`bio_nipt_qsub`、`bio_nipt_docker`、`bio_pgta`。
- Airflow services use the project image `airflow-demo/airflow:0.1.0`, based on `apache/airflow:2.9.3-python3.11`.
- The project Airflow image keeps Snakemake in `/opt/airflow/snakemake-venv` and puts it on `PATH`; use `/usr/local/bin/python` when a test specifically needs the Airflow system Python.
- On Linux hosts, `AIRFLOW_UID` must match the deploy user's `id -u` so Airflow workers can write bind-mounted `./shared`.
- PGT-A 另有 Airflow-only 验证 DAG `bio_pgta_airflow`，用于从 Airflow UI/CLI 直接读取 manifest 并验证 Snakemake 9 logger plugin，不替代后端触发的 `bio_pgta` 闭环。
- DAG task 数量保持项目级，不按 Snakemake rule 拆分。
- DAG run conf 必须包含：`analysis_id`、`pipeline`、`mode`、`sample_sheet_path`、`workdir`、`email_to`、`params`。
- 对 PGT-A，`sample_sheet_path` 指向 backend 生成的 `runs/<analysis_id>/config/samples.selected.tsv`，不是上传文件。
- DAG task 日志中不得打印敏感信息。

## 5. Snakemake 规范

- Snakefile 中所有 rule 必须有明确 input/output/log。
- 每个 rule 应显式重定向 stdout/stderr。
- 所有 rule 输出必须在 workdir 下。
- 不得把生产绝对路径硬编码进 Snakefile；使用 config.yaml。
- 默认开启 `--rerun-incomplete`，禁止默认 `--forceall`。
- WES/NIPT qsub profile runtime 使用 `snakemake-runner` 容器，不修改 `/biosoftware/miniconda/envs/*` 或宿主机系统 Python。
- `bio_wes_qsub` v1 runs the same WES mock Snakefile and `profiles/qsub` inside the Airflow worker; it sets `XDG_CACHE_HOME` under the run workdir so Snakemake does not write `/home/airflow/.cache`.

## 6. qsub 规范

- qsub 提交必须通过统一 wrapper。
- wrapper 必须记录：analysis_id、rule、sample、snakemake jobid、qsub jobid、stdout、stderr。
- demo 限制最大 jobs，例如 `MAX_DEMO_JOBS=<TO_BE_FILLED>`。
- 默认 queue 从 `SERVER_INFO.md` 或 `.env` 读取。

## 7. 文件路径规范

```text
shared/runs/<analysis_id>/config/request.json
shared/runs/<analysis_id>/config/samples.selected.tsv
shared/runs/<analysis_id>/config/config.yaml
shared/runs/<analysis_id>/logs/snakemake.stdout.log
shared/runs/<analysis_id>/logs/snakemake.stderr.log
shared/runs/<analysis_id>/logs/rules/<rule>/<sample>.stdout.log
shared/runs/<analysis_id>/logs/rules/<rule>/<sample>.stderr.log
shared/runs/<analysis_id>/results/...
shared/reports/<analysis_id>/multiqc_report.html
shared/reports/<analysis_id>/snakemake_report.html
```

## 8. 环境变量

| Variable | Required | Example | Notes |
|---|---|---|---|
| PROJECT_ROOT | yes | /opt/airflow-demo | 服务器项目目录 |
| SHARED_ROOT | yes | /data/airflow-demo | run、报告和日志根目录 |
| DOCKER_SUBNET | yes | 172.30.10.0/24 | demo Docker network |
| DOCKER_GATEWAY | yes | 172.30.10.1 | demo Docker gateway |
| BACKEND_IP | yes | 172.30.10.20 | fixed container IP |
| FRONTEND_IP | yes | 172.30.10.30 | fixed container IP |
| POSTGRES_IP | yes | 172.30.10.40 | fixed container IP |
| REDIS_IP | yes | 172.30.10.50 | fixed container IP |
| MAILHOG_IP | yes | 172.30.10.60 | fixed container IP |
| AIRFLOW_PORT | yes | 12958 | Airflow web/api host port; container port remains 8080 |
| FRONTEND_PORT | yes | 12959 | Docker nginx/frontend host port; container port remains 80 |
| BACKEND_IMAGE | yes | airflow-demo/backend:0.1.0 | explicit project image tag; avoid implicit latest |
| FRONTEND_IMAGE | yes | airflow-demo/frontend:0.1.0 | explicit project image tag; avoid implicit latest |
| AIRFLOW_IMAGE | yes | airflow-demo/airflow:0.1.0 | project Airflow image with isolated Snakemake 9 runtime |
| SNAKEMAKE_RUNNER_IMAGE | WES/NIPT qsub | airflow-demo/snakemake-runner:0.1.0 | Snakemake 9.23.1 plus `cluster-generic` executor image |
| AIRFLOW_UID | yes | 1005 on fengxian | set to `id -u` of the deploy user that owns `./shared` |
| BACKEND_CORS_ORIGINS | frontend only | * | demo CORS allowlist for browser access from `FRONTEND_PORT` |
| AIRFLOW_BASE_URL | yes | http://airflow-api-server:8080 | 容器内地址 |
| AIRFLOW_API_USERNAME | yes | admin | backend 调用 Airflow REST API 的用户名 |
| AIRFLOW_API_PASSWORD | yes | <SECRET_FROM_ENV> | only in untracked `.env` |
| AIRFLOW_ADMIN_USERNAME | yes | admin | Airflow init user; no password in Git |
| AIRFLOW_ADMIN_PASSWORD | yes | <SECRET_FROM_ENV> | only in untracked `.env` |
| AIRFLOW_ADMIN_EMAIL | yes | airflow-demo@example.com | demo Airflow admin email |
| AIRFLOW_DAGS_ROOT | PGT-A logger only | /opt/airflow/dags | Snakemake 9 subprocess `PYTHONPATH` for repo-local logger plugin |
| AIRFLOW_PIPELINES_ROOT | WES qsub | /opt/airflow/pipelines | read-only pipeline mount inside Airflow worker |
| AIRFLOW_PROFILES_ROOT | WES qsub | /opt/airflow/profiles | read-only Snakemake profile mount inside Airflow worker |
| BIODEMO_DB | yes | biodemo | 业务数据库名 |
| BIODEMO_USER | yes | biodemo | 业务数据库用户 |
| BIODEMO_PASSWORD | yes | <SECRET_FROM_ENV> | only in untracked `.env` |
| DATABASE_URL | yes | postgresql+psycopg://demo:***@postgres:5432/biodemo | 不提交真实密码 |
| PGTA_PIPELINE_ROOT | PGT-A only | /home/jiucheng/pipelines/PGT_A | host read-only mount |
| PGTA_CONTAINER_ROOT | PGT-A only | /opt/pipelines/PGT_A | container read-only mount target |
| BIOSOFTWARE_ROOT | PGT-A only | /biosoftware | host read-only mount |
| PGTA_SNAKEMAKE9_BIN | PGT-A logger only | /biosoftware/miniconda/envs/snakemake9_env/bin/snakemake | Snakemake 9 executable used by `bio_pgta_airflow` |
| PGTA_DATA_ROOT | PGT-A only | /data/project/CNV/PGT-A | host read-only mount |
| PGTA_CONTAINER_DATA_ROOT | PGT-A only | /data/project/CNV/PGT-A | container read-only mount target |
| INPUT_SCAN_ROOTS | PGT-A only | /data/project/CNV/PGT-A/rawdata | comma-separated backend allowlist for server-path scan |
| SMTP_HOST | no | mailhog | demo 邮件 |
| SMTP_PORT | no | 1025 | demo 邮件 |
| QSUB_QUEUE | no | all.q | 服务器补齐 |
| MAX_DEMO_JOBS | yes | 20 | 防止压垮集群 |
| ALLOW_REAL_QSUB | qsub only | false | real qsub stays disabled unless separately approved |
| AIRFLOW_DEMO_QSUB_MODE | qsub only | mock | wrapper mode; default must remain mock |
| AIRFLOW_DEMO_QSUB_PYTHON | qsub only | python | Python executable used by `profiles/qsub` submit command inside runner |

## 9. Git 忽略建议

```text
.env
*.local.md
shared/
data/
*.fastq.gz
*.fq.gz
*.bam
*.cram
*.vcf.gz
*.bcf
*.npz
*.log
__pycache__/
node_modules/
```

## 10. 代码审查 checklist

- 是否越过任务边界？
- 是否引入未批准依赖？
- 是否泄露路径/密码/患者信息？
- 是否更新相应文档？
- 是否有最小测试？
- 是否支持失败定位？
- 是否支持 resume 而不是强制全量重跑？
