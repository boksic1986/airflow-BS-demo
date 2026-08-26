# 08 Snakemake + qsub 接入设计

> **WGS 说明：** 顶部 T133/WGS 4.1.0 logger overlay 是历史候选。当前固定的
> WGS 4.1.1 Master 镜像已经包含 `rule-status` logger；Airflow T141 已完成
> disabled-mode JSONL bridge，真实运行验收仍被 T140 门禁阻塞。当前合同以
> [`25_WGS_4_1_1_AIRFLOW_INTEGRATION_PLAN.md`](25_WGS_4_1_1_AIRFLOW_INTEGRATION_PLAN.md)
> 为准，以下旧插件名称和事件路径不得当成当前功能。

## T141 WGS 4.1.1 CCE Rule logger contract

固定 Master RepoDigest `sha256:815d70a6...`内实际运行 Snakemake
`9.24.0+biosan1`，并已安装 `snakemake_logger_plugin_rule_status`。正式
`cloud_wgs_all`命令增加 `--logger rule-status`，输出到：

```text
<run_root>/evidence/<run_id>/rule-status/raw/*.jsonl
```

插件不发 HTTP，不改变 Rules、Worker images 或原有 `analysis.log`。事件使用
schema `1`，`attempt`形如 `attempt-1`；observer 将其规范化为数据库 attempt 1，
同时继续校验 `run_label`、role 和 stream ID。

node200 不直接挂载 `/workspace` SFS。Airflow Step3 每约五秒通过 kubectl 从运行中
Master 增量读取各 JSONL，只复制完整换行并为每个 stream 保存 byte offset。Master
退出后创建一个仅只读挂载 workspace PVC 的一次性 reader Job补最终增量，完成后
删除。reader 不入库、不展示，Worker Pod 仍不持续监控。bridge 重启按 cursor
续读；同步失败只产生 monitoring degraded，缺失终态事件按
`unknown_interrupted`处理。

## T133 WGS 4.1.0 CCE Rule logger implementation

The Airflow-owned WGS snapshot includes the independent package
`snakemake-logger-plugin-biosan-jsonl` version 1.0.0. It has no HTTP client,
FastAPI URL, token, callback, or Worker dependency. It declares
`writes_to_stream=False` and `writes_to_file=True`, so Snakemake's standard
stream handler and the existing `analysis.log` remain in place while the
plugin appends:

```text
<run_root>/evidence/<run_id>/rule-events.jsonl
```

Only the formal CCE `cloud_wgs_all` invocation receives
`--logger biosan-jsonl` plus `analysis_id`, `run_id`, `attempt`, snapshot ID and
events path settings. Unlock, cloud preflight, final dry-run, local, and SGE do
not enable the plugin. The `rule-event.v1` record includes deterministic
`event_id`, monotonic `sequence`, batch identity, Rule instance/name, job/retry,
wildcards, sample/family, status, message and log paths. `job_info`,
`job_started`, `job_finished`, `job_error`, and `group_error` map to the common
Rule state model.

Write failure is non-fatal to WGS: the plugin writes a diagnostic to stderr,
atomically creates `LOGGER_DEGRADED.json` when possible, and never raises into
Snakemake. The observer then reports `monitoring_health=degraded`; missing
terminal Rule events are not converted to success.

The node 200 evidence bridge incrementally copies complete newline-delimited
records by byte offset into `rule-status/raw/master.jsonl`. Restart resumes at
the local mirror size and observer deduplication uses `event_id`. Kubernetes
projection accepts only the batch Master Job/Pod; Worker Pods are neither
persisted nor shown. CCE never calls the BS10610 API.

The approved immutable r2 Master base already contains Snakemake
`9.24.0+biosan1`, Kubernetes Executor `0.6.4+biosan3`, cce-pipeline `0.2.0`,
and the three lifecycle scripts. The production overlay does not reinstall
cce-pipeline or replace cleanup/reset; it adds only the logger plugin and a
logger-aware Master runner based on the current dynamic-path, attempt and
state-machine implementation. Only formal analysis receives logger args. The
pushed overlay is pinned at RepoDigest `sha256:5d1d977fb21e541582230f31540cc8cd4f7a183e417b41e508162060cfcdf211`.

