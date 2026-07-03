# 07 Airflow DAG 设计

## 1. DAG 列表

| DAG ID | Pipeline | Runner | Notes |
|---|---|---|---|
| bio_wes_qsub | WES | Snakemake + qsub | 核心 demo 优先 |
| bio_nipt_qsub | NIPT | Snakemake/wrapper + qsub | 第二阶段 |
| bio_nipt_docker | NIPT Docker | docker runner | 第二阶段 |
| bio_pgta | PGT-A | Snakemake direct in Airflow worker | v1 只跑 metadata target，不使用 qsub；dry-run 后续扩展 |
| bio_pgta_airflow | PGT-A | Snakemake 9 direct in Airflow worker | Airflow-only metadata DAG，使用 repo-local logger plugin 写 JSONL 并在 Airflow log/XCom 展示状态 |

## 2. 通用 DAG run conf

`POST /api/runs` 只创建 `analysis_run.status=created`，不会触发 Airflow。`POST /api/runs/{analysis_id}/actions/submit` 会读取 DB 中的 `sample_sheet_path`、`workdir` 和 `params_json`，触发 Airflow 并生成以下 DAG run conf。

```json
{
  "analysis_id": "WES_20260702_000001",
  "pipeline": "wes_qsub",
  "mode": "new",
  "sample_sheet_path": "/data/airflow-demo/runs/WES_20260702_000001/config/samples.selected.tsv",
  "workdir": "/data/airflow-demo/runs/WES_20260702_000001",
  "email_to": "demo@example.com",
  "params": {
    "genome": "hg19",
    "queue": "<QSUB_QUEUE>",
    "max_jobs": 20
  }
}
```

PGT-A metadata v1 conf example:

```json
{
  "analysis_id": "PGTA_20260702_171533_9A85B1",
  "pipeline": "pgta",
  "mode": "new",
  "sample_sheet_path": "/data/airflow-demo/runs/PGTA_20260702_171533_9A85B1/config/samples.selected.tsv",
  "workdir": "/data/airflow-demo/runs/PGTA_20260702_171533_9A85B1",
  "email_to": null,
  "params": {
    "project_name": "PGT-A metadata smoke",
    "rawdata_root": "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28",
    "target": "metadata",
    "input_mode": "server_path_scan",
    "selected_count": 1
  }
}
```

## 3. 通用 task graph

```text
validate_request
  -> prepare_workdir
  -> validate_selected_manifest
  -> generate_pipeline_config
  -> dry_run
  -> run_pipeline
  -> collect_qc
  -> register_artifacts
  -> notify_success
```

失败路径：

```text
any failure -> extract_error_summary -> notify_failure
```

## 4. Task 说明

### validate_request

检查：

- analysis_id 存在。
- workdir 在允许路径内。
- sample_sheet_path 存在。
- pipeline/mode 合法。
- max_jobs 不超过 demo 限额。

### prepare_workdir

创建：

```text
workdir/config
workdir/logs
workdir/logs/rules
workdir/results
workdir/tmp
reports/<analysis_id>
```

### validate_selected_manifest

读取 backend 生成的 selected manifest。T022/T024 的 PGT-A v1 manifest 来自服务器路径扫描和勾选，不是上传文件。检查：

- `sample_id/R1/R2/source_dir` 列存在。
- R1/R2 路径在允许的 PGT-A 数据根目录内。
- R1/R2 文件可读。
- sample_id 在本次 run 内唯一。

必要时输出 DAG 内归一化副本：

```text
workdir/config/samples.normalized.tsv
```

### generate_pipeline_config

输出 Snakemake config：

```text
workdir/config/config.yaml
```

必须包含：

```yaml
analysis_id: ...
workdir: ...
sample_sheet: ...
input_mode: server_path_scan
backend_event_url: http://backend:8000/api/events/snakemake
max_jobs: ...
queue: ...
```

### dry_run

运行 Snakemake dry-run：

```bash
snakemake -n --printshellcmds --configfile <config>
```

失败时不进入 run_pipeline。

### run_pipeline

根据 mode 生成 flags：

| mode | Snakemake flags |
|---|---|
| new | `--rerun-incomplete` |
| resume | `--rerun-incomplete` |
| rerun_failed | `--rerun-incomplete` + backend 传入 failed targets |
| rerun_rule | `--forcerun <rule>` 或指定 target |
| clone_new | 新 workdir，等同 new |

禁止默认：

```bash
--forceall
```

### collect_qc

读取 pipeline 生成的 QC 文件，写入 DB 或调用 backend API。

### register_artifacts

登记：

- MultiQC HTML。
- Snakemake report。
- final summary TSV。
- 关键日志。

### notify_success / notify_failure

demo 可使用 MailHog。失败邮件必须包含 error summary 和 stderr path。

