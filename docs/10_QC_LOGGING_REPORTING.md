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
| qsub stdout | workdir/logs/qsub/*.o | 集群 job 标准输出 |
| qsub stderr | workdir/logs/qsub/*.e | 集群 job 标准错误 |
| rule stdout | workdir/logs/rules/...stdout.log | rule 自身输出 |
| rule stderr | workdir/logs/rules/...stderr.log | rule 自身错误 |
| events jsonl | workdir/logs/events/*.jsonl | backend 不可用 fallback |

## 6. Error summary 提取

失败时 backend/airflow 应提取：

```text
analysis_id
pipeline
failed_task
failed_rule
sample_id
qsub_jobid
stderr_path
last_100_lines
suspected_reason
```

不要只显示 “subprocess returned non-zero”。

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