`wgs-cloud-delivery` is not part of this Master logger overlay. It remains the
separate Worker image for `cloud_stage_cram`, `cloud_package_results` and
`cloud_finalize_delivery`, and needs neither cce-pipeline nor biosan-jsonl.

## Historical T133 WGS 4.0.1 monitoring design (superseded)

WGS CCE 监控采用两条独立证据链，当前仍是待实现设计：

- Rule：在 Master 的 `cloud_wgs_all` Snakemake 命令中安装并启用 `airflow-demo` logger，只向 SFS `evidence/<run_id>/rule-status/raw/master.jsonl` 追加 `job_info/job_started/job_finished/job_error`；CCE 不回调 FastAPI。
- Master：BS10610 宿主机 `wgs-cce-monitor` 只查询当前批次唯一的 Master Job/Pod，并保存 phase、reason、exit code、OOM、image、node 和心跳。
- 入库：无 kubeconfig 的 Compose `wgs-observer` 按 byte/line cursor 和 event ID 幂等消费本地 spool，写 biodemo；前端约五秒轮询。

logger 不安装到每个 Worker Pod，也不负责 Kubernetes phase、OOMKilled、ImagePullBackOff 或 exit code。平台不常驻监控 Worker Pod；Worker 失败和重试由 Snakemake 汇总为 Rule 事件，管理员需要深度排障时再结合 Master 日志和原生 `jobs.ndjson` 临时查询 CCE。

由于前端不展示 Worker Pod，当前不需要扩展 `jobs.ndjson`，也不建立 Rule→Worker Pod 一一映射。Master 状态与 Rule 列表均按 `analysis_id + attempt` 归属同一批次即可。

当前 `run_cce_master_job.sh` 尚未加入 `--logger airflow-demo`，Master 镜像也尚未安装该 logger plugin；旧 `wgs_evidence_bridge.py` 仍对常驻 Deployment 执行 `kubectl exec`，不适用于 4.0.1 batch Master Job。这三项均是 T133 实现前置，不得写成已完成。

## T127 WGS host Snakemake 9 integration

WGS uses the host environment at
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/envs/wgs-snakemake9`
with Snakemake 9.23.1 and Python 3.12. Rule tools continue to come from the
approved WGS environment script; Airflow does not containerize the WGS
analysis software.

The host command uses `--executor local --cores 96 --rerun-incomplete
--keep-going --printshellcmds --show-failed-logs --logger airflow-demo` and
never uses `--forceall`. One family validation uses three pre-calling samples;
the additional downstream cohort rows are linked as read-only historical
pre-calling context from exact approved roots. Logger events and resource
samples are written below the run workdir and posted to FastAPI when available.

T127 final acceptance is `WGS_20260715_062217_351C76`, an Airflow-managed
pre-calling dry-run with 21 planned jobs. The logger marks planned jobs
terminal `skipped` with `dry_run_planned` metadata; it does not report them as
running or executed. The run completed success in 12 seconds and produced no
WGS biological output. Rule phase reporting treats the top-level `all` target
as Pre-calling for pre-calling runs and QC for full graph validation.

## T114 terminal events and output integrity

The first project-level terminal event records immutable pipeline completion:
PGT-A predict uses `cnv_predict=success`, and NIPT full analysis uses parent
`all=success`. Event replay and retry remain idempotent and cannot move the
completion time forward.

Collect tasks validate sample-set integrity rather than trusting a zero exit
code alone. PGT-A compares the selected manifest with prediction statuses and
statistics outputs. NIPT compares the selected manifest with mappingQC,
model-prediction rows, and per-sample CNV statistics/aberration outputs.

## T113 NIPT Snakemake 9 logger integration

The NIPT derivative image invokes Snakemake with `--cores 40 --keep-going
--rerun-incomplete --printshellcmds --show-failed-logs --logger airflow-demo`.
It never uses `--forceall`. The plugin writes one JSONL lifecycle stream with
rule, sample/wildcards, job ID, timestamps, status, and log paths.

The Airflow worker tails this file while the container runs, posts events to
`/api/events/snakemake`, and writes concise phase/rule/sample lines to the
Airflow task log. Backend failures do not fail analysis; JSONL remains the
authoritative fallback and terminal sync imports it idempotently. Resume uses
the same workdir and appends attempt logs so completed outputs and prior logs
remain available.

## T111 run-local config override contract

Editable configuration is a run-local Snakemake YAML subset, not a shell or
executor profile. The backend records `snakemake.user.yaml` and its hash; the
runner verifies that hash and the approved runtime-profile hash before merging
schema-listed paths. Protected samples, workdirs, references, software paths,
targets, databases, and container settings remain generated by the platform.

The resulting `snakemake.resolved.yaml` is immutable audit evidence. Changing
parameters requires a new run; resume and stage rerun reuse the original run
configuration and continue to avoid `--forceall`.

The PGT-A profile controls Snakemake, Python, samtools, fastp, BWA,
WisecondorX, reference, and pipeline-root paths. The NIPT profile controls its
pipeline root and approved images. Airflow validates those resources before
prepare, while `config_provenance.json` keeps a hidden runtime snapshot.

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

T040 v1 已实现最小 WES mock workflow：`pipelines/wes/workflow/Snakefile` 使用 tiny text input，生成 mock clean reads、BAM、markdup BAM 和 `reports/final_summary.tsv`。T060 v1 让 `final_summary` 同时生成 `reports/qc_summary.tsv`，用于 demo QC 入库和前端展示。每个 rule 都有 input/output/log，rule stdout/stderr 写到 `workdir/logs/rules/<rule>/...`。后续真实 WES 再补 bqsr、haplotypecaller、mosdepth、annovar、multiqc。

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
  ${AIRFLOW_DEMO_QSUB_PYTHON:-python} \
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
  ${{AIRFLOW_DEMO_QSUB_PYTHON:-python}}
  pipelines/common/qsub_submit.py

default-resources:
  - mem_mb=512
  - runtime=10
```

