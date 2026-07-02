# 07 Airflow DAG 设计

## 1. DAG 列表

| DAG ID | Pipeline | Runner | Notes |
|---|---|---|---|
| bio_wes_qsub | WES | Snakemake + qsub | 核心 demo 优先 |
| bio_nipt_qsub | NIPT | Snakemake/wrapper + qsub | 第二阶段 |
| bio_nipt_docker | NIPT Docker | docker runner | 第二阶段 |

## 2. 通用 DAG run conf

```json
{
  "analysis_id": "WES_20260702_000001",
  "pipeline": "wes_qsub",
  "mode": "new",
  "sample_sheet_path": "/data/airflow-demo/uploads/WES_20260702_000001/samples.tsv",
  "workdir": "/data/airflow-demo/runs/WES_20260702_000001",
  "email_to": "demo@example.com",
  "params": {
    "genome": "hg19",
    "queue": "<QSUB_QUEUE>",
    "max_jobs": 20
  }
}
```

## 3. 通用 task graph

```text
validate_request
  -> prepare_workdir
  -> parse_sample_sheet
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

### parse_sample_sheet

可以调用 backend parser 或共用 Python 模块。输出：

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
