# 07 Airflow DAG 设计

## T145 Step3 observer lifecycle

`start_step3_monitor`只在 node200 接受后激活 observer。`wait_step3_analysis`看到终态
后请求 draining；`release_leases`也始终执行最终 drain，覆盖失败、取消和
上游 skip。Step1/Step5 sensor 各自只同步当前 transfer 的精确路径。

## T144 Step4 maintenance mode

唯一`bio_wgs`仍为18 tasks、manual、paused。`maintenance_mode=repair_step4`复用
同一 DAG和同一 analysis attempt：Step1-Step3只做无副作用跳过，Step4执行固定
`step4_repair_cram`；原 DagRun已失败时继续普通Step4核验、Step5、Step6和
finalize，原 DagRun仍等待时由原 DagRun继续。浏览器不能提供 group、路径或确认
串。执行门禁关闭时后端在触发 DagRun前返回409。T7扫描属于 observer，不新增
扫描 DAG。完整设计见[文档 26](26_WGS_T7_INTAKE_STEP4_REPAIR.md)。

## T142 当前单一 DAG 合同（历史基线）

`bio_wgs`保持版本无关、18 tasks、manual schedule、`max_active_runs=4`和
`is_paused_upon_creation=true`。`validate_request`要求后端绑定的
`pipeline_release_id`、`wgs_version`和`wgs_source_commit`，但客户端不能提交这些
字段。prepare 使用 request v3 调用 node200 固定 WGS 仓库；其余 Step1-Step6
只执行冻结 bundle。DAG 不包含 snapshot path、cce-pipeline version gate、
FASTQ MD5、上传后 FASTQ verify、local/SGE 或 Worker Pod task。六个长等待仍为
五秒 `reschedule` sensor。

> **WGS 说明：** BS10610 当前只加载 WGS 4.1.1 的 18-task `bio_wgs`，且保持
> paused。现行 task graph 与 Step1-Step6 合同见
> [`25_WGS_4_1_1_AIRFLOW_INTEGRATION_PLAN.md`](25_WGS_4_1_1_AIRFLOW_INTEGRATION_PLAN.md)
>；以下 T133/WGS 4.1.0 graph 仅为历史记录。

当前 Step3 worker 每约五秒同时执行两项工作：调用 WGS
`Step3_status.sh --output json`取得唯一 Master Job/Pod 状态，并通过 node200
kubectl 从 Master 的 SFS `rule-status/raw/*.jsonl`按文件 offset 拉取完整行。
Master 退出后使用一次性、workspace PVC 只读的 reader Job补齐末尾事件；reader
和 Worker Pod 都不进入 `/pods`或前端。证据同步失败只标记 monitoring degraded，
不改变 WGS 退出码。

## T133 WGS 4.1.0 current implementation (2026-08-24)

The WGS-only release now publishes exactly one DAG, `bio_wgs`. It accepts only
`pipeline=wgs` and `execution_mode=cce`, has `max_active_runs=4`, and is paused
on creation. Compose mounts only `dags/bio_wgs.py`; the legacy files
`bio_wgs_cce.py`, `bio_wgs_onprem.py`, and `bio_wgs_intake_scan.py` were removed
from this candidate. No Airflow metadata cleanup or production Compose recreate
has been performed yet.

```text
validate_request
→ prepare_wgs_batch
→ input_transfer.acquire_obs_transfer_slot
→ input_transfer.start_input_upload
→ input_transfer.wait_input_upload                 # reschedule
→ validate_cce_bundle
→ submit_master
→ wait_analysis_and_rules                          # reschedule
→ wait_result_publish                              # reschedule
→ result_transfer.acquire_obs_transfer_slot
→ result_transfer.start_result_download
→ result_transfer.wait_result_download             # reschedule
→ materialize_results
→ finalize_run
→ release_leases                                   # all_done
```

There is no FASTQ MD5 task, upload verification task, database Master slot, or
Worker Pod reconciliation task. `wgs_cce_runs` limits project concurrency to
four and `wgs_obs_transfer` serializes private-line transfer. Long waits use
reschedule sensors. The restricted SSH connection is `wgs_runner_200`; node
200 is the single operator boundary for private OBS and kubectl. Containers do
not receive OBS or kubeconfig credentials.

All execution remains gated by both `WGS_EXECUTION_ENABLED=false` and
`WGS_RUNTIME_ADAPTER_ENABLED=false`. The confirmed cce-pipeline CLI is wired by
explicit immutable revision to `prepare`, `validate`, and idempotent `run`
actions, but the real gate cannot be opened until the FASTQ source-manifest
and transfer-progress contracts described in
`24_WGS_RUNTIME_INTEGRATION_DEVELOPMENT_STATUS.md` are reconciled.

## Historical T133 WGS 4.0.1 design (superseded)

本节是 WGS 后续实现的权威目标；下方 T127、Phase 1 和 T131 内容仅保留为历史记录。当前 BS10610 仍加载以下三个 paused DAG，它们尚未删除或改名：

| 当前 DAG | 当前性质 | 后续处理 |
|---|---|---|
| `bio_wgs_cce` | 已部署的 Phase 1 mock 项目拓扑，没有真实 4.0.1 CCE 启动能力 | 重构并最终由 `bio_wgs` 取代 |
| `bio_wgs_onprem` | local/SGE 未实现占位 | 待删除，不并入 4.0.1 CCE 发布 |
| `bio_wgs_intake_scan` | 每十分钟调用后端扫描的独立扫描器 | 扫描职责迁入 `wgs-observer` 后待删除 |

