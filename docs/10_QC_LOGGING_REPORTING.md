# 10 QC、日志和报告设计

## 1. QC 总体原则

- QC 指标既要有 HTML 报告，也要有结构化表格。
- HTML 报告用于展示完整信息；结构化表用于 dashboard 和筛选。
- QC parser 必须容忍部分指标缺失，并给出 unknown/warn。

## 2. WES QC 指标

建议 MVP：

```text
sample_id
raw_reads
clean_reads
q30_rate
mapping_rate
duplication_rate
mean_depth
pct_20x
pct_30x
insert_size_median
sex_check
qc_status
```

## 3. NIPT QC 指标

建议 MVP：

```text
sample_id
total_reads
clean_reads
mapped_reads
mapping_rate
gc_bias_metric
fetal_fraction
chr13_z
chr18_z
chr21_z
qc_status
```

## 4. QC 状态规则

```text
pass: 满足 demo 阈值
warn: 指标偏离但流程完成
fail: 关键指标缺失或严重异常
unknown: 未生成或未解析
```

阈值先放配置文件：

```yaml
wes:
  mean_depth_warn: 80
  pct_20x_warn: 0.90
nipt:
  fetal_fraction_warn: 0.04
  mapping_rate_warn: 0.60
```

## 5. 日志分层

| Log | Path | Purpose |
|---|---|---|
| Airflow task log | Airflow managed | DAG/task 级失败 |
| Snakemake stdout | workdir/logs/snakemake.stdout.log | 主流程命令 |
| Snakemake stderr | workdir/logs/snakemake.stderr.log | 主流程错误 |
| Snakemake command | workdir/logs/snakemake.command.txt | WES mock 实际 Snakemake 命令，用于确认 `--forcerun` 且无 `--forceall` |
| qsub stdout | workdir/logs/qsub/*.o | 集群 job 标准输出 |
| qsub stderr | workdir/logs/qsub/*.e | 集群 job 标准错误 |
| rule stdout | workdir/logs/rules/...stdout.log | rule 自身输出 |
| rule stderr | workdir/logs/rules/...stderr.log | rule 自身错误 |
| events jsonl | workdir/logs/events/*.jsonl | backend 不可用 fallback |
| PGT-A Snakemake 9 events | workdir/logs/events/snakemake_events.jsonl | Airflow-only logger plugin 事件 |
| PGT-A rule summary | workdir/logs/events/snakemake_rule_summary.tsv | Airflow task log/XCom 的 rule 状态汇总 |

## 6. Error summary 提取

PGT-A v1 当前已实现 run-level error summary。显式调用：

```http
POST /api/runs/{analysis_id}/actions/sync-airflow
```

若 Airflow DAG run 为 failed，backend 会优先读取：

```text
workdir/logs/snakemake.stderr.log
```

并把以下 JSON 文本写入 `analysis_run.error_summary`：

```text
analysis_id
dag_id
dag_run_id
status
stderr_path
last_100_lines
```

若 stderr 不存在或为空，`last_100_lines` 使用 `no stderr available`。Airflow task log 抓取、failed task、failed rule、sample_id、qsub_jobid 和 suspected_reason 留到 T026/T043 后补齐；不要把当前 run-level 摘要冒充 rule/qsub 级诊断。

T026/T043 已补齐 PGT-A Snakemake 9 rule/job 事件入库基础：`POST /api/events/snakemake` 可 upsert `snakemake_rule_event`，`GET /api/runs/{analysis_id}/rules` 可返回 rule/job 最新状态。qsub job id、qsub stdout/stderr 细粒度诊断仍留给后续 qsub wrapper 任务。

## 7. Artifact 类型

```text
multiqc_html
snakemake_report
qc_tsv
final_summary
airflow_log
snakemake_log
rule_log
qsub_log
```

## 8. 报告生成

MVP 可以生成：

```text
shared/reports/<analysis_id>/multiqc_report.html
shared/reports/<analysis_id>/qc_summary.tsv
shared/reports/<analysis_id>/final_summary.json
```

进阶：

```text
snakemake --report shared/reports/<analysis_id>/snakemake_report.html
```

## 9. 前端日志查看要求

- 默认展示最后 200 行。
- 支持下载完整日志。
- 支持按 rule/sample 过滤。
- failed rule 默认打开 stderr。
- 日志不存在时显示明确状态，而不是空白。

## 10. 验收

- 成功 run 显示 QC pass/warn/fail。
- 失败 run 显示 failed rule 和 stderr 摘要。
- artifacts API 返回 report 链接。
- 邮件中包含 report 链接和错误摘要。

已完成的 PGT-A v1 后端验收：

- `GET /api/runs/{analysis_id}/logs?stream=stdout|stderr|metadata` 可读取固定 metadata run 文件。
- `GET /api/runs/{analysis_id}/artifacts` 可动态发现 metadata、dry-run stdout/stderr 和 config 产物，包括 `config/pgta_run_config.json`。
- `POST /api/runs/{analysis_id}/actions/sync-airflow` 可把 Airflow success/failed 同步到 biodemo，并在 failed 时写入 `error_summary`。

已完成的 PGT-A Airflow-only logger 验收：

- `bio_pgta_airflow` 可用 Snakemake 9.23.1 的 `--logger airflow-demo` 执行 metadata target。
- repo-local logger plugin 写入 `logs/events/snakemake_events.jsonl`。
- Airflow `collect_snakemake_events` task 写入 `logs/events/snakemake_rule_summary.tsv`，并在 task log 与 XCom 中展示 event count、status counts 和 failed jobs。
- 配置 `backend_event_url=http://backend:8000/api/events/snakemake` 时，PGT-A metadata smoke 已把 `all` 和 `collect_run_metadata` rule 状态 upsert 为 `success`，并可通过 `/api/runs/{analysis_id}/rules` 查询。