## 5. Airflow 实现规范

- 任务之间通过 XCom 传小 JSON，不传大文件。
- 大文件路径写入 DB 或 config。
- DAG 默认 `catchup=False`。
- DAG 不自动 schedule，使用 manual/API trigger。
- retry 策略谨慎：validate/generate 不重试，run_pipeline 可配置 0-1 次。

## 6. DAG import test

推荐测试：

```bash
python -m py_compile dags/*.py
airflow dags list
```

如果 Airflow CLI 不在宿主机，应在容器中运行：

```bash
docker compose exec airflow-scheduler airflow dags list
```

## 7. `bio_pgta` v1

第一版 `bio_pgta` 只用于 PGT-A metadata smoke，不跑 mapping、CNV、baseline QC，也不使用 qsub。

Task graph:

```text
validate_request
  -> prepare_pgta_config
  -> run_metadata
  -> collect_metadata_artifact
```

### validate_request

检查：

- `analysis_id` 非空。
- `pipeline = pgta`。
- `params.target = metadata`。
- `workdir` 在 `/data/airflow-demo` 下。
- `sample_sheet_path` 存在，且位于 `workdir` 下。

### prepare_pgta_config

读取 `config/samples.selected.tsv`，检查 `sample_id/R1/R2/source_dir` 列，确认 R1/R2/source_dir 均在 `/data/project/CNV/PGT-A` 只读数据根目录下。

输出：

```text
shared/runs/<analysis_id>/config.yaml
shared/runs/<analysis_id>/config/pgta_metadata_config.json
```

### run_metadata

在 Airflow worker 中直接调用 PGT-A Snakemake 环境：

```bash
/biosoftware/miniconda/envs/snakemake_env/bin/snakemake \
  --snakefile /opt/pipelines/PGT_A/Snakefile \
  --cores 1 \
  --printshellcmds
```

执行目录为 `/data/airflow-demo/runs/<analysis_id>`。Snakemake 使用 run-local `config.yaml`，输出只允许写入该 run workdir。stdout/stderr 写入：

```text
shared/runs/<analysis_id>/logs/snakemake.stdout.log
shared/runs/<analysis_id>/logs/snakemake.stderr.log
```

### collect_metadata_artifact

验收 `logs/run_metadata.tsv` 是否存在，并返回 metadata artifact 信息供后续 T025/T057 登记或展示。

本阶段已知边界：

- backend 只把 run 更新到 `submitted`，还没有 Airflow success/failed 状态回写。
- backend artifact/log API 尚未实现。
- dry-run、非法 target failure smoke 和前端展示仍在后续任务中。

## 8. `bio_pgta_airflow` Airflow-only logger v1

`bio_pgta_airflow` 用于验证 PGT-A 在 Snakemake 9.23.1 下通过 logger plugin 接入 Airflow UI。它不走 FastAPI，不写 biodemo DB，也不替代 `bio_pgta`。

DAG run conf 第一版只支持已有 manifest 路径：

```json
{
  "analysis_id": "PGTA_AIRFLOW_20260703_074844",
  "workdir": "/data/airflow-demo/runs/PGTA_AIRFLOW_20260703_074844",
  "sample_sheet_path": "/data/airflow-demo/runs/PGTA_AIRFLOW_20260703_074844/config/samples.selected.tsv",
  "target": "metadata",
  "email_to": null,
  "backend_event_url": "http://backend:8000/api/events/snakemake"
}
```

Task graph:

```text
validate_request
  -> prepare_pgta_config
  -> run_snakemake9_with_logger
  -> collect_snakemake_events
  -> collect_metadata_artifact
```

`run_snakemake9_with_logger` 调用：

```bash
/biosoftware/miniconda/envs/snakemake9_env/bin/snakemake \
  --snakefile /opt/pipelines/PGT_A/Snakefile \
  --cores 1 \
  --printshellcmds \
  --show-failed-logs \
  --logger airflow-demo \
  --logger-airflow-demo-analysis-id <analysis_id> \
  --logger-airflow-demo-workdir <workdir> \
  --logger-airflow-demo-events-path <workdir>/logs/events/snakemake_events.jsonl \
  --logger-airflow-demo-backend-event-url http://backend:8000/api/events/snakemake
```

`collect_snakemake_events` 读取 JSONL，生成：

```text
workdir/logs/events/snakemake_events.jsonl
workdir/logs/events/snakemake_rule_summary.tsv
```

Airflow 网页第一版通过 task log 和 XCom 查看状态汇总；不实现自定义 Airflow Web 插件。若 `backend_event_url` 未配置，logger 只写 JSONL；若配置，则 rule/job 级事件会同步 POST 到 FastAPI 并 upsert 到 biodemo `snakemake_rule_event`。
