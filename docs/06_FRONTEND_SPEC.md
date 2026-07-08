# 06 前端设计

## 0. Current T050/T051/T054/T056/T057 v1

第一版前端已经从 nginx placeholder 替换为 Vite React + TypeScript app，由 Docker nginx 镜像服务静态文件，宿主机端口保持 `12959`。

已实现范围：

- 首页即 analysis submit/list/detail workspace，当前可展示 `pgta` 和 `wes_qsub`。
- 主内容顶部 `Submit new analysis` 工作区包含 `New PGT-A Run` 和 `New WES Mock Run`；左侧只保留 run list，避免提交表单被挤在窄侧栏。
- `New PGT-A Run` 面板支持 `project_name`、`rawdata_root`、`max_samples`、`target` 下拉、可选 `email_to` 和备注；target 下拉使用可读标签：metadata smoke、CNV dry-run、failure smoke、baseline QC smoke。
- `Scan` 调用 `POST /api/input/scan`，展示服务器路径 FASTQ 候选样本，支持勾选样本；`truncated=true` 时显示收窄路径提示。
- 未勾选样本时 `Create Run` 禁用，并显示 `Select at least one scanned sample to enable Create Run.` 提示；`baseline_qc` 少于 2 个样本时继续禁用，并显示 `Baseline QC smoke requires at least 2 selected samples.`。
- `Create Run` 调用 JSON `POST /api/runs`，创建成功后自动选中新 run 并展示 detail。
- 对 `status=created` 且 `target` 为 `metadata`、`dryrun_cnv`、`invalid_target` 或 `baseline_qc` 的 run，detail toolbar 显示 `Submit to Airflow`，调用 `POST /api/runs/{analysis_id}/actions/submit`。
- 左侧 `New WES Mock Run` 面板可一键创建 `pipeline=wes_qsub,target=final_summary` run 并提交到 `bio_wes_qsub`。
- `GET /api/runs?limit=50&offset=0` 展示 run 列表。
- run detail 展示 overview、samples、Snakemake rules、metadata/stdout/stderr logs、artifacts。
- Samples 表直接展示后端 `/api/runs/{analysis_id}/samples` 的 `sample.status`；提交后应为 `running`，显式 `Sync Airflow` 后应随 Airflow 最终状态变为 `success` 或 `failed`。
- WES mock run detail 展示 QC panel：pass/warn/fail/unknown summary 和样本级 mock QC 指标表。
- 手动同步按钮调用 `POST /api/runs/{analysis_id}/actions/sync-airflow`。
- T091 后，选中的 active run（`submitted/running/queued` 且已有 `dag_run_id`）每 15 秒自动调用同一 `sync-airflow` endpoint，并刷新 run list、detail、samples、rules、artifacts、QC 和当前 log；进入 `success/failed` 后停止自动同步。toolbar 显示 `Auto sync active` 和 `Last synced ...`。
- 对已有 `wes_qsub` DAG run，detail toolbar 显示 `Resume` 和 `Rerun rule` 控件；`Rerun rule` 支持 `fastp/bwa_mem/markdup/final_summary`，样本级 rule 可选 `S001/S002`。
- T093 后，对 `pipeline=pgta,target=baseline_qc` 且状态为 `failed` 或 `terminated` 的 run，detail toolbar 显示 `Resume with 64 cores`；running/success run 不显示该按钮。
- API base 默认按浏览器当前 host 推导为 `http://<host>:8000/api`，可通过 `window.__AIRFLOW_DEMO_CONFIG__.apiBaseUrl` 或 `VITE_API_BASE_URL` 覆盖。
- 后端返回的 run 时间保持 timezone-aware ISO 字符串；前端默认按 `Asia/Shanghai` 显示为 `YYYY-MM-DD HH:mm:ss Asia/Shanghai`。如迁移到其他时区，可用 `window.__AIRFLOW_DEMO_CONFIG__.timeZone` 或 build arg `FRONTEND_DISPLAY_TIME_ZONE` 覆盖。

未实现范围：

- 登录系统。
- 独立日志查看页、MultiQC iframe/report viewer。
- 自定义 Airflow Web 插件或 Airflow task log API 抓取。

