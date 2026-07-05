# 07 Airflow DAG 设计

## 1. DAG 列表

| DAG ID | Pipeline | Runner | Notes |
|---|---|---|---|
| bio_wes_qsub | WES | Snakemake + qsub | 核心 demo 优先 |
| bio_nipt_qsub | NIPT | Snakemake/wrapper + qsub | 第二阶段 |
| bio_nipt_docker | NIPT Docker | docker runner | 第二阶段 |
| bio_pgta | PGT-A | Snakemake direct in Airflow worker | v1 支持 metadata、dryrun_cnv 和 invalid_target failure smoke，不使用 qsub |
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

PGT-A v1 conf example:

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

## 7. `bio_wes_qsub` v1

`bio_wes_qsub` is the first WES mock project-level DAG. T031 proved Airflow-only execution; T044/T056 adds FastAPI/frontend create, submit, resume, and selected-rule rerun for the same mock workflow. T060 adds deterministic mock QC output consumed by the backend after explicit `sync-airflow`. It still does not add email notification, NIPT, production WES data, or real qsub.

Task graph:

```text
validate_request
  -> prepare_wes_config
  -> run_wes_qsub
  -> collect_wes_artifacts
```

Supported DAG run conf:

```json
{
  "analysis_id": "WES_AIRFLOW_20260705_004506",
  "pipeline": "wes_qsub",
  "mode": "new",
  "workdir": "/data/airflow-demo/runs/WES_AIRFLOW_20260705_004506",
  "backend_event_url": null,
  "params": {
    "target": "final_summary",
    "max_jobs": 2
  }
}
```

Validation rules:

- `pipeline` must be `wes_qsub`.
- `mode` must be `new`, `resume`, or `rerun_rule`.
- `params.target` must be `final_summary`.
- `params.max_jobs` must be `1..2`.
- `workdir` must be under `/data/airflow-demo`.
- `rerun_rule` requires `params.rule` in `fastp/bwa_mem/markdup/final_summary`; sample-level rules require `params.sample_id=S001/S002`.

`prepare_wes_config` reads `pipelines/wes/config/mock_config.yaml` and writes run-local:

```text
workdir/config/wes_mock_config.yaml
workdir/config/wes_airflow_request.json
```

It rewrites mock sample input paths to Airflow container paths under `/opt/airflow/pipelines/wes/mock_data`.

`run_wes_qsub` runs inside the Airflow worker image `airflow-demo/airflow:0.1.0`:

```bash
snakemake \
  --snakefile /opt/airflow/pipelines/wes/workflow/Snakefile \
  --configfile <workdir>/config/wes_mock_config.yaml \
  --profile /opt/airflow/profiles/qsub
```

For `mode=resume`, the command remains profile-based and relies on Snakemake output state plus `rerun-incomplete`; no `--forceall` is added. For `mode=rerun_rule`, `run_wes_qsub` appends:

```bash
--forcerun <rule> <selected-target>
```

Selected targets are limited to the mock output path for `fastp/bwa_mem/markdup` and `reports/final_summary.tsv`. The project-level `final_summary` rule also writes `reports/qc_summary.tsv`.

Runtime environment:

- `AIRFLOW_DEMO_QSUB_MODE=mock`.
- `AIRFLOW_DEMO_QSUB_PYTHON=python`.
- `XDG_CACHE_HOME=<workdir>/tmp/xdg-cache`, so Snakemake does not write `/home/airflow/.cache`.
- Airflow services must run with `AIRFLOW_UID=$(id -u)` for the deploy user that owns `./shared`; `fengxian` uses `1005`.

Expected outputs:

```text
workdir/reports/final_summary.tsv
workdir/reports/qc_summary.tsv
workdir/logs/snakemake.stdout.log
workdir/logs/snakemake.stderr.log
workdir/logs/snakemake.command.txt
workdir/logs/qsub/*.o
workdir/logs/qsub/*.e
workdir/logs/events/snakemake_events.jsonl
```

2026-07-05 `fengxian` smoke:

- DAG run `manual__WES_AIRFLOW_20260705_004506` ended `success`.
- `reports/final_summary.tsv` contains `S001` and `S002` with `mock_success`.
- `logs/events/snakemake_events.jsonl` has 14 lines and contains `qsub_submitted` / `qsub_success`.
- `collect_wes_artifacts` returned XCom summary `event_count=14` and `qsub_log_count=14`.
- Real `qsub/qstat` was not called.

