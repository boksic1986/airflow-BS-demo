# ADR-0002 业务数据库与 Airflow metadata 分离

## Status

Accepted for demo.

## Context

Airflow metadata DB 存 DAG/task/run 状态，但不适合作为业务系统数据库。生信 demo 需要保存 sample、QC、rule event、artifact、reanalysis action 等业务实体。

## Decision

使用独立 `biodemo` database/schema 存业务数据。Airflow metadata DB 仅由 Airflow 管理。后端通过 Airflow REST API 查询/触发 DAG run。

## Consequences

优点：

- 降低与 Airflow 内部 schema 耦合。
- 业务查询更清晰。
- 未来升级 Airflow 风险更小。

缺点：

- 需要同步 Airflow 状态到业务状态。
- 需要处理 Airflow API 失败和状态不一致。
