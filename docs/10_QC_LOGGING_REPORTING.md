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
| Snakemake command | workdir/logs/snakemake.command.txt | PGT-A/WES 实际 Snakemake 命令，用于复现和确认 flags；WES reanalysis 还用于确认 `--forcerun` 且无 `--forceall` |
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

## 7. WES mock QC v1

T060/T054 已实现 WES mock QC 的最小闭环：

```text
workdir/reports/qc_summary.tsv
```

TSV 固定列：

```text
sample_id
metric_name
metric_value
metric_numeric
threshold
status
```

当前 mock 指标为每个 `S001/S002` 生成 `workflow_status=mock_success`、`mock_mean_depth=100`、`mock_pct_20x=0.95`，状态均为 `pass`。这些值只用于 demo 展示，不代表真实 WES 生产 QC。

导入规则：

- 只在显式调用 `POST /api/runs/{analysis_id}/actions/sync-airflow` 且 `wes_qsub` Airflow DAG run 为 `success` 时导入。
- 复用 `qc_metric` 表，不新增 migration。
- 每次导入先清理同一 `analysis_id` 的旧 QC metrics，再写入当前 TSV，因此重复 sync 不产生重复指标。
- 同步更新 `sample.qc_status`，聚合优先级为 `fail > warn > unknown > pass`。
- `GET /api/runs/{analysis_id}/qc` 返回 `summary` 和 `items`，普通 GET 不修改 DB。

前端 T054 v1 在 run detail 中展示 QC panel：pass/warn/fail/unknown 计数、样本级指标表和空状态。MultiQC HTML、Snakemake report artifact 表登记和邮件引用仍留给 T061/T063。

## 7.1 PGT-A baseline QC v1

T087 v1 复用现有 `qc_metric` 表和 `/api/runs/{analysis_id}/qc`，只在 `pgta` 且 `target=baseline_qc` 的 Airflow DAG run 显式 `sync-airflow` 到 `success` 后导入：

```text
workdir/qc/baseline/baseline_qc_summary.tsv
```

该 TSV 来自 PGT-A 现有 `aggregate_baseline_qc.py`，稳定列包括：

```text
sample_id
qc_decision
mapped_fragments
zero_bin_fraction
bin_cv
pearson_r
median_abs_z
gc_signal_slope
```

导入规则：

- `qc_decision` 映射为 `baseline_qc_decision`，`PASS/WARN/FAIL` 分别进入 `pass/warn/fail`。
- 数值列作为样本级 metric 导入，status 继承该样本 `qc_decision`。
- 每次导入先清理同一 `analysis_id` 旧 QC metrics，因此重复 sync 幂等。
- 同步更新 `sample.qc_status`。
- 若 `baseline_qc_summary.tsv` 未生成，sync 只更新 run 状态，不伪造 QC。

动态 artifact 同时发现：

```text
qc/baseline/baseline_qc_summary.tsv
qc/baseline/baseline_qc_pass_samples.txt
qc/baseline/baseline_qc_report.md
```

## 8. Artifact 类型

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

## 9. 报告生成

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

## 10. 前端日志查看要求

- 默认展示最后 200 行。
- 支持下载完整日志。
- 支持按 rule/sample 过滤。
- failed rule 默认打开 stderr。
- 日志不存在时显示明确状态，而不是空白。

## 11. 验收

- 成功 run 显示 QC pass/warn/fail。
- 失败 run 显示 failed rule 和 stderr 摘要。
- artifacts API 返回 report 链接。
- 邮件中包含 report 链接和错误摘要。

已完成的 PGT-A v1 后端验收：

- `GET /api/runs/{analysis_id}/logs?stream=stdout|stderr|metadata` 可读取固定 metadata run 文件。
- `GET /api/runs/{analysis_id}/artifacts` 可动态发现 metadata、dry-run stdout/stderr、command 和 config 产物，包括 `logs/snakemake.command.txt` 与 `config/pgta_run_config.json`。
- `POST /api/runs/{analysis_id}/actions/sync-airflow` 可把 Airflow success/failed 同步到 biodemo，并在 failed 时写入 `error_summary`。
- T088 后 `bio_pgta` 和 `bio_pgta_airflow` 均设置 `XDG_CACHE_HOME=<workdir>/tmp/xdg-cache`，避免 Snakemake 写入不可写的 `/home/airflow/.cache/snakemake`。

已完成的 PGT-A Airflow-only logger 验收：

- `bio_pgta_airflow` 可用 Snakemake 9.23.1 的 `--logger airflow-demo` 执行 metadata target。
- repo-local logger plugin 写入 `logs/events/snakemake_events.jsonl`。
- Airflow `collect_snakemake_events` task 写入 `logs/events/snakemake_rule_summary.tsv`，并在 task log 与 XCom 中展示 event count、status counts 和 failed jobs。
- 配置 `backend_event_url=http://backend:8000/api/events/snakemake` 时，PGT-A metadata smoke 已把 `all` 和 `collect_run_metadata` rule 状态 upsert 为 `success`，并可通过 `/api/runs/{analysis_id}/rules` 查询。

已完成的 WES mock QC 验收：

- `bio_wes_qsub` 成功 run `WES_20260705_164813_C5561C` 生成 `reports/qc_summary.tsv`。
- 显式 `sync-airflow` 后，`GET /api/runs/WES_20260705_164813_C5561C/qc` 返回 `pass=6`、`warn=0`、`fail=0`、`unknown=0` 和 6 条指标。
- artifacts API 动态发现 `wes_qc_summary`。
- 前端 Docker test target 覆盖 QC panel 渲染、空 QC 状态和 summary 显示。
