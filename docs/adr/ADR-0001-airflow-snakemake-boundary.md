# ADR-0001 Airflow 与 Snakemake 边界

## Status

Accepted for demo.

## Context

WES/NIPT 流程包含大量 sample/rule 级步骤，依赖输入文件和中间结果。Airflow 可以调度和监控 DAG，但如果把每个 Snakemake rule 都映射成 Airflow task，会导致 DAG 复杂、动态任务过多、维护成本高。

## Decision

Airflow 只负责项目级生命周期：validate、prepare、generate config、run pipeline、collect QC、notify。Snakemake 负责 rule/file dependency、qsub 并行、断点续跑。Rule 级状态通过 Snakemake logger/qsub wrapper 事件写入业务 DB。

## Consequences

优点：

- DAG 简洁。
- 保留 Snakemake 的生信优势。
- 易接入已有流程。
- 失败定位仍然能到 rule/sample/qsub/log。

缺点：

- Airflow UI 本身看不到每个 rule，需要前端展示。
- 需要额外事件采集。
