# 01 系统架构设计

## 1. 总体架构

```text
Browser
  |
  v
React Frontend
  |
  v
FastAPI Backend  ----> PostgreSQL biodemo DB
  |                         ^
  |                         |
  |                   Snakemake/qsub event POST
  v
Airflow REST API
  |
  v
Airflow DAGs
  |
  +--> prepare workdir/config
  +--> run Snakemake / Docker runner
  +--> collect QC/artifacts
  +--> notify email

Shared filesystem
  uploads/
  runs/<analysis_id>/
  reports/<analysis_id>/
  logs/
```

## 2. 服务列表

| Service | Role | Data ownership | Notes |
|---|---|---|---|
| frontend | UI | none | React/TypeScript |
| backend | API/orchestrator facade | biodemo DB | FastAPI |
| airflow-api-server | DAG API/UI | Airflow metadata | 不存业务样本详情 |
| airflow-scheduler | scheduling | Airflow metadata | |
| airflow-worker | execute tasks | shared filesystem | CeleryExecutor demo |
| postgres | DB | airflow + biodemo | 分 database/schema |
| redis | broker | transient | Celery broker |
| mailhog | demo mail | transient | 非生产 |

## 3. 数据流

### Submit

```text
frontend upload/form
  -> backend /api/runs
  -> save uploads/<analysis_id>/samples.*
  -> parse sample sheet
  -> insert analysis_run/sample rows
  -> trigger Airflow DAG run with conf
  -> return analysis_id/dag_run_id
```

### Run

```text
Airflow validate_request
  -> prepare_workdir
  -> generate_snakemake_config
  -> snakemake dry-run
  -> snakemake execute
  -> collect_qc
  -> notify_email
```

### Rule event

```text
Snakemake logger/qsub wrapper
  -> POST /api/events/snakemake
  -> backend upsert snakemake_rule_event
  -> frontend polling/SSE refreshes rule table
```

### Logs

```text
qsub stdout/stderr files
  -> shared/runs/<analysis_id>/logs/...
  -> backend /api/runs/<id>/logs?rule=&sample=&stream=
  -> frontend log viewer
```

## 4. 状态模型

### analysis_run.status

```text
submitted
preparing
running
success
failed
qc_warning
cancelled
unknown
```

### snakemake_rule_event.status

```text
planned
submitted
running
success
failed
skipped
cached
unknown
```

## 5. 关键架构决策

- Airflow metadata DB 不作为业务查询来源。
- 业务状态存入 biodemo DB。
- Rule 级状态通过事件/日志采集，不把每个 rule 拆成 Airflow task。
- 重分析由 Snakemake 的文件依赖和 rerun flags 控制。
- Demo 首选 shared filesystem，后续才考虑对象存储。

## 6. 部署模式

### 本地 demo

```text
docker compose up
frontend: localhost:12959
backend: localhost:8000
airflow: localhost:12958
mailhog: localhost:8025
```

### 服务器 demo

```text
http://<SERVER_HOST>:12959
http://<SERVER_HOST>:8000
http://<SERVER_HOST>:12958
http://<SERVER_HOST>:8025
```

生产化时应加反向代理、HTTPS、SSO/LDAP、访问控制和日志留存策略。