最终 Airflow 只加载一个 WGS 分析 DAG：`bio_wgs`，且只支持 `execution_mode=cce`。自动 FASTQ 扫描不再占用 Airflow DAG，由 `wgs-observer` 每十分钟调用内部扫描接口；扫描发现、幂等入库和是否提交仍受后端策略及执行开关控制。

目标项目级任务链为：

```text
bio_wgs
validate/request
→ prepare_wgs_batch（sampleinfo/config/CCE bundle）
→ upload_fastq（Step1；无独立 FASTQ MD5/上传后验证 task）
→ launch_batch_master（Step2）
→ wait_analysis_terminal（Rule + Master Job/Pod monitoring）
→ publish_results（Step4）
→ download_and_verify_results（Step5，仅结果校验）
→ materialize_results（Step6）
→ finalize_run
```

该设计固定 WGS release 4.0.1，源提交为 `6cb1255fc1b218c9b18fb931eb3b6a172afe907b`。每批创建独立 Kubernetes Master Job，不再使用固定四个 Master Deployment 或数据库 Master slot；并发以后由 Airflow pool 与 CCE 配额控制。长时间传输和分析等待继续使用 reschedule sensor。

当前本地未发布 runtime gate 仍依赖旧 Master Deployment、固定槽位以及 4.0.1 已删除的旧 Step 文件名，因此属于待替换遗留实现，不能作为 4.0.1 启动入口。`WGS_EXECUTION_ENABLED=false`、DAG pause 和真实提交禁用状态必须保持，直到后续代码实现与 mock/真实验收完成。

4.0.1 不生成 `FASTQ.MD5SUMS`。`obsutil cp -vmd5` 只属于 Step1 单次传输实现；Airflow 不设置 `start_fastq_md5`、`wait_fastq_md5` 或 `verify_input_obs`。Step2 内部检查 `FASTQ_UPLOAD_COMPLETE` 和预期 FASTQ 可见性后再创建/启动批次 Master，这个检查不展开成独立 DAG task。

监控范围固定为 Rule 优先、Master-only：Snakemake logger 提供逐 Rule 状态，Kubernetes watcher 只轮询每批唯一的 Master Job/Pod。Worker Job/Pod 和原生 `jobs.ndjson` 仅供管理员按需排障，不持续入库、不展示在前端，也不建立 Rule→Worker Pod 映射。

## T127 BS10610 shared deployed DAG scope

The shared NIPT/WGS deployment uses `CeleryExecutor` with worker concurrency 2.
Only `bio_nipt_docker`, `bio_wgs`, and `bio_intake_scan` are loaded. PGT-A is
not deployed on BS. `bio_nipt_docker` and `bio_wgs` both use the one-slot
`bs_heavy_analysis` pool, so the two heavy workflows cannot overlap. A pool
slot limits concurrent batches, not NIPT's 32 container cores or WGS's 96 host
cores.

`bio_wgs` uses project-level tasks:

```text
validate_request -> prepare_wgs_run -> wgs_pipeline.pre_calling
  -> choose_wgs_path
     -> collect_wgs_artifacts                         # pre-calling validation
     -> wgs_pipeline.variant_analysis
        -> wgs_pipeline.collect_qc -> collect_wgs_artifacts  # full
```

Each WGS host stage is an `SSHOperator` command accepted only by the forced SSH
gate. NIPT and WGS rule/sample detail is emitted by Snakemake 9
`--logger airflow-demo`; it is not expanded into hundreds of Airflow tasks.
The scanner remains paused and neither NIPT nor WGS auto-submit is enabled.
T127 validates WGS by dry-run only. `WGS_20260715_062217_351C76` completed the
Airflow-managed pre-calling branch successfully in 12 seconds. Its 21 planned
Snakemake jobs are terminal `skipped` dry-run events and no biological rule
was executed. The earlier intentionally stopped full-path handoff record
`WGS_20260714_180953_9D7981` remains historical failed evidence and is not the
accepted dry-run.

## T119 scheduled discovery scope

`bio_intake_scan` calls the backend for both `pgta` and `nipt_docker` discovery.
This does not enable NIPT automatic submission: the NIPT pipeline config keeps
`auto_submit.enabled=false`. The NIPT scheduled root is limited to
`/opt/pipelines/NIPT/fastq/intake/BS_DEMO_20260713`; the broad manual scan root
continues to be available only from Submit Run.

The DAG remains a scanner/discovery task and does not execute NIPT full runs.
Full NIPT analyses are created and submitted manually and are serialized by
the existing one-slot `nipt_s9_full` pool.

## T113 NIPT S9 execution gate

`bio_nipt_docker` deliberately remains:

```text
validate_request -> prepare_nipt_docker_run -> run_nipt_docker -> collect_nipt_artifacts
```

It does not create one Airflow task per Snakemake job. The DAG has
`max_active_runs=1`; `run_nipt_docker` uses pool `nipt_s9_full` with one slot
and `execution_timeout=90 minutes`. Rule/sample concurrency and retry state
remain Snakemake responsibilities. The worker tails logger JSONL during Docker
execution and mirrors phase/rule/sample transitions into the Airflow task log
and backend event API.

## T111 runtime profiles and config resolution

T111 does not add or rename a DAG or task. `bio_pgta` and `bio_nipt_docker`
continue to use their existing validate, prepare, execute, and collect graph.

For profile-aware runs, validate/prepare reads the read-only
`pipeline_profiles.yaml`, checks the profile revision and requested-config
hash, then merges only schema-approved leaves into the generated pipeline
config. The prepare task writes `config/snakemake.resolved.yaml` and updates
`config/config_provenance.json`. PGT-A still executes `config.yaml` (and its
stage-derived configs); NIPT still executes `config/nipt_run_config.yaml`.

