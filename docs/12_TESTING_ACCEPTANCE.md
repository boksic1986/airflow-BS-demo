# 12 测试和验收设计

## 1. 测试层级

测试执行位置约束：

- 本地 `D:\pipeline\airflow-demo` 只做编辑、Git、文档一致性和 manifest 检查。
- 运行时验收测试一律在远端执行，当前默认节点为 `ssh fengxian`。
- 不把本地 pytest、Docker Compose、Snakemake、Airflow 或服务启动结果作为验收证据。
- 如果某项远端测试无法执行，必须在 `HANDOFF.md` 记录命令、原因和下一步环境条件。

```text
unit tests
  input scanner, run creation, qc parser, airflow client mock, log tail
integration tests
  backend + DB, event receiver, artifact registry
DAG tests
  import, conf validation, mock task execution
Snakemake tests
  dry-run, mock execution, failure/resume
frontend tests
  render, API client, key flows
E2E smoke
  submit -> airflow -> snakemake -> qc -> email
```

## 2. Backend tests

必须覆盖：

- `/api/health`。
- `/api/input/scan` 成功发现白名单路径下的 R1/R2 候选样本。
- `/api/input/scan` 拒绝白名单外路径。
- `/api/runs` 用 selected samples 创建 `analysis_run` 和 `sample`。
- `/api/runs` 生成 `samples.selected.tsv` 和 `request.json`。
- `/api/runs/{analysis_id}/actions/submit` 只允许 `created` / `pgta` / `metadata`，并触发 Airflow client。
- event receiver 幂等 upsert。
- log API 防路径穿越。
- reanalysis mode 生成正确 payload。

## 3. DAG tests

必须覆盖：

- DAG import 无错误。
- `validate_request` 对缺字段报错。
- `generate_pipeline_config` 输出 config。
- `run_pipeline` 根据 mode 生成正确 Snakemake flags。
- failure callback 能生成 error summary。

## 4. Snakemake tests

必须覆盖：

- `snakemake -n` 通过。
- mock 运行成功。
- mock rule 故意失败时生成 stderr。
- resume 后不重复已成功输出。
- qsub wrapper mock mode 生成 event。

T040/T041/T042 WES mock qsub v1 当前验收：

```text
WES mock dry-run:
  使用 pipelines/wes/workflow/Snakefile
  -> 两个 mock sample
  -> Snakemake dry-run 显示 all/fastp/bwa_mem/markdup/final_summary 共 8 个 jobs

mock qsub wrapper:
  使用 AIRFLOW_DEMO_QSUB_MODE=mock
  -> 不调用真实 qsub
  -> 生成 MOCK-* qsub_jobid
  -> 写 logs/qsub/<rule>.<sample>.o/e
  -> 写 logs/events/snakemake_events.jsonl
  -> backend run 存在时 POST /api/events/snakemake 并可通过 /api/runs/{analysis_id}/rules 查询

qsub profile:
  profiles/qsub/config.yaml 已固定 jobs=2 和 rerun-incomplete
  -> 当前 fengxian 宿主机 Snakemake 环境缺 snakemake-executor-plugin-cluster-generic
  -> T042 使用 Dockerized snakemake-runner 补齐 Snakemake 9.23.1 和 cluster-generic executor
  -> profile runtime smoke 必须真正运行 `--profile profiles/qsub`
```

2026-07-04 `fengxian` WES mock qsub 验收记录：
- official mirror `/home/jiucheng/project/airflow-demo` 已同步到 `a7f03f3` 后执行。
- `docker compose -f docker-compose.yaml config --quiet` 通过。
- `docker run --rm airflow-demo/backend:0.1.0 pytest -q` 通过，35 tests passed。
- `python -m unittest pipelines.tests.test_qsub_submit pipelines.tests.test_wes_mock_contract` 在 Docker 化 backend 镜像中通过，5 tests OK。
- WES mock Snakemake dry-run 通过，job stats 为 `all=1, fastp=2, bwa_mem=2, markdup=2, final_summary=1, total=8`。
- mock qsub wrapper 以 `AIRFLOW_DEMO_QSUB_MODE=mock` 和 `AIRFLOW_DEMO_BACKEND_EVENT_URL=http://127.0.0.1:8000/api/events/snakemake` 执行 `WES_20260704_180650_MOCK`，生成 `MOCK-WES_20260704_180650_MOCK-12-bwa_mem-S001`。
- `/api/runs/WES_20260704_180650_MOCK/rules` 返回 `bwa_mem/S001=success`，包含 `qsub_jobid`、stdout/stderr path 和 `return_code=0`。

T042 profile runtime 验收要求：
- `docker compose -f docker-compose.yaml build snakemake-runner` 成功。
- `docker compose -f docker-compose.yaml run --rm snakemake-runner snakemake --version` 返回 `9.23.1`。
- `snakemake --profile profiles/qsub` 运行 WES mock 成功，生成 `reports/final_summary.tsv`。
- `logs/events/snakemake_events.jsonl` 包含 `qsub_submitted` 和 `qsub_success`。
- `logs/qsub/*.o/e` 存在；仍不调用真实 qsub。