## 1. 页面结构

```text
/dashboard
/runs
/runs/:analysis_id
/submit
/settings/demo
```

## 2. Dashboard

展示卡片：

- Today submitted。
- Running。
- Failed。
- QC warning。
- qsub running jobs。
- Airflow health。

Pipeline cards：

```text
PGT-A: created/running/success/failed
WES qsub: running/success/failed
NIPT qsub: running/success/failed
NIPT docker: running/success/failed
```

## 3. Submit 页面

字段：

```text
Pipeline:
  - PGT-A
  - WES qsub
  - NIPT qsub
  - NIPT docker
Input mode:
  - server path scan
PGT-A v1 fields:
  - project_name
  - rawdata_root
  - scan button
  - candidate sample checkbox table
  - target: metadata / dryrun_cnv / invalid_target / baseline_qc
  - email_to
  - note
Params:
  - genome
  - queue
  - max_jobs
  - email_to
  - analysis_mode
```

PGT-A v1 不上传 FASTQ 或 sample sheet。前端调用 `POST /api/input/scan` 扫描白名单服务器路径下已有 FASTQ，用户勾选样本后用 JSON 调用 `POST /api/runs`。提交成功后状态为 `created`，不会立即出现 Airflow DAG run。

T051/T045 v1 已在当前单页 workspace 中实现该表单，不引入路由库。T051 usability fix 后，表单位于主内容顶部的 `Submit new analysis` 区域，candidate table 使用主内容宽度，run list 不再混入创建表单。创建 run 和提交执行保持两步模式：创建后先进入 `created`，用户在 run detail toolbar 点击 `Submit to Airflow` 后才触发 `bio_pgta`。默认 target 是 `metadata`；`dryrun_cnv` 用于 Snakemake dry-run smoke，`invalid_target` 仅用于失败摘要 smoke，`baseline_qc` 是 Level 4 staged real smoke，要求至少 2 个 selected samples。

WES mock v1 不上传或扫描数据。前端 `New WES Mock Run` 直接调用 JSON `POST /api/runs` 创建固定 `S001/S002` mock run，然后调用 `POST /api/runs/{analysis_id}/actions/submit` 提交 `bio_wes_qsub`。

提交后跳转：

```text
/runs/<analysis_id>
```

## 4. Runs 列表

列：

```text
analysis_id
pipeline
status
samples
qc
created_at
runtime
actions
```

Actions：

```text
View
Resume
Clone
```

## 5. Run Detail Tabs

### Overview

- analysis_id。
- pipeline。
- mode。
- status。
- sample count。
- workdir。
- submit time/start/end/runtime。
- Airflow link。
- error summary。

### Airflow

- DAG run id。
- Task list。
- Task status。
- Link to Airflow UI。

### Snakemake

组件：

- Rule status summary。
- Rule table。
- Per sample progress。
- qsub job id。
- stdout/stderr button。

Rule table columns：

```text
rule
sample_id
status
snakemake_jobid
qsub_jobid
runtime
log actions
```

### QC

- T054 v1 已实现 WES mock QC panel，调用 `GET /api/runs/{analysis_id}/qc`；T087 v1 复用同一 panel 展示 PGT-A `baseline_qc` summary 导入后的样本级指标。
- QC summary：pass/warn/fail/unknown。
- Sample QC table：sample_id、metric_name、metric_value、threshold、status。
- 没有 QC 时显示空状态，不影响 rules/logs/artifacts。
- MultiQC report link/iframe 和 Snakemake report link 留给 T061/T063 后续。

### Logs

- stream selector：Airflow/Snakemake/rule/qsub。
- rule selector。
- sample selector。
- stdout/stderr selector。
- tail lines selector。
- refresh button。

### Reanalysis

- Resume failed run。
- Rerun failed/incomplete。
- Rerun selected rule/sample。
- Clone as new analysis。

T056 v1 已完成 WES mock 最小入口：

