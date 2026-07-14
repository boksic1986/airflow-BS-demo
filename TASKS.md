# TASKS.md

任务状态：`todo` / `in_progress` / `blocked` / `review` / `done`。

## P0 文档和环境探测

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T000 | 初始化仓库文档 | coordinator/docs | none | docs, AGENTS, skills | 文档完整、占位符明确 | done |
| T001 | 探测服务器环境 | infra | T000 | SERVER_INFO.md 更新 | docker/qsub/python/node 状态清楚 | done |
| T002 | 确定部署路径和数据路径 | infra/coordinator | T001 | CURRENT_STATE.md 更新 | 项目路径和 shared 路径确定 | done |
| T003 | 确定 demo 数据策略 | coordinator/snakemake | T000 | mock samples 规范 | 不使用真实患者数据 | todo |
| T004 | fengxian PGT-A demo 测试计划 | coordinator/docs | T000 | docs/18_PGTA_FENGXIAN_TEST_PLAN.md | pgta/bio_pgta 命名、Compose 准入、Level 0-4 验收、BS10610 迁移注意事项明确 | done |
| T005 | 本地 Git/GitHub 和插件工作流文档 | coordinator/docs | T000,T004 | git remote, docs/19, plugin usage docs | 本地 main 仓库指向 GitHub remote；superpowers/GitHub 插件和 fengxian 镜像规则写入文档 | done |

## P1 Airflow Docker 基础部署

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T010 | 创建 docker-compose 基础服务 | infra | T001 | docker-compose.yaml, .env.example | docker compose config 通过 | done |
| T011 | 启动 Airflow/Postgres/Redis | infra | T010 | Airflow UI/API 可访问 | airflow health 正常 | done |
| T012 | 增加 MailHog demo 邮件服务 | infra | T010 | mailhog service | http://host:8025 可访问 | done |
| T013 | 定义 shared volume 目录 | infra | T010 | shared/{uploads,runs,reports,logs} | 容器内路径一致 | done |
| T014 | fengxian 用户级 Docker Compose v2 准入 | infra | T001,T004 | `$HOME/.docker/cli-plugins/docker-compose` | `docker compose version` 输出固定 v2 版本，未做系统级 Docker 升级 | done |

## P2 Backend API 和数据库

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T020 | FastAPI 项目骨架 | backend | T010 | backend/app | /health 返回 ok | done |
| T021 | biodemo DB models/migrations | backend | T020 | analysis_run/sample/rule_event/qc/artifact | migration 可重复执行 | done |
| T022 | PGT-A 服务器路径样本发现和项目创建 | backend | T021 | `/api/input/scan`, JSON `/api/runs`, selected manifest | 白名单 rawdata_root 可扫描 R1/R2；创建 `created` run、sample rows、`samples.selected.tsv` 和 `request.json`；不触发 Airflow | done |
| T023 | Airflow API client | backend | T020,T011 | trigger/list/get dag run | mock 或真实 API 测试通过 | done |
| T024 | run 状态 API | backend | T021 | `/api/runs` list/detail/samples endpoints | 可返回 pgta run 列表、detail 和 sample fq1/fq2 路径 | done |
| T025 | logs/artifacts API | backend | T021 | PGT-A v1 log tail + dynamic artifact list | `stdout/stderr/metadata` 可读取；缺失文件返回 `LOG_NOT_FOUND`；路径穿越被拒绝 | done |
| T026 | Snakemake event receiver | backend | T021 | `/api/events/snakemake`, `/api/runs/{analysis_id}/rules` | 可幂等 upsert rule event；PGT-A logger rule 状态可从 API 查询 | done |
| T027 | PGT-A `pgta` Airflow trigger API 支持 | backend | T021,T022,T023,T004 | created run -> Airflow `bio_pgta` trigger | 已创建的 `pgta` metadata run 可通过 submit action 提交为 DAG run；状态推进到 `submitted` 且 `dag_run_id` 非空 | done |
| T090 | sample lifecycle status sync | backend/docs | T024,T027,T025 | submit/sync updates `sample.status` | submit/reanalyze 后 sample 为 `running`；显式 sync 后随 Airflow 变 `success/failed`；远端 backend pytest 48 passed；已同步近期可见 run 的 sample 状态 | done |

