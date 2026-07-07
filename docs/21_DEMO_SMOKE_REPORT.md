# 21 Demo Smoke Report

## Summary

2026-07-07 在 `ssh fengxian` 对当前 demo 主链路做只读复核。本轮没有提交新的 PGT-A/WES run，没有重跑 baseline_qc，也没有执行 destructive Docker 操作。

结论：

- 前端、后端和 Airflow 均可访问。
- PGT-A Level 4 `baseline_qc` workflow 已成功，可用于展示真实 PGT-A 执行闭环。
- PGT-A 当前 G10/G11 样本 QC decision 均为 `FAIL`，不能当作 QC pass 样本展示。
- WES mock QC success 和 WES mock rerun_rule 均可用于展示平台能力。

## Environment

| Item | Evidence |
|---|---|
| Repo head on `fengxian` | `3310134` |
| Frontend | `http://127.0.0.1:12959/` returned HTTP `200` |
| Backend | `GET /api/health` returned `{"status":"ok"}` |
| Airflow | `GET /health` returned metadatabase `healthy`, scheduler `healthy` |
| Runtime safety | only read-only API/CLI/file checks were run |

## PGT-A Evidence

Run:

```text
analysis_id: PGTA_20260706_162150_00C4FD
dag_run_id: manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z
pipeline: pgta
target: baseline_qc
workflow_status: success
```

Verified API/file evidence:

| Check | Result |
|---|---|
| `GET /api/runs/PGTA_20260706_162150_00C4FD` | status `success` |
| `GET /samples` | G10 `success/fail`, G11 `success/fail` |
| `GET /qc` | `pass=0,warn=0,fail=14,unknown=0`, 14 items |
| `GET /artifacts` | includes `snakemake_command`, `pgta_python_preflight`, `pgta_baseline_qc_summary`, `pgta_baseline_qc_pass_samples`, `pgta_baseline_qc_report` |
| `baseline_qc_summary.tsv` | exists; G10/G11 `qc_decision=FAIL` |

Interpretation:

```text
workflow success != QC pass
```

The Airflow/Snakemake workflow completed and generated the expected baseline QC outputs. The sample-level QC decision is `FAIL`, with reasons including `median_abs_z>1.5` and `outlier_frac_abs_z_gt_3>0.3`. This is suitable for demonstrating QC visibility and separation of execution status from biological/sample QC status.

## WES Mock Evidence

QC success run:

```text
analysis_id: WES_20260705_164813_C5561C
status: success
dag_run_id: manual__WES_20260705_164813_C5561C
qc_summary: pass=6,warn=0,fail=0,unknown=0
artifacts: wes_final_summary, wes_qc_summary
```

Resume/rerun rule run:

```text
analysis_id: WES_20260705_162041_2507AF
status: success
dag_run_id: manual__WES_20260705_162041_2507AF__rerun_rule__20260705T162151Z
rule_count: 7
command evidence: contains --forcerun fastp; does not contain --forceall
```

WES mock is the cleanest current demo path for qsub observability, rule status, QC pass panel, and safe rerun-rule behavior.

## Demo Readiness

Ready to demonstrate:

- PGT-A server-path sample scan, create, submit, sync, logs, artifacts.
- PGT-A `metadata` smoke for a quick live action.
- PGT-A historical `baseline_qc` run as workflow success with sample QC fail.
- WES mock QC success.
- WES mock rule table with mock qsub job ids.
- WES mock rerun rule without `--forceall`.

Not ready / future work:

- MailHog success/failure notification is still `T034/T063`.
- NIPT qsub/docker flows are still todo.
- PGT-A QC pass sample is not yet identified; do a read-only data/threshold audit before another baseline_qc run.
- MultiQC/Snakemake report registration remains `T061`.

## Acceptance

T080/T081 acceptance for this stage:

- Demo script explains what is already implemented and what is not.
- PGT-A workflow success and QC fail are explicitly separated.
- Evidence is tied to concrete `analysis_id` / `dag_run_id` values.
- No new heavy PGT-A run was submitted during report preparation.