- `Resume` 调用 `POST /api/runs/{analysis_id}/actions/reanalyze`，payload `{"mode":"resume"}`。
- `Rerun rule` 调用同一 endpoint，payload `{"mode":"rerun_rule","rule":"fastp","sample_id":"S001"}`。
- PGT-A `baseline_qc` failed/terminated run can call the same endpoint with `{"mode":"resume"}` through `Resume with 64 cores`; it reuses the same workdir and relies on the backend/Airflow guardrails.
- `clone_new`、`rerun_failed` and PGT-A rule-level reanalysis remain deferred.

必须显示提示：

```text
Resume 会复用当前 workdir，不默认重新分析已成功输出。
Clone 会创建新 analysis_id 和新 workdir。
```

## 6. 状态颜色

| Status | Color semantic |
|---|---|
| success/pass | green |
| running/submitted | blue |
| failed/fail | red |
| warn/qc_warning | orange |
| skipped/cached | gray |
| unknown | neutral |

具体颜色由 UI 框架实现，不写死在业务逻辑。

## 7. 前端容错

- API 失败时显示错误 message，不吞掉。
- 日志文件不存在时显示“尚未生成或路径不可访问”。
- 长日志默认只显示 tail。
- 刷新状态使用 polling；后续可升级 SSE/WebSocket。

## 8. Demo 优先级

MVP 必须完成：

1. Submit。
2. Runs list。
3. Run detail overview。
4. Snakemake rule table。
5. Log viewer。
6. QC table。
7. Resume button。

可后置：

- fancy rule graph。
- auth。
- dark mode。
- WebSocket 实时推送。

## 9. T096 platform UI redesign v2

T096 keeps the existing FastAPI contracts and upgrades the frontend from a single workspace page into a routed bioinformatics operations platform. The detailed v2 design is split into:

- `docs/frontend-design-review.md`: UI audit, reference patterns, and keep/refactor decisions.
- `docs/frontend-spec.md`: page/resource model, fields, loading/empty/error states, status machine, and WES/PGT-A/NIPT/WGS behavior.
- `DESIGN.md`: visual tokens, layout rules, component contracts, log/failure interactions, and accessibility requirements.

### Routes

```text
/dashboard
/submit
/runs
/runs/:analysisId
/samples
/workflows
/failures
/settings
```

### Implemented pages

- Dashboard: platform counts, failed/completed runs, pipeline status, backend/Airflow health, and demo resource metrics.
- Submit Task: PGT-A server-path scan/create/submit remains real; WES mock create/submit remains real; NIPT/WGS are clearly marked mock/demo with validated sample-sheet preview only.
- Runs: dense table with pipeline/status/keyword filters, sorting, status text plus icon, and batch action shell.
- Run Detail: summary header, failure diagnosis, workflow timeline, QC summary, tabs for Overview/Samples/Workflow/QC/Logs/Files/Config, PGT-A resume guard, and WES resume/rerun controls.
- Samples: aggregate sample table from recent backend runs plus mock/demo NIPT/WGS examples.
- Workflows: WES, PGT-A, NIPT qsub, NIPT docker, and WGS templates with implementation status.
- Failures: consolidated failed-run triage view with failed step, error type, stderr excerpt, retry suggestion, and detail link.
- Settings: environment/API display and demo-mode notes; no secrets.

### Component and data rules

- Shared components live under `frontend/src/components`.
- Status color/icon/text mapping is centralized in `frontend/src/lib/status.ts`.
- API access remains isolated in `frontend/src/api.ts`; no frontend code connects to Airflow DB or Postgres directly.
- Mock-only NIPT/WGS/workflow/resource fixtures live in `frontend/src/mocks/platform.ts` and are labeled `demo/mock`.
- Logs default to stderr for failed runs, support stream tabs, search, copy excerpt, fixed-height scroll, error highlighting, and missing-log states.

### Verification

T096 remote validation on `ssh fengxian`:

- `docker build --target test -f frontend/Dockerfile frontend`: passed, 7 Vitest tests.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker compose -f docker-compose.yaml build frontend`: passed, including `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`: passed.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200 after the recreated nginx container was ready.
- Backend API spot checks on port 8000 confirmed existing PGT-A and WES run detail/samples/rules/QC/log endpoints still return data consumed by the redesigned UI.

`npm run lint` is not available in `frontend/package.json`; the package currently defines only `test` and `build`.

## 10. T097 PGT-A-only deployment scope

T097 narrows the deployable frontend demo surface to PGT-A only. This is a product/deployment scope change, not a backend/DAG deletion.

### Current visible routes

```text
/dashboard
/submit
/runs
/runs/:analysisId
/samples
/failures
/settings
```

The `/workflows` route remains available for direct navigation during development, but the sidebar no longer links to it and the page only shows the PGT-A workflow template.

### Visible PGT-A behavior

- Dashboard cards and pipeline state use only `pipeline=pgta` backend runs.
- Submit Task defaults to and only allows PGT-A server-path scan/create/submit.
- Runs is locked to the PGT-A pipeline filter.
- Samples aggregates PGT-A samples only.
- Failures shows PGT-A failed runs only.
- Run Detail keeps the PGT-A tabs: Overview, Samples, Workflow, QC, Logs, Files, Config.
- PGT-A `baseline_qc` failed/terminated resume remains visible through `Resume with 64 cores`.
- Workflow success and QC failure remain displayed separately for `PGTA_20260706_162150_00C4FD`.

### Hidden or deferred behavior

- WES qsub is not shown in the current frontend demo and should not be presented as deployed, even though historical backend/DAG/Snakemake code remains in the repository.
- NIPT qsub and WGS are not shown in the current frontend demo. T103 exposes NIPT Docker as a deployable scanned-batch workflow; see sections 14 and 16.
- MailHog/SMTP success/failure notification remains deferred; `T034` and `T063` stay todo.
- No backend/DAG/Snakemake code is removed by T097.

### T097 verification

Remote validation on `ssh fengxian` at frontend code commit `3119be5`:

- `docker build --no-cache --target test -f frontend/Dockerfile frontend`: passed, `1 test file`, `5 tests`.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker compose -f docker-compose.yaml build frontend`: passed, including `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`: passed, recreated only the frontend container.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200 from nginx.
- `GET /api/health`: `{"status":"ok"}`.
- `GET /api/health/airflow`: metadatabase and scheduler healthy.
- `GET /api/runs/PGTA_20260706_162150_00C4FD`: returned the PGT-A detail payload.
- `GET /api/runs/PGTA_20260706_162150_00C4FD/qc`: returned `pass=0,warn=0,fail=14,unknown=0`.
- `GET /api/runs/PGTA_20260706_162150_00C4FD/logs?stream=stderr&tail=20`: returned stderr tail lines.

## 11. T098 Frontend/Airflow data reconciliation

The frontend does not connect directly to Airflow, the Airflow metadata DB, or Postgres. The supported data path remains:

```text
React frontend -> FastAPI backend -> Airflow REST API + biodemo DB
```

T098 fixes two places where the PGT-A-only UI could look disconnected from Airflow/backend state:

- PGT-A Run Detail now auto-syncs active runs through `POST /api/runs/{analysis_id}/actions/sync-airflow`. When a selected PGT-A run has `dag_run_id` and status `submitted/running/queued/scheduled`, the page syncs immediately and then every 15 seconds until the backend returns a terminal state.
- `GET /api/runs` now returns run-level `qc_status` aggregated from sample `qc_status` values, so Dashboard/Runs/Samples no longer show `unknown` while the detail `/qc` endpoint already shows PGT-A baseline QC failures.

Expected product semantics:

- Frontend run counts are analysis-run counts from biodemo, not raw Airflow DAG-run counts.
- A resumed PGT-A analysis can have multiple historical Airflow DAG runs, but the frontend shows one `analysis_id` with the latest `dag_run_id`.
- Workflow status and QC status remain separate. `PGTA_20260706_162150_00C4FD` is workflow `success` with sample/run QC `fail`.

### T098 verification

Remote validation on `ssh fengxian` at commit `f64e0d2`:

- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker run --rm airflow-demo/backend:t098-test pytest -q`: passed, `53 passed`.
- `docker build --target test -f frontend/Dockerfile frontend`: passed, `6` Vitest tests.
- `docker compose -f docker-compose.yaml build backend frontend`: passed, including frontend `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend frontend`: passed; backend became healthy and frontend returned HTTP 200 on port `12959`.
- `GET /api/runs?pipeline=pgta&limit=50&offset=0` returned `17` PGT-A analysis runs; `PGTA_20260706_162150_00C4FD` had `status=success` and `qc_status=fail`.
- `GET /api/runs/PGTA_20260706_162150_00C4FD/qc` returned `pass=0,warn=0,fail=14,unknown=0`.
- Airflow `bio_pgta` listed `20` DAG runs total and `5` DAG runs matching `PGTA_20260706_162150_00C4FD`; the latest matching run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` was `success`.

## 12. T099 PGT-A Run Tracker and submit handoff

T099 changes the PGT-A-only Dashboard from split recent-failure/recent-success blocks into one run-centric tracker. The primary user story is: a bioinformatics operator enters Dashboard and can immediately find a project/run, see whether it is in Airflow, see current workflow progress, and take View/Submit/Sync action.

### Dashboard tracker

- Dashboard calls `GET /api/runs?pipeline=pgta&limit=50&offset=0`, then enriches the first visible runs with run detail and rule events.
- The main list is `PGT-A Run Tracker`; it no longer separates failed and completed runs into different panels.
- Each row shows project name, `analysis_id`, workflow status, QC status, sample count, created/started/duration fields, current step, progress percentage, and a progress bar.
- Project display name comes from `detail.params.project_name`; if absent it falls back to `analysis_id`.
- Rows are ordered by operational urgency: active runs, failed/QC failed, created-only, then recent success.
- Filters are: All, Running, Submitted / queued, Created only, Failed, QC failed, Success.
- Created-only runs show `Not in Airflow` and can be submitted from the tracker.
- Active runs can be synced from the tracker; Dashboard polls every 15 seconds only while active PGT-A runs are present.
- The bottom of Dashboard uses three equal panels: Service health, PGT-A resource overview, and PGT-A workflow.

### Progress semantics

Progress is a frontend demo estimate from current backend contracts, not a true Airflow task-progress API:

- `created`: `0%`, `Created only`, `Not in Airflow`.
- `submitted/queued/scheduled`: `5-10%`, Airflow handoff visible.
- `running`: if rule events exist, progress is terminal rule events divided by total rule events; otherwise `15%` with `waiting for workflow events`.
- `success`: `100%`.
- `failed`: shows the failed step when available and preserves any rule-derived partial progress.

A future backend endpoint should expose Airflow task instances and Snakemake progress snapshots directly; until then the UI labels this as an estimate.

### Submit handoff

Submit Task now treats "create" and "submit to Airflow" as distinct observable states:

- The primary action is `Create and submit to Airflow`; it performs `POST /api/runs`, then immediately `POST /api/runs/{analysis_id}/actions/submit`, then fetches `GET /api/runs/{analysis_id}`.
- The secondary action is `Create only`; it creates a backend run and shows that it will not be visible in Airflow until submitted.
- A successful handoff summary displays `analysis_id`, `dag_run_id`, backend status, and pipeline.
- If submit returns without `dag_run_id`, the UI shows `Submit returned without dag_run_id; check backend/Airflow handoff.`
- Submit preview uses separated fields so `Pipeline` and `PGT-A` do not visually collide.

### Scan folder view

PGT-A scan results are grouped by `source_dir`:

- The top-level scan table shows folder name, relative parent path, sample count, and a folder-level checkbox.
- FASTQ file names are shown only when the folder row is expanded.
- Absolute FASTQ paths are hidden by default and shown only in a per-sample `full path` disclosure.
- Selecting a folder selects all samples in that folder; baseline QC still requires at least two selected samples.

### T099 verification

Remote validation on `ssh fengxian`:

- `docker build --target test -f frontend/Dockerfile frontend`: passed, `7` Vitest tests.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker compose -f docker-compose.yaml build frontend`: passed, including `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`: passed, recreated only the frontend container.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200 from nginx.
- `GET /api/health`: `{"status":"ok"}`.
- `GET /api/health/airflow`: metadatabase and scheduler healthy.
- `GET /api/runs?pipeline=pgta&limit=20&offset=0`: returned 19 total PGT-A analysis runs and included `PGTA_20260707_182024_8CA2A0` plus `PGTA_20260707_182056_39A374`.
- `GET /api/runs/PGTA_20260707_182024_8CA2A0` and `GET /api/runs/PGTA_20260707_182056_39A374`: both returned non-null `dag_run_id` and `status=success`.
- Deployed frontend bundle contains `PGT-A Run Tracker`.

## 13. T100 PGT-A submit/Airflow status auto-sync

T100 fixes the operator-visible gap where a run could be created, submitted to Airflow, and still remain displayed as `submitted` in the frontend/backend after Airflow had already completed it.

### Root cause

Observed run:

```text
analysis_id: PGTA_20260708_012630_352915
dag_run_id: manual__PGTA_20260708_012630_352915
backend status before sync: submitted
Airflow state: success
```

The submit endpoint correctly returned a `dag_run_id`, and Airflow completed the DAG run. The missing frontend behavior was a post-handoff reconciliation call to:

```text
POST /api/runs/{analysis_id}/actions/sync-airflow
```

Without that call, biodemo could keep `status=submitted` until a user clicked Sync or another page-level poll happened.

### Required frontend behavior

- `Create only` creates a biodemo run and must keep showing `Not visible in Airflow until submitted`.
- `Create and submit to Airflow` must:
  - call `POST /api/runs`;
  - call `POST /api/runs/{analysis_id}/actions/submit`;
  - if a `dag_run_id` is returned, call `POST /api/runs/{analysis_id}/actions/sync-airflow`;
  - briefly retry sync so fast metadata runs can display `success` in the handoff summary;
  - show a warning if submit returns without `dag_run_id`.
- Dashboard must auto-sync active/submitted PGT-A tracker rows immediately and then every 15 seconds while such rows remain active.
- The UI must continue to route all Airflow status reconciliation through FastAPI; it must not query Airflow DB directly.

### Product semantics

- `created`: the project exists only in biodemo/shared files and is not visible in Airflow.
- `submitted`: Airflow handoff has a `dag_run_id`, but biodemo has not yet observed a terminal Airflow state.
- `running`: Airflow/Snakemake activity is in progress or rule events show activity.
- `success/failed`: terminal state after backend `sync-airflow` has reconciled Airflow state into biodemo.

### T100 verification

Remote validation on `ssh fengxian`:

- Red frontend test target first failed because Dashboard and Submit did not call `sync-airflow`.
- `docker build --target test -f frontend/Dockerfile frontend`: passed after implementation, `7` Vitest tests.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker compose -f docker-compose.yaml build frontend`: passed, including `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`: passed, recreated only the frontend container.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200 from nginx.
- `GET /api/health`: `{"status":"ok"}`.
- `GET /api/health/airflow`: metadatabase and scheduler healthy.
- Manual sync of `PGTA_20260708_012630_352915` reconciled backend status from `submitted` to `success`; no workflow rerun was submitted.
- `GET /api/runs?pipeline=pgta&status=submitted&limit=20&offset=0`: returned no stuck submitted PGT-A runs after reconciliation.

Remaining gap: authoritative Airflow task progress still needs a backend task-instance/attempt-history API. Current Dashboard progress remains a demo estimate based on run state and Snakemake rule events.

## 14. T101 PGT-A + NIPT Docker deployment scope

T101 expands the deployable frontend surface from PGT-A-only to two runnable workflows: PGT-A and NIPT Docker. WES qsub, NIPT qsub, WGS, and email notification remain hidden/deferred in the current demo.

### Visible routes and resources

- Sidebar links Dashboard, Submit Task, Runs, Samples, Workflows, Failures, and Settings.
- Dashboard loads recent runs across `pipeline=pgta` and `pipeline=nipt_docker`, then displays them in one run tracker with pipeline badges, project/run ordering, progress estimate, QC status, and View/Submit/Sync actions.
- Dashboard bottom panels are Service health, PGT-A/NIPT resource overview, and deployed workflow scope.
- Submit Task offers only PGT-A and NIPT Docker in `PipelineSelector`.
- Runs, Samples, and Failures filters include `PGT-A` and `NIPT Docker`; WES/NIPT qsub/WGS are not presented as deployed options.
- Workflows shows exactly PGT-A and NIPT Docker templates.