## P3 Airflow DAG

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T030 | DAG 公共工具 | airflow | T011,T023 | dags/common | shared-root path check, mkdir, subprocess stdout/stderr helpers added; Dockerized DAG tests and import check passed | done |
| T031 | bio_wes_qsub DAG 骨架 | airflow | T030 | dags/bio_wes_qsub.py | `manual__WES_AIRFLOW_20260705_004506` Airflow smoke success; final summary, qsub logs, and JSONL events generated | done |
| T032 | bio_nipt_qsub DAG 骨架 | airflow | T030 | dags/bio_nipt_qsub.py | dry run/mock run 成功 | todo |
| T033 | bio_nipt_docker DAG 骨架 | airflow | T030 | dags/bio_nipt_docker.py | T101 `bio_nipt_docker` template-run v1 imported cleanly; mount_smoke DAG run `manual__NIPT_20260708_033450_8362A0` reached success | done |
| T034 | email notify task | airflow/backend | T030,T012 | success/fail notify | MailHog 收到邮件 | todo |
| T035 | bio_pgta DAG 骨架 | airflow | T030,T027,T004 | dags/bio_pgta.py, pgta metadata runner | metadata target real-light run 成功，不使用 qsub；`logs/run_metadata.tsv` 生成 | done |
| T036 | PGT-A Airflow-only Snakemake 9 logger DAG | airflow/snakemake | T035,T045 | `bio_pgta_airflow`, repo-local logger plugin | Airflow-only manifest run 使用 Snakemake 9.23.1 `--logger airflow-demo` 成功；生成 events JSONL、summary TSV，并在 Airflow task log/XCom 展示状态 | done |

## P4 Snakemake/qsub 接入

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T040 | WES mock Snakefile | snakemake | T013 | pipelines/wes/workflow | WES mock 两样本 Snakemake dry-run 通过，显示 all/fastp/bwa_mem/markdup/final_summary 共 8 个 jobs | done |
| T041 | qsub submit wrapper | snakemake | T040,T026 | qsub_submit.py | mock mode 可生成 `MOCK-*` qsub_jobid、qsub stdout/stderr 和 JSONL/Backend event；`WES_20260704_180650_MOCK` 已通过 `/rules` 查询 | done |
| T042 | qsub profile | snakemake | T041 | profiles/qsub/config.yaml, snakemake_runner | Dockerized `snakemake-runner` 固定 Snakemake 9.23.1 + `cluster-generic` plugin；`--profile profiles/qsub` 已在 `fengxian` 跑通 WES mock，生成 final summary、qsub stdout/stderr 和 JSONL events | done |
| T043 | rule event logger | snakemake/backend | T026,T036 | PGT-A Snakemake 9 logger POST events | PGT-A rule 状态在 biodemo DB 和 `/api/runs/{analysis_id}/rules` 可见；WES mock qsub job id 路径已由 T041/T042 跑通 | done |
| T044 | resume/rerun 策略 | snakemake/airflow | T031,T040 | WES `new/resume/rerun_rule` -> Snakemake flags; command log artifact | `WES_20260705_162041_2507AF` initial/resume/rerun_rule smoke success；`snakemake.command.txt` contains `--forcerun fastp` and no `--forceall` | done |
| T045 | PGT-A Snakemake runner | snakemake/airflow | T035,T004 | pgta config 生成和 metadata/dry-run runner | metadata runner 已随 T035 通过；Airflow-only Snakemake 9 logger 已随 T036 通过；`dryrun_cnv` 和 `invalid_target` runner 已在 `fengxian` 通过 smoke；输出只写 shared/runs/<analysis_id>，PGT_A 目录只读 | done |
| T085 | PGT-A real target audit | coordinator/airflow | T045,T084 | docs/20 audit, baseline_qc contract | 只读审计确认 `baseline_qc` 存在、需要至少 2 个样本、会触发 mapping+metadata+baseline QC；未运行重任务 | done |
| T086 | PGT-A staged baseline_qc integration | backend/airflow/frontend | T085 | baseline_qc allowlist, build_ref config, frontend target label | API/DAG/frontend 支持 `target=baseline_qc`，创建和 submit 均要求至少 2 样本；远端 Docker 化 backend/frontend/DAG tests 通过；真实 Level 4 smoke 待用户确认 | done |
| T088 | PGT-A Snakemake cache permission fix | airflow/snakemake | T035,T045 | run-local `XDG_CACHE_HOME`, command artifact | `PGTA_20260706_140854_8F2CA4` metadata submit smoke success；stderr 不再出现 `/home/airflow/.cache/snakemake` PermissionError；artifacts include `snakemake_command` | done |
| T089 | demo log/timezone alignment | infra/frontend | T011,T050 | Compose `TZ`, Airflow core/UI timezone, frontend display timezone | `fengxian` containers and Airflow config use `Asia/Shanghai`; frontend renders UTC API timestamps as `Asia/Shanghai`; DB timestamps remain timezone-aware | done |
| T091 | PGT-A 64-core runner and frontend auto-sync | airflow/frontend/docs | T086,T089,T090 | `PGTA_SNAKEMAKE_CORES=64`, PGT-A command artifact, frontend active-run polling | `bio_pgta` and `bio_pgta_airflow` default to `--cores 64` with env override; selected active run auto-calls `sync-airflow` every 15s and stops at terminal state; current running baseline_qc was not interrupted; remote tests/deploy passed at `fb107a4` | done |