2026-07-05 `fengxian` T044/T056 smoke:

- API/frontend path created `WES_20260705_162041_2507AF`.
- `manual__WES_20260705_162041_2507AF` ended `success`.
- `manual__WES_20260705_162041_2507AF__resume__20260705T162142Z` ended `success`.
- `manual__WES_20260705_162041_2507AF__rerun_rule__20260705T162151Z` ended `success`.
- `logs/snakemake.command.txt` for the final run contains `--forcerun fastp` and does not contain `--forceall`.
- `logs/events/snakemake_events.jsonl` has 28 lines after the sequence.

2026-07-05 `fengxian` T060/T054 smoke:

- API/frontend path created and submitted `WES_20260705_164813_C5561C`.
- `manual__WES_20260705_164813_C5561C` ended `success` after explicit sync.
- `reports/qc_summary.tsv` exists with 6 deterministic mock QC rows across `S001/S002`.
- `GET /api/runs/WES_20260705_164813_C5561C/qc` returned `pass=6`, `warn=0`, `fail=0`, `unknown=0`.
- Dynamic artifacts include `wes_qc_summary`.

## 8. `bio_pgta` v1

第一版 `bio_pgta` 用于 PGT-A metadata、CNV dry-run 和受控 failure smoke。不跑真实 CNV、baseline QC，也不使用 qsub。

Task graph:

```text
validate_request
  -> prepare_pgta_config
  -> run_pgta_target
  -> collect_pgta_artifact
```

### validate_request

检查：

- `analysis_id` 非空。
- `pipeline = pgta`。
- `params.target` 为 `metadata`、`dryrun_cnv` 或 `invalid_target`。
- `workdir` 在 `/data/airflow-demo` 下。
- `sample_sheet_path` 存在，且位于 `workdir` 下。

### prepare_pgta_config

读取 `config/samples.selected.tsv`，检查 `sample_id/R1/R2/source_dir` 列，确认 R1/R2/source_dir 均在 `/data/project/CNV/PGT-A` 只读数据根目录下。

输出：

```text
shared/runs/<analysis_id>/config.yaml
shared/runs/<analysis_id>/config/pgta_run_config.json
shared/runs/<analysis_id>/config/pgta_metadata_config.json
```

target 映射：

| demo target | Snakemake 行为 |
|---|---|
| `metadata` | `pipeline.targets=["metadata"]`，真实执行轻量 metadata |
| `dryrun_cnv` | `pipeline.targets=["cnv"]`，启用 `wisecondorx.cnv.enable`，使用只读 sex-specific WisecondorX reference，并加 `--dry-run --ignore-incomplete --rerun-triggers mtime` |
| `invalid_target` | 向 Snakemake 传入 `__airflow_demo_invalid_target__`，用于失败 smoke |

### run_pgta_target

在 Airflow worker 中直接调用 PGT-A Snakemake 环境：

```bash
/biosoftware/miniconda/envs/snakemake_env/bin/snakemake \
  --snakefile /opt/pipelines/PGT_A/Snakefile \
  --cores 1 \
  --printshellcmds \
  --configfile <workdir>/config.yaml
```

`dryrun_cnv` 会额外传 `--dry-run --ignore-incomplete --rerun-triggers mtime`；`invalid_target` 会额外传 `__airflow_demo_invalid_target__`。执行目录为 `/data/airflow-demo/runs/<analysis_id>`，输出只允许写入该 run workdir。stdout/stderr 写入：

```text
shared/runs/<analysis_id>/logs/snakemake.stdout.log
shared/runs/<analysis_id>/logs/snakemake.stderr.log
```

### collect_pgta_artifact

`metadata` 验收 `logs/run_metadata.tsv` 是否存在；`dryrun_cnv` 验收 `logs/snakemake.stdout.log` 是否存在并返回 dry-run stdout artifact。`invalid_target` 预期在 `run_pgta_target` failed，不进入 collect task。

本阶段已知边界：

- `invalid_target` 是测试错误摘要链路的受控失败入口，不代表生产 target。
- qsub、baseline_qc 和真实 CNV 运行仍在后续任务中。

## 9. `bio_pgta_airflow` Airflow-only logger v1

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