### NIPT Docker submit UI

T103 supersedes the template-run UI. The NIPT Docker form now uses server-path scanned chip batches:

- `rawdata_root` from `GET /api/input/roots?pipeline=nipt_docker`.
- `selected_samples` from `POST /api/input/scan`; `template_id` is no longer sent by new UI submissions.
- Folder-level checkbox selects all samples in one NIPT chip; expanded rows show sample id and FASTQ file names.
- `run_mode`: `mount_smoke` by default; `full_run` is visible but guarded by backend `NIPT_ALLOW_HEAVY_RUN=false` unless explicitly enabled for a heavy run.
- `cores`: integer, default 40, max 40.
- `project_name` and `note` are sent in `params`.
- The primary action remains `Create and submit to Airflow`, calling `POST /api/runs`, then `POST /api/runs/{analysis_id}/actions/submit`, then `sync-airflow`.
- Successful handoff displays `analysis_id`, `dag_run_id`, backend status, and pipeline.

### T101 verification

Remote validation on `ssh fengxian`:

- `docker build --target test -f frontend/Dockerfile frontend`: passed, 9 Vitest tests.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler airflow-api-server frontend`: passed; frontend production build ran `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend airflow-api-server airflow-scheduler airflow-worker frontend`: passed.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200.
- Final NIPT Docker smoke `NIPT_20260708_033450_8362A0` submitted to `manual__NIPT_20260708_033450_8362A0` and reached Airflow/backend `success`.
- `/api/runs/NIPT_20260708_033450_8362A0/qc` returned `pass=96,warn=0,fail=0,unknown=0`.
- `/api/runs?pipeline=nipt_docker&limit=3&offset=0` returned the final run with `qc_status=pass`.
- NIPT artifacts included `nipt_qc_summary`, `nipt_docker_compose`, `nipt_run_config`, `nipt_airflow_request`, and `nipt_docker_command`; WES artifact keys were not exposed for the NIPT run.

## 15. T102 Airflow + pipeline progress observability

T102 replaces the Dashboard-only estimate with backend progress data from `GET /api/runs/{analysis_id}/progress`.

### Dashboard tracker

- Dashboard loads recent PGT-A and NIPT Docker runs, calls `sync-airflow` for active runs, then calls `/progress`.
- Each tracker row shows the backend `percent`, `current_step`, `current_source`, and note from `/progress`.
- Airflow-only historical runs still show task-instance progress even when no rule events were captured.
- Active rows keep the 15-second polling behavior; polling refreshes both backend status and progress.

### Run Detail workflow tab

- Run Detail is shared by PGT-A and NIPT Docker; it no longer gates NIPT behind a PGT-A-only message.
- The Overview tab includes a progress card with percent, current source, and progress note.
- The Workflow tab is split into `Airflow tasks` and `Pipeline steps`.
- `Airflow tasks` renders task id, state, operator, try number, start/end time, and duration from `/progress.airflow_tasks`.
- `Pipeline steps` renders rule/runner events from `/progress.rule_events`.
- If `rule_events` is empty, the UI shows `No rule events captured` while still keeping Airflow task progress visible.

### Progress display rules

- `created` stays `0%` and shows `Not in Airflow`.
- Submitted/queued/scheduled runs show Airflow handoff progress.
- PGT-A run task `run_pgta_target` and NIPT run task `run_nipt_docker` can be refined by pipeline events.
- `success` shows `100%`.
- Failed runs show the failed Airflow task or failed pipeline step when available.

### T102 frontend verification

Remote validation on `ssh fengxian`:

- `docker build --target test -f frontend/Dockerfile frontend`: passed, 10 Vitest tests.
- `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler airflow-api-server frontend`: passed; frontend production build ran `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend airflow-api-server airflow-scheduler airflow-worker frontend`: passed.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200.
- PGT-A progress smoke `PGTA_20260708_050811_A24E36` reached `success` with Airflow tasks plus `metadata=success` pipeline event.
- NIPT Docker progress smoke `NIPT_20260708_050843_B3B05E` reached `success` with Airflow tasks plus `nipt_mount_smoke=success` pipeline event.

## 16. T103 Batch Scan And Auto Intake UI

- Submit Task uses one server-path scan experience for PGT-A and NIPT Docker.
- NIPT Docker no longer shows `run1/run2` or a `NIPT template` selector.
- Scan roots are loaded from `GET /api/input/roots?pipeline=...`.
- Batch rows show folder/chip name, relative path, sample count, and a folder
  checkbox. Expanding a batch shows sample id plus R1/R2 file names; absolute
  paths stay hidden in a details element.
- NIPT Docker create requests send `rawdata_root`, `selected_samples`,
  `run_mode`, `cores`, `project_name`, and optional `note`.
- Dashboard adds a read-only `Intake auto scanner` panel backed by
  `GET /api/intake/status`; page refresh must not call
  `POST /api/intake/scan-and-submit`.
- Automatic create+submit is owned by the Airflow `bio_intake_scan` DAG after
  bootstrap protects historical batches.

## 17. T104 Dashboard Command Center

T104 changes the Dashboard from a run-detail fan-out page into a backend
aggregation client.

### First-screen data calls

Dashboard first load calls only:

- `GET /api/dashboard/overview?pipeline=...&period=7d`
- `GET /api/dashboard/runs?pipeline=...&limit=10&offset=0`
- `GET /api/intake/status?...`
- `GET /api/system/resources`

The Dashboard page must not loop over visible runs and call
`/api/runs/{analysis_id}`, `/progress`, or `/rules` for each row. Active rows
still use the existing `sync-airflow` action every 15 seconds, then reload the
aggregated page.

### Layout

- Left rail: `All pipelines`, `PGT-A`, `NIPT Docker`.
- Main top panel: status distribution, 7-day activity sparkline, QC/failure
  focus.
- Run Tracker: paginated rows, default `limit=10`, status filter, keyword
  search, previous/next controls.
- Intake scanner: `Observed`, `Stable ready`, `Auto-submitted`, `Bootstrap
  observed`, `Disabled`, and `Error`; observed/bootstrap states must not display
  as queued execution.
- Bottom panels: `Service & Node Health`, `Pipeline Resources`, and `Workflow
  Activity`.

### Run Tracker row fields

Rows render `project_name`, `analysis_id`, `pipeline`, workflow status,
`qc_status`, `sample_count`, timestamps, progress percent, current Airflow task,
current pipeline rule, `progress_source`, and `not_in_airflow`.

`current_airflow_task` is the project-level Airflow task. `current_pipeline_rule`
is the Snakemake/runner event layer. The UI must keep these labels separate so
operators can tell whether a run is in Airflow handoff, a project task, or an
inner bioinformatics rule.

### Visual rules

Charts remain lightweight CSS/SVG, with no Recharts/D3/Ant Design dependency in
T104. Status meaning still comes from `StatusBadge` and `frontend/src/lib/status.ts`.

## 18. T105 Intake Scanner Settings Console

T105 extends `/settings` with a read-only intake scanner readiness console.

### Data calls

The Settings intake section loads:

- `GET /api/intake/config`
- `GET /api/intake/status?limit=100`
- `GET /api/intake/scanner-state`

It does not call `POST /api/intake/scan-and-submit`, does not unpause
`bio_intake_scan`, and does not expose any NIPT `full_run` trigger.

### Display

- Scanner card: `bio_intake_scan` DAG id, Airflow reachable/unavailable,
  paused/unpaused/unknown state, latest scanner DAG run id/state/start/end.
- Config card: sanitized `config/intake.yaml` source, ready rule, stable scan
  count, and default auto-submit setting.
- Root cards: PGT-A and NIPT Docker container roots, NIPT file flavor and
  clean FASTQ patterns, and auto-submit target/run mode.
- Discovery cards: recent `intake_discovery` rows with
  `Bootstrap observed`, `Observed`, `Stable ready`, `Auto-submitted`,
  `Disabled`, or `Error`.

### Product boundary

This page is an operator visibility surface before enabling automatic intake.
It intentionally provides only `Refresh`, `View Dashboard`, and `View Runs`
actions. Airflow DAG unpause and bootstrap/scan actions remain runbook-driven
until explicitly approved.
