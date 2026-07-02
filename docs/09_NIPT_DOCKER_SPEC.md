# 09 NIPT Docker 版本接入设计

## 1. 目标

把 NIPT Docker 版本作为独立 pipeline 接入 Airflow demo，展示 Docker 化流程与 qsub 流程的差异。

## 2. 运行模型

```text
Airflow bio_nipt_docker DAG
  -> validate_request
  -> prepare_workdir
  -> generate config
  -> docker run nipt-pipeline:demo
  -> collect QC
  -> register artifacts
  -> notify
```

## 3. Volume contract

```text
host shared root -> container /data/airflow-demo
input fq dir -> container /input:ro
reference root -> container /refs:ro
```

## 4. Docker command 模板

```bash
docker run --rm \
  --name "nipt_${analysis_id}" \
  -v "${SHARED_ROOT}:/data/airflow-demo" \
  -v "${INPUT_DIR}:/input:ro" \
  -v "${REF_ROOT}:/refs:ro" \
  -e ANALYSIS_ID="${analysis_id}" \
  -e BACKEND_EVENT_URL="${BACKEND_EVENT_URL}" \
  nipt-pipeline:demo \
  run_NIPTPro.py \
    --fq_dir /input \
    --out_dir "/data/airflow-demo/runs/${analysis_id}/results" \
    --config "/data/airflow-demo/runs/${analysis_id}/config/config.yaml"
```

## 5. 安全提醒

- demo 阶段可以用 Docker socket，但只限受控服务器。
- 不要把 docker socket 暴露给公网服务。
- Docker runner 不得删除宿主机路径。
- 容器输出必须限制在 workdir。

## 6. QC 输出 contract

NIPT Docker 至少输出：

```text
results/qc/nipt_qc_summary.tsv
reports/multiqc_report.html optional
logs/nipt_docker.stdout.log
logs/nipt_docker.stderr.log
```

`nipt_qc_summary.tsv` 建议列：

```text
sample_id	total_reads	mapped_reads	mapping_rate	fetal_fraction	chr13_z	chr18_z	chr21_z	qc_status
```

## 7. 前端展示

NIPT Docker run detail 与 qsub 版保持一致，但 Snakemake tab 可显示：

- Docker step 状态。
- 内部 pipeline stage 状态，如果容器能产出事件。
- stdout/stderr。
- QC 指标。

## 8. 验收

- mock Docker image 能启动。
- 输入 mock FASTQ 或 mock sample sheet 后生成 QC TSV。
- Airflow DAG 能捕获非零退出码。
- 失败时能看到 stderr。
- 成功后邮件包含 QC summary。