## P5 Frontend

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T050 | React 项目骨架 | frontend | T020 | frontend/src | React/Vite app 由 Docker nginx 在 12959 提供访问 | done |
| T051 | Submit Analysis 页面 | frontend | T022,T023 | PGT-A server-path form UI | 填写 rawdata_root、扫描候选样本、勾选后创建 run，并可从 created run 提交 `bio_pgta` metadata | done |
| T052 | Runs Dashboard | frontend | T024 | run list/status cards | 可筛选 pipeline/status | done |
| T053 | Run Detail 页面 | frontend | T024,T026 | overview/airflow/snakemake tabs | 展示 rule 状态 | done |
| T054 | QC 面板 | frontend | T060 | WES mock QC panel | Run detail 显示 WES/PGT-A QC pass/warn/fail/unknown summary 和样本级指标表；frontend Docker test target 14 tests passed | done |
| T055 | Log Viewer | frontend | T025 | stdout/stderr tail | 失败默认显示 stderr | done |
| T056 | Reanalysis UI | frontend/backend | T044 | WES mock create/submit panel plus resume/rerun buttons | 前端 Docker test target 10 tests passed；WES detail can trigger `resume` and `rerun_rule` via backend | done |
| T057 | PGT-A run detail 展示 | frontend | T027,T035,T025 | pgta run overview/sample/rule/log/artifact/sync UI | PGT-A run detail v1 可查看 rules/logs/artifacts；T084 failure smoke 后失败摘要可通过现有 detail/logs API 查看 | done |
| T096 | Frontend platform UI redesign v2 | frontend/docs | T050-T057,T054,T056 | routed app shell, Dashboard/Submit/Runs/Run Detail/Samples/Workflows/Failures/Settings, shared components, design docs | remote frontend Docker test target passed 7 tests; frontend production build passed `tsc -b && vite build`; 12959 HTTP 200; PGT-A/WES backend API spot checks passed | done |
| T097 | PGT-A-only frontend deployment scope | frontend/docs | T096,T027,T087,T092 | Sidebar/Dashboard/Submit/Runs/Samples/Failures scoped to PGT-A; WES/NIPT/WGS hidden from deployable demo; docs/state updated | remote frontend Docker test target passed 5 PGT-A-only tests; frontend build/deploy on 12959 verified; mail notification remains todo and WES qsub historical code remains untouched | done |
| T098 | PGT-A frontend/Airflow data reconciliation | frontend/backend/docs | T097,T090,T087,T092 | active PGT-A detail auto-sync through backend `sync-airflow`; `/api/runs` run-level QC aggregation from samples; docs/state updated | remote backend pytest passed 53 tests; remote frontend Docker test target passed 6 tests; backend/frontend build and redeploy passed; `PGTA_20260706_162150_00C4FD` list/detail/Airflow latest state reconciled as workflow success + QC fail | done |
| T099 | PGT-A Dashboard run tracker and submit handoff | frontend/docs | T098,T097,T027 | Dashboard uses one project/run-centric PGT-A tracker with progress estimate, filters, View/Submit/Sync actions, bottom health panels; Submit Task uses primary create+submit handoff, secondary create-only, and folder-based scan results | remote frontend Docker test target passed 7 tests; frontend production build passed `tsc -b && vite build`; frontend 12959 HTTP 200; PGT-A list/detail spot checks confirmed `PGTA_20260707_182024_8CA2A0` and `PGTA_20260707_182056_39A374` have non-null `dag_run_id` and `status=success` | done |
| T100 | PGT-A submit 后 Airflow 状态自动回写 | frontend/docs | T099,T098,T027 | Submit Task 在 create+submit 后主动调用 `sync-airflow` 并短轮询 handoff 状态；Dashboard 对 active/submitted tracker rows 立即 sync 并每 15 秒 sync；记录 submitted 卡住根因 | red frontend test first failed on missing sync calls; remote frontend Docker test target passed 7 tests; frontend production build/deploy passed; `PGTA_20260708_012630_352915` was reconciled from backend `submitted` to Airflow/backend `success`; submitted PGT-A list returned empty | done |
| T101 | NIPT Docker template-run deployment | backend/airflow/frontend/docs | T033,T071,T072,T099,T100 | `pipeline=nipt_docker` API create/submit, `bio_nipt_docker` DAG, repo-owned Docker runner, NIPT QC/log/artifact integration, PGT-A + NIPT Docker frontend scope, docs/state updates | remote frontend test passed 9 tests; backend targeted tests passed 31 then 17 after artifact fix; NIPT DAG/runner tests passed 9; compose config/build/recreate passed; final smoke `NIPT_20260708_033450_8362A0` reached Airflow/backend success with QC `pass=96` | done |
| T102 | Airflow + Snakemake progress observability | backend/airflow/snakemake/frontend/docs | T099,T100,T101,T026,T043 | `/api/runs/{analysis_id}/progress`, Airflow task-instance client, PGT-A/NIPT runner progress events with JSONL fallback, Dashboard/Run Detail progress UI, docs/state updates | remote backend targeted tests passed 29; Airflow DAG/runner tests passed 35; frontend Docker test target passed 10; deploy/recreate passed; progress smokes `PGTA_20260708_050811_A24E36` and `NIPT_20260708_050843_B3B05E` returned Airflow tasks plus pipeline events | done |
| T103 | PGT-A/NIPT batch scan and auto intake | backend/airflow/frontend/docs | T101,T102,T022,T027 | NIPT Docker server-path scan replaces new run1/run2 submissions; `intake_discovery`; `/api/input/roots`; `/api/intake/status`; `/api/intake/scan-and-submit`; `bio_intake_scan`; Dashboard intake panel; Submit one-run-per-NIPT-batch | remote compose config passed; frontend Docker test passed 10; backend targeted pytest passed 25; Airflow DAG tests passed 4 and NIPT runner/progress tests passed 12; deploy/recreate/migration passed; scanned NIPT smoke `NIPT_20260708_072349_4F942A` reached success; intake bootstrap recorded existing batches without auto-submit | done |
| T104 | Dashboard performance, observability, and intake config | backend/frontend/docs | T103,T102 | `/api/dashboard/overview`; `/api/dashboard/runs`; `/api/system/resources`; `/api/intake/config`; `config/intake.yaml`; Dashboard pipeline selector, charts, paginated Run Tracker, resource tabs, and non-queued intake states | remote frontend Docker test passed 10; backend targeted pytest passed 7; final compose/deploy/runtime curl checks recorded in HANDOFF | done |
| T105 | Intake settings and scanner readiness console | backend/frontend/docs | T104,T103 | `GET /api/intake/scanner-state`; Settings read-only Intake Scanner console; config/status/scanner-state visibility; no unpause/scan-now/full-run frontend actions | remote backend targeted pytest passed 10; frontend Docker test target passed 11; backend/frontend build/recreate passed; `/api/intake/scanner-state` returned `airflow_reachable=true,is_paused=true`; `bio_intake_scan` remained paused | done |
| T106 | Intake dry-run preview and auto-submit gating | backend/frontend/docs | T105,T104,T103 | `POST /api/intake/scan-preview`; `scan-and-submit` obeys global and pipeline `auto_submit.enabled` gates; Settings dry-run preview; default config keeps PGT-A/NIPT auto-submit disabled | remote compose config passed; backend targeted pytest passed 8; frontend Docker test target passed 11; backend/frontend build/recreate passed; preview returned `would_submit=0` and left discovery `21/21` plus NIPT runs `5/5`; `bio_intake_scan` remained paused | done |
| T107 | UI density fix and PGT-A DAG stages | frontend/airflow/backend/docs | T106,T102,T087,T095 | Submit preview definition layout; Samples source-file formatter; QC matrix with search/filter/pagination; PGT-A baseline_qc TaskGroup stages; staged progress weights and artifacts | remote compose config passed; frontend Docker test passed 13; backend targeted pytest passed 19; Airflow DAG/runner unittest passed 27; Airflow import check passed; backend/Airflow/frontend redeployed; `bio_pgta` task tree shows staged TaskGroup; metadata smoke `PGTA_20260708_141653_B57AB6` reached success; no heavy baseline_qc run started | done |
| T108 | Dashboard/Run Detail usability polish and controlled PGT-A rerun | frontend/backend/airflow/docs | T107,T104,T102,T095 | Dashboard sample throughput, table Run Tracker, readable current stage, ETA estimate, compact Intake scanner, Run Detail manifest/QC failure/config polish, controlled PGT-A `rerun_stage` | remote compose config passed; frontend Docker test passed 14; backend targeted pytest passed 25; Airflow DAG/runner unittest passed 28; backend/Airflow/frontend rebuilt and recreated; Dashboard APIs returned sample throughput/current-stage/ETA fields; light PGT-A metadata smoke `PGTA_20260708_160227_EFAD64` reached success; no intake unpause, no heavy baseline_qc, no NIPT full_run | done |
| T109 | PGT-A/NIPT Control Tower frontend polish | frontend/docs | T108,T104,T102 | Control Tower navigation labels, theme tokens, dark sidebar, Dashboard command summary, Submit Run stepper, Run Detail layered timeline, frontend-only stage labels | remote frontend Docker test target passed 14 Vitest tests; compose config passed in deployment dir; frontend image built from clean T109 worktree and 12959 returned HTTP 200; no backend API/DAG/intake/full-run behavior changes | done |
| T110 | Operator Workspace stability and action closure | backend/frontend/docs | T109,T108,T104 | responsive Control Tower; independent Dashboard loading boundaries; paginated Runs/Samples/Failures resources; aggregate failure diagnosis; feature component split | remote backend pytest passed 94; frontend Docker test passed 20; production `tsc -b && vite build` passed; final dashboard median warm response was about 33 ms with no active runs; 24 live-data browser viewport/page combinations passed without document horizontal overflow; backend/frontend redeployed only; intake remained paused and no workflow was triggered | done |
| T111 | Snakemake config editor and runtime profiles | backend/airflow/frontend/docs | T110,T107,T101 | approved PGT-A/NIPT runtime profiles; collapsed validated YAML editor; immutable requested/resolved config provenance; Compose hidden from frontend | remote backend pytest passed 103; Airflow unittest passed 74 with 5 expected skips; frontend Docker test passed 24 and production build passed; final reviewed-profile smokes `PGTA_20260710_110056_DC8A8D` and `NIPT_20260710_110057_79A631` reached success with resolved provenance; browser checks passed at 1440/390; intake remained paused | done |
| T112 | PGT-A Snakemake 9 predict and manifest intake | backend/airflow/snakemake/frontend/docs/qa | T111,T107,T103 | immutable PGT-A S9 release, predict-only profile, TaskGroup stages, rule logger, submitted/progress audit, QC/log index, full-sample and manifest validation | `pgta-s9-v1.4` deployed with full release checksum verification; 2 x 1M, full H3, and full H4/H5 manifest runs passed; READY mutation and crash-window duplication are blocked; scanner/events use service auth; PGT-A intake unpaused while NIPT auto-submit/full-run remain disabled; backend 113, Airflow 79 (5 expected skips), logger 5, frontend 25 tests passed | done |
| T113 | NIPT Snakemake 9 full analysis and live rule observability | backend/airflow/snakemake/frontend/docs/qa | T112,T111,T102 | derivative dual-runtime image; approved full profile; one-slot DAG gate; real-time logger forwarding; phase/rule/sample progress; paginated jobs/logs; 72-sample S7 comparison | 72-sample S9 run completed 591 jobs in about 24.8 minutes with 44.61 GiB observed peak memory; 592 persisted events all terminal success; key outputs byte-identical to S7 baseline; original image/bundle/input unchanged; offline OCI rollback archive generated; NIPT auto intake remains disabled | done |
| T114 | Run status, immutable timing, NIPT QC, and biodemo cleanup | backend/airflow/frontend/docs/qa | T113,T112,T110 | combined workflow/QC status; submit-to-first-finish timing; sample-count ETA; decision-metric QC; prediction output integrity; guarded CLI cleanup | backend 127, Airflow/runner 89 with 5 expected skips, frontend 28 passed; NIPT 72/72 sample QC pass with 504 metrics and 24m37s runtime; biodemo backed up then reduced from 49 to 3 complete runs and 75 samples; workdirs/Airflow history/FASTQ preserved | done |
| T115 | Platform Settings and Discovery Tracker consistency | backend/frontend/docs/qa | T114,T110,T105 | paginated/filterable intake status API; shared Dashboard/Settings discovery table; independent Settings loading states; responsive Settings layout | backend 129 and frontend 36 tests passed; production build and Compose config passed; live Settings had no document overflow at 1440/1280/1024/390; 25 discovery records paginate without changing the retained 3 runs or scanner state | done |
| T116 | Intake and Airflow strict history cleanup | backend/airflow/infra/docs/qa | T115,T114,T113,T112 | exact-snapshot CLI cleanup for discovery and Airflow history; PGT-A-only scheduled intake; legacy DAG deployment ignore; pg_dump-backed remote maintenance | backend 134 and DAG 90 tests passed with 5 expected skips; Airflow retained 2 PGT-A + 1 NIPT full runs and only three deployed DAGs; discovery reduced 25 to 1; scanner restored unpaused and a new PGT-A-only cycle did not recreate old rows | done |
| T117 | Submit semantics, workflow phase visualization, and PGT-A manifest recovery | backend/frontend/infra/docs/qa | T116,T112,T110 | remembered free-text Submitted by ID; low-pass WGS assay labels; bulk workflow summaries; selected/alternate Airflow paths; audited operator correction; recoverable pre-run manifest errors | backend 139, frontend 38, DAG 90 with 5 expected skips, production build and Compose passed; two retained PGT-A operators corrected to jiucheng; project-20260712 created one four-sample run PGTA_20260712_171630_AE8239 and entered Mapping without duplicate submission | done |
| T118 | PGT-A manifest hardening, five-sample auto intake, and scanner retention audit | backend/infra/docs/qa | T117,T116,T112 | ignore blank manifest lines; protect submitted discovery; recover stale state; atomically publish five-sample request; measure scanner growth | backend 141 passed; stale T112 discovery restored; project-20260713-five-samples created only PGTA_20260713_034634_939AFF and entered Mapping; scanner remained unpaused; 30-day scanner retention and Docker log rotation documented for a separate rollout | done |
| T119 | Operations age, Intake archive, and NIPT small-batch validation | backend/frontend/airflow/infra/docs/qa | T118,T115,T113 | terminal relative age; shared operations search; active/archived Intake lifecycle; PGT-A manifest archive; restricted NIPT discovery root; checksum-verified 10/15/20-sample manual full runs | migration applied; 6 completed discoveries archived and active=0; NIPT 10/15/20 runs reached success with 96/136/176 terminal events and all 45 samples QC pass; backend 168, frontend 40, DAG 3, build/Compose/browser checks passed; NIPT auto-submit remains disabled | done |
| T120 | NIPT YAML request parsing and explicit intake trigger | backend/infra/docs/qa | T119,T113 | path-free YAML request contract; approved-root batch resolution; sample selection; stable-scan and explicit-submit gates; request-only archive; dedicated backend inbox mount | parser and intake tests pass remotely; full backend regression and Compose config pass; deployment inbox is empty during acceptance; ordinary NIPT directory auto-submit remains disabled | done |
| T121 | PGT-A Intake error visibility and manifest template correction | backend/frontend/docs/qa | T120,T119,T118 | explicit Intake validation stage; visible `last_error` in shared Dashboard/Settings table; corrected non-trigger PGT-A manifest template | backend 181 and frontend 40 tests pass; production build/Compose/HTTP pass; live API exposes the path error; corrected two-sample `.par.tsv` resolves uniquely without publishing trigger files | done |
| T122 | NIPT Intake completed-run visibility and refresh | frontend/docs/qa | T121,T120,T119 | Dashboard/Settings default All lifecycle; Intake refresh after Airflow sync/submit; display status contract regression | frontend 40 tests and production build pass; deployed Dashboard bundle queries all lifecycle records; latest 72-sample NIPT appears as success/100%/Completed while scanner and backend remain unchanged | done |

