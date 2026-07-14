# 01 系统架构设计

## T127 BS shared control-plane topology

BS10610 uses one Airflow control plane for NIPT Docker and host-native WGS.
It is not two platform deployments. One frontend/nginx gateway, FastAPI,
PostgreSQL/Redis pair, Airflow API server, scheduler, and Celery worker serve
both `bio_nipt_docker` and `bio_wgs`; a shared paused `bio_intake_scan` handles
both request contracts. PGT-A is not deployed on BS.

WGS analysis software remains on the host and is invoked through a restricted
`SSHOperator` gate. NIPT remains inside the validated Snakemake 9 container.
The one-slot `bs_heavy_analysis` pool serializes both heavy workflows without
reducing the WGS 96-core or NIPT 32-core runtime allocations.

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
  runs/<analysis_id>/
    config/samples.selected.tsv
    config/request.json
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
frontend server-path form
  -> backend /api/input/scan scans allowed rawdata_root
  -> frontend user selects candidate samples
  -> backend /api/runs creates analysis_run/sample rows
  -> write runs/<analysis_id>/config/samples.selected.tsv
  -> write runs/<analysis_id>/config/request.json
  -> return analysis_id with status=created
```

PGT-A v1 采用两步模式：创建 run 后，再由 submit action 把已创建 run 转为 Airflow DAG run。

```text
backend /api/runs/<analysis_id>/actions/submit
  -> read analysis_run/workdir/sample_sheet_path
  -> trigger Airflow DAG bio_pgta with conf
  -> update analysis_run dag_run_id/status=submitted
  -> return analysis_id/dag_run_id
```

### Run

```text
Airflow bio_pgta v1
  -> validate_request
  -> prepare_pgta_config
  -> run_metadata
  -> collect_metadata_artifact
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
created
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
