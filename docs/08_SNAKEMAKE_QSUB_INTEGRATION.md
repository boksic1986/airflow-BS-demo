# 08 Snakemake + qsub 接入设计

## 1. 设计目标

- 保留已有 WES/NIPT 生产脚本的核心逻辑。
- 用 Snakemake 包装成 rule/file dependency。
- 用 qsub profile 并行提交计算任务。
- 把 rule/job 状态、qsub job id、stdout、stderr 回传 backend。
- 支持 resume 和局部重跑。

## 2. WES mock rule 设计

```text
all
  fastp
  bwa_mem
  markdup
  final_summary
```

T040 v1 已实现最小 WES mock workflow：`pipelines/wes/workflow/Snakefile` 使用 tiny text input，生成 mock clean reads、BAM、markdup BAM 和 `reports/final_summary.tsv`。每个 rule 都有 input/output/log，rule stdout/stderr 写到 `workdir/logs/rules/<rule>/...`。后续真实 WES 再补 bqsr、haplotypecaller、mosdepth、annovar、multiqc。

## 3. NIPT qsub rule 设计

如果现有 NIPT 已经有 Snakemake：

```text
Airflow -> existing runner one-shot -> existing Snakefile
```

如果现有 NIPT 是脚本/qsub 混合：

```text
all
  prepare_input
  map_reads
  count_bins
  gc_correct
  zscore
  plot_cnv
  final_summary
```

## 4. qsub wrapper contract

`pipelines/common/qsub_submit.py` 输入：Snakemake jobscript。

职责：

1. 解析 job properties。
2. 读取 `analysis_id`、rule、wildcards、threads、resources。
3. 生成 stdout/stderr 路径。
4. 组装 qsub 命令。
5. 提交任务。
6. 解析 qsub job id。
7. POST backend event：`submitted`。
8. 返回 job id。

T041 v1 默认只支持 mock 模式：

```bash
AIRFLOW_DEMO_QSUB_MODE=mock \
  /biosoftware/miniconda/envs/snakemake_env/bin/python \
  pipelines/common/qsub_submit.py <snakemake-jobscript>
```

mock 模式不调用真实 qsub，会同步执行 jobscript，生成稳定 fake job id（如 `MOCK-WES_20260704_DIRECT-12-bwa_mem-S001`），写 `logs/qsub/<rule>.<sample>.o/e`，并写 submitted/final status 事件。`AIRFLOW_DEMO_BACKEND_EVENT_URL` 非空时会 POST FastAPI；不论 POST 是否成功都会写 JSONL fallback。

Event 示例：

```json
{
  "analysis_id": "WES_20260702_000001",
  "event": "qsub_submitted",
  "rule": "bwa_mem",
  "sample_id": "S001",
  "snakemake_jobid": "12",
  "qsub_jobid": "123456",
  "status": "submitted",
  "stdout_path": "/data/.../bwa_mem.S001.o",
  "stderr_path": "/data/.../bwa_mem.S001.e"
}
```

## 5. qsub 命令模板

SGE/UGE 示例：

```bash
qsub \
  -N "ad_<analysis_id>_<rule>_<sample>" \
  -q "${QSUB_QUEUE}" \
  -pe smp "${threads}" \
  -l h_vmem="${mem_mb}M" \
  -o "${stdout_path}" \
  -e "${stderr_path}" \
  "${jobscript}"
```

实际参数必须由 `SERVER_INFO.md` 和服务器 qsub 类型确认。

## 6. Snakemake profile 示例

```yaml
executor: cluster-generic
jobs: 2
latency-wait: 30
rerun-incomplete: true
printshellcmds: true
keep-going: false

cluster-generic-submit-cmd: >-
  AIRFLOW_DEMO_QSUB_MODE=mock
  /biosoftware/miniconda/envs/snakemake_env/bin/python
  pipelines/common/qsub_submit.py

default-resources:
  - mem_mb=512
  - runtime=10
```