The runtime section of an approved profile may select the PGT-A executable
environment or NIPT image. Request payloads cannot supply arbitrary runtime
paths or images. `validate_request` checks the approved PGT-A executables,
reference, and Snakefile or inspects both approved NIPT images before prepare.
Existing runs without profile fields keep the historical
environment-variable behavior. Heavy-run gates, TaskGroups, resume/rerun
semantics, and the no-`--forceall` rule are unchanged.

## 1. DAG 列表

| DAG ID | Pipeline | Runner | Notes |
|---|---|---|---|
| bio_wes_qsub | WES | Snakemake + qsub | 核心 demo 优先 |
| bio_nipt_qsub | NIPT | Snakemake/wrapper + qsub | 第二阶段 |
| bio_nipt_docker | NIPT Docker | docker runner | 第二阶段 |
| bio_pgta | PGT-A | Snakemake direct in Airflow worker | v1 支持 metadata、dryrun_cnv、invalid_target failure smoke；T085/T086 后受控支持 baseline_qc staged real smoke，不使用 qsub |
| bio_pgta_airflow | PGT-A | Snakemake 9 direct in Airflow worker | Airflow-only metadata DAG，使用 repo-local logger plugin 写 JSONL 并在 Airflow log/XCom 展示状态 |

T116 deployed scope is intentionally narrower than the historical catalog.
Only `bio_pgta`, `bio_nipt_docker`, and `bio_intake_scan` are parsed in the
current deployment. `bio_pgta_airflow.py` and `bio_wes_qsub.py` remain in Git
for audit/rollback but are excluded by `.airflowignore`; their Airflow metadata
and run history were removed. Scheduled `bio_intake_scan` defaults to the
`pgta` pipeline only, while manual NIPT input scanning remains a backend/UI
operation.

## 2. 通用 DAG run conf

`POST /api/runs` 只创建 `analysis_run.status=created`，不会触发 Airflow。`POST /api/runs/{analysis_id}/actions/submit` 会读取 DB 中的 `sample_sheet_path`、`workdir` 和 `params_json`，触发 Airflow 并生成以下 DAG run conf。

```json
{
  "analysis_id": "WES_20260702_000001",
  "pipeline": "wes_qsub",
  "mode": "new",
  "sample_sheet_path": "/data/airflow-demo/runs/WES_20260702_000001/config/samples.selected.tsv",
  "workdir": "/data/airflow-demo/runs/WES_20260702_000001",
  "email_to": "demo@example.com",
  "params": {
    "genome": "hg19",
    "queue": "<QSUB_QUEUE>",
    "max_jobs": 20
  }
}
```

PGT-A v1 conf example:

```json
{
  "analysis_id": "PGTA_20260702_171533_9A85B1",
  "pipeline": "pgta",
  "mode": "new",
  "sample_sheet_path": "/data/airflow-demo/runs/PGTA_20260702_171533_9A85B1/config/samples.selected.tsv",
  "workdir": "/data/airflow-demo/runs/PGTA_20260702_171533_9A85B1",
  "backend_event_url": "http://backend:8000/api/events/snakemake",
  "email_to": null,
  "params": {
    "project_name": "PGT-A metadata smoke",
    "rawdata_root": "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28",
    "target": "metadata",
    "input_mode": "server_path_scan",
    "selected_count": 1
  }
}
```

## 3. 通用 task graph

```text
validate_request
  -> prepare_workdir
  -> validate_selected_manifest
  -> generate_pipeline_config
  -> dry_run
  -> run_pipeline
  -> collect_qc
  -> register_artifacts
  -> notify_success
```

失败路径：

```text
any failure -> extract_error_summary -> notify_failure
```

## 4. Task 说明

### validate_request

检查：

- analysis_id 存在。
- workdir 在允许路径内。
- sample_sheet_path 存在。
- pipeline/mode 合法。
- max_jobs 不超过 demo 限额。

### prepare_workdir

创建：

```text
workdir/config
workdir/logs
workdir/logs/rules
workdir/results
workdir/tmp
reports/<analysis_id>
```

### validate_selected_manifest

读取 backend 生成的 selected manifest。T022/T024 的 PGT-A v1 manifest 来自服务器路径扫描和勾选，不是上传文件。检查：

- `sample_id/R1/R2/source_dir` 列存在。
- R1/R2 路径在允许的 PGT-A 数据根目录内。
- R1/R2 文件可读。
- sample_id 在本次 run 内唯一。

必要时输出 DAG 内归一化副本：

```text
workdir/config/samples.normalized.tsv
```

### generate_pipeline_config

输出 Snakemake config：

```text
workdir/config/config.yaml
```

必须包含：

```yaml
analysis_id: ...
workdir: ...
sample_sheet: ...
input_mode: server_path_scan
backend_event_url: http://backend:8000/api/events/snakemake
max_jobs: ...
queue: ...
```

### dry_run

运行 Snakemake dry-run：

```bash
snakemake -n --printshellcmds --configfile <config>
```

失败时不进入 run_pipeline。

### run_pipeline

根据 mode 生成 flags：

| mode | Snakemake flags |
|---|---|
| new | `--rerun-incomplete` |
| resume | `--rerun-incomplete` |
| rerun_failed | `--rerun-incomplete` + backend 传入 failed targets |
| rerun_rule | `--forcerun <rule>` 或指定 target |
| clone_new | 新 workdir，等同 new |

禁止默认：

```bash
--forceall
```

### collect_qc

读取 pipeline 生成的 QC 文件，写入 DB 或调用 backend API。