## P6 QC/日志/报告/邮件

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T060 | QC parser | backend/snakemake | T021,T040 | WES mock `reports/qc_summary.tsv` + `qc_metric` 写库 + `/api/runs/{analysis_id}/qc` | `WES_20260705_164813_C5561C` sync 后 `/qc` 返回 6 条 pass metrics；重复 sync 幂等；artifacts include `wes_qc_summary` | done |
| T061 | MultiQC/Snakemake report artifact | snakemake/backend | T040,T060 | report link | artifact 表有记录 | todo |
| T062 | PGT-A run-level error summary extractor | backend | T025,T027,T035 | run-level Airflow sync + stderr summary | PGT-A run-level `error_summary` 已完成；rule 状态基础已由 T026/T043 入库，WES mock qsub stdout/stderr 事件路径已由 T041/T042 验证 | done |
| T063 | 邮件模板 | backend/airflow | T034,T060 | success/fail emails | 邮件含 QC 和错误链接 | todo |
| T087 | PGT-A baseline QC artifact/QC visibility | backend/frontend/docs | T086 | baseline QC artifacts + qc_metric import | artifacts 动态发现 `baseline_qc_summary/pass_samples/report`；sync success 后可导入 baseline QC metrics；远端 backend tests 覆盖 parser/import/artifacts；真实 run smoke 待用户确认 | done |

