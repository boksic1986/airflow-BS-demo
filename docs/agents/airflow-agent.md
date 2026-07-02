# Airflow Agent

Airflow agent 负责 DAG、task helper、通知、DAG import 测试。不得把每个 Snakemake rule 拆成 Airflow task。

## Standard start

1. Read `AGENTS.md`.
2. Read `CURRENT_STATE.md`.
3. Read `TASKS.md`.
4. Read role-related docs.
5. Confirm scope.

## Standard finish

1. Run role-specific tests.
2. Update related docs.
3. Update `CURRENT_STATE.md` and `TASKS.md`.
4. Append `HANDOFF.md`.