### register_artifacts

登记：

- MultiQC HTML。
- Snakemake report。
- final summary TSV。
- 关键日志。

### notify_success / notify_failure

demo 可使用 MailHog。失败邮件必须包含 error summary 和 stderr path。

## 5. Airflow 实现规范

- 任务之间通过 XCom 传小 JSON，不传大文件。
- 大文件路径写入 DB 或 config。
- DAG 默认 `catchup=False`。
- DAG 不自动 schedule，使用 manual/API trigger。
- retry 策略谨慎：validate/generate 不重试，run_pipeline 可配置 0-1 次。

## 6. DAG import test

推荐测试：

```bash
python -m py_compile dags/*.py
airflow dags list
```

如果 Airflow CLI 不在宿主机，应在容器中运行：

```bash
docker compose exec airflow-scheduler airflow dags list
```

## 7. `bio_wes_qsub` v1

`bio_wes_qsub` is the first WES mock project-level DAG. T031 proved Airflow-only execution; T044/T056 adds FastAPI/frontend create, submit, resume, and selected-rule rerun for the same mock workflow. T060 adds deterministic mock QC output consumed by the backend after explicit `sync-airflow`. It still does not add email notification, NIPT, production WES data, or real qsub.

Task graph:

```text
validate_request
  -> prepare_wes_config
  -> run_wes_qsub
  -> collect_wes_artifacts
```

Supported DAG run conf:

```json
{
  "analysis_id": "WES_AIRFLOW_20260705_004506",
  "pipeline": "wes_qsub",
  "mode": "new",
  "workdir": "/data/airflow-demo/runs/WES_AIRFLOW_20260705_004506",
  "backend_event_url": null,
  "params": {
    "target": "final_summary",
    "max_jobs": 2
  }
}
```

Validation rules:

- `pipeline` must be `wes_qsub`.
- `mode` must be `new`, `resume`, or `rerun_rule`.
- `params.target` must be `final_summary`.
- `params.max_jobs` must be `1..2`.
- `workdir` must be under `/data/airflow-demo`.
- `rerun_rule` requires `params.rule` in `fastp/bwa_mem/markdup/final_summary`; sample-level rules require `params.sample_id=S001/S002`.

`prepare_wes_config` reads `pipelines/wes/config/mock_config.yaml` and writes run-local:

```text
workdir/config/wes_mock_config.yaml
workdir/config/wes_airflow_request.json
```

It rewrites mock sample input paths to Airflow container paths under `/opt/airflow/pipelines/wes/mock_data`.

`run_wes_qsub` runs inside the Airflow worker image `airflow-demo/airflow:0.1.0`:

```bash
snakemake \
  --snakefile /opt/airflow/pipelines/wes/workflow/Snakefile \
  --configfile <workdir>/config/wes_mock_config.yaml \
  --profile /opt/airflow/profiles/qsub
```

For `mode=resume`, the command remains profile-based and relies on Snakemake output state plus `rerun-incomplete`; no `--forceall` is added. For `mode=rerun_rule`, `run_wes_qsub` appends:

```bash
--forcerun <rule> <selected-target>
```

Selected targets are limited to the mock output path for `fastp/bwa_mem/markdup` and `reports/final_summary.tsv`. The project-level `final_summary` rule also writes `reports/qc_summary.tsv`.

Runtime environment:

- `AIRFLOW_DEMO_QSUB_MODE=mock`.
- `AIRFLOW_DEMO_QSUB_PYTHON=python`.
- `XDG_CACHE_HOME=<workdir>/tmp/xdg-cache`, so Snakemake does not write `/home/airflow/.cache`.
- Airflow services must run with `AIRFLOW_UID=$(id -u)` for the deploy user that owns `./shared`; `fengxian` uses `1005`.

Expected outputs:

```text
workdir/reports/final_summary.tsv
workdir/reports/qc_summary.tsv
workdir/logs/snakemake.stdout.log
workdir/logs/snakemake.stderr.log
workdir/logs/snakemake.command.txt
workdir/logs/qsub/*.o
workdir/logs/qsub/*.e
workdir/logs/events/snakemake_events.jsonl
```

2026-07-05 `fengxian` smoke:

- DAG run `manual__WES_AIRFLOW_20260705_004506` ended `success`.
- `reports/final_summary.tsv` contains `S001` and `S002` with `mock_success`.
- `logs/events/snakemake_events.jsonl` has 14 lines and contains `qsub_submitted` / `qsub_success`.
- `collect_wes_artifacts` returned XCom summary `event_count=14` and `qsub_log_count=14`.
- Real `qsub/qstat` was not called.

2026-07-05 `fengxian` T044/T056 smoke:

- API/frontend path created `WES_20260705_162041_2507AF`.
- `manual__WES_20260705_162041_2507AF` ended `success`.
- `manual__WES_20260705_162041_2507AF__resume__20260705T162142Z` ended `success`.
- `manual__WES_20260705_162041_2507AF__rerun_rule__20260705T162151Z` ended `success`.
- `logs/snakemake.command.txt` for the final run contains `--forcerun fastp` and does not contain `--forceall`.
- `logs/events/snakemake_events.jsonl` has 28 lines after the sequence.

2026-07-05 `fengxian` T060/T054 smoke:

- API/frontend path created and submitted `WES_20260705_164813_C5561C`.
- `manual__WES_20260705_164813_C5561C` ended `success` after explicit sync.
- `reports/qc_summary.tsv` exists with 6 deterministic mock QC rows across `S001/S002`.
- `GET /api/runs/WES_20260705_164813_C5561C/qc` returned `pass=6`, `warn=0`, `fail=0`, `unknown=0`.
- Dynamic artifacts include `wes_qc_summary`.