## P7 NIPT 接入

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T070 | NIPT qsub wrapper 设计 | snakemake | T032,T041 | pipelines/nipt_qsub | mock dry-run 通过 | todo |
| T071 | NIPT Docker runner | infra/snakemake | T033 | `dags/nipt_docker_runner.py` scanned-batch v1 with legacy template compatibility | `mount_smoke` executes host Docker through airflow-worker socket, mounts scanned source batch read-only as `/input_batch`, writes command/stdout/stderr, no `down -v` or prune; full_run remains gated and is enabled for supervised manual use by T113 | done |
| T072 | NIPT QC parser | backend/snakemake | T060,T071 | NIPT metrics in `reports/qc_summary.tsv` | `sync-airflow` imports NIPT QC metrics and updates `sample.qc_status`; scanned smoke `NIPT_20260708_072349_4F942A` returned `pass=1` and frontend/API can display NIPT QC | done |

## P8 Demo 验收

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T080 | 端到端 smoke test | qa | T050-T063 | docs/21_DEMO_SMOKE_REPORT.md | PGT-A workflow success/QC fail、WES mock QC success、WES rerun_rule without forceall 均有远端只读证据；未提交新的重型 PGT-A run | done |
| T081 | Demo script | docs/coordinator | T080 | docs/17_DEMO_SCRIPT.md | 10-15 分钟演示脚本已更新，明确普通用户主入口是前端，PGT-A workflow success 与 QC fail 分开讲 | done |
| T082 | 回滚和清理 runbook | infra/docs | T080 | docs/11 更新 | 不删除 volume 的停止流程清楚 | todo |
| T083 | 最终交接 | coordinator | T080-T082 | HANDOFF/CURRENT_STATE | 下一阶段任务明确 | todo |
| T084 | PGT-A Level 0-3 smoke 验收 | qa | T014,T027,T035,T045,T057 | acceptance report | preflight、metadata、dry-run、failure smoke 记录完整；`dryrun_cnv=PGTA_20260703_170917_20E8F2` success，`invalid_target=PGTA_20260703_170957_3DDEC3` failed with error_summary | done |
| T092 | PGT-A baseline_qc 当前 run 收口与 64-core 生效验证 | qa/coordinator | T086,T087,T091 | current baseline_qc terminal sync evidence; 64-core resume command evidence | `PGTA_20260706_162150_00C4FD` final resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` reached Airflow/backend `success`; command contains `--cores 64 --rerun-incomplete`, no `--forceall`; artifacts and `/qc` verified; QC decision is sample-level `FAIL`, not workflow failure | done |
| T093 | PGT-A 受控中断与 64-core resume | backend/airflow/frontend/qa | T086,T087,T091,T092 | PGT-A baseline_qc resume API, DAG unlock/rerun-incomplete, frontend resume button, runtime evidence | code/tests passed at `2821a5e`; old `PGTA_20260706_162150_00C4FD` `--cores 1` run was controlled-interrupted and synced failed; first resume run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T095201Z` used `--cores 64 --rerun-incomplete` and no `--forceall` but failed on stale samtools sort tmp BAMs; T094 supersedes runtime recovery | done |
| T094 | PGT-A resume 临时 BAM 清理与再次恢复 | airflow/backend/qa | T093 | run-local cleanup of `mapping/*.sorted.bam.tmp.*.bam`, cleanup artifact, same-workdir resume | code/tests passed at `0a8e756`; cleanup log deleted 16 stale `G11.sorted.bam.tmp.*.bam` files and remaining tmp count is 0; cleanup resume run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z` used `--cores 64 --rerun-incomplete`, no `--forceall`, reached baseline QC, then failed on a new Python library path issue handled by T095; artifacts include `pgta_resume_cleanup` | done |
| T095 | PGT-A baseline QC Python 库路径与 preflight | airflow/backend/qa/docs | T094 | PGT-A subprocess env sets `LD_LIBRARY_PATH` to conda lib, preloads conda `libstdc++.so.6`, uses run-local `MPLCONFIGDIR`, writes `logs/pgta.python_preflight.log`, and resumes same workdir | remote Airflow tests passed; first post-`LD_LIBRARY_PATH` resume still failed preflight, `LD_PRELOAD` fix passed preflight; final resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` succeeded and `/qc` imported 14 failed QC metrics | done |