T042 profile runtime 已验收：
- 2026-07-04 official mirror fast-forward 到 `cd22c90`。
- `docker compose -f docker-compose.yaml config --quiet` 成功。
- `docker compose -f docker-compose.yaml build snakemake-runner` 成功，镜像为 `airflow-demo/snakemake-runner:0.1.0`。
- `docker compose -f docker-compose.yaml run --rm snakemake-runner snakemake --version` 返回 `9.23.1`。
- `snakemake --help` 显示 `cluster-generic` executor 和 `--cluster-generic-submit-cmd`。
- Dockerized contract tests `python -m unittest pipelines.tests.test_wes_mock_contract -v` 通过，4 tests OK。
- `WES_PROFILE_20260704_230713` 使用 `--profile profiles/qsub` 成功完成 8 个 WES mock jobs。
- `shared/runs/WES_PROFILE_20260704_230713/reports/final_summary.tsv` 包含 `S001` 和 `S002` 的 `mock_success`。
- `shared/runs/WES_PROFILE_20260704_230713/logs/events/snakemake_events.jsonl` 共 14 行，包含 `qsub_submitted` 和 `qsub_success`。
- `shared/runs/WES_PROFILE_20260704_230713/logs/qsub/*.o/e` 存在；未调用真实 qsub。

T030/T031 Airflow WES mock qsub DAG 已验收：

- `airflow-demo/airflow:0.1.0` 构建成功；Airflow version `2.9.3`，Snakemake version `9.23.1`。
- `snakemake --help` 在 Airflow image 中显示 `cluster-generic` executor。
- Dockerized contract tests `pipelines.tests.test_wes_mock_contract` 通过，6 tests OK。
- Dockerized DAG/runner tests `dags.tests.test_bio_wes_qsub_dag` and `dags.tests.test_wes_qsub_runner` 通过，8 tests OK。注意该命令使用 `/usr/local/bin/python`，避免 `PATH` 上的 Snakemake venv Python。
- `docker compose -f docker-compose.yaml config --quiet` 通过。
- `docker compose -f docker-compose.yaml build airflow-worker airflow-scheduler airflow-api-server` 通过。
- Airflow import check `airflow dags list-import-errors` 返回 `No data found`，`bio_wes_qsub` 可见。
- 2026-07-05 `fengxian` smoke run `manual__WES_AIRFLOW_20260705_004506` ended `success`。
- `shared/runs/WES_AIRFLOW_20260705_004506/reports/final_summary.tsv` 包含 `S001` 和 `S002` 的 `mock_success`。
- `shared/runs/WES_AIRFLOW_20260705_004506/logs/events/snakemake_events.jsonl` 共 14 行，包含 `qsub_submitted` 和 `qsub_success`。
- `collect_wes_artifacts` XCom summary returned `event_count=14` and `qsub_log_count=14`。
- Real `qsub/qstat` 未调用。

## 5. Frontend tests

必须覆盖：

- Submit 页面必填校验。
- Runs table 渲染。
- Rule table status 渲染。
- Log viewer 处理空日志/不存在日志。
- Reanalysis button 调用正确 API。

## 6. E2E smoke 场景

### 成功场景

```text
PGT-A v1:
  扫描服务器 rawdata_root
  -> 勾选 1-2 个样本
  -> 创建 PGTA_*
  -> analysis_run.status = created
  -> sample.fq1/fq2 保存服务器路径
  -> 生成 samples.selected.tsv 和 request.json
  -> submit action 触发 Airflow bio_pgta
  -> analysis_run.status = submitted, dag_run_id 非空
  -> bio_pgta success
  -> logs/run_metadata.tsv 存在
```

PGT-A Level 2/3:

```text
dryrun_cnv:
  扫描服务器 rawdata_root
  -> 勾选 1 个样本
  -> 创建 target=dryrun_cnv run
  -> submit action 触发 Airflow bio_pgta
  -> bio_pgta success
  -> logs/snakemake.stdout.log 和 stderr 存在
  -> 不产生真实 CNV 结果

invalid_target:
  创建 target=invalid_target run
  -> submit action 触发 Airflow bio_pgta
  -> Snakemake 因 __airflow_demo_invalid_target__ failed
  -> sync-airflow 后 analysis_run.status = failed
  -> error_summary 包含 stderr path 和最后 100 行
```

2026-07-04 `fengxian` 验收记录：

- `dryrun_cnv`: `PGTA_20260703_170917_20E8F2`, Airflow `success`, stdout 记录 7 个 dry-run jobs，artifact API 返回 stdout/stderr/config。
- `invalid_target`: `PGTA_20260703_170957_3DDEC3`, Airflow `failed`, `sync-airflow` 后 `analysis_run.status=failed`，`error_summary` 非空并包含 stderr path 和最后错误内容。

完整 E2E 后续场景：

```text
提交已创建的 run
  -> Airflow DAG success
  -> Snakemake all success
  -> QC pass/warn
  -> report artifacts
  -> MailHog 收到 success email
```

### 失败场景

```text
提交包含 FAIL_SAMPLE 的 mock input
  -> mock rule intentional_fail 返回非零
  -> Airflow run failed
  -> rule table 显示 failed
  -> stderr 展示 intentional error
  -> MailHog 收到 failure email
```

### Resume 场景

```text
修复 mock 条件
  -> 点击 resume
  -> 已成功 rule skipped/cached
  -> 失败 rule 重跑
  -> run success
```

## 7. 验收报告模板

```markdown
# Acceptance Report

Date:
Agent:
Commit:
Environment:

## Commands

## Results

## Screenshots / URLs

## Known issues

## Decision

- [ ] accepted
- [ ] accepted with issues
- [ ] rejected
```