## 8. `bio_pgta` v1

第一版 `bio_pgta` 用于 PGT-A metadata、CNV dry-run 和受控 failure smoke。T085/T086 补充 `baseline_qc` staged real smoke：它会真实执行 mapping + metadata + baseline QC，但要求至少 2 个 selected samples、低并发、隔离 workdir，并且仍不使用 qsub、不跑完整 CNV/reference build。

Task graph:

```text
validate_request
  -> prepare_pgta_config
  -> choose_pgta_path
     -> run_pgta_target
     -> pgta_pipeline.run_pgta_mapping
        -> pgta_pipeline.run_pgta_metadata
        -> pgta_pipeline.run_pgta_baseline_qc
  -> collect_pgta_artifact
```

T107 changes only `target=baseline_qc` to use the `pgta_pipeline` TaskGroup.
`metadata`, `dryrun_cnv`, and `invalid_target` continue to branch to the
historical `run_pgta_target` task.

### validate_request

检查：

- `analysis_id` 非空。
- `pipeline = pgta`。
- `params.target` 为 `metadata`、`dryrun_cnv`、`invalid_target` 或 `baseline_qc`。
- `baseline_qc` 要求 selected manifest 至少 2 个样本。
- `workdir` 在 `/data/airflow-demo` 下。
- `sample_sheet_path` 存在，且位于 `workdir` 下。

### prepare_pgta_config

读取 `config/samples.selected.tsv`，检查 `sample_id/R1/R2/source_dir` 列，确认 R1/R2/source_dir 均在 `/data/project/CNV/PGT-A` 只读数据根目录下。

输出：

```text
shared/runs/<analysis_id>/config.yaml
shared/runs/<analysis_id>/config/pgta_run_config.json
shared/runs/<analysis_id>/config/pgta_metadata_config.json
```

target 映射：

| demo target | Snakemake 行为 |
|---|---|
| `metadata` | `pipeline.targets=["metadata"]`，真实执行轻量 metadata |
| `dryrun_cnv` | `pipeline.targets=["cnv"]`，启用 `wisecondorx.cnv.enable`，使用只读 sex-specific WisecondorX reference，并加 `--dry-run --ignore-incomplete --rerun-triggers mtime` |
| `invalid_target` | 向 Snakemake 传入 `__airflow_demo_invalid_target__`，用于失败 smoke |
| `baseline_qc` | `pipeline.mode="build_ref"`，`pipeline.targets=["mapping","metadata","baseline_qc"]`，`build_reference.groups.demo` 使用 selected sample IDs；真实执行 baseline QC，但不运行 reference/reference_qc/CNV |

### run_pgta_target and staged baseline_qc tasks

在 Airflow worker 中直接调用 PGT-A Snakemake 环境：

```bash
/biosoftware/miniconda/envs/snakemake_env/bin/snakemake \
  --snakefile /opt/pipelines/PGT_A/Snakefile \
  --cores ${PGTA_SNAKEMAKE_CORES:-64} \
  --printshellcmds \
  --configfile <workdir>/config.yaml
```

`dryrun_cnv` 会额外传 `--dry-run --ignore-incomplete --rerun-triggers mtime`；`invalid_target` 会额外传 `__airflow_demo_invalid_target__`；`baseline_qc` 不加 dry-run，会用 `PGTA_SNAKEMAKE_CORES` 真实执行，默认值为 64。T107 后，baseline QC 由 `run_pgta_stage(conf, stage)` 分三次调用同一 Snakemake workdir/config family：`mapping`、`metadata`、`baseline_qc`。每个 stage 写 run-local derived config `config/pgta_stage_<stage>.yaml`，将 `pipeline.targets` 缩小为单个 stage；不修改生产 `/opt/pipelines/PGT_A/Snakefile`，不使用 `--forceall`。执行目录为 `/data/airflow-demo/runs/<analysis_id>`，输出只允许写入该 run workdir。T088 后 Snakemake 环境设置 `XDG_CACHE_HOME=<workdir>/tmp/xdg-cache`，并写出实际命令。T095 后同一 subprocess env 还会设置 `MPLCONFIGDIR=<workdir>/tmp/matplotlib`，把 `LD_LIBRARY_PATH` 设为 `PGTA_CONDA_LIB`，并在可用时 `LD_PRELOAD=PGTA_LIBSTDCXX`，默认 `/biosoftware/miniconda/envs/snakemake_env/lib/libstdc++.so.6`，避免 baseline QC 的 `matplotlib/scipy/pysam` 等 compiled Python packages 加载到容器系统旧 `libstdc++` 或继承的 `/usr/local/lib`。stdout/stderr/command 写入：

```text
shared/runs/<analysis_id>/logs/snakemake.command.txt
shared/runs/<analysis_id>/logs/snakemake.stdout.log
shared/runs/<analysis_id>/logs/snakemake.stderr.log
```

For T107 staged baseline runs, stage-specific logs are also written:

```text
shared/runs/<analysis_id>/logs/snakemake.mapping.command.txt
shared/runs/<analysis_id>/logs/snakemake.mapping.stdout.log
shared/runs/<analysis_id>/logs/snakemake.mapping.stderr.log
shared/runs/<analysis_id>/logs/snakemake.metadata.command.txt
shared/runs/<analysis_id>/logs/snakemake.metadata.stdout.log
shared/runs/<analysis_id>/logs/snakemake.metadata.stderr.log
shared/runs/<analysis_id>/logs/snakemake.baseline_qc.command.txt
shared/runs/<analysis_id>/logs/snakemake.baseline_qc.stdout.log
shared/runs/<analysis_id>/logs/snakemake.baseline_qc.stderr.log
```