## 任务卡模板

```markdown
### TXXX - <title>

Owner: <agent>
Status: todo
Dependencies: <ids>
Scope:
- 
Out of scope:
- 
Files likely touched:
- 
Acceptance:
- [ ] 
Test commands:
- 
Rollback:
- 
Notes:
```

### T124 - QC formatting, Intake alignment, and tracker ordering

Owner: frontend/backend/docs
Status: done
Dependencies: T123,T119,T114
Scope:
- Normalize PGT-A/NIPT QC display units, sort terminal runs newest-finished
  first, and align Intake project/sample/runtime cells with Run Tracker.
Out of scope:
- DAG/Snakemake changes, database migrations, scanner policy, and new analysis
  execution.
Acceptance:
- [x] Backend ordering and Intake timing tests.
- [x] Frontend QC and shared operations-cell tests.
- [x] Remote production build, deployment, API and browser spot-check.
Rollback:
- Redeploy T123 backend/frontend images; no data rollback is required.

### T123 - Predict path and operations consistency

Owner: platform/frontend/backend/airflow
Status: done
Dependencies: T121,T122
Scope:
- Predict-only PGT-A UI, consistent Run/Intake state, QC/log semantics, live
  workflow catalog, 32-core NIPT default, and scanner-only retention.
Out of scope:
- Build Reference DAG, NIPT auto-submit, WES/WGS, email notifications.
Acceptance:
- [x] Backend tests, frontend tests/build, DAG/config tests, Compose config.
- [x] Deploy and reconcile failed NIPT rule states.
- [x] Complete supervised 32-core NIPT clone acceptance.
Rollback:
- Redeploy prior images; preserve DB, workdirs, FASTQ, logs, and volumes.