T042 v1 profile 已放在 `profiles/qsub/config.yaml`。当前 `fengxian` 的 Snakemake 8.5.4 和 9.23.1 都未安装 `snakemake-executor-plugin-cluster-generic`，因此 `--profile profiles/qsub` 会在 executor 选择阶段失败；在安装/镜像化该 executor plugin 前，远端验收使用 Snakemake dry-run + direct mock wrapper smoke。

## 7. 日志路径规范

```text
workdir/logs/snakemake.stdout.log
workdir/logs/snakemake.stderr.log
workdir/logs/qsub/<rule>.<sample>.o
workdir/logs/qsub/<rule>.<sample>.e
workdir/logs/rules/<rule>/<sample>.stdout.log
workdir/logs/rules/<rule>/<sample>.stderr.log
```

## 8. Rule 事件状态

```text
planned: dry-run 中发现
submitted: qsub 提交成功
running: 可选，由 qstat 轮询或 wrapper 更新
success: job 完成且输出文件存在
failed: job 返回非零或缺失输出
skipped: Snakemake 判断已有输出无需执行
```

## 9. Backend 不可用时的 fallback

qsub wrapper/event logger 如果 POST backend 失败，必须写 JSONL：

```text
workdir/logs/events/snakemake_events.jsonl
```

后续 `collect_qc` 或 recovery task 可以补导入。

### PGT-A Snakemake 9 logger plugin

PGT-A Airflow-only DAG 使用仓库内 Python 包 `snakemake_logger_plugin_airflow_demo`，通过 `PYTHONPATH=/opt/airflow/dags` 暴露给 Snakemake 9，不安装进 `/biosoftware/miniconda/envs/snakemake9_env`，也不修改 PGT-A 流程目录。

CLI 约定：

```bash
snakemake --logger airflow-demo \
  --logger-airflow-demo-analysis-id <analysis_id> \
  --logger-airflow-demo-workdir <workdir> \
  --logger-airflow-demo-events-path <workdir>/logs/events/snakemake_events.jsonl \
  --logger-airflow-demo-backend-event-url http://backend:8000/api/events/snakemake
```

T026/T043 后，logger 默认仍强制写 JSONL；当 `backend_event_url` 非空时，会把 rule/job 级事件 POST 到 FastAPI `/api/events/snakemake`。backend POST 失败不影响 Snakemake 运行，失败信息会追加为本地 JSONL `backend_post_error` 事件。

为了适配 Snakemake 9 部分 `job_finished/job_error` 事件缺少 rule 字段的情况，logger 会缓存 `jobid -> rule/sample/wildcards` 上下文，并用前序 `job_info` 补齐后续 job 事件，再 POST backend。

JSONL 事件字段：

```text
analysis_id
event
status
rule
sample_id
wildcards
snakemake_jobid
qsub_jobid
stdout_path
stderr_path
message
return_code
timestamp
```

Airflow 后置 task 会把 JSONL 汇总成 `snakemake_rule_summary.tsv` 并写入 task log/XCom。workflow/progress/generic log 可保留在 JSONL 中；第一版 backend 只接收 `rule` 非空的 rule/job 事件。

## 10. 重分析策略

### resume

```bash
snakemake --rerun-incomplete --configfile config.yaml
```

### rerun selected rule

```bash
snakemake --forcerun <rule> --configfile config.yaml <target>
```

### rerun selected target

```bash
snakemake --configfile config.yaml path/to/target.file
```

禁止默认：

```bash
snakemake --forceall
```

## 11. 验收场景

1. mock WES 两个样本 dry-run 通过。
2. qsub wrapper 能生成 job name 和日志路径。
3. mock qsub 模式下能写 `snakemake_events.jsonl`，并在 backend run 存在时写入 `snakemake_rule_event`。
4. cluster-generic executor plugin 安装后，再验证 `--profile profiles/qsub` 真正驱动 wrapper。
5. 故意让一个 rule 失败，前端能看到 stderr。
6. 修复后 resume，只执行失败/incomplete 目标。