T093 adds `mode=resume` for `baseline_qc` only. `validate_request` rejects resume for other PGT-A targets. In resume mode, `run_pgta_target` first runs the same Snakemake command with `--unlock` and writes:

```text
shared/runs/<analysis_id>/logs/snakemake.unlock.command.txt
shared/runs/<analysis_id>/logs/snakemake.unlock.stdout.log
shared/runs/<analysis_id>/logs/snakemake.unlock.stderr.log
```

The main command then adds `--rerun-incomplete` and keeps `--cores ${PGTA_SNAKEMAKE_CORES:-64}`. `--forceall` is explicitly not used; Snakemake is expected to reuse completed outputs from the same workdir and rerun only missing or incomplete work.

T094 adds a run-local cleanup step between successful `--unlock` and the main resume command. It removes only interrupted samtools sort temporary files matching:

```text
workdir/mapping/*.sorted.bam.tmp.*.bam
```

It writes:

```text
shared/runs/<analysis_id>/logs/pgta.resume.cleanup.tsv
```

The cleanup refuses non run-local workdirs, does not delete `*.sorted.bam`, `*.sorted.bam.bai`, FASTQ, QC, logs, config, PGT-A source files, or rawdata, and still does not use `--forceall`.

T095 adds a baseline-QC-only Python import preflight before the main Snakemake command, after resume unlock/cleanup when `mode=resume`. It uses the same subprocess env and runs `PGTA_PYTHON_BIN` to import `matplotlib`, `numpy`, `pandas`, `pysam`, and `scipy`. Output is written to:

```text
shared/runs/<analysis_id>/logs/pgta.python_preflight.log
```

If preflight fails, `run_pgta_target` fails immediately with a clear preflight error and does not start the long Snakemake command.

### collect_pgta_artifact

`metadata` 验收 `logs/run_metadata.tsv` 是否存在；`dryrun_cnv` 验收 `logs/snakemake.stdout.log` 是否存在并返回 dry-run stdout artifact；`baseline_qc` 验收 `qc/baseline/baseline_qc_summary.tsv`、`baseline_qc_pass_samples.txt` 和 `baseline_qc_report.md`。`invalid_target` 预期在 `run_pgta_target` failed，不进入 collect task。

本阶段已知边界：

- `invalid_target` 是测试错误摘要链路的受控失败入口，不代表生产 target。
- `baseline_qc` 是 Level 4 staged real smoke，不代表完整生产 reference/CNV 流程。
- qsub、真实 CNV、reference build 和生产批量运行仍在后续任务中。

## 9. `bio_pgta_airflow` Airflow-only logger v1

`bio_pgta_airflow` 用于验证 PGT-A 在 Snakemake 9.23.1 下通过 logger plugin 接入 Airflow UI。它不走 FastAPI，不写 biodemo DB，也不替代 `bio_pgta`。

DAG run conf 第一版只支持已有 manifest 路径：

```json
{
  "analysis_id": "PGTA_AIRFLOW_20260703_074844",
  "workdir": "/data/airflow-demo/runs/PGTA_AIRFLOW_20260703_074844",
  "sample_sheet_path": "/data/airflow-demo/runs/PGTA_AIRFLOW_20260703_074844/config/samples.selected.tsv",
  "target": "metadata",
  "email_to": null,
  "backend_event_url": "http://backend:8000/api/events/snakemake"
}
```

Task graph:

```text
validate_request
  -> prepare_pgta_config
  -> run_snakemake9_with_logger
  -> collect_snakemake_events
  -> collect_metadata_artifact
```

`run_snakemake9_with_logger` 调用：

```bash
/biosoftware/miniconda/envs/snakemake9_env/bin/snakemake \
  --snakefile /opt/pipelines/PGT_A/Snakefile \
  --cores ${PGTA_SNAKEMAKE_CORES:-64} \
  --printshellcmds \
  --show-failed-logs \
  --logger airflow-demo \
  --logger-airflow-demo-analysis-id <analysis_id> \
  --logger-airflow-demo-workdir <workdir> \
  --logger-airflow-demo-events-path <workdir>/logs/events/snakemake_events.jsonl \
  --logger-airflow-demo-backend-event-url http://backend:8000/api/events/snakemake
```

## 10. `bio_nipt_docker` scanned-batch v1

T103 keeps `bio_nipt_docker` as the second deployable workflow in the demo and
changes new submissions to scanned NIPT chip batches. It is a Docker integration
for NIPT, not the deferred NIPT qsub workflow. The default acceptance mode is
`mount_smoke`; `full_run` is always gated by `NIPT_ALLOW_HEAVY_RUN`. The
repository safety default is false; T113 sets the validated manual deployment
to true while leaving NIPT automatic intake disabled.

Task graph:

```text
validate_request
  -> prepare_nipt_docker_run
  -> run_nipt_docker
  -> collect_nipt_artifacts
```

Supported DAG run conf:

```json
{
  "analysis_id": "NIPT_20260708_033450_8362A0",
  "pipeline": "nipt_docker",
  "mode": "new",
  "sample_sheet_path": "/data/airflow-demo/runs/NIPT_20260708_033450_8362A0/config/samples.selected.tsv",
  "workdir": "/data/airflow-demo/runs/NIPT_20260708_033450_8362A0",
  "backend_event_url": "http://backend:8000/api/events/snakemake",
  "email_to": null,
  "params": {
    "project_name": "T103 NIPT Docker scanned batch smoke",
    "rawdata_root": "/opt/pipelines/NIPT/fastq",
    "source_batch_dir": "/opt/pipelines/NIPT/fastq/FQ2026/260414_TPNB500380AR_1065_AH32CCBGY2",
    "source_batch_id": "FQ2026/260414_TPNB500380AR_1065_AH32CCBGY2",
    "source_fingerprint": "sha256...",
    "run_mode": "mount_smoke",
    "input_mode": "nipt_docker_scan",
    "selected_count": 1,
    "chip_name": "260414_TPNB500380AR_1065_AH32CCBGY2",
    "cores": 40
  }
}
```

Validation rules:

- `pipeline` must be `nipt_docker`.
- `mode` must be `new`.
- `params.input_mode` must be `nipt_docker_scan` for new frontend submissions.
- `params.source_batch_dir` must be present and point to the scanned NIPT chip folder.
- `params.run_mode` must be `mount_smoke` or `full_run`.
- `full_run` is rejected unless `NIPT_ALLOW_HEAVY_RUN=true`.
- `cores` must be between 1 and 40.
- `workdir` must be under `CONTAINER_SHARED_ROOT`.
- `sample_sheet_path` must be inside `workdir` and readable.

`prepare_nipt_docker_run` writes:

```text
workdir/config/nipt_run_config.yaml
workdir/config/nipt_docker_compose.yml
workdir/config/nipt_airflow_request.json
```

For scan runs, the task also writes `workdir/<chip_name>.csv` from
`samples.selected.tsv`. The generated config points `input.fastq_dir` at
`/input_batch`; the Docker runner mounts the host source chip directory
read-only at that path and does not copy large FASTQ files.

The compose artifact uses a unique container name `NIPTPro_<analysis_id>` and must not reuse the external `NIPTPro_runner` name. The Airflow worker mounts:

```text
${NIPT_PIPELINE_ROOT}:${NIPT_CONTAINER_ROOT}:ro
/var/run/docker.sock:/var/run/docker.sock
```

On `fengxian`, Docker socket access also requires `group_add: ${DOCKER_SOCKET_GID:-114}` for `airflow-worker`; scheduler and API server do not receive the Docker socket.

`run_nipt_docker` generates the compose artifact for auditability, then executes the equivalent `docker run --rm` command because the worker image has Docker CLI but no `docker compose` subcommand. The command is written to:

```text
workdir/logs/nipt_docker.command.txt
workdir/logs/snakemake.stdout.log
workdir/logs/snakemake.stderr.log
```

For `mount_smoke`, the container verifies the NIPT bundle mounts, reference mount, selected chip samplesheet, read-only `/input_batch`, and run workdir, then writes `reports/qc_summary.tsv` with one `nipt_mount_smoke=pass` row per selected sample.

T101 remote acceptance on `fengxian`:

- `bio_nipt_docker` imported with no DAG import errors.
- Final smoke `manual__NIPT_20260708_033450_8362A0` reached Airflow/backend `success`.
- stdout contained `mount_smoke_ok NIPT_20260708_033450_8362A0 260414_TPNB500380AR_1065_AH32CCBGY2`.
- `/api/runs/NIPT_20260708_033450_8362A0/qc` returned `pass=96,warn=0,fail=0,unknown=0`.

## 10.1 T102 progress observability

T102 keeps Airflow as the project-level scheduler and exposes progress through the FastAPI backend, not by reading the Airflow metadata database directly.

Backend progress source:

```text
GET /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances
```

Airflow task weights:

| DAG | Task | Percent |
|---|---|---:|
| `bio_pgta` | `validate_request` | 5 |
| `bio_pgta` | `prepare_pgta_config` | 10 |
| `bio_pgta` | `choose_pgta_path` | 10 |
| `bio_pgta` | `pgta_pipeline.run_pgta_mapping` | 55 |
| `bio_pgta` | `pgta_pipeline.run_pgta_metadata` | 70 |
| `bio_pgta` | `pgta_pipeline.run_pgta_baseline_qc` | 90 |
| `bio_pgta` | historical `run_pgta_target` | 90 |
| `bio_pgta` | `collect_pgta_artifact` | 100 |
| `bio_nipt_docker` | `validate_request` | 5 |
| `bio_nipt_docker` | `prepare_nipt_docker_run` | 15 |
| `bio_nipt_docker` | `run_nipt_docker` | 90 |
| `bio_nipt_docker` | `collect_nipt_artifacts` | 100 |

Runner event behavior:

- `POST /api/runs/{analysis_id}/actions/submit` includes `backend_event_url=http://backend:8000/api/events/snakemake` for both PGT-A and NIPT Docker.
- PGT-A `run_pgta_target` emits target-level `running/success/failed` events for historical and non-baseline targets. T107 staged baseline runs emit stage-level `mapping`, `metadata`, and `baseline_qc` events and parse Snakemake stdout/stderr for rule blocks when available.
- NIPT Docker `mount_smoke` emits `nipt_mount_smoke` `running/success/failed`; `full_run` parses Docker stdout/stderr for Snakemake rule blocks.
- Every runner event is written to `workdir/logs/events/snakemake_events.jsonl` before optional backend POST.
- Backend POST failure must not fail the Airflow task; it is recorded as a JSONL `backend_post_error`.
- `sync-airflow` can import the JSONL fallback when Airflow reaches a terminal state.

T102 verified progress smokes on `fengxian`:

- `PGTA_20260708_050811_A24E36`: `bio_pgta` metadata smoke reached success with Airflow task instances and `metadata=success` pipeline event.
- `NIPT_20260708_050843_B3B05E`: `bio_nipt_docker` mount smoke reached success with Airflow task instances and `nipt_mount_smoke=success` pipeline event.

