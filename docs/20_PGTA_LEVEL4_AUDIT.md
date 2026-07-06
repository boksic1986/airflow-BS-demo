# 20 PGT-A Level 4 baseline_qc 审计记录

## Summary

2026-07-06 在 `ssh fengxian` 对 `/home/jiucheng/pipelines/PGT_A` 做了只读审计。结论是：PGT-A 真实流程已经支持 `baseline_qc` target，但它不是轻量单样本 smoke，而是 `build_ref` 模式下的 staged real workflow，会触发 mapping、metadata 和 baseline BAM uniformity QC。

本轮没有运行真实 `baseline_qc`，只把目标、约束和产物接入 airflow-demo。

## Findings

- `Snakefile` 中 `AVAILABLE_TARGETS` 包含 `baseline_qc`。
- `baseline_qc` 属于 `pipeline.mode=build_ref`，不能与 `cnv/cnv_qc` predict targets 混用。
- `Snakefile` 明确要求至少 2 个 baseline/reference samples。
- `baseline_qc` 目标产物：
  - `qc/baseline/baseline_qc_summary.tsv`
  - `qc/baseline/baseline_qc_pass_samples.txt`
  - `qc/baseline/baseline_qc_report.md`
- `rules/qc_workflow.smk` 的 baseline QC 会调用：
  - `scripts/bam_uniformity_qc.py`
  - `scripts/aggregate_baseline_qc.py`
- `aggregate_baseline_qc.py` 的 summary TSV 稳定字段包括 `sample_id`、`qc_decision`、`mapped_fragments`、`zero_bin_fraction`、`bin_cv`、`pearson_r`、`median_abs_z`、`gc_signal_slope`。

## Implemented Contract

- API/后端允许 `target=baseline_qc`，但创建和 submit 都要求至少 2 个 selected samples。
- `bio_pgta` 为 baseline QC 生成 run-local config：
  - `pipeline.mode=build_ref`
  - `pipeline.targets=["mapping","metadata","baseline_qc"]`
  - `build_reference.groups.demo=<selected sample ids>`
- `bio_pgta` 仍使用 `--cores 1`，不使用 qsub，不运行 CNV、reference 或 reference_qc。
- artifacts API 动态发现 baseline summary/pass/report。
- 显式 `sync-airflow` 到 success 后，backend 将 baseline summary 导入 `qc_metric`，复用前端 QC panel。

## Safety Notes

- 不修改 `/home/jiucheng/pipelines/PGT_A`。
- 不写回 `/data/project/CNV/PGT-A/rawdata`。
- Level 4 真实运行前必须由用户确认样本和运行窗口。
- 如果 `baseline_qc` 执行时间或资源超出 demo 预期，应停止并保留 stdout/stderr/error_summary，不重试重任务。