T042 v1 profile 已放在 `profiles/qsub/config.yaml`。当前 `fengxian` 的 Snakemake 8.5.4 和 9.23.1 都未安装 `snakemake-executor-plugin-cluster-generic`，因此宿主机 `--profile profiles/qsub` 会在 executor 选择阶段失败；T042 v2 通过仓库自带 `snakemake-runner` 容器补齐 `snakemake==9.23.1` 和 `snakemake-executor-plugin-cluster-generic==1.0.9`，不修改 `/biosoftware/miniconda/envs/*`。

`snakemake-runner` 只用于 run-only profile smoke，不暴露宿主机端口；`.:/app:ro` 挂载仓库代码，`./shared:/data/airflow-demo` 写 run 输出，`/app/.snakemake` 使用 writable tmpfs。真实 qsub 仍默认关闭，wrapper 只允许 `AIRFLOW_DEMO_QSUB_MODE=mock`。注意 profile 里的 shell 参数展开必须写成 `${{AIRFLOW_DEMO_QSUB_PYTHON:-python}}`，因为 Snakemake 会先格式化 cluster submit command。

T031 adds a separate Airflow runtime path for the same WES mock profile: `bio_wes_qsub` runs Snakemake directly inside `airflow-demo/airflow:0.1.0`, using read-only mounts `/opt/airflow/pipelines` and `/opt/airflow/profiles`. It does not mount the Docker socket and does not call the standalone `snakemake-runner` service during the DAG. Because Airflow runs as the deploy user's uid on `fengxian`, the DAG sets `XDG_CACHE_HOME=<workdir>/tmp/xdg-cache` before launching Snakemake, avoiding writes to `/home/airflow/.cache`.

2026-07-05 `fengxian` Airflow smoke: `bio_wes_qsub` run `manual__WES_AIRFLOW_20260705_004506` finished `success`, produced `reports/final_summary.tsv`, 14 qsub stdout/stderr files, and 14 JSONL events with `qsub_submitted` / `qsub_success`. Real `qsub/qstat` was not called.

T060/T054 extends the same mock workflow with deterministic QC rows:

```text
workdir/reports/qc_summary.tsv
```

