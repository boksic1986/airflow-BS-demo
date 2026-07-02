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
  bqsr
  haplotypecaller
  mosdepth
  annovar
  multiqc
  final_summary
```

Demo 可以先用 mock command 生成小文件，后续替换成真实命令。

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
jobs: 20
latency-wait: 60
rerun-incomplete: true
printshellcmds: true
keep-going: false

cluster-generic-submit-cmd: >-
  python pipelines/common/qsub_submit.py

default-resources:
  - mem_mb=4000
  - runtime=120
```

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
  --logger-airflow-demo-events-path <workdir>/logs/events/snakemake_events.jsonl
```

第一版只写 JSONL，不 POST backend。`backend_event_url` 和 `post_timeout_seconds` 保留为 T026/T043 后续接入钩子。

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
timestamp
```

Airflow 后置 task 会把 JSONL 汇总成 `snakemake_rule_summary.tsv` 并写入 task log/XCom。

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
3. mock qsub 模式下能写 rule_event。
4. 故意让一个 rule 失败，前端能看到 stderr。
5. 修复后 resume，只执行失败/incomplete 目标。