## 10.2 `bio_intake_scan`

T103 adds a scheduled intake DAG that calls the backend API instead of directly
reading the biodemo database.

Task graph:

```text
scan_and_submit
```

Default schedule:

```text
*/10 * * * *
```

Runtime endpoint:

```text
POST ${BACKEND_BASE_URL}/api/intake/scan-and-submit
```

Default payload:

```json
{
  "pipelines": ["pgta", "nipt_docker"],
  "bootstrap": false,
  "max_samples": 200
}
```

Safety:

- `is_paused_upon_creation` defaults to true through
  `INTAKE_SCAN_PAUSED_ON_CREATION=true`.
- Deployment should call `/api/intake/scan-and-submit` with `bootstrap=true`
  first, confirm `/api/intake/status`, then unpause the DAG if auto intake is
  desired.
- The DAG must not mount or modify production pipeline roots. All scanning and
  idempotency state is handled by FastAPI.

T104 moves scanner root and ready-rule configuration into `config/intake.yaml`.
`bio_intake_scan` still calls only the backend endpoint above; it does not read
the YAML directly, does not access biodemo DB, and does not scan the filesystem
itself. The backend exposes the active sanitized config through
`GET /api/intake/config`.

## 10.3 T108 PGT-A controlled stage rerun

T108 keeps `bio_pgta` as a project-level DAG and adds a controlled branch for
PGT-A `baseline_qc` stage reruns.

For a normal new `target=baseline_qc` run, the staged path remains:

```text
validate_request
prepare_pgta_config
choose_pgta_path
pgta_pipeline.run_pgta_mapping
pgta_pipeline.run_pgta_metadata
pgta_pipeline.run_pgta_baseline_qc
collect_pgta_artifact
```

When the backend submits `mode=rerun_stage` with `params.rerun_stage`, the
branch starts at the requested stage and then continues downstream:

| `rerun_stage` | First Airflow task |
|---|---|
| `mapping` | `pgta_pipeline.run_pgta_mapping` |
| `metadata` | `pgta_pipeline.run_pgta_metadata` |
| `baseline_qc` | `pgta_pipeline.run_pgta_baseline_qc` |

This is intentionally not an arbitrary DAG/task trigger. The backend rejects
non-PGT-A runs, non-`baseline_qc` targets, active runs, unsupported stages, and
rule/sample selection. The runner still uses the same workdir and
`--rerun-incomplete`; it must not use `--forceall`.

## 11. `bio_pgta_airflow` collect events

`collect_snakemake_events` 读取 JSONL，生成：

```text
workdir/logs/events/snakemake_events.jsonl
workdir/logs/events/snakemake_rule_summary.tsv
```

## 12. T112 PGT-A predict TaskGroup

`bio_pgta` adds the production path
`validate -> prepare -> mapping -> metadata -> cnv_qc -> cnv_predict -> collect`
under TaskGroup `pgta_predict`. All four full stages use one-slot pool
`pgta_s9_full`; `max_active_runs=1` serializes complete predictions.
`bio_pgta_airflow` is deprecated and paused. Snakemake rules stay rule/sample
events instead of becoming hundreds of Airflow tasks.

`bio_intake_scan` has `max_active_runs=1` and sends the internal service token
header to backend. Intake remains a project-level scanner DAG; it does not read
the biodemo database or execute Snakemake rules itself.

Airflow 网页第一版通过 task log 和 XCom 查看状态汇总；不实现自定义 Airflow Web 插件。若 `backend_event_url` 未配置，logger 只写 JSONL；若配置，则 rule/job 级事件会同步 POST 到 FastAPI 并 upsert 到 biodemo `snakemake_rule_event`。

T088 后 `bio_pgta_airflow` 也使用 run-local `XDG_CACHE_HOME=<workdir>/tmp/xdg-cache`，避免 Snakemake 9 logger 路径回退到不可写的 `/home/airflow/.cache/snakemake`。
# T123 scanner retention and operator path

- `bio_pgta` compatibility branches remain unchanged, but the operator UI
  projects only `pgta_predict`. Build Reference will use a future dedicated
  DAG and is not represented by renaming `run_pgta_target`.
- `bio_intake_scan` remains a ten-minute DAG with `scan_and_submit`,
  `prune_scanner_history`, and `propagate_scanner_result`. Retention uses
  `all_done` so it can run after a failed scan, while the final task explicitly
  propagates either upstream failure so the DAG run cannot become false
  success. Retention performs work only on the 03:00 scheduled cycle, uses the
  internal token, and is restricted to the scanner DAG.
- Scanner logs older than 30 days are removed only below
  `/opt/airflow/logs/dag_id=bio_intake_scan`; analysis logs/workdirs are excluded.
- Airflow services use Docker json-file rotation of 50 MB with three files.
## WGS-only Phase 1 DAGs

> Historical Phase 1 record only; it is not the WGS 4.0.1 target.

`bio_wgs_intake_scan` is the paused legacy ten-minute scanner. `bio_wgs_cce` is the paused legacy project topology with fixed CCE slots and reschedule sensors. `bio_wgs_onprem` is an unimplemented local/SGE placeholder. Runner tasks intentionally contain no production commands and fail closed. These three DAGs still exist in the current server metadata and are pending replacement/removal by T133; they have not already been removed.

The historical T131 `bio_wgs_cce` Phase 1 graph is described in `23_WGS_CLOUD_ORCHESTRATION_PHASE1.md`; it must not be used as the WGS 4.0.1 runtime contract.