Columns are fixed as `sample_id,metric_name,metric_value,metric_numeric,threshold,status`. Current mock metrics are `workflow_status`, `mock_mean_depth`, and `mock_pct_20x` for each `S001/S002`, all with `status=pass`. Backend `sync-airflow` imports this TSV into `qc_metric` only after `bio_wes_qsub` reaches `success`; GET endpoints remain read-only.

T044/T056 extends the same path with backend/frontend `resume` and `rerun_rule`. `run_wes_qsub` writes the exact command to:

```text
workdir/logs/snakemake.command.txt
```

This file is a dynamic artifact and is used to verify `rerun_rule` contains `--forcerun <rule>` and never defaults to `--forceall`.

2026-07-04 official mirror smoke：`WES_20260704_180650_MOCK` 通过 direct mock wrapper 向 backend POST 事件，`/api/runs/WES_20260704_180650_MOCK/rules` 返回 `bwa_mem/S001=success`，并带有 `MOCK-WES_20260704_180650_MOCK-12-bwa_mem-S001`、stdout/stderr path 和 `return_code=0`。

## 7. 日志路径规范

```text
workdir/logs/snakemake.stdout.log
workdir/logs/snakemake.stderr.log
workdir/logs/snakemake.command.txt
workdir/logs/qsub/<rule>.<sample>.o
workdir/logs/qsub/<rule>.<sample>.e
workdir/logs/rules/<rule>/<sample>.stdout.log
workdir/logs/rules/<rule>/<sample>.stderr.log
workdir/reports/qc_summary.tsv
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

### T102 runner progress events

T102 adds `dags/common/progress_events.py` for PGT-A and NIPT Docker runner progress. This helper is independent from the older Snakemake 9 logger plugin and can be used by direct Python runners.

### T112 PGT-A Snakemake 9 predict release

Sample-free source is versioned in `pipelines/pgta_s9` and deployed as immutable
releases under `/home/jiucheng/pipelines/PGT_A_S9/releases/<revision>` with a
`current` symlink and SHA256 manifest. The original PGT-A directory is not
modified. The approved profile uses Snakemake 9.23.1 and fixed hg19 XX, XY, and
gender references.

The logger maps Snakemake 9 `job_info` to `running`, caches job context for
terminal events, and captures rule/sample/job ID plus rule log paths when
provided. CNV QC failure writes `skipped_qc` for prediction and remains distinct
from workflow failure.

The approved predict runtime prepends the directory of the profile-owned
`rscript_bin` to `PATH`, locks the CBS seed to `42`, and checks that
`<sample>_statistics.txt` is non-empty after WisecondorX predict. This output
check is required because the deployed WisecondorX release can log an R failure
while returning process exit code zero.

Contract:

- Write every event to `workdir/logs/events/snakemake_events.jsonl`.
- If `backend_event_url` is configured, POST rule events to `POST /api/events/snakemake`.
- Backend POST failure never fails the workflow; append a local `backend_post_error` JSONL record instead.
- Events with `rule` and `status` are importable into biodemo `snakemake_rule_event`.
- `sync-airflow` imports the JSONL fallback when a run reaches `success` or `failed`, using the same idempotent upsert key as the live event API.

Parser coverage:

```text
rule <name>:
jobid: <id>
wildcards: sample=S1, ...
Finished jobid: <id>
Error in rule <name>:
```

PGT-A behavior:

- `run_pgta_target` emits a target-level rule event such as `metadata` or `baseline_qc`.
- Captured Snakemake stdout/stderr is parsed for additional rule blocks.
- Existing resume/preflight behavior stays unchanged: `--rerun-incomplete` is used and `--forceall` remains forbidden.

NIPT Docker behavior:

- `mount_smoke` emits `nipt_mount_smoke` `running/success/failed`.
- `full_run` parses Docker stdout/stderr for Snakemake rule blocks when the heavy path is explicitly enabled.
- The runner must not run `docker compose down -v`, `docker volume prune`, or `docker system prune`.

## 10. 重分析策略

### resume

```bash
snakemake --rerun-incomplete --configfile config.yaml
```

For `bio_wes_qsub` v1, `resume` reuses the same workdir and does not add any force flag. The qsub profile already has `rerun-incomplete: true`.

### rerun selected rule

```bash
snakemake --forcerun <rule> --configfile config.yaml <target>
```

For WES mock v1, allowed rules are `fastp`, `bwa_mem`, `markdup`, and `final_summary`. Sample-level rules are limited to `S001/S002`; `final_summary` is project-level. The final T044 smoke run `WES_20260705_162041_2507AF` wrote a command containing:

```text
--forcerun fastp /data/airflow-demo/runs/WES_20260705_162041_2507AF/fastp/S001.clean.txt
```

and no `--forceall`.

### T112 PGT-A S9 release integrity and service events

The approved runtime profile pins the release directory, `SHA256SUMS` path, and
the SHA256 of that manifest. DAG validation verifies both the manifest and every
listed release file before Snakemake starts. An in-place release modification
therefore fails explicitly instead of running under an unchanged profile ID.

Logger and fallback progress-event POSTs include `X-Airflow-Demo-Token` from the
worker environment. POST failure still writes `backend_post_error` to JSONL and
does not hide the original workflow result.

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
4. `snakemake-runner` 容器内 cluster-generic executor plugin 可用后，已验证 `--profile profiles/qsub` 真正驱动 wrapper。

2026-07-04 `fengxian` runtime 证据：`airflow-demo/snakemake-runner:0.1.0` 构建成功，`snakemake --version` 返回 `9.23.1`，`cluster-generic` executor 可见；`WES_PROFILE_20260704_230713` 通过 `--profile profiles/qsub` 完成 8 个 WES mock jobs，生成 `reports/final_summary.tsv`、`logs/qsub/*.o/e` 和 14 行 `logs/events/snakemake_events.jsonl`。
5. `reports/qc_summary.tsv` 能在 `sync-airflow` 后导入 `qc_metric`，前端 QC panel 能看到 pass summary 和样本级指标。
6. 故意让一个 rule 失败，前端能看到 stderr。
7. 修复后 resume，只执行失败/incomplete 目标。
## WGS-only Phase 1 boundary

No WGS Snakemake logger or executor is changed because the workflow is not final. Phase 2 must pin one logger contract across CCE, SGE, and local and preserve resume/rerun-failed without `--forceall`.

## T130 server-copy Rule evidence contract

Airflow integration code is developed only in the BS10610 copy at
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs`.
The upstream `/mnt/biodevrwbi/33.chenjiucheng/project/wgs` tree remains
unchanged. The development copy emits schema-version-1 newline-delimited Rule
events under `rule-status/raw/*.jsonl`.

The platform observer no longer infers runs from an `analysis.json` file. A
platform-owned binding must provide `analysis_id`, positive `attempt`, approved
`pipeline_snapshot_id`, `run_label`, and a relative evidence path. That binding
must match both the immutable snapshot pinned in `analysis_run.params_json` and
the corresponding `run_attempt` row.

The observer consumes only complete newline-terminated UTF-8 JSON objects and
persists one byte/line cursor per file in biodemo. Raw events, Rule projection,
and the advanced cursor commit atomically. A partial trailing line waits for a
later poll; malformed complete JSON stops only that file at the bad record;
replacement or truncation resets the cursor and replays through deterministic
event IDs. Supported events are `rule_planned`, `job_info`, `job_started`,
`job_finished`, and `job_error`. Worker terminal evidence takes precedence
over conflicting Master terminal evidence.

CCE evidence additionally consumes the real `group_evidence.py` files
`pod-events.jsonl`, `pod-metrics.jsonl`, and `job-events.jsonl`. Pod state is
keyed by `pod_hash`; Kubernetes `resource_version` is compared numerically so
version 10 supersedes version 9, while a later metrics record enriches resources
without regressing phase. Container state preserves terminal details such as
`OOMKilled` with exit code 137 and waiting details such as
`ImagePullBackOff`. Job conditions enrich the matching Pod rows with status and
failure message.
# T131: Real WGS Rules remain deferred. Timing is calculated from observer
# `rule_state`; final logger arguments and CCE launch are Phase 2 adapters.
