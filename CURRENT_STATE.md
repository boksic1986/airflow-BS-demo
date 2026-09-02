# CURRENT_STATE.md

## 2026-09-02 T163 登录、T7发现与在途状态修复

```text
auth: PlatformCapabilitiesProvider只在SessionProvider确认已登录后挂载；登录页不再提前请求受保护capabilities并缓存AUTH_REQUIRED。生产API在未登录时仍正确返回401，登录后由新provider重新加载。
scanner_ui: Dashboard改为产品语义“自动发现新的测序批次；分析任务需人工确认”，以三个状态标签显示10分钟周期、本轮1841个批次目录和最近更新时间；不再暴露BarcodeStat实现细节。
scanner_data: 2226th_20260830B_E250197447确认无关联AnalysisRun后，在受保护备份后单事务删除；生产env加入精确ignore，立即重扫后该行仍为0。扫描仍计数1841，AnalysisRun=1、Airflow DagRun=1，自动提交仍关闭。
runtime: WGS_20260901_031616_C74E6C同attempt的Step4权威状态已success；业务投影由残留failed恢复为downloading/step5_download并写审计。原DagRun仍running，Step5 sensor为up_for_reschedule；Step1-Step4没有重跑，未创建新Master或上传。
race_guard: 后端只在同identity的Step4成功状态文件存在时允许Step5恢复failed投影；Airflow start任务会等待新async generation状态可见，避免sensor读取上一代failed。
release: current -> 20260902-wgs-4.1.1-2499749-t163-ui-intake-recovery-r1；frontend image airflow-demo/frontend:t163-ui-intake-recovery@sha256:23f916eb9c60...。只滚动重建应用/Airflow服务，不迁移DB、不删除volume或网络。
validation: BS10610 backend 251 passed/1 skipped；bio_wgs 8 tests、py_compile和import_errors=0；frontend 9 files/32 tests及Vite build通过。health=200，匿名capabilities=401符合安全合同。
network: nipt_analysis_test_net仍为192.168.199.0/24、gateway 192.168.199.1；唯一宿主机发布仍是172.17.106.10:12959。
gate: 当前获批真实batch尚未完成，因此execution/runtime和DAG现状未在本次中途关闭；自动dispatch=false。批次终态后再执行禁用态门禁切换。
```

## 2026-09-02 T161 生产WGS 4.1.1接入与仓库整理

```text
wgs: 用户最终确认生产云端流程继续使用共享仓库wgs-4.1.1；只读审计为dev_CJC_4.1.1_cloud@6c982817614db6a1157b6f287427ddf01ac91827，该提交已统一structured ANALYSIS_COMPLETE合同。wgs-4.2.0只用于测试。
catalog: 生产release为wgs-4.1.1-6c98281；BS10610/node200共享路径分别为/mnt/.../wgs-4.1.1和/bi/.../wgs-4.1.1。生产API不能选择4.2.0。
prepare: platform=T7；sequencing_batch与analysis_batch分别传给--batch/--analysis-batch；4.1.1无--algo参数。服务端派生最终batch_no=WGS_<analysis_batch>_T7Hg38V4.1.1。
frontend: Submit表单展示V4.1.1/6c98281和T7，不显示测试版本或variant caller；此前Batch、业务阶段、精确进度、安全Samples、Rule图、opaque日志与失败诊断修复均保留。
validation: 生产4.1.1纠正后BS10610 Docker backend 280 passed/1 skipped；scripts 38 passed；Airflow DagBag import_errors=0、bio_wgs=18 tasks/6 reschedule sensors/paused-on-creation；frontend 9 files/32 tests及Vite build通过。此前PostgreSQL 15迁移往返、Compose解析和固定网络检查继续通过。
runtime: 未部署、未切current、未启动OBS/CCE/WGS/Step7；在线T152状态未改变。
network: 只读复核nipt_analysis_test_net=192.168.199.0/24、gateway=192.168.199.1；仅frontend发布172.17.106.10:12959。
repository: 主功能PR #4 merge 17c0f97；错误4.2.0路径PR #6未部署并已由生产纠正PR #8完整覆盖。PR #8 merge commit为6046a280db1271ae41575113cacd431e990a74c2，root main已ff-only同步。
```

## 2026-09-02 T159 WGS提交、传输进度与失败日志合同修正

```text
submission: 撤回三步draft preview作为生产入口；新增catalog受控POST /api/wgs/runs。DAG prepare按WGS原生语义执行sampleinfo→analysis，只有batch_root/sampleinfo.tsv中的最终selection.kept会进入公开Samples，FASTQ扫描结果和pending不再预先冒充分析样本。
transfer: 新增Airflow自有透明obsutil wrapper和node200 runner聚合，合同为wgs-runtime.transfer-progress.v1。wrapper保留原命令stdout/stderr/exit code，只写请求级脱敏bytes/files/speed/ETA；解析失败只降级监控，不改变传输结果。cce-pipeline旧v1仅作为读兼容，不再是部署门禁。
logs: 取消失败Rule的SFS路径registry要求；只从已经绑定并镜像的analysis.log最后2MiB按snakemake job ID/rule name生成不超过64KiB摘要，完整日志继续通过后端自动生成的opaque key读取，用户不配置key且logger路径不被信任。T160将日志API改为64KiB分块倒读，单次最多8MiB/1000行并返回file_size/truncated，不再把完整analysis.log载入内存。
release: catalog仍保持wgs-4.1.1-2499749。共享WGS HEAD 6c982817...只作为待审计候选；等待WGS更新完成后再一次性更新commit/release ID，不静默跟随HEAD。
validation: BS10610 backend 279 passed/1 skipped（含T160大日志RED→GREEN）；runner/adapter/timing 51 passed；前端在BS10610无网络Docker容器内使用Node 22.22.2/npm 10.9.7完成Vitest 32 passed及Vite production build；git diff --check和Python compile通过。测试证据在/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/t159-20260902。本机Node结果不作为验收证据。
network: BS10610只读preflight确认外部`nipt_analysis_test_net`仍为`192.168.199.0/24`、gateway `192.168.199.1`，现有容器地址均唯一且在网段内；候选Compose不声明IPAM或静态容器IP，只复用该外部网络。唯一宿主机端口映射仍为前端`172.17.106.10:12959`；测试容器使用`--network none`，未创建或修改Docker网络。
deployment: 本轮未部署、未切current、未修改在线T152开关或DAG pause，未启动OBS/CCE/WGS/Step7。node200仍需在disabled release阶段安装wrapper并把受控operator config的obsutil_bin指向wrapper。
```

## 2026-09-02 T153-T158 WGS生产前端开发检查点

```text
code: migration 20260901_0013、权威stage/Rule状态、安全日志索引、Batch/业务阶段UI、Samples、Rule阶段图、三步draft API/UI、资源快照和admin Step7合同已在T146 worktree实现。独立审查后的提交/DagRun幂等、Step7 action绑定、draft过期/源漂移、严格transfer v1、terminal单调和WGS QC残留均已修正。
logs: node200 evidence bridge现在增量同步Rule JSONL和绑定run的analysis.log，并在Master终态用只读reader补齐。
validation: BS10610 backend 298 passed/1 skipped；scripts 37 passed；bio_wgs DAG 8 passed且DagBag为18 tasks/paused-on-creation/import_errors=0；临时PostgreSQL 15完成0013 upgrade/受控downgrade/upgrade。此前记录的本机Node结果不作为验收证据；T159已在BS10610无网络Docker容器内重新完成32 tests及TypeScript/Vite build。BS10610离线镜像`airflow-demo/frontend:t153-production-ui-disabled`（sha256:c7e49e0a69d40570dfafd3e20b3a66308f7a6f726ed7623127d004bb3f9ba202）的nginx及无端口HTTP smoke通过。独立只读审查最终为Critical/Important/Minor均0。
progress: 没有cce-pipeline.transfer-progress.v1时Step1/Step5明确返回progress_available=false，不伪造速度或ETA；Step3使用结构化completed/total/percent。
blocker_draft: 当前WGS sampleinfo子命令只生成临床metadata，不生成FASTQ配对和pending预览；生产draft worker不得自行复制业务选择逻辑。WGS_SUBMISSION_PREVIEW_ENABLED默认false，API/UI fail closed，等待WGS只读preview合同或批准的adapter。
blocker_rule_stderr: analysis.log和stage worker日志已使用opaque索引；失败Rule stderr仍缺少经审查的log-key到SFS相对路径registry，未开放任意logger路径读取。
blocker_release: catalog仍绑定wgs-4.1.1-2499749；共享WGS仓库当前HEAD为6c982817614db6a1157b6f287427ddf01ac91827。不得静默改绑或启用。
deployment: 本轮尚未迁移生产DB、重建服务或切换current；未启动OBS/CCE/WGS，未执行Step7。当前在线仍为T152 release，旧生产env的execution/runtime=true且现有bio_wgs为unpaused；本轮disabled candidate已用四个门禁显式false解析验证，不擅自覆盖在线状态。
network: Compose解析只发布frontend 172.17.106.10:12959；外部nipt_analysis_test_net实测192.168.199.0/24、gateway 192.168.199.1；scanner默认600秒。
```

## 2026-09-01 T152 - Step4 Master时序修复已部署，当前批次被WGS marker合同阻断

```text
t152_airflow_fix: node200 runner只在Step3已success且Master与冻结binding完全一致时，将"Step4 requires a successful Master Job"作为短暂状态每5秒重试，最长600秒；其他Master错误继续硬失败。
t152_retry_generation: 已退出的failed step4_publish可在相同request SHA下归档status/worker/log到history/step4_publish/retry-N后重启；活动worker、请求漂移和其他stage不允许该行为。
t152_backend: 同attempt重新登记已知Master完成竞争时恢复业务状态为publishing并写run.step4_publish_recovered审计；后续真实Step4 terminal failure会写回biodemo为failed和错误摘要，前端不再滞留publishing；Step4 repair不再依赖wgs-master-*前缀，而使用Step3绑定后生成的canonical event identity。
t152_deployment: current -> 20260901-wgs-4.1.1-2499749-t152-step4-recovery-r8；Airflow实现commit为29c8378b2b4e5cf860e7978d9e23233f710035af和1bd7530f2a55bab530475fffb48eeabb025fea21。backend/API/scheduler/worker和共享runner已更新，数据库、volume、网络、WGS仓库和冻结bundle未修改。
t152_recovery: 原DagRun同attempt只清除了Step4、Step5、Step6、finalize和release_leases。Step1、Step2、Step3仍success；Master仍是cce-master-79c59ff6401e15d76aa5，UID 8ef69ad6-96cd-4dd2-a94a-b214287af1d2，Complete时间08:26:26Z；没有重新上传FASTQ或创建Master。
t152_new_blocker: 普通Step4已经越过Master前置检查，但在OBS交付核验时报ANALYSIS_COMPLETE is invalid。OBS marker是149-byte schema-1 JSON且身份/status=PASS正确；冻结WGS 2499749的cce_delivery.py仍只接受字面量status=PASS\\n。这是WGS内部producer/consumer合同不一致，不是cloud_finalize_delivery重复执行，也不是Airflow Master时序问题。
t152_safety_stop: 按本任务“不修改WGS仓库或冻结bundle、不修改OBS/SFS”边界，未热补丁bundle、未覆盖OBS marker、未使用CRAM repair、未再次清Task。当前DagRun再次failed于普通Step4；Step5-Step6未执行，最终成功尚未达成。
t152_backup: backups/T152-step4-recovery-20260901T173906+0800；biodemo.dump SHA256 08af9e4f6a50945affb355380858a4ab11653356dbfa43fa44fdccf6174e6c3e，airflow.dump SHA256 3ac29e63f3dcb4dba401a2490e8485acd6c246550a2b9955e6330790f4da4256。
t152_validation: runner 28 passed；backend 250 passed；DAG import errors=0；Compose config和network preflight通过；生产API已显示failed/step4_publish及真实错误。网络仍192.168.199.0/24、gateway 192.168.199.1，仅172.17.106.10:12959发布。
```

## 2026-09-01 T151 - exclude YF non-clinical samples

```text
t151_behavior: sample IDs beginning with uppercase YF are ignored before eligible/add-on/pair-issue accounting. YF-only is no_new_wgs and an incomplete YF pair does not trigger needs_review.
t151_fingerprint: name fingerprint is v3 and excludes YF names; an equivalent old v2 fingerprint is accepted once so existing ready rows upgrade without false drift. No DB field or migration was added.
t151_production: 2222 contained 192 YF FASTQ entries (96 pairs) and changed from ready/96 to no_new_wgs/0. 2223/2224/2227 remain ready with 12/8/10 eligible pairs; 2221/2225 remain no_new_wgs and 2226 retains its prior needs_review.
t151_side_effect_gate: AnalysisRun, RunAttempt and Airflow DagRun counts remained 1/1/1. WGS_20260901_031616_C74E6C stayed running in step3_monitor with the same attempt and DagRun.
t151_release: current -> 20260901-wgs-4.1.1-2499749-t151-yf-filter-r6; only wgs-intake-scanner was recreated. The scanner bind-mounts only the release backend and /bi/fastq/T7_Fastq read-only.
t151_source: scanner policy, regression tests and contracts are committed as 9ab2dd2c95528875b11cf8b82a7e4350eedb08b8.
t151_backup: backups/T151-yf-filter-20260901T162127+0800/biodemo.dump SHA256 ed7dfe046d19a53b6cee0f52da2e0925e5e58e844eeca19d2b37848cb52d0ae3.
t151_validation: focused scanner 18 passed; full backend 247 passed / 1 skipped; API reports schedule_seconds=600, auto_dispatch=false and 1837 scanned directories with no scanner error.
t151_network: nipt_analysis_test_net remains 192.168.199.0/24, gateway 192.168.199.1; only frontend publishes 172.17.106.10:12959.
```

## 2026-09-01 T150 - T7 FASTQ scanner repair

```text
t150_behavior: scanner classifies regular files, hard links and symlinks only by the direct entry name; it never resolves or reads FASTQ targets. Fingerprint v2 contains chip/batch/BarcodeStat metadata and sorted eligible names, while add-on -S\d+ samples remain excluded.
t150_production: 2227th_20260830C_E250197831 is ready with 10 complete pairs; 2222/2223/2224 are ready with 96/12/8 pairs; 2221/2225 remain no_new_wgs; 2226 retains its pre-existing needs_review drift state.
t150_side_effect_gate: before and after deployment, AnalysisRun=1, RunAttempt=1 and Airflow DagRun=1. WGS_20260901_031616_C74E6C attempt 1 stayed running in step3_monitor with the same DagRun; no automatic analysis was created.
t150_release: current -> 20260901-wgs-4.1.1-2499749-t150-t7-scanner-r5; only wgs-intake-scanner and frontend-nginx were recreated. Tested frontend image airflow-demo/frontend:t150-t7-scanner-10m is sha256:cef9e1117810e0482b9099281d00dcea329a47e19e838959b004c24a4e386cdb.
t150_source: scanner/frontend implementation is commit b5afe9c0349557ff710e0f1ee6f3bfc49a393d36. The T149 r4 rollback scanner files were restored byte-for-byte from its parent commit after a test staging symlink was detected, and the staging link was removed.
t150_backup: protected biodemo backup is backups/T150-t7-scanner-20260901T151336+0800; biodemo.dump SHA256 b606f3f284ffc7d72e992cae79534c5d3580f20dcb6890d2902dbdb2f2026380.
t150_validation: BS10610 backend 243 passed / 1 skipped; frontend 31 passed plus TypeScript/Vite build; API reports schedule_seconds=600 and auto_dispatch=false. Scanner only mounts /bi/fastq/T7_Fastq read-only.
t150_network: nipt_analysis_test_net remains 192.168.199.0/24, gateway 192.168.199.1; only frontend publishes 172.17.106.10:12959.
```

## 2026-09-01 T149 - Step3 monitor repair and in-flight takeover

```text
t149_run: WGS_20260901_031616_C74E6C attempt 1 remains running in the original DagRun manual__WGS_20260901_031616_C74E6C__a1.
t149_preserved: Step1 upload and Step2 Master remain success/try 1; the existing cce-master-79c59ff6401e15d76aa5 remains Running. No OBS upload, Master Job, analysis ID, attempt or run ID was recreated.
t149_repair: runner status writes are unique-temp/fsync/atomic/monotonic; accepted precedes worker launch; Step3 carries frozen Master identity and cce-pipeline status. Backend validates the exact binding rather than a name prefix, accepts incomplete transitions as not-ready, and recovers the same failed business attempt with an audit event.
t149_evidence: observer is active/healthy on cce-run-650a0767d41b3157. Authenticated API shows current Rule MEI_MEICall, 41 Rule rows (19 success, 2 running, 20 planned), and only the bound Master workload.
t149_airflow: start_step3_monitor is success/try 2 and wait_step3_analysis is up_for_reschedule/try 2. The original DagRun will advance to Step4-Step6 only after the real CCE terminal state; no manual high-frequency polling remains.
t149_release: current -> 20260901-wgs-4.1.1-2499749-t149-step3-recovery-r4; deployed runtime code commit b7730bc1a09481f67663b2c3d7f37e50b5770b93.
t149_backup: pre-takeover biodemo, Airflow metadata, runner state and binding are retained at backups/T149-step3-recovery-20260901T132953+0800 with verified SHA256 checksums.
t149_network: nipt_analysis_test_net remains 192.168.199.0/24, gateway 192.168.199.1; only frontend publishes 172.17.106.10:12959 and the scheduler is not paused.
```

## 2026-09-01 T148 - historical worktree and branch cleanup

```text
t148_worktrees: only the root main worktree and D:/pipeline/airflow-demo-worktrees/T146-wgs-081-manual-run remain; seven completed/historical secondary worktrees and the unregistered T133 staging-artifact directory were deleted.
t148_branches: only local main and jiucheng/platform/T146-wgs-081-manual-run remain; 54 local historical branches and 16 remote historical branches were deleted. GitHub now exposes only origin/main.
t148_discarded: the obsolete T096 root edits, untracked airflow-snakemake-ppt directory and T133 local staging artifacts were explicitly deleted under the user's cleanup authorization and are not recoverable from the working tree; committed history remains in Git objects until normal repository maintenance removes it.
t148_preserved: T146 .artifacts and its active WGS analysis state remain untouched; the T146 worktree is synchronized to the merged main baseline.
t148_runtime: no Airflow, WGS, CCE, OBS, database, Docker service, network or production-run operation was performed.
```

## 2026-09-01 T147 - Airflow worktree reconciliation

```text
t147_main: origin/main is cf9b716bf2b712fc802e9d6d44d500ca998d4773 before this documentation-only PR; it already contains the T146 WGS production checkpoint.
t147_fast_forwarded: clean T132 and T145 worktrees were fast-forwarded to origin/main without rewriting history.
t147_equivalent: T127 dashboard, frontend compatibility, review fixes and WGS rule-phase branches have patch-equivalent commits already present in main; they were not merged again.
t147_preserved: the dirty T096 documentation/PPT worktree and its five local changes were left untouched; the clean T128 NIPT manual-scan branch remains isolated because it is obsolete for the WGS-only platform.
t147_active: T146 production analysis WGS_20260901_031616_C74E6C remains under Airflow scheduled monitoring; this repository reconciliation does not restart, cancel, pause or otherwise alter the run.
t147_scope: no application, DAG, deployment, database, Docker network or runtime configuration changes; only repository state documentation is included in the PR.
```

## 2026-09-01 T146 - WGS 2499749 clean reanalysis（运行中）

```text
t146_release_contract: WGS V4.1.1 commit 2499749ce7fd200d4269d1ee03d7b6a4e8d5bb68，release wgs-4.1.1-2499749；BS10610和node200共享仓库HEAD一致。
t146_cleanup: 旧analysis WGS_20260831_194429_145176的biodemo业务行、11个Airflow DagRun、Airflow runtime、三处task evidence、SFS run/linkage、OBS FASTQ/result和CCE Job/Pod/batch lock均已精确清空；只保留一条受控清理审计。
t146_backups: 清理前biodemo和Airflow metadata均已生成mode 0600 pg_dump备份；不删除用户、scanner singleton、Docker volume或network。
t146_active_run: 前端等价API新建并提交WGS_20260901_031616_C74E6C attempt 1，DagRun manual__WGS_20260901_031616_C74E6C__a1，未复用旧analysis/run-id。
t146_checkpoint: validate和prepare成功，Step1输入上传正在运行；前端/API显示15% input_transfer.wait_step1_upload。用户要求停止人工高频轮询，后续由Airflow 5秒reschedule sensor和Step3按任务激活的observer持续同步。
t146_runtime: node200 cce-pipeline 0.8.1，resolved Master digest sha256:965473cf89539ec67869cb38265f1416de508aa71ab5f35ad9be6a979548dab0。
t146_gates: WGS_EXECUTION_ENABLED=true、WGS_RUNTIME_ADAPTER_ENABLED=true、WGS_AUTO_DISPATCH_ENABLED=false；bio_wgs已unpaused以运行本次手工批次。
t146_network: nipt_analysis_test_net保持192.168.199.0/24、gateway 192.168.199.1，只发布172.17.106.10:12959。
```

## 2026-09-01 T146 - WGS cdee32c / cce-pipeline 0.8.1 manual run（运行时阻断）

```text
t146_release_contract: WGS V4.1.1 commit cdee32c9d3c689f4af6ea8a0f7a8296f79c10a1d, release wgs-4.1.1-cdee32c；BS10610和node200共享同一仓库，只有docs/下允许的未跟踪文档。
t146_runtime: node200 /bi/software/mamba/envs/WGS/bin/cce-pipeline 为0.8.1；Airflow不校验其版本，只记录prepare产生的resolved runtime。
t146_prepare_fix: Airflow从batch_no WGS_20260825A_T7Hg38V4.1.1提取sequencing batch 20260825A并传入--batch；--outpath仍是Airflow attempt runtime下的WGS_Clinical，不重建旧/sg2/.../wgs_test目录。
t146_validation: BS10610 runner 19 passed、backend 227 passed、DAG 10 passed、Compose/network contract 5 passed；frontend 31 passed且TypeScript/Vite build通过；Step3多行stdout解析回归后scripts全量22 passed。
t146_intake: 3对FASTQ软链接已原样复制到Airflow受控intake，两端可见；软链接源文件保持不变。
t146_cleanup: 初始旧批次SFS/OBS和CCE状态已清理；真实attempt 5/7失败后产生的Master、空SFS evidence stub和批次lock也已按精确身份清理。OBS input保留已上传FASTQ，OBS result为空；旧本地分析目录仍保留但从未被新流程读取或重建。
t146_deployment: current已切换到20260901-wgs-4.1.1-cdee32c-t146。真实run保留为attempt 7 failed，前端/API可见；发现兼容性阻断后BS10610和node200两个execution gate已恢复false，bio_wgs已重新paused，自动提交仍false。
t146_airflow_fix: Step3_status.sh允许kubectl提示后最后一行JSON；runtime gate从后向前解析最后一个合法JSON并严格校验。修复后Step3正确报告Master FAILED，不再被JSONDecodeError掩盖。
t146_recovery_gate: backend的resume/rerun_failed现同时检查execution和runtime adapter gate；生产复核HTTP 409、attempt保持7且attempt8 DagRun为0。cancel仍可用。
t146_blocker: node200 cce-pipeline 0.8.1的Step2在START前创建run_root/evidence/<run_id>/jobs.ndjson；当前resolved Master image仍为cce-pipeline 0.7.0系列并拒绝“已有run目录但缺run-id”，Master立即退出。须先发布/选择与0.8.1合同一致的Master镜像或修正该顺序，Airflow不得继续重试。
t146_scanner: Compose命令改为读取WGS_INTAKE_SCAN_INTERVAL_SECONDS；生产受保护值为600秒，保持10分钟扫描且不新增记录膨胀。
t146_network: 必须继续保留nipt_analysis_test_net 192.168.199.0/24、gateway 192.168.199.1，且只发布172.17.106.10:12959。
```

## 2026-08-30 T145 - scanner 稀疏入库与 event-driven observer

```text
t145_release: current -> /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260830-wgs-4.1.1-observer-lifecycle-disabled-t145。
t145_release_cleanup: 验收后已用无网络root容器精确删除T142和T143旧release；releases目录只保留T145。旧release目录删除不可就地恢复，代码仍可从Git重建。
t145_services: 旧wgs-observer已停止并移除；wgs-intake-scanner只读T7根并每1800秒扫描，wgs-run-observer只读evidence并在无active/draining attempt时阻塞PostgreSQL LISTEN/NOTIFY。
t145_sparse_intake: 生产首次和第二次扫描均统计1830个匹配目录，wgs_intake_batch仍为0；bootstrap_ignored和waiting_barcode_stat不再入库。
t145_cleanup: 清理前1830行中关联analysis数为0；受保护单事务删除1830个batch和1个scanner state。清理后AnalysisRun、observer state均为0。
t145_backup: /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/backups/t145-before-sparse-observer-20260830T045310+0800/biodemo.dump，SHA256 6cd7026498748c2e6ec231f01ebde7867c5bee3d2e97827d24b3bf36bc11b4e8。
t145_database: biodemo Alembic revision 20260830_0012；populated临时库完成0011->0012、1830行清理和零副作用验收后已删除临时库。
t145_observer_idle: 生产wgs-run-observer启动后无活动分析，10分钟日志字节数为0，不读取binding/runtime/transfer也不输出空心跳。
t145_validation: 当前release在BS10610通过backend 227 tests、DAG 7 tests、Compose/network 5 tests、frontend 30 tests及TypeScript/Vite build；隔离PostgreSQL实测4个attempt通知全部按identity到达；登录、health、scanner-state和intake API HTTP smoke通过。
t145_frontend: airflow-demo/frontend:t145-wgs-observer-lifecycle-disabled -> sha256:21468c83853c873559b4805c65f58b49cf72c86a4aca5f3a2415cea6db95579a；UI包含“本轮扫描”和“CCE监控尚未启动”。
t145_gates: WGS_EXECUTION_ENABLED=false、WGS_RUNTIME_ADAPTER_ENABLED=false、WGS_AUTO_DISPATCH_ENABLED=false，bio_wgs paused且DagRun=0。
t145_network: 外部nipt_analysis_test_net保持192.168.199.0/24、gateway 192.168.199.1；仅frontend发布172.17.106.10:12959。
```

## 2026-08-29 T143/T144 - T7 scan-only 与 Step4 repair

```text
t143_baseline: WGS V4.1.1 commit 1656b5d7a6e2f24242c38149f6d1c92ac266cd37, release wgs-4.1.1-1656b5d; Airflow不安装或校验cce-pipeline 0.7.1。
t143_scanner: wgs-observer独立线程按扫描开始时间每1800秒只读扫描/bi/fastq/T7_Fastq；首次completed目录bootstrap_ignored，未完成目录waiting_barcode_stat；eligible/add-on配对、fingerprint漂移和PostgreSQL advisory lock已实现。永久bootstrap_ignored只更新扫描时间，不再重复枚举FASTQ。
t143_side_effect_gate: WGS_AUTO_DISPATCH_ENABLED=false；scanner不运行sampleinfo、不建分析目录、不创建AnalysisRun/DagRun、不访问OBS/CCE。
t143_data_api_ui: migration 20260829_0011增加nullable intake、scanner singleton和maintenance action；API/UI只暴露芯片、批次、计数和状态，不暴露sample ID、源路径或fingerprint。
t144_repair: operator/admin可请求固定cram Step4维护；后端从冻结binding生成确认串，同bio_wgs和同attempt执行；viewer与任意参数被拒绝，重复点击返回同一操作。
t144_disabled: WGS_EXECUTION_ENABLED=false、WGS_RUNTIME_ADAPTER_ENABLED=false时repair在Airflow/SSH前返回409。真实0.7.1修复未执行。
t143_local_remote_validation: BS10610 backend 217 passed/1 skipped，scripts 17 passed，DAG/Compose合同通过；frontend 30 tests、TypeScript和Vite build通过；临时PostgreSQL 0010->0011->0010->0011迁移往返及SET NULL外键检查通过。
t143_deployment: current -> /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260829-wgs-4.1.1-t7-scan-disabled-t143；biodemo revision 0011。bootstrap得到1817 bootstrap_ignored和11 waiting_barcode_stat，随后新发现1个no_new_wgs。
t143_cycle_acceptance: stable baseline 10:20:30.971949 UTC；cycle1 10:50:30.972362 / 516ms；cycle2 11:20:30.972623 / 1216ms。两次均保持1817 bootstrap_ignored、11 waiting、1 no_new_wgs，business run/attempt/maintenance和Airflow DagRun均为0。
t143_network: 必须保留外部nipt_analysis_test_net 192.168.199.0/24，gateway 192.168.199.1，且只发布172.17.106.10:12959。
```

## 2026-08-28 T142 - single WGS release disabled production deployment

```text
t142_target: replace the Airflow development snapshot catalog with one server-owned WGS release, request v3, release-bound observer/API/UI, and no Airflow cce-pipeline version gate.
t142_baseline: the user approved shared WGS commit 1778fcabd99b5253aa90cd410112dc2f78e0c51a and release wgs-4.1.1-1778fca; BS10610 and node200 resolve the same commit and only docs/WGS_V4.1.1_LOCAL_CCE_RESULT_CONSISTENCY_TEST_REPORT.md is untracked.
t142_release: BS10610 current -> /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260828-wgs-4.1.1-single-release-disabled-t142; schema-3 release wgs-4.1.1-1778fca is the only task binding contract.
t142_implementation: request v3, fixed-repository prepare validation, frozen bundle reuse, migration 0010, release-bound observer/ETA/API/UI and removal of obsolete candidate copy adapters are deployed.
t142_validation: isolated BS10610 backend 202 passed, scripts 16 passed, Airflow focused DAG tests plus py_compile/DagBag passed with only one 18-task paused bio_wgs, frontend 27 tests and production build passed, temporary and production PostgreSQL 0009-to-0010 migrations passed, and disabled HTTP create/detail/submit-409 smoke passed before exact synthetic cleanup.
t142_runtime_ssh: node200 noninteractive SSH was blocked by unconditional conda initialization in ~/.bashrc. A preserved backup was made and a noninteractive early-return guard plus fixed /usr/local/bin PATH restored Airflow command execution; host t640, WGS HEAD 1778fca, allowed docs-only drift and invalid forced-command rejection were verified without running a WGS stage.
t142_platform_state: biodemo revision 20260827_0010; 1 admin and zero sessions/runs/attempts/snapshots/issues/transfers/Rule events/states/workloads/audit/cursors. Airflow has zero DAG runs. Network remains 192.168.199.0/24 and only frontend publishes 172.17.106.10:12959.
t142_frontend: airflow-demo/frontend:t142-wgs-4.1.1-single-release-disabled -> sha256:59cbfce7c8537c3a943f6c35a1ccea8bcfe6dc2ae1bba02fbe0d6ff6bb8b0903; deployed index/CSS/JS SHA256 match the locally tested dist.
t142_cleanup: after all disabled smokes passed, the exact T141 release and the redundant failed-attempt T142 backup were irreversibly removed with no-network root containers; releases contains only T142 and backups retains only t142-before-single-release-20260828T002349+0800.
t142_safety: WGS_EXECUTION_ENABLED=false, WGS_RUNTIME_ADAPTER_ENABLED=false and bio_wgs paused remain mandatory. No OBS transfer, CCE workload, WGS source edit or cce-pipeline install/update is authorized.
```

## 2026-08-27 T141 - WGS 4.1.1 Master Rule evidence bridge

```text
t141_release: BS10610 current -> /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260827-wgs-4.1.1-disabled-t141; releases contains only this directory.
t141_master_runtime: pinned Master digest 815d70a6... contains Snakemake 9.24.0+biosan1 and snakemake_logger_plugin_rule_status; the formal cloud_wgs_all command adds --logger rule-status while preserving analysis.log. node200's local Snakemake is not part of CCE execution.
t141_event_contract: the installed logger writes schema 1 JSONL under <run_root>/evidence/<run_id>/rule-status/raw/*.jsonl and labels attempts as attempt-N. The observer now accepts positive integers, numeric strings and attempt-N without changing the database attempt identity.
t141_bridge: node200 has no direct /workspace SFS mount. Step3 therefore uses kubectl to copy only complete JSONL lines by per-stream byte offset into /sg2/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/<analysis_id>/attempt-N. After Master exit, an exact one-shot reader Job mounts only the workspace PVC read-only, copies the final increment and is deleted.
t141_scope: Master Job/Pod remains the only Kubernetes workload exposed by API/UI. The reader is internal transport plumbing; Worker Pods are not enumerated or persisted.
t141_failure_policy: evidence-copy failure marks stage monitoring_health=degraded but does not fail WGS. Missing terminal Rule events remain unknown_interrupted; batch success still depends on WGS and result delivery gates.
t141_validation: BS10610 passed backend 193 passed/1 skipped, scripts 17 passed, no-bytecode syntax check, HTTP health, runtime/release SHA256 equality, observer clean polling, one paused bio_wgs and zero DAG import errors. Master image Python 3.11.9 path smoke passed. Real kubectl reader/Rule ingestion awaits the separately approved T140 batch.
t141_execution_gate: WGS_EXECUTION_ENABLED=false, WGS_RUNTIME_ADAPTER_ENABLED=false and bio_wgs paused remain unchanged.
```

## 2026-08-26 T139 - WGS 4.1.1 disabled production release

```text
t139_release: BS10610 current -> /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260826-wgs-4.1.1-disabled-t139.
t139_wgs_source: /mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1, clean commit 3489b3958869e5cfab983aca1eb9c7f158c06dff.
t139_snapshot: wgs-v4.1.1-candidate-3489b39-64d50022; manifest SHA256 9b1bfe00ebf7e8ed693f1e9eb17ec05174aa43b04900802d67e54f50dc27f52e; prepare/config.yaml is excluded.
t139_cce_contract: cce-pipeline 0.5.0, source commit 70a9a737c62865f232ed0b49f682aa7c9a69e467, formal wheel SHA256 43a4ab478e8b8810b1691bb755e54336b0bc8fd86a16d4fed9be3783036e1756, profile wgs-4.1.1-r1.
t139_dag: only bio_wgs is loaded; it has 18 Step1-Step6 project tasks, no schedule, and remains paused. The old bio_wgs_cce, bio_wgs_intake_scan and bio_wgs_onprem sources and metadata are removed.
t139_ssh: Airflow runs ssh -tt -F /opt/airflow/ssh/config wgs-node200; the protected config fixes node200 172.17.61.200, user, RSA IdentityFile, known_hosts, BatchMode, IdentitiesOnly and StrictHostKeyChecking. This is direct SSH config login, not an authorized_keys forced-command key.
t139_ssh_key: the user-provided RSA is installed outside the release at /home/chenjc/.config/airflow-wgs/ssh-node200/id_rsa, owned by Airflow UID 50000 and mounted read-only. It is absent from Git, images, releases, databases and logs.
t139_runtime_path: BS10610 /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime maps to node200 /sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime; a cross-host marker probe passed.
t139_data: biodemo migration 20260826_0009; one administrator retained; auth sessions and demo run/sample/event/transfer/workload/audit state cleared; Redis state cleared; database and Redis volumes retained.
t139_cleanup: releases contains only 20260826-wgs-4.1.1-disabled-t139 and backups is empty; the removed old releases/demo-state backups are not recoverable on host. Production WGS sources, inputs, results, database/Redis volumes and Docker network were not removed.
t139_network: existing external nipt_analysis_test_net remains 192.168.199.0/24; only frontend publishes 172.17.106.10:12959.
t139_frontend_image: airflow-demo/frontend:t139-wgs-4.1.1-disabled now resolves to sha256:f64b1ed3b2287b5cfa8b12d0a23732339a84a1aeed49a4219de671c2f10a32e6; the image deletes inherited demo assets before copying the fixed WGS build and exposes only the current JS/CSS pair.
t139_final_tests: backend 193 passed; node/runtime scripts 14 passed; deployment contract 5 passed; live Airflow DAG contract passed with 18 tasks and zero import errors; frontend 27 passed plus TypeScript/Vite build; Compose/network/HTTP/auth/DB/SSH/secret checks passed.
t139_execution_gate: WGS_EXECUTION_ENABLED=false, WGS_RUNTIME_ADAPTER_ENABLED=false, bio_wgs paused and real submission denied. No real OBS transfer or CCE WGS batch was started.
t140_blocker: Airflow-side Master Rule evidence integration is implemented in disabled mode, but no real CCE batch has validated kubectl incremental reads, the terminal reader Job, retry events or terminal reconciliation. Keep execution disabled until separately approved T140 acceptance.
```

## 2026-08-26 T135 planning - WGS 4.1.1 Airflow integration baseline

```text
t135_scope: doc-only; no DAG/backend/observer/frontend/Compose/migration/runtime code, BS10610 service, database, Docker network/volume, WGS source, OBS object or CCE workload was changed.
t135_wgs_source: /mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1, branch dev_CJC_4.1.1_cloud, clean commit 29388a81b182011a68d400adeb178ed0de147a49.
t135_cce_contract: WGS-owned cfg/profiles/cce/runtime.yaml, cce-pipeline 0.5.0, profile wgs-4.1.1-r1, WGS_cloud.smk target cloud_wgs_all, normal chain Step1-Step6.
t135_operator_boundary: node200 172.17.61.200 owns WGS prepare, private OBS and kubectl; BS10610 owns Airflow/FastAPI/observer/PostgreSQL/Redis/frontend; CCE never calls the local API.
t135_current_airflow: BS10610 still loads paused bio_wgs_cce, bio_wgs_intake_scan and bio_wgs_onprem; the worktree's uncommitted bio_wgs/T133 implementation is a 4.1.0 candidate and is not deployed 4.1.1 code.
t135_runtime_gap: cce-pipeline 0.5.0 exists only in the temporary nipttest environment; /bi/software/mamba/envs/WGS/bin/cce-pipeline is absent and must not be installed until wheel/source/build provenance is locked.
t135_monitoring: target observer consumes SFS rule-status/raw/*.jsonl, normalizes attempt/run_label from BATCH_RUNTIME.yaml, and stores only deterministic Master Job/Pod evidence; Worker Pods are not continuously monitored.
t135_transfer_decision: first production release exposes reliable stage state only; bytes/speed/ETA remain null with progress_detail_available=false until cce-pipeline publishes a stable machine-readable contract.
t135_intake_decision: first production release accepts manual frontend/API WGS CCE submission only; automatic intake remains disabled.
t135_cleanup_decision: production reset preserves user_account/roles, clears sessions and all demo runtime/audit state, and does not delete database volumes or the fixed Docker network.
t135_security_gate: tracked host prepare configuration and stale Master image labels require secret rotation/externalization and trusted image/build provenance before any real batch; sensitive values are not recorded in repository docs.
t135_execution_gate: WGS_EXECUTION_ENABLED=false, WGS_RUNTIME_ADAPTER_ENABLED=false and target bio_wgs paused remain mandatory through disabled-mode T139 acceptance.
t135_status: WGS 4.1.1 source/runtime audit and decision-complete integration documentation are complete; implementation starts at T135 contract freeze and remains todo.
```

## 2026-08-24 T133 Master logger overlay image follow-up

```text
t133_cce_followup_doc: cce-pipeline branch jiucheng/cce-pipeline-production-contract has doc-only commits d830d1f and 916c7c1 recording the two-column FASTQ manifest, transfer progress spool, Master logger runner, separate wgs-cloud-delivery boundary, and corrected immutable image contract; no cce-pipeline production code was changed.
t133_node200: Airflow runner address is fixed to 172.17.61.200 in Compose/example configuration; it remains a restricted OBS/kubectl runner and does not build images.
t133_delivery_image: wgs-cloud-delivery@sha256:d6d06ff... remains an unchanged Worker image for cloud_stage_cram/cloud_package_results/cloud_finalize_delivery; it receives neither cce-pipeline runtime nor logger plugin.
t133_master_base: direct inspection confirms the approved r2 digest 834b78c5... already contains Snakemake 9.24.0+biosan1, Kubernetes Executor 0.6.4+biosan3, cce-pipeline 0.2.0, and Master/cleanup/reset scripts.
t133_logger_image: BS10610 built and pushed tag cce-pipeline-0.2.0-schema3-20260824-r2-biosan-jsonl-v1 at RepoDigest sha256:5d1d977fb21e541582230f31540cc8cd4f7a183e417b41e508162060cfcdf211. The overlay adds only biosan-jsonl 1.0.0 and the logger-aware Master runner; tag- and digest-based container smokes pass.
```

## 2026-08-24 T133 WGS 4.1.0 logger + single-DAG implementation

```text
t133_wgs_source: isolated worktree /mnt/biodevrwbi/33.chenjiucheng/project/worktrees/wgs-4.1.0-airflow-logger, base commit b72ebea6616f79432c5ee6378f38f80b53575fa1; upstream worktree was not modified.
t133_wgs_snapshot: wgs-v4.1.0-candidate-b72ebea-2178aa5b at /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development, manifest SHA256 5f3aa5c0496b1224a8ae61799550392d37ff8269a4596cdc2a9a00e80dcc4631; execution_enabled=false.
t133_logger: snakemake-logger-plugin-biosan-jsonl 1.0.0 writes SFS rule-event.v1 JSONL only; no HTTP/FastAPI callback; standard analysis.log remains enabled; write failures emit LOGGER_DEGRADED.json without failing WGS.
t133_master_command: only formal cloud_wgs_all receives --logger biosan-jsonl; unlock, cloud_preflight, final dry-run and local/SGE remain unchanged.
t133_airflow: target release now publishes only paused CCE DAG bio_wgs with 15 project tasks; old bio_wgs_cce, bio_wgs_onprem and bio_wgs_intake_scan source/mounts are removed.
t133_runner: restricted wgs-runtime command targets node 200; node 200 is the sole OBS/kubectl operator boundary. WGS_EXECUTION_ENABLED=false and WGS_RUNTIME_ADAPTER_ENABLED=false remain in Compose.
t133_observer: accepts rule-event.v1 incrementally, deduplicates event_id, supports ISO timestamps and sequence, projects Rule state, recognizes LOGGER_DEGRADED.json, and accepts only Master Kubernetes evidence. Frontend tab is Master, not Worker Pods.
t133_cce_pipeline: confirmed clean worktree /mnt/biodevrwbi/33.chenjiucheng/project/worktrees/huawei-cloud-runtime-production-contract at 02adcecd85cc052b81330181a17d0377a742c39f; 65 tests pass; Airflow runner is wired to prepare/validate/run using an explicit immutable revision.
t133_open_contract_1: confirmed cce-pipeline prepare requires source,target,size_bytes,md5, while WGS 4.1.0 emits two-column source,target and the approved Airflow flow must not calculate FASTQ MD5. No FASTQ hash task was reintroduced; real prepare remains blocked until this interface is reconciled.
t133_image_contract: confirmed cce-pipeline Master digest 834b78c... runs Snakemake 9.24.0+biosan1 and Executor 0.6.4+biosan3 as intended; logger overlay digest 5d1d977f... preserves those versions and cce-pipeline 0.2.0.
t133_validation: WGS snapshot 27 tests pass; cce-pipeline 65 tests pass; backend focused 46 tests pass; node scripts 12 tests pass; DAG imports as bio_wgs with exactly 15 paused tasks; Compose/DAG contract 4 tests pass; WGS frontend focused tests 7 pass and local TypeScript/Vite production build passes. Full legacy backend suite is 215 pass/30 fail/1 skip and the legacy multi-product frontend capability tests remain incompatible because this WGS-only worktree intentionally rejects old NIPT/PGTA/WES product contracts.
t133_deployment: code is staged only under WGS_test and Airflow development snapshot; current BS10610 Compose was not recreated and no real OBS/CCE action ran.
```

## 2026-08-18 T133 WGS 4.0.1 code-driven flow correction

```text
t133_fastq_hash: WGS 4.0.1 does not generate/upload FASTQ.MD5SUMS; Airflow must not have start/wait FASTQ MD5 tasks.
t133_fastq_upload: Step1_upload_fastq.sh owns idempotent upload/reuse and writes FASTQ_UPLOAD_COMPLETE; obsutil -vmd5 remains a transfer option, not an Airflow hash stage.
t133_input_verify: no standalone verify_input_obs task; Step2 checks the upload marker and expected mounted FASTQ as an internal launch precondition.
t133_target_chain: validate -> prepare_wgs_batch -> upload -> launch batch Master -> wait/monitor -> publish -> download/result verification -> materialize -> finalize.
t133_rule_monitor: future Master-only Snakemake logger writes SFS Rule JSONL; current Master image/command is not wired yet.
t133_pod_monitor: future BS10610 host watcher monitors only the batch Master Job/Pod; Worker Job/Pod is not continuously collected or shown, and observer remains kubeconfig-free.
t133_correlation_scope: Rule state comes from the Master logger; because Worker Pods are outside the UI scope, no Rule-to-Worker-Pod mapping or jobs.ndjson schema extension is required.
t133_host_gap: upstream assumes one operator host; Airflow must split OBS/SFS actions on node005 from kubectl/CCE actions on BS10610 through restricted adapters.
t133_status: corrected design and read-only code audit complete; implementation and deployment remain not started.
```

## 2026-08-18 T133 WGS 4.0.1 单一 DAG 文档设计

```text
t133_scope: doc-only; no DAG/backend/observer/frontend/Compose/DB/config or BS10610 runtime change was made.
t133_baseline: WGS release 4.0.1 at commit 6cb1255fc1b218c9b18fb931eb3b6a172afe907b.
t133_current_dags: bio_wgs_cce, bio_wgs_onprem, and bio_wgs_intake_scan are current paused legacy DAGs; none has been removed.
t133_target: one CCE-only DAG named bio_wgs; ten-minute automatic scanning moves to wgs-observer.
t133_master: future runs use one batch-specific Master Job per analysis; fixed Master Deployments and PostgreSQL Master slots are pending deletion.
t133_evidence: native events.ndjson is batch state only; Rule state requires a separate Snakemake logger JSONL; run-state.json plus RUN_COMPLETE.json/RUN_FAILED.json and result verification determine terminal outcome.
t133_boundaries: node005 handles private OBS only; BS10610 handles kubectl/CCE only; Step7/Step8 are never automatic.
t133_gate: WGS_EXECUTION_ENABLED=false and all current DAG pauses remain unchanged.
t133_status: design and current-state audit complete; single-DAG implementation, launch adapter, runtime validation, and deployment have not started.
```

## 2026-08-18 T132 WGS 4.0.1 baseline replacement

```text
t132_wgs_source: /mnt/biodevrwbi/33.chenjiucheng/project/wgs, branch dev_CXJ_4.0.1_docker, clean commit 6cb1255fc1b218c9b18fb931eb3b6a172afe907b.
t132_airflow_copy: /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs was atomically replaced from the tracked upstream HEAD; upstream remained unchanged.
t132_snapshot: wgs-v4.0.1-dev-6cb1255-53453d5d; SNAPSHOT_MANIFEST.sha256 digest e9ce0f11c8c663ce13e88c7472a67ae36e2666cfba935312275396c3c7f5ce17.
t132_security: prepare/config.yaml, cfg/config.mail.ini, and legacy site publication/mail helpers were excluded; no literal password/token/access-key/secret-key assignment was found in the Airflow copy.
t132_runtime_gate: no active WGS DAG runs; bio_wgs_cce, bio_wgs_onprem, and bio_wgs_intake_scan remain paused; WGS_EXECUTION_ENABLED=false; no CCE analysis was launched.
t132_network: nipt_analysis_test_net remains 192.168.199.0/24 with gateway 192.168.199.1; only frontend publishes 172.17.106.10:12959.
t132_next: replace the obsolete persistent-Master/group_evidence adapter assumptions with the native 4.0.1 per-batch Master Job and SFS run-state/events/jobs/terminal-marker contracts before mock execution.
```

## 2026-08-12 T130 WGS server-copy observability release

t130_status: deployed on BS10610 as current release `20260812-wgs-observer-553be3f`; WGS execution remains disabled and all three WGS DAGs remain paused.
t130_source: upstream `/mnt/biodevrwbi/33.chenjiucheng/project/wgs` was not modified. Airflow integration lives in `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs`, source commit `136da1ad9e45ac1abcbeb3efa40bb2e2269b6ab9`, manifest SHA256 `b10cd8af1db19c313e15167c295d007d9eca246d03b2721592c4c0532a05696c`.
t130_observer: schema `20260812_0007`; binding/catalog validation; durable byte/line cursors; partial-line wait; restart/replacement replay; schema-1 Rule projection; real `pod-events.jsonl`, `pod-metrics.jsonl`, and `job-events.jsonl` normalization.
t130_ui: authenticated Run Detail displays pinned snapshot, observer freshness/errors, Rule state, and Pod phase/reason/exit/node/resources with five-second active polling.
t130_network: immutable external `nipt_analysis_test_net`, subnet `192.168.199.0/24`, gateway `192.168.199.1`; only frontend publishes `172.17.106.10:12959`. Preflight runs before every recreate; service DNS is used because internal container IPs may change within the fixed subnet.
t130_acceptance: backend focused 27 passed; WGS frontend 3 passed plus TypeScript/Vite build; deployment contract 4 passed; synthetic partial append consumed 1 then 4 events and restart consumed 0; OOMKilled/137 and metrics projected; login/RBAC passed; submit HTTP 409; synthetic DB/files removed.
t130_rollback: restore `/airflow-WGS/env/bs10610.wgs.env` from validation backup, recreate only backend/observer/frontend from the prior release, and if necessary restore biodemo from `validation/t130-observer/backups/biodemo-before-0007.dump`. Never recreate the Docker network or delete volumes.

## 2026-08-12 T129 WGS-only Phase 1

```text
t129_goal: deploy the WGS-only control platform on BS10610 while the WGS 3.9.3 workflow remains mutable.
t129_scope: FastAPI/biodemo, RBAC sessions and audit, WGS-only React UI, read-only wgs-observer, paused Airflow CCE/on-prem/intake topologies, and fresh platform state.
t129_execution_gate: WGS_EXECUTION_ENABLED=false; backend submit returns HTTP 409; DAG runner tasks contain no production commands and fail closed.
t129_deferred: WGS Rules/logger changes, node005 OBS transfer, CCE submission, group_evidence integration, four-real-run concurrency, and CCE/SGE/local biological smoke are Phase 2.
t129_safety: no WGS 3.9.3 workflow file, production FASTQ/result/reference directory, kubeconfig, or private OBS credential is modified or copied.
t129_deployment: BS10610 current -> releases/20260812-wgs-only-phase1 (Git a30dcdb); fresh migration 20260812_0006, eight services healthy/running, three WGS DAGs paused, pools 4/1, auth/RBAC smoke passed, synthetic request created, submit returned 409.
t129_cleanup: old airflow-NIPT root, its Postgres/Redis volumes, and all old airflow-WGS releases were permanently removed after acceptance; 20260812-wgs-only-phase1 is the only release. Production WGS 3.9.3, CCE evidence, FASTQ, references, and results were preserved.
t129_status: Phase 1 deployed and accepted. T130 workflow integration remains todo.
```

> 本文件由 Codex/agent 持续维护。每次任务开始前先读，每次任务结束前更新。

## 1. 当前阶段

```text
current_goal_ascii: T128 repairs BS10610 NIPT manual FASTQ discovery latency without submitting analysis; BS1069 remains a stopped cold standby.
t128_root_cause: /api/input/scan eagerly materialized the complete /data/nipt-fastq tree before applying max_samples; the BS root contains hundreds of batches and more than 23,000 clean FASTQ files, so nginx returned 504 after 60 seconds.
t128_change: NIPT discovery now walks newest directories lazily and exits at max_samples; the BS default approved scan root is /data/nipt-fastq/FQ2026 and Submit Run adopts the root returned by /api/input/roots.
t128_safety: the existing /data/nipt-fastq read-only mount and historical run paths are unchanged; no run is created/submitted, bio_intake_scan remains paused, and no FASTQ/database/volume/network mutation is allowed.
t128_status: implementation and isolated backend/frontend tests pass; BS10610 deployment and real FQ2026 latency acceptance remain pending.
t127_architecture: one existing Compose project airflow-nipt; shared PostgreSQL, Redis, FastAPI, React/nginx, Airflow API, scheduler, and Celery worker; deployed DAGs are bio_nipt_docker, bio_wgs, and paused bio_intake_scan; PGT-A is absent.
t127_concurrency: NIPT Docker and host WGS share one-slot bs_heavy_analysis; WGS uses up to 96 host cores and NIPT uses 32 container cores; the two heavy workflows cannot overlap.
t127_wgs_runtime: host Snakemake 9.23.1/Python 3.12 is deployed under /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS; Airflow invokes a restricted forced wgs-run command through SSHOperator; production WGS sources remain read-only.
t127_validation_scope: WGS acceptance stops at an Airflow-managed Snakemake 9 pre-calling dry-run for one family; WGS_20260715_062217_351C76 completed success in 12 seconds with 21 planned jobs persisted as terminal skipped and no biological rule executed.
t127_active_run: none. The latest accepted WGS dry-run and all three T127 NIPT validations are terminal success; the earlier intentionally stopped WGS_20260714_180953_9D7981 remains a historical failed handoff record.
t127_nipt_validation: NIPT_20260715_030032_9A815B, NIPT_20260715_031706_C435A8, and NIPT_20260715_033817_4B4F72 each completed 27-sample full analysis serially in 858, 783, and 884 seconds; each has 27/27 sample QC pass and 232/232 success rule events with zero running events.
t127_images: BS10610 uses backend bs-control-f11ea02 (sha256:221955332609...) and frontend bs-control-f11ea02 (sha256:93cf3a076c43...); archives moved fengxian -> local Windows -> each BS and passed SHA256. BS1069 loaded the same images and remains stopped.
t127_frontend: live browser acceptance shows one NIPT Docker + WGS control plane, zero visible PGT-A labels, zero console warnings/errors, JSON-safe /api routing, WGS dry-run as success with QC not applicable, and 21 planned dry-run jobs rather than false running rules.
t127_safety: scanner remains paused, automatic NIPT/WGS submission remains disabled, PostgreSQL/Redis volumes were preserved, and no FASTQ/result/workflow source was deleted or modified.
t126_primary: BS10610 runs fresh PostgreSQL/Redis, FastAPI, React/nginx, Airflow CeleryExecutor API/scheduler/worker, bio_nipt_docker, and paused bio_intake_scan under /mnt/biodevrwbi/33.chenjiucheng/project/airflow-NIPT.
t126_runtime: NIPT_20260714_133355_B3081A (10 samples) and NIPT_20260714_140419_F999B0 (72 samples) completed with 10/10 and 72/72 QC pass; the 72-sample run completed in 923 seconds with 592/592 terminal-success rule events and 42.86 GiB observed peak memory.
t126_integrity: all 144 source FASTQ SHA256 and stat records were identical before/after the 72-sample run; mapping QC, T21 classifier, and dynamic-reference summaries match the fengxian S9 baseline, with fetal-fraction deltas <=4e-6.
t126_images: default 172.17.61.235:2333/niptpro/niptpro:1.1.11 preserves source image ID sha256:71df36b7f8080762f2db771e13e4daa7f4a666b3e1efc19c3bf12add22187254; legacy 1.0.11 remains available and unmodified.
t126_standby: BS1069 receives archives through fengxian -> local Windows -> BS1069 only; checksums pass and images are loaded, while scheduler/worker/frontend/backend remain stopped.
t126_network: external nipt_analysis_test_net remains immutable at 192.168.199.0/24 with gateway 192.168.199.1; only frontend-nginx publishes 172.17.106.10:12959 and :12958.
t126_safety: bio_intake_scan remains paused, NIPT automatic submission remains disabled, FASTQ/workflow/locale mounts are read-only, and no Postgres/Redis volume or historical output was deleted.
t125_network: external network nipt_analysis_test_net, subnet 192.168.199.0/24, gateway 192.168.199.1; deployment must not create, recreate, delete, or alter it.
t125_scope: writable project root /mnt/biodevrwbi/33.chenjiucheng/project/airflow-NIPT; BS10610 primary, BS1069 cold standby; NIPT Snakemake 9 only.
t125_ingress: BS10610 observed the current SSH client as 172.17.61.18, so nginx allowlist 172.17.61.0/24 covers the present operator path; final HTTP source still requires access-log verification.
t125_status: documentation and BS10610/BS1069 project-root write probes completed and were superseded by the accepted T126 runtime deployment.
t124_baseline: T124 QC formatting, Intake alignment, and terminal sorting is deployed and remotely accepted.
t124_code: terminal runs sort by latest pipeline completion; Intake shares project/runtime cells and the success-only ETA model; QC count/rate/fraction formatting is centralized in the frontend.
t124_validation: remote backend pytest passed 168; frontend Vitest passed 49; production tsc/vite build and Compose config passed; backend/frontend were rebuilt and recreated; HTTP/API and live browser checks passed at 1280/1024/390 px.
t124_runtime: latest completed NIPT is first in Run Tracker; linked Intake rows expose elapsed/ETA and hide scan roots; NIPT rate/fetal values and PGT-A count/decimal values render with operator units. Scanner remains unpaused on */10 and no analysis was triggered.
t124_backup: /home/jiucheng/project/airflow-demo-t121/backups/T124-20260714-1220/pre-overlay-source.tar.gz (SHA256 ed1f54f5b9114622604c60e95674c1427b0bb02959cdddebae04168083743666).
t123_baseline: T123 Predict-only operator path and runtime-state consistency is deployed and remotely accepted.
t123_frontend: Dashboard Intake defaults to Pending & errors with History for linked runs; Run Tracker shows Manual/Intake provenance; PGT-A Run Detail shows only Predict and hides historical baseline actions; logs are grouped by failure/current/workflow/other; Workflow Catalog is live.
t123_backend: dashboard exposes run source and QC display semantics; failed parents cancel stale running rule events; workflows aggregate live persisted state; scanner state exposes trigger/retention contracts.
t123_runtime_policy: NIPT S9 default is 32 cores; Airflow json logs rotate at 50 MB x 3; scanner-only DAG history/log retention runs at 03:00, cannot target analysis DAGs, and a terminal propagation task prevents cleanup from masking scan failure.
t123_validation: remote isolated backend pytest 187, frontend Vitest 47, frontend tsc/vite build, Intake DAG unittest 6, config override unittest 10, Compose config, Airflow import, HTTP health, and live browser checks passed.
t123_safety: PGTA_20260713_144002_E73F72 reached success before any worker restart; no active runs were reported at the deployment gate.
t123_runtime: backend, Airflow API/scheduler/worker, and frontend are deployed from /home/jiucheng/project/airflow-demo-t121; scanner remains unpaused on */10, NIPT auto-submit remains disabled, and Airflow/Postgres/Redis volumes were not recreated.
t123_reconciliation: NIPT_20260713_145457_ACCBDC retains two true failed mapping samples while eight stale running siblings are canceled; no rule event remains running, and failed sample logs open first in Run Detail.
t123_nipt_32c: manual clone NIPT_20260713_162606_5B5B11 completed success in about 14 minutes with 20/20 sample QC pass and 176/176 rule events success; Workflow Catalog now reports it as the latest NIPT Full run.
t123_backup: /home/jiucheng/project/airflow-demo-t121/backups/T123-20260714-0025 contains the pre-deploy scanner state/run inventory and SHA256SUMS.
t122_root_cause: NIPT run and Discovery data were already synchronized as success, but successful Discovery rows were archived and hidden by Dashboard lifecycle=active; the Dashboard Intake query also did not refresh after active-run sync, leaving stale submitted rows in an open browser session.
t122_frontend: Dashboard and Platform Settings default to lifecycle=all. Active polling, manual Sync, and Submit refresh Intake with no loading flash. Linked rows use display_status/analysis_status, so submit_state=submitted does not mask workflow success.
t122_live_nipt: NIPT_20260713_135001_98E375 is success, QC pass, 72 samples, progress 100, current stage Completed, and archived with workflow_success. The four NIPT Discovery records are visible through lifecycle=all.
t122_runtime: frontend only was rebuilt/recreated from /home/jiucheng/project/airflow-demo-t121; backend, Airflow services, scanner, DB, FASTQ, workdirs, and pipeline containers were unchanged.
t122_validation: remote frontend Vitest passed 40; production tsc/vite build and Compose config passed; frontend returned HTTP 200 and deployed bundle contains the completed-intake label.
t121_root_cause: project-20260713 failed before run creation because source_batch 2026-06-08/batch01 did not exist and H1/H2 were not resolvable FASTQ sample IDs. This was an Intake manifest error, not a Snakemake config or Airflow DAG failure.
t121_ui: Dashboard and Platform Settings now show Intake validation failed plus the concrete backend last_error in their shared Discovery table.
t121_template: project-20260713.samples.par.tsv now uses source batch 2026-06-08/HZSW-20260602-L-01-2026-06-062220 and samples JZ26117424-H1-H1/JZ26117425-H2-H2. Read-only parsing resolved two unique R1/R2 pairs with no errors.
t121_safety: the files retain non-trigger .par.tsv/.par.READY names; no project-20260713.samples.tsv or project-20260713.READY was published, so no PGT-A run was started. The original template is backed up under /home/jiucheng/project/airflow-intack-configs/pgta/backups/T121-20260713.
t121_runtime: backend/frontend are deployed from /home/jiucheng/project/airflow-demo-t121; health is green, scanner remains unpaused, and the live error row exposes current_stage and last_error.
t121_validation: remote backend pytest passed 181; frontend Vitest passed 40; production tsc/vite build and Compose config passed; frontend returned HTTP 200.
t120_scope: operators edit path-free YAML under /home/jiucheng/project/airflow-intack-configs/nipt and atomically publish final *.nipt.yaml files to /home/jiucheng/project/airflow-intake-requests/nipt.
t120_parser: request_id/project_id/batch_id, all-or-list samples, approved runtime profile, full_run, cores, and explicit submit are validated; batch_id resolves uniquely below approved read-only NIPT FASTQ roots.
t120_gates: two stable scans, submit=true, defaults.auto_submit=true, request_submit_enabled=true, approved profile, and NIPT heavy-run policy are all required. Ordinary NIPT directory auto_submit.enabled remains false.
t120_runtime: backend is deployed from /home/jiucheng/project/airflow-demo-t120; the request inbox mount is active and empty, bio_intake_scan is unpaused, and no run or Discovery row was created during acceptance.
t120_template: project-20260713.nipt.yaml in the non-scanned edit workspace resolves 72 samples from 260422_TPNB500380AR_1070_AH33KYBGY2 with cores=32 and submit=true; publishing it would start a full run, so acceptance did not copy it to the trigger inbox.
t120_validation: remote backend pytest passed 181; Compose config passed; a read-only submit=false probe resolved 72 samples from batch 260422_TPNB500380AR_1070_AH33KYBGY2; API health/config/preview passed.
t119_scope: Dashboard terminal age updates locally every 60 seconds; Search operations drives Run Tracker and Intake; completed Intake records archive while preserving fingerprints and audit history.
t119_intake: scheduled discovery covers PGT-A READY manifests and the restricted NIPT BS_DEMO_20260713 root; NIPT auto-submit remains disabled and full runs are manually serialized.
t119_backup: pre-migration remote backup is /home/jiucheng/project/airflow-demo-backups/T119-20260713T140647 with Airflow/biodemo dumps, inventories, PGT-A inbox archive, and SHA256SUMS.
t119_status: done. T119 is deployed from /home/jiucheng/project/airflow-demo-t119; migration 20260713_0005 is applied; backend/frontend/Airflow health is green.
t119_data: biodemo has 8 successful runs and 129 samples. Intake has 6 archived rows and 0 active rows; the scanner is unpaused, scheduled PGT-A/NIPT discovery is healthy, and NIPT auto-submit remains disabled.
t119_nipt_runs: NIPT_20260713_080217_DEC52B has 10/10 QC pass and 96 terminal events; NIPT_20260713_090714_C941EA has 15/15 QC pass and 136 terminal events after a controlled 32-core same-workdir recovery from a 40-core cgroup OOM; NIPT_20260713_095250_374EA9 has 20/20 QC pass and 176 terminal events.
t119_validation: remote backend pytest 168, frontend Vitest 40, Intake DAG unittest 3, production tsc/vite build, Compose config, health, and live 1280/390 browser checks passed.
t118_intake_fix: blank and whitespace-only manifest lines are ignored; malformed non-empty rows still fail with a line number. Later parse errors cannot downgrade submitted Discovery, and restoring the valid manifest clears the warning.
t118_legacy_repair: t112-pgta-s9-full-h4-h5-20260711 was backed up and restored from false error to submitted for successful run PGTA_20260711_071416_C8C7BA; the next scan preserved the repair.
t118_five_sample: project-20260713-five-samples.samples.tsv and READY contain H1, H2, H6, H8, and H9 from one 2026-06-08 batch. Two scans created only PGTA_20260713_034634_939AFF; a third stayed idempotent. The run is active in Mapping/fastp_bwa and was not awaited to completion.
t118_log_audit: 212 ten-minute scanner runs occupied about 2.5 MB across 211 worker task-log files; Airflow DB was 13 MB and Docker json-file logging had no rotation. Follow up with 50 MB x 3 rotation and 30-day scanner-only retention.
t118_backup: /home/jiucheng/project/airflow-demo-t117/backups/T118-20260713-intake-repair contains the biodemo dump, Discovery snapshots, new manifest/READY, and SHA256 evidence.
t118_validation: remote backend pytest passed 141; dry-run resolved 5 samples, 10 FASTQ, and 17.47 GB; backend/frontend HTTP passed; scanner remains unpaused.
t117_runtime: backend/frontend run from /home/jiucheng/project/airflow-demo-t117. Submit labels submission provenance as Submitted by, defaults manual submissions to jiucheng, accepts arbitrary IDs with jiucheng/airflow suggestions, remembers the last ID in browser storage, describes both deployed assays as low-pass WGS, and Batch Runs renders bulk workflow phase summaries without per-run requests.
t117_workflow_ui: Run Detail separates selected Airflow tasks from skipped alternate branches. Browser checks at 1280 and 390 CSS pixels showed no document overflow; mobile Batch Runs collapses the phase rail to current stage and completed/total count.
t117_operator: PGTA_20260711_062522_4C4FC2 and PGTA_20260711_071416_C8C7BA were changed from codex-validation to jiucheng through an exact-snapshot CLI; each correction has a metadata_correction RunAction. NIPT codex-t113 remains unchanged.
t117_intake: project-20260712 malformed space-delimited rows were corrected to TSV after backup. Three controlled scans produced exactly one run, PGTA_20260712_171630_AE8239, with 4 samples and operator jiucheng; Airflow/backend are running in fastp_bwa Mapping. Acceptance intentionally did not wait for terminal completion.
t117_backup: /home/jiucheng/project/airflow-demo-t117/backups/T117-20260713-012000 contains biodemo dump, original/corrected manifest evidence, operator preview/apply output, before/after inventories, and SHA256SUMS.
t117_validation: backend pytest passed 139; frontend Vitest passed 38; production tsc/vite build passed; DAG unittest passed 90 with 5 expected logger skips; Compose config and HTTP health passed.
t116_runtime: backend and Airflow API/scheduler/worker run from /home/jiucheng/project/airflow-demo-t116; frontend remains healthy on 12959. Postgres, Redis, volumes, workdirs, FASTQ, logs, results, and pipeline releases were not recreated or deleted.
t116_airflow: deployed DAGs are only bio_pgta, bio_nipt_docker, and bio_intake_scan. Airflow retains two complete PGT-A runs and one complete NIPT run; legacy bio_pgta_airflow and bio_wes_qsub metadata were deleted and their source files are excluded by .airflowignore.
t116_intake: discovery was reduced from 25 rows to the submitted PGTA_20260711_071416_C8C7BA manifest row. Scheduled intake defaults to pgta only; manual NIPT server scan/submit remains available. bio_intake_scan was restored unpaused and subsequent successful cycles continue to leave discovery at one row without recreating NIPT/bootstrap rows.
t116_backup: /home/jiucheng/project/airflow-demo-t116/backups/T116-20260712-014626 contains verified Airflow+biodemo pg_dump files, before/after inventories, cleanup preview/apply JSON, and SHA256SUMS.
t116_validation: backend pytest passed 134; DAG unittest passed 90 with 5 expected logger-interface skips; Compose config, DagBag import, backend/frontend health, 3 runs, 75 samples, and retained workdirs were verified.
t115_runtime: backend/frontend are deployed from /home/jiucheng/project/airflow-demo-t115; frontend 12959 and backend 8000 are healthy. Airflow services, Postgres, Redis, volumes, and pipeline runners were not recreated.
t115_intake_ui: Platform Settings and Dashboard share one Discovery Tracker table. Settings uses server-side pipeline/state/keyword filters, 10-row pagination, independent config/scanner/discovery/preview states, and no scan/submit/unpause action.
t115_data_safety: /api/intake/status reported 25 discovery rows and the deployed run list remained exactly 3 retained successful runs. bio_intake_scan remained unpaused, PGT-A manifest intake remained enabled, and NIPT automatic intake remained disabled.
t115_validation: backend pytest passed 129; frontend Vitest passed 36; tsc/vite production build and Compose config passed; live Settings at 1440/1280/1024/390 had no document-level horizontal overflow and only the discovery table scrolled internally.
t114_runtime: services are deployed from /home/jiucheng/project/airflow-demo-t114; frontend 12959 and backend 8000 are healthy; bio_intake_scan was restored to its original unpaused state after maintenance.
t114_data: biodemo was backed up and reduced from 49 runs to PGTA_20260711_062522_4C4FC2, PGTA_20260711_071416_C8C7BA, and NIPT_20260711_111140_63C5A6; 75 samples remain. Airflow metadata, workdirs, logs, outputs, FASTQ, volumes, and pipeline releases were not deleted.
t114_nipt_qc: NIPT_20260711_111140_63C5A6 has 504 metrics, 72/72 sample QC pass, submitted_at 2026-07-11T11:11:40Z, pipeline_finished_at 2026-07-11T11:36:18Z, and runtime 1477 seconds.
t114_backup: /home/jiucheng/project/airflow-demo-t114/backups/T114-20260711-2230 contains the pre-cleanup pg_dump, run inventory, cleanup preview, and applied result.
t113_image: airflow-demo/niptpro:1.0.11-snakemake9.23.1-v1 image sha256:71df36b7f8080762f2db771e13e4daa7f4a666b3e1efc19c3bf12add22187254; original Snakemake 7 image and /opt/conda analysis environment remain unchanged.
t113_validation: 72-sample run NIPT_20260711_111140_63C5A6 completed all 591 Snakemake jobs in about 24.8 minutes; 592 persisted terminal events include the parent workflow event, with no residual running/failed events.
t113_comparison: samplesheet, mapping QC, model prediction, chr21 outputs, and four summary CSVs are byte-identical to the approved Snakemake 7 baseline; observed peak memory was 44.61 GiB and input/bundle stat manifests were unchanged.
t113_runtime: services are deployed from /home/jiucheng/project/airflow-demo-t113; NIPT full analysis uses a one-slot Airflow pool, max_active_runs=1, 90-minute timeout, real-time Snakemake rule/sample events, and paginated phase observability.
t113_gate: manual NIPT full analysis is approved after engineering validation; NIPT automatic intake remains disabled. PGT-A S9 and its manifest intake remain unchanged.
t112_release: pgta-s9-v1.4 is deployed at /home/jiucheng/pipelines/PGT_A_S9/releases/pgta-s9-v1.4; current points to the verified SHA256 release and the original PGT_A directory is unchanged.
t112_validation: small 2 x 1M run PGTA_20260711_061816_F1E358, full H3 run PGTA_20260711_062522_4C4FC2, and full H4/H5 manifest run PGTA_20260711_071416_C8C7BA all reached success with terminal logger events, passing QC, and WisecondorX predict outputs.
t112_runtime: frontend/backend/Airflow services are healthy from isolated /home/jiucheng/project/airflow-demo-t112; Airflow uses CeleryExecutor for project tasks, Snakemake 9 manages rule/sample parallelism inside the worker, internal scanner/event endpoints require a shared service token, and the worker verifies the immutable release manifest before execution.
t112_intake_gate: bio_intake_scan is unpaused after validation; PGT-A READY-manifest auto-submit is enabled and idempotent, NIPT auto-submit remains disabled, and NIPT full-run remains guarded.
last_t111_backend_tests: remote Dockerized full pytest passed 103 tests.
last_t111_airflow_tests: full unittest discovery passed 74 tests with 5 expected logger-interface skips; compose worker profile-mount and approved-runtime availability regressions passed.
last_t111_frontend_tests: remote Dockerized Vitest passed 24 tests; production tsc/vite build passed.
last_t111_runtime_smoke: PGTA_20260710_110056_DC8A8D metadata and NIPT_20260710_110057_79A631 mount_smoke both reached success with final reviewed profiles and resolved config provenance.
last_t111_browser_check: Submit and Run Detail Config passed at 1440 and 390 CSS pixels without document overflow; Compose artifacts remained hidden.
当前阶段: P3/P4/P6 Airflow + Snakemake/qsub mock observability + PGT-A Level 4 staged integration
当前目标: T110 已将 Dashboard、Batch Runs、Sample Matrix、Failure Triage 和 Run Detail 收敛为可分页、可筛选、无 N+1 的 PGT-A/NIPT 操作员工作区；下一步在不启用自动 intake 的前提下继续做正式流程上线前的审计与权限边界。
最近更新时间: 2026-07-10
最后更新 agent: Codex
```

## 2. 服务器信息

详见 `SERVER_INFO.md`。不得在此处写入密码或 token。

```text
server_host: fengxian
deploy_user: jiucheng
project_root: /home/jiucheng/project/airflow-demo
docker_available: true on fengxian read-only preflight
docker_compose_available: true, Docker Compose version v2.24.7 at $HOME/.docker/cli-plugins/docker-compose
qsub_available: false on fengxian read-only probe 2026-07-04; mock qsub wrapper available in repo
snakemake_available: true for PGT-A at /biosoftware/miniconda/envs/snakemake_env/bin/snakemake and /biosoftware/miniconda/envs/snakemake9_env/bin/snakemake
python_version: PGT-A locked python 3.12.2
node_version: <unknown>
```

## 3. 仓库状态

```text
repo_url: git@github.com:boksic1986/airflow-BS-demo.git
main_branch: main
active_branch: codex/platform/T119-operations-age-intake-archive-nipt-batches in isolated local worktree; T118 baseline is `224a792`
last_verified_code_commit: T119 branch is based on `224a792`; verified implementation is recorded by the current T119 branch head
worktree_strategy: single-worktree for now; fengxian is code mirror only
fengxian_mirror: /home/jiucheng/project/airflow-demo cloned from GitHub; T108 overlay is deployed there and `origin/main` on the mirror has been fetched to `0857e3d`, but the mirror worktree itself remains on its existing dirty deployment branch
```

## 4. 服务状态

| Service | Expected port | Status | Notes |
|---|---:|---|---|
| frontend | 12959 | running, healthy from T122 | Intake defaults to active + completed records, refreshes after Airflow sync, and exposes validation reasons |
| backend | 8000 | running, healthy from T121 | Intake error stage semantics, lifecycle/archive, and authoritative terminal Airflow reconciliation are deployed; migration `20260713_0005` is current |
| airflow web/api | 12958 | running, healthy | deployed DAGs remain `bio_pgta`, `bio_nipt_docker`, and `bio_intake_scan`; scanner is unpaused and its latest scheduled run succeeded |
| postgres | internal 5432 | running, healthy | image `postgres:15-alpine`; T119 backup verified; biodemo contains 8 successful runs, 129 samples, 6 archived Intake rows, and 0 active Intake rows |
| redis | internal 6379 | running, healthy | image `redis:7-alpine`; no host port published |
| mailhog | 8025 | stopped in T051 smoke | HTTP GET probe passed in earlier smoke; not started for T051 |

## 5. 数据库状态

```text
airflow_metadata_db: initialized by `docker compose -f docker-compose.yaml up airflow-init`; admin user exists, password only in remote .env
biodemo_db: initialized on fengxian by `docker compose -f docker-compose.yaml run --rm biodemo-db-init`
migrations_tool: Alembic
last_migration: 20260713_0005 Intake lifecycle fields (applied on fengxian during T119 rollout)
core_tables: pipeline, analysis_run, sample, snakemake_rule_event, qc_metric, artifact, run_action, intake_discovery
```

## 6. Pipeline 接入状态

| Pipeline | DAG | Snakemake | qsub | Docker | QC | Status |
|---|---|---|---|---|---|---|
| PGT-A S9 predict | `bio_pgta` stages validate, prepare, mapping, metadata, cnv_qc, cnv_predict, collect; full-run pool has one slot | Snakemake 9.23.1 release `pgta-s9-v1.4`; per-rule/sample logger events; fixed approved hg19 XX/XY/gender references | not used | not used | mapping QC, estimated depth, CNV QC, prediction status; QC fail is separate from workflow fail | engineering validation passed for 2 x 1M, one full H3, and full H4/H5 READY-manifest runs; PGT-A manifest intake enabled; not claimed as clinical validation |
| PGT-A demo | `bio_pgta` metadata/dryrun/failure smoke passed; `bio_pgta_airflow` Airflow-only logger/event POST passed; `baseline_qc` staged real run `PGTA_20260706_162150_00C4FD` completed after controlled interrupt/resume sequence; final resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` ended Airflow/backend `success` | direct Snakemake metadata target, `dryrun_cnv`, controlled `invalid_target`, and Level 4 `baseline_qc` smoke in Airflow worker passed; T088 sets `XDG_CACHE_HOME=<workdir>/tmp/xdg-cache`; T093 resume runs `--unlock` then `--cores 64 --rerun-incomplete`, no `--forceall`; T094 adds run-local cleanup of `mapping/*.sorted.bam.tmp.*.bam`; T095 sets conda `LD_LIBRARY_PATH`, `LD_PRELOAD=PGTA_LIBSTDCXX`, run-local `MPLCONFIGDIR`, and baseline QC Python preflight; Snakemake 9.23.1 logger plugin writes JSONL, Airflow log/XCom summary, and optional backend rule/job events | not used | server-path project creation, submit, status sync, logs, artifacts, rule event API, PGT-A run detail frontend v1, New PGT-A Run frontend scan/create/submit, active-run auto-sync, failed baseline_qc `Resume with 64 cores`, and QC/artifact panel API are available | baseline_qc parser/artifacts added; `/qc` imports 14 metrics for G10/G11 and both samples have QC decision `FAIL` | `/api/input/scan` and `/api/runs` create `created` run; submit triggers `bio_pgta`; Airflow-only manifest run can POST rule events to biodemo; frontend can create pgta runs for metadata/dryrun/failure/baseline_qc smoke, submit created runs, view run list/detail, samples, rules, logs, artifacts, QC, sync Airflow, and resume failed baseline_qc |
| WES qsub | `bio_wes_qsub` Airflow mock DAG passed with `new/resume/rerun_rule` and QC smoke | WES mock Snakefile dry-run passed; WES mock profile runtime passed in `snakemake-runner`; `bio_wes_qsub` runs Snakemake 9.23.1 inside Airflow worker with `profiles/qsub`, writes command/stdout/stderr/events and `reports/qc_summary.tsv` | mock qsub wrapper direct smoke passed with backend POST; Airflow/API/frontend smoke generated mock qsub job ids, stdout/stderr files, JSONL events, and command log proving `--forcerun fastp` without `--forceall` | `airflow-demo/snakemake-runner:0.1.0` and `airflow-demo/airflow:0.1.0` builds passed | WES mock QC parser and frontend QC panel done; real WES QC and MultiQC not started | T040/T041/T042/T030/T031/T044/T056/T060/T054 done; next step is T034/T063 MailHog notification or T080 smoke report/demo script |
| NIPT qsub | not started | not started | not started | n/a | not started | pending |
| NIPT Docker S9 | `bio_nipt_docker` keeps validate, prepare, run, collect project tasks; `max_active_runs=1`, pool `nipt_s9_full=1`, timeout 90 minutes | derivative image runs Snakemake 9.23.1/Python 3.12 logger while rules retain the original `/opt/conda` tools; per-rule/sample events are persisted and streamed | n/a | host Docker via Airflow worker socket; clean FASTQ batch is read-only; original NIPT bundle and S7 image are unchanged | reads, Q30, unique mapping, duplication, chrY, gender, fetal ratio, CNV/classifier artifacts | 72-sample baseline plus T119 10/15/20-sample runs passed; 40 cores can exceed the 60 GiB cgroup on heterogeneous mapping, while controlled 32-core recovery/validation passed; NIPT auto-submit remains disabled |

## 7. 最近测试结果

```text
last_backend_tests: remote Dockerized full T121 pytest passed 181 tests, including explicit Intake validation stage semantics.
last_frontend_tests: remote Dockerized T122 Vitest passed 40 tests; production `tsc -b && vite build` passed.
last_dag_import_tests: remote repo-mounted T119 Intake DAG unittest passed 3 tests using `/home/airflow/.local/bin/python`; deployed scanner and analysis DAGs are healthy.
last_snakemake_dryrun: passed on fengxian; `dryrun_cnv` run `PGTA_20260703_170917_20E8F2` ended Airflow/backend `success`, stdout log size 12677 bytes and recorded 7 dry-run jobs, stderr only had config-extension notice, artifacts returned stdout/stderr/config files
last_compose_config: passed on fengxian for T122; frontend only was rebuilt/recreated without changing backend, Airflow services, Postgres/Redis volumes, FASTQ, workdirs, logs, or results.
last_browser_responsive: T119 live Dashboard and Settings passed at 1280/390; document `scrollWidth <= clientWidth`, terminal age rendered from real data, and Archived Intake displayed all 6 records with only its table scrolling internally.
last_minimal_smoke: passed on fengxian for postgres redis backend frontend airflow-api-server airflow-scheduler airflow-worker, then docker compose down
last_airflow_health: passed on fengxian at http://127.0.0.1:12958/health with healthy metadatabase and scheduler
last_biodemo_migration: `biodemo-db-init` first run created role/database, repeat run succeeded; T103 `alembic upgrade head` applied 20260708_0002 `intake_discovery`
last_backend_airflow_client: mock tests covered health/list/get/trigger; real smoke verified backend `/api/health/airflow` against Airflow `/health`
last_backend_build: backend image built on fengxian using `backend/pip.conf` TUNA PyPI mirror and `/opt/venv`; dependency install step dropped from about 9 minutes to about 11 seconds after mirror config
last_pgta_project_create_smoke: passed on fengxian; scan root `/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28` returned 5 candidates with `truncated=true`, created `PGTA_20260702_162531_74CE91` with 2 samples, status `created`, `dag_run_id=null`, and generated `samples.selected.tsv` plus `request.json`
last_pgta_submit_metadata_smoke: passed on fengxian for T107; created/submitted `PGTA_20260708_141653_B57AB6`, backend status `success`, `dag_run_id=manual__PGTA_20260708_141653_B57AB6`, progress current_step `metadata`, and the new `bio_pgta` task tree shows both the historical metadata branch and the staged baseline_qc TaskGroup
last_pgta_t108_metadata_smoke: passed on fengxian; created/submitted `PGTA_20260708_160227_EFAD64` with target `metadata`, backend sync returned `success`, `dag_run_id=manual__PGTA_20260708_160227_EFAD64`, progress returned `percent=100`, Airflow task instances, and Snakemake rule event `metadata=success`; no heavy baseline_qc run was started.
last_pgta_diagnostics_smoke: passed on fengxian; `sync-airflow` changed `PGTA_20260702_171533_9A85B1` to `success` with `error_summary=null`, changed historical failed `PGTA_20260702_171200_A68C19` to `failed` with non-null `error_summary`, log API read metadata/stderr, artifact API returned metadata/stdout/stderr/config files, and missing log returned `LOG_NOT_FOUND`
last_pgta_airflow_logger_smoke: passed on fengxian; `bio_pgta_airflow` run `manual__PGTA_AIRFLOW_20260703_054712_501D8B_events` ended `success`, generated `run_metadata.tsv` (11 lines), `snakemake_events.jsonl` (22 lines), `snakemake_rule_summary.tsv` (29 lines), and `/api/runs/PGTA_20260703_054712_501D8B/rules` returned `all=success` and `collect_run_metadata=success`
last_frontend_run_detail_smoke: passed on fengxian at http://127.0.0.1:12959/; React HTML served, `/api/runs?pipeline=pgta` returned existing PGT-A runs, `PGTA_20260703_054712_501D8B` rules returned `all=success` and `collect_run_metadata=success`, metadata log/artifacts/samples APIs returned data, CORS preflight returned 200
last_frontend_submit_smoke: passed on fengxian; frontend HTML served at `http://127.0.0.1:12959/`, API scan of `/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28` returned 1 candidate with `truncated=true`, created `PGTA_20260703_154341_408A29`, submit returned `dag_run_id=manual__PGTA_20260703_154341_408A29`, sync ended `success`, artifacts returned 5 items, metadata log tail returned 3 lines, and run list contained the new run
last_frontend_submit_workspace_fix: passed on fengxian; red test first failed because `Submit new analysis` region was missing and `New PGT-A Run` lived inside the run-list aside, then frontend Docker test target passed with 12 tests after moving submit panels to main content; `docker compose build frontend` succeeded and `docker compose up -d frontend` redeployed 12959, with HTTP 200 and deployed CSS containing `submit-workspace`
last_pgta_level4_audit: 2026-07-06 read-only audit on fengxian confirmed `/home/jiucheng/pipelines/PGT_A/Snakefile` has real `baseline_qc`, it requires at least 2 baseline/reference samples and emits `qc/baseline/baseline_qc_summary.tsv`, `baseline_qc_pass_samples.txt`, and `baseline_qc_report.md`; no real Level 4 run executed in this audit
last_pgta_baseline_staged_integration: passed code-level remote validation on fengxian at commit 4cf6f6e; backend/frontend/Airflow images built, backend pytest 48 passed, frontend Vitest 14 passed, DAG unittest 14 passed, Airflow import errors `No data found`, frontend HTTP 200, backend `/api/health` ok, Airflow `/health` healthy after startup; no real baseline_qc run was executed
last_pgta_cache_fix_smoke: passed on fengxian at commit dd5c6e7; tests first failed on missing `workdir/tmp/xdg-cache`, then passed after setting `XDG_CACHE_HOME`; new metadata run `PGTA_20260706_140854_8F2CA4` submitted to `bio_pgta`, sync progressed running -> success, Airflow listed the DAG run as success, `logs/run_metadata.tsv` has 11 lines, artifacts include `snakemake_command`, and stderr no longer contains `/home/airflow/.cache/snakemake` PermissionError
last_timezone_alignment: passed on fengxian at commit f2fdff2; `docker compose config --quiet` rendered `AIRFLOW__CORE__DEFAULT_TIMEZONE=Asia/Shanghai`, `AIRFLOW__WEBSERVER__DEFAULT_UI_TIMEZONE=Asia/Shanghai`, `TZ=Asia/Shanghai`, and frontend build arg `VITE_DISPLAY_TIME_ZONE=Asia/Shanghai`; frontend Docker test target passed 15 tests; backend/frontend/Airflow containers report `date` as `+0800 CST`; Airflow logs show `+0800` and `Configured default timezone Asia/Shanghai`; frontend bundle contains `Asia/Shanghai`
last_sample_status_sync: passed on fengxian at commit 065907c; red backend tests first showed submit/sync left samples `pending`, then implementation passed targeted 3 tests and full backend pytest 48 passed; backend redeployed healthy; explicit sync refreshed visible runs, e.g. `PGTA_20260706_141915_5BE5E2` samples `E2/E3=success`, `PGTA_20260706_140854_8F2CA4` sample `E2=success`, and `WES_20260705_164813_C5561C` samples `S001/S002=success`
last_pgta_64core_autosync: passed on fengxian at commit fb107a4; compose renders `PGTA_SNAKEMAKE_CORES=64`; Airflow image unit tests for `bio_pgta`/`bio_pgta_airflow` command construction passed 4 tests; frontend Docker test target passed 16 Vitest tests including active-run auto sync and terminal stop; Airflow import errors returned `No data found`; frontend image rebuilt/redeployed at 12959 and returned HTTP 200; current baseline_qc run `PGTA_20260706_162150_00C4FD` remained `running` and was not interrupted
last_pgta_baseline_t092_monitor: 2026-07-07 14:11 CST read-only check on fengxian found compose config ok and services running; Airflow `bio_pgta` run `manual__PGTA_20260706_162150_00C4FD` still `running`; task states show `validate_request=success`, `prepare_pgta_config=success`, `run_pgta_target=running`, `collect_pgta_artifact=None`; backend run status and samples G10/G11 are `running`; `logs/snakemake.command.txt` contains `--cores 1` because the run started before T091; G10 mapping is complete with BWA real time 33885.400 sec, G11 BWA log is still updating; no `qc/baseline` files, no `/qc` metrics, and artifacts currently only include command/config; no `sync-airflow`, restart, retry, or new run was executed
last_pgta_t093_resume: 2026-07-07 18:09 CST on fengxian at commit 2821a5e; backend pytest 50 passed, Airflow DAG unittest 43 OK/5 skipped logger-interface-in-this-Python-env, frontend Docker test 17 passed, Airflow import errors `No data found`; old run `manual__PGTA_20260706_162150_00C4FD` was controlled-interrupted from exact matching Snakemake/BWA/Samtools processes and synced to backend `failed` with non-null `error_summary`; new resume run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T095201Z` is running, command contains `--cores 64 --rerun-incomplete`, unlock command contains `--unlock`, no `--forceall`, and active G11 processes show `bwa mem -t 16` plus `samtools sort -@ 16`; no `qc/baseline` terminal files yet
last_pgta_t094_resume_cleanup: 2026-07-07 20:13 CST on fengxian at commit 0a8e756; red tests first failed on missing tmp cleanup and missing cleanup artifact; after fix, compose config passed, backend image rebuilt and full pytest passed 51 tests, Airflow DAG unittest discover passed 44 tests with 5 logger-interface skips, Airflow import errors returned `No data found`; backend and Airflow scheduler/worker were recreated without touching Postgres/Redis/frontend or volumes; pre-resume check found 16 stale `mapping/G11.sorted.bam.tmp.*.bam` files and no matching running processes; resume run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z` started, `logs/pgta.resume.cleanup.tsv` recorded deletion of all 16 tmp BAMs, remaining tmp count is 0, command contains `--cores 64 --rerun-incomplete` and no `--forceall`, artifacts API exposes `pgta_resume_cleanup`, backend sync shows status `running`, and active process currently shows G11 `fastp -w 16`; terminal baseline QC artifacts still pending
last_pgta_t095_python_preflight: 2026-07-07 22:53 CST on fengxian at commit 3bd1270; initial read-only failure check found T094 resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z` failed in `baseline_bam_uniformity_qc` with `ImportError: /usr/lib/x86_64-linux-gnu/libstdc++.so.6: version CXXABI_1.3.15 not found`; first T095 commit `966e0d8` added conda `LD_LIBRARY_PATH`, run-local `MPLCONFIGDIR`, and preflight, but Airflow task resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T143132Z` still failed preflight; final fix `3bd1270` adds `LD_PRELOAD=/biosoftware/miniconda/envs/snakemake_env/lib/libstdc++.so.6`, remote DAG unittest passed 47 tests with 5 expected logger-interface skips, `docker compose config --quiet` passed, Airflow import errors returned `No data found`, direct worker preflight logged `matplotlib/numpy/pandas/pysam/scipy` versions, final resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` reached Airflow/backend `success`; artifacts include `pgta_python_preflight`, `pgta_baseline_qc_summary`, `pgta_baseline_qc_pass_samples`, `pgta_baseline_qc_report`; `/api/runs/PGTA_20260706_162150_00C4FD/qc` returns `pass=0,warn=0,fail=14,unknown=0`, and samples G10/G11 are workflow `success` with QC status `fail`
last_pgta_frontend_airflow_reconcile: 2026-07-08 on fengxian at commit f64e0d2; T098 deployed backend/frontend only, no new analysis submitted; `/api/health` ok and `/api/health/airflow` healthy; `/api/runs?pipeline=pgta&limit=50&offset=0` returned 17 PGT-A analysis runs and `PGTA_20260706_162150_00C4FD` list item now shows `status=success,qc_status=fail`; detail shows latest `dag_run_id=manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z`; `/qc` returns `pass=0,warn=0,fail=14,unknown=0`; Airflow `bio_pgta` lists 20 DAG runs total, with 5 matching that analysis because of resume history, and the latest matching DAG run is `success`
last_pgta_t099_run_tracker: 2026-07-08 on fengxian; T099 deployed frontend only, no new analysis submitted; frontend bundle contains `PGT-A Run Tracker`; `/api/health` ok and `/api/health/airflow` healthy; `/api/runs?pipeline=pgta&limit=20&offset=0` returned 19 PGT-A analysis runs and includes `PGTA_20260707_182024_8CA2A0` plus `PGTA_20260707_182056_39A374`; both run details return non-null `dag_run_id` (`manual__PGTA_20260707_182024_8CA2A0`, `manual__PGTA_20260707_182056_39A374`) and `status=success`; `PGTA_20260706_162150_00C4FD/qc` remains `pass=0,warn=0,fail=14,unknown=0`
last_pgta_t100_submit_autosync: 2026-07-08 on fengxian; user-reported stuck run `PGTA_20260708_012630_352915` had backend `status=submitted` and `dag_run_id=manual__PGTA_20260708_012630_352915`, while Airflow CLI showed that DAG run had already reached `success` at `2026-07-08T01:26:43.802222+00:00`; a safe manual `POST /api/runs/PGTA_20260708_012630_352915/actions/sync-airflow` reconciled backend status to `success` without rerunning workflow; T100 frontend fix now calls `sync-airflow` after Submit handoff and auto-syncs active Dashboard tracker runs; frontend Docker test target passed 7 tests, compose config/build/recreate passed, frontend 12959 returned HTTP 200, `/api/health` ok, `/api/health/airflow` healthy, and `/api/runs?pipeline=pgta&status=submitted&limit=20&offset=0` returned no stuck submitted PGT-A runs
last_image_check: passed on fengxian; compose external images pulled and backend built with explicit tag
last_image_cleanup: removed 37 dangling <none> images; no docker system prune, no volume prune
last_pgta_failure_smoke: passed on fengxian; `invalid_target` run `PGTA_20260703_170957_3DDEC3` ended Airflow/backend `failed` as expected, stderr log size 1322 bytes, `sync-airflow` wrote non-null `error_summary` containing `stderr_path` and last error lines
last_wes_mock_dryrun: passed on fengxian official mirror at `/home/jiucheng/project/airflow-demo`; Snakemake 8.5.4 dry-run for `pipelines/wes/workflow/Snakefile` showed 8 jobs across all/fastp/bwa_mem/markdup/final_summary
last_mock_qsub_wrapper: passed on fengxian official mirror with backend POST; analysis `WES_20260704_180650_MOCK` generated `MOCK-WES_20260704_180650_MOCK-12-bwa_mem-S001`, qsub stdout/stderr files, submitted/success JSONL events, and `/api/runs/WES_20260704_180650_MOCK/rules` returned `bwa_mem/S001=success`
last_qsub_profile_runtime: passed on fengxian official mirror with `airflow-demo/snakemake-runner:0.1.0`; `WES_PROFILE_20260704_230713` ran `snakemake --profile profiles/qsub`, Snakemake 9.23.1 saw `cluster-generic`, executed 8 WES mock jobs, wrote `reports/final_summary.tsv`, qsub stdout/stderr files, and 14 JSONL events containing `qsub_submitted`/`qsub_success`
last_wes_airflow_qsub_smoke: passed on fengxian official mirror with `airflow-demo/airflow:0.1.0`; `WES_AIRFLOW_20260705_004506` / `manual__WES_AIRFLOW_20260705_004506` ended Airflow `success`, wrote `reports/final_summary.tsv` with `S001/S002 mock_success`, qsub stdout/stderr files, and 14 JSONL events; `collect_wes_artifacts` XCom returned `event_count=14` and `qsub_log_count=14`
last_wes_reanalysis_smoke: passed on fengxian official mirror; API/frontend-created `WES_20260705_162041_2507AF` initial submit, `resume`, and `rerun_rule fastp/S001` all reached Airflow/backend `success`; `/rules` returned 7 rows; `logs/events/snakemake_events.jsonl` has 28 lines; `logs/snakemake.command.txt` contains `--forcerun fastp` and no `--forceall`
last_wes_qc_smoke: passed on fengxian official mirror; API/frontend-created `WES_20260705_164813_C5561C` submitted to `bio_wes_qsub`, sync reached `success`, `/qc` returned `pass=6,warn=0,fail=0,unknown=0` with 6 items, artifacts included `wes_qc_summary`, and `reports/qc_summary.tsv` exists
last_e2e_smoke: T080/T081 read-only demo smoke on fengxian at mirror head 3310134 confirmed frontend HTTP 200, backend health ok, Airflow metadatabase/scheduler healthy; PGT-A `PGTA_20260706_162150_00C4FD` workflow status success with G10/G11 QC status fail and `/qc` summary `pass=0,warn=0,fail=14,unknown=0`; WES QC run `WES_20260705_164813_C5561C` success with `/qc` summary `pass=6,warn=0,fail=0,unknown=0`; WES rerun_rule run `WES_20260705_162041_2507AF` success with command containing `--forcerun fastp` and no `--forceall`; full email/NIPT E2E not run
```

## 8. 已知问题

| ID | Issue | Severity | Owner | Next step |
|---|---|---|---|---|
| K003 | BS10610 与 fengxian 用户和路径不同，不能复用 fengxian 硬编码路径 | medium | infra/coordinator | 迁移前把路径参数化到 `.env` 并重复 Level 0 preflight |
| K004 | 远端直接访问 GitHub release 不稳定 | low | infra | 优先本地 GitHub 下载后 scp 到 fengxian；国内 Docker CE 镜像作为 Compose fallback |
| K005 | fengxian 仍有非 airflow-demo 的 `latest` 镜像和未使用 volumes | low | infra | 未经确认不要删除；本轮只清理 dangling images，不碰非项目镜像和 volume |
| K006 | fengxian 宿主机 3000 已被非项目 `next-server` 占用 | low | infra | airflow-demo frontend 改用 12959；不要停止非项目进程 |
| K007 | BS NIPT-only 部署依赖共享外部 Docker 网络，错误 IPAM 或静态 IP 冲突会影响同网段服务 | high | infra | 启动前检查 `nipt_analysis_test_net` 必须为 `192.168.199.0/24`、gateway `192.168.199.1`，并核对当前 attachments；不允许自动修复或替换网段 |

## 9. 当前阻塞

```text
真实部署/启动前阻塞:
- 真实 `qsub/qstat` 在 `fengxian` 仍不可用；当前 WES/NIPT qsub demo 只能使用 mock qsub wrapper，不提交真实集群任务
- PGT-A `baseline_qc` staged real run `PGTA_20260706_162150_00C4FD` 已通过 final resume 成功；当前不是 workflow blocker，但 G10/G11 的 baseline QC decision 均为 `FAIL`，后续若要作为演示成功样本需要评估数据或阈值
```

## 10. 下一步建议

```text
1. 若要正式启用自动扫描，先规划 T107：只在用户明确批准后修改 `config/intake.yaml` gates 并 unpause `bio_intake_scan`，用 before/after run-count 检查收口。
2. 执行 T082：整理回滚/清理 runbook，重点是不删除 volumes、不碰生产 PGT-A/NIPT 源目录、不盲目重跑 baseline_qc 或 NIPT full_run。
3. 执行 T034/T063：补 MailHog success/failure 邮件通知，邮件包含 run detail、QC/report、错误摘要链接。
4. 若演示需要 PGT-A QC pass 样本，先做只读数据/阈值审计，不要盲目重跑 baseline_qc。
```

## 11. T106 Intake dry-run preview and auto-submit gate checkpoint

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/intake/T106-intake-dry-run-gating` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

T106 adds a safety layer before automatic intake is ever unpaused:

- New backend `POST /api/intake/scan-preview` scans configured PGT-A/NIPT roots
  and returns dry-run rows plus summary counts without writing DB state,
  creating runs, or triggering Airflow.
- `POST /api/intake/scan-and-submit` now obeys both
  `defaults.auto_submit` and `pipelines.<name>.auto_submit.enabled` from
  `config/intake.yaml`.
- Default `config/intake.yaml` keeps PGT-A and NIPT Docker automatic
  create+submit disabled.
- Settings shows `Preview configured roots`, a read-only preview panel, and
  blocked-by-config reasons; it still has no unpause, scan-now submit, or
  full-run action.
- NIPT run creation now uses intake config roots with env fallback, so scanner
  and run creation validate against the same configured source roots.

Remote validation on `ssh fengxian`:

- `docker compose -f docker-compose.yaml config --quiet`: passed.
- backend Docker targeted pytest passed: `8 passed`.
- frontend Docker test target passed: `11 passed`.
- backend/frontend build and recreate passed; frontend production build ran
  `tsc -b && vite build`.
- Frontend `http://127.0.0.1:12959/` returned HTTP 200.
- `/api/health` and `/api/health/airflow` returned healthy payloads.
- `/api/intake/config` showed global and pipeline auto-submit gates disabled.
- `/api/intake/scan-preview` returned `total_batches=21,would_submit=0`.
- Preview did not mutate state: intake discovery count stayed `21/21`, NIPT
  run count stayed `5/5`.
- `bio_intake_scan` remained paused (`airflow dags list` final column `True`).

Known caveat: a future auto-intake enablement task must be explicit and reviewed before changing gates
or unpausing `bio_intake_scan`.

## 12. T107 UI density and PGT-A staged DAG checkpoint

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/frontend/T107-ui-pgta-dag-stages` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

T107 is implemented and remotely validated. Scope:

- Submit Task preview now uses a definition-style field layout so labels and
  values no longer collide; long scan root and workflow fields wrap on their
  own full-width rows.
- Samples views use `source files` instead of `fastq_path`, showing R1/R2
  basenames and a batch/folder secondary line when `metadata.source_dir` is
  available. Legacy rows show `Path not captured for this run`.
- Run Detail QC uses a compact sample-by-metric matrix with fail/warn-first
  sorting, sample search, status filter, and 20-row pagination.
- PGT-A `baseline_qc` now branches into an Airflow TaskGroup:
  `pgta_pipeline.run_pgta_mapping -> pgta_pipeline.run_pgta_metadata ->
  pgta_pipeline.run_pgta_baseline_qc`.
- PGT-A `metadata`, `dryrun_cnv`, and `invalid_target` continue to use the
  historical `run_pgta_target` task.
- Runner staging writes `logs/snakemake.<stage>.stdout.log`,
  `logs/snakemake.<stage>.stderr.log`, and
  `logs/snakemake.<stage>.command.txt`, plus stage events for Pipeline steps.
- `/api/runs/{analysis_id}/progress` keeps the same response shape but now
  knows T107 PGT-A stage task weights.

Remote validation on `ssh fengxian`:

- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker build --no-cache --target test -f frontend/Dockerfile frontend`:
  passed, 13 Vitest tests.
- backend Docker targeted pytest passed: 19 tests.
- Airflow worker unittest passed: 27 tests for `bio_pgta` DAG and
  `pgta_metadata_runner`.
- Airflow import check returned `No data found`.
- backend, airflow-worker, airflow-scheduler, and frontend images rebuilt and
  recreated without deleting volumes.
- Frontend `http://127.0.0.1:12959/` returned HTTP 200; `/api/health` returned
  ok and `/api/health/airflow` returned healthy metadatabase/scheduler.
- `airflow tasks list bio_pgta --tree` shows the staged TaskGroup plus the
  historical `run_pgta_target` branch.
- Light PGT-A metadata smoke `PGTA_20260708_141653_B57AB6` reached backend and
  Airflow `success`.

Local limitations and deliberate exclusions:

- Local Windows `python` shim was unusable; `py` exists but local backend tests
  lack FastAPI and Airflow dependencies.
- Local runner unittest runs under Windows but existing POSIX path assertions
  fail on backslash paths; remote Linux/container validation was used.
- Local Node/NPM are unavailable, so frontend tests/build ran in the remote
  frontend Docker test target.
- No heavy PGT-A `baseline_qc` run has been started by T107.

## 12. T096 frontend platform redesign checkpoint

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/frontend/T096-platform-ui-redesign` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

T096 upgrades the frontend from the prior single workspace into a routed bioinformatics operations platform while preserving the existing PGT-A and WES backend API behavior. New documentation is in `DESIGN.md`, `docs/frontend-design-review.md`, and `docs/frontend-spec.md`; `docs/06_FRONTEND_SPEC.md` now points to the v2 structure.

Implemented frontend routes:

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

Implemented shared components include `StatusBadge`, `MetricCard`, `PipelineCard`, `RunTable`, `WorkflowTimeline`, `LogViewer`, `SampleSheetUploader`, `PipelineSelector`, `ErrorPanel`, and `QcMetricCard`. Status semantics are centralized in `frontend/src/lib/status.ts`; mock/demo NIPT, WGS, workflow-template, and resource data are isolated in `frontend/src/mocks/platform.ts`.

Remote validation on `ssh fengxian`:

- `docker build --target test -f frontend/Dockerfile frontend`: passed, 7 Vitest tests.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker compose -f docker-compose.yaml build frontend`: passed, including `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`: passed.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200 after nginx readiness.
- `GET http://127.0.0.1:8000/api/health`, `/api/health/db`, and `/api/health/airflow`: all returned ok/healthy.
- Existing PGT-A run `PGTA_20260706_162150_00C4FD` detail, samples, and stderr log endpoints returned data.
- Existing WES run `WES_20260705_170904_5D1C74` detail, rules, and QC endpoints returned data.

Local notes: local Windows has no `node`, `npm`, or `docker`; local checks remain git/docs/manifest only. `frontend/package.json` has no `lint` script, so `npm run lint` was not run.

## 12. T097 PGT-A-only frontend deployment scope

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/frontend/T097-pgta-only` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

The current frontend deployment target is PGT-A-only. This supersedes the T096 visible product surface for demo purposes:

- Sidebar shows Dashboard, Submit Task, Runs, Samples, Failures, and Settings. Workflows is not linked in the sidebar.
- Dashboard, Runs, Samples, and Failures filter to `pipeline=pgta` and do not surface WES/NIPT/WGS demo entries.
- Submit Task only exposes the PGT-A server-path scan/create/submit path.
- Run Detail keeps PGT-A tabs, logs, QC, files, config, sync, and baseline_qc `Resume with 64 cores`.
- Direct `/workflows` navigation remains development-accessible but displays only the PGT-A workflow template.
- Historical WES qsub backend/DAG/Snakemake code is intentionally left in place but is no longer a current deployable frontend entry.
- NIPT/WGS remain hidden from the current frontend demo.
- MailHog/SMTP notification work is not part of T097; `T034` and `T063` remain todo.

Remote validation and deployment on `ssh fengxian`:

- Remote mirror switched to `codex/frontend/T097-pgta-only` at frontend code commit `3119be5`.
- `docker build --no-cache --target test -f frontend/Dockerfile frontend`: passed, `1 test file`, `5 tests`.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker compose -f docker-compose.yaml build frontend`: passed, including `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`: passed, recreated only the frontend container.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200 from nginx.
- `GET /api/health`: returned `{"status":"ok"}`.
- `GET /api/health/airflow`: metadatabase and scheduler healthy.
- `GET /api/runs/PGTA_20260706_162150_00C4FD`: returned PGT-A detail data.
- `GET /api/runs/PGTA_20260706_162150_00C4FD/qc`: returned `pass=0,warn=0,fail=14,unknown=0`.
- `GET /api/runs/PGTA_20260706_162150_00C4FD/logs?stream=stderr&tail=20`: returned stderr tail lines.

## 13. T099 PGT-A Dashboard run tracker and submit handoff

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/frontend/T099-pgta-run-tracker` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

The current deployed frontend remains PGT-A-only. T099 changes the main operator experience:

- Dashboard no longer splits recent failed and completed runs into separate blocks. It shows one large `PGT-A Run Tracker` ordered by active, failed/QC failed, created-only, then recent success runs.
- Each tracker row shows project name from `params.project_name` when available, `analysis_id`, workflow status, QC status, current step, progress estimate, progress bar, samples, created/started/duration fields, and View/Submit/Sync actions.
- Tracker filters are All, Running, Submitted / queued, Created only, Failed, QC failed, and Success.
- Created-only runs show `Not in Airflow`; active runs can be synced and are eligible for 15-second Dashboard polling.
- Dashboard bottom panels are now Service health, PGT-A resource overview, and PGT-A workflow.
- Submit Task primary action is `Create and submit to Airflow`; it calls `POST /api/runs`, then `POST /api/runs/{analysis_id}/actions/submit`, then fetches detail and displays `dag_run_id`.
- `Create only` remains available as a secondary action and explicitly warns that the run is not visible in Airflow until submitted.
- Scan results are grouped by source folder, with FASTQ file names behind an expand control and absolute paths hidden by default behind `full path`.

Remote validation and deployment on `ssh fengxian`:

- `docker build --target test -f frontend/Dockerfile frontend`: passed, `7` Vitest tests.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker compose -f docker-compose.yaml build frontend`: passed, including `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`: passed, recreated only frontend.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200 from nginx.
- `GET /api/health`: returned `{"status":"ok"}`.
- `GET /api/health/airflow`: metadatabase and scheduler healthy.

## 14. T104 Dashboard aggregation and intake config checkpoint

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/dashboard/T104-dashboard-intake-config` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

T104 changes the Dashboard from frontend fan-out requests into backend
aggregation:

- New backend APIs: `/api/dashboard/overview`, `/api/dashboard/runs`,
  `/api/system/resources`, and `/api/intake/config`.
- New config file: `config/intake.yaml`; backend reads it through
  `INTAKE_CONFIG_PATH=/app/config/intake.yaml` and keeps env roots as fallback.
- Dashboard first screen uses overview, dashboard/runs, intake/status, and
  system/resources; it does not call run detail, `/progress`, or `/rules` for
  each visible run.
- Run Tracker defaults to 10 rows per page, supports pipeline selector,
  status filter, keyword search, previous/next pagination, progress bar,
  current Airflow task, and current pipeline rule.
- Intake scanner states distinguish `Observed`, `Stable ready`,
  `Auto-submitted`, `Bootstrap observed`, `Disabled`, and `Error`; observed
  bootstrap rows are not displayed as queued workflow execution.
- Bottom Dashboard panels are `Service & Node Health`, `Pipeline Resources`,
  and `Workflow Activity`.

Validation completed so far:

- Local Python syntax check passed for changed backend modules.
- Remote backend Docker targeted pytest passed: 7 tests
  (`test_dashboard_service.py`, `test_intake_config.py`,
  `test_system_resources.py`).
- Remote frontend Docker test target passed: 10 Vitest tests.
- Remote `docker compose -f docker-compose.yaml config --quiet` passed.
- Remote `airflow dags list-import-errors` returned `No data found`.
- Remote build/recreate passed for backend, airflow-worker, airflow-scheduler,
  and frontend; frontend production build ran `tsc -b && vite build`.
- Frontend `http://127.0.0.1:12959/` returned HTTP 200.
- Backend `/api/health` returned ok; `/api/health/airflow` returned healthy
  scheduler and metadatabase.
- Runtime `/api/dashboard/overview?pipeline=all` returned 26 visible PGT-A/NIPT
  runs, 0 running, 8 failed, and intake summary with 21 bootstrap rows.
- Runtime `/api/dashboard/runs?pipeline=all&limit=10&offset=0` returned
  `limit=10`, `items=10`, `total=26`.
- Runtime `/api/system/resources` returned `source=host_proc`, 128 CPU cores,
  and disks `/` plus `/data`.
- Runtime `/api/intake/config` returned `source=/app/config/intake.yaml` with
  pipelines `pgta` and `nipt_docker`.
- Endpoint timing on `fengxian`: dashboard overview about 0.019s; dashboard runs
  first page about 1.641s.
- `bio_intake_scan` remains paused (`airflow dags list` final column `True`).
- `GET /api/runs?pipeline=pgta&limit=20&offset=0`: returned 19 total PGT-A analysis runs, including `PGTA_20260707_182024_8CA2A0` and `PGTA_20260707_182056_39A374`.
- Both July 7 run details returned non-null `dag_run_id` and `status=success`.
- `GET /api/runs/PGTA_20260706_162150_00C4FD/qc`: returned `pass=0,warn=0,fail=14,unknown=0`.

## 14. T100 PGT-A submit/Airflow status auto-sync

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/frontend/T099-pgta-run-tracker` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

T100 addresses the user-reported symptom: after creating and submitting a PGT-A project, the frontend stayed at `submitted` and the operator could not tell whether Airflow had entered the workflow.

Root cause found on `fengxian`:

- `PGTA_20260708_012630_352915` existed in biodemo with `status=submitted`, `dag_run_id=manual__PGTA_20260708_012630_352915`, `started_at=null`, `ended_at=null`, and no rule events.
- Airflow showed the same DAG run had already completed with `state=success`.
- The frontend Submit flow fetched run detail after `/actions/submit`, but did not call `/actions/sync-airflow`; Dashboard also waited for user/manual sync rather than reconciling active tracker rows immediately.
- A manual `POST /api/runs/PGTA_20260708_012630_352915/actions/sync-airflow` reconciled that run to backend `status=success` without creating or rerunning any workflow.

Implemented frontend behavior:

- Dashboard auto-syncs active/submitted PGT-A tracker runs immediately and every 15 seconds through backend `sync-airflow`, then reloads tracker data.
- Submit Task primary `Create and submit to Airflow` now calls `sync-airflow` after a successful Airflow handoff with `dag_run_id`, retrying briefly so fast metadata runs can move from `submitted` to `success` in the handoff summary.
- If Airflow is still running after the brief sync window, the Dashboard tracker continues polling and syncing until terminal state.

Remote validation and deployment on `ssh fengxian`:

- Red frontend test target first failed as expected because Dashboard and Submit did not call `sync-airflow`.
- `docker build --target test -f frontend/Dockerfile frontend`: passed after implementation, `7` Vitest tests.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker compose -f docker-compose.yaml build frontend`: passed, including `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`: passed, recreated only frontend.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200 from nginx.
- `GET /api/health`: returned `{"status":"ok"}`.
- `GET /api/health/airflow`: metadatabase and scheduler healthy.
- `GET /api/runs/PGTA_20260708_012630_352915`: returned `status=success`, `dag_run_id=manual__PGTA_20260708_012630_352915`, and Airflow start/end timestamps.
- `GET /api/runs?pipeline=pgta&status=submitted&limit=20&offset=0`: returned no stuck submitted PGT-A runs.

Remaining limitation: progress is still a frontend estimate from backend run/rule data. A future backend Airflow task-instance endpoint is needed for authoritative per-task progress and Airflow attempt history.

## 15. T101 NIPT Docker template-run deployment

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/nipt/T101-nipt-docker-demo` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

Current deployable frontend surface is now PGT-A + NIPT Docker. WES qsub, NIPT qsub, WGS, and mail notification remain hidden/deferred in the current demo.

Implemented:

- Backend `POST /api/runs` supports `pipeline=nipt_docker` with `template_id=run1|run2`, `run_mode=mount_smoke|full_run`, `cores`, `project_name`, and `note`.
- Backend submit supports `nipt_docker` and triggers Airflow DAG `bio_nipt_docker`.
- `full_run` remains guarded by `NIPT_ALLOW_HEAVY_RUN=false`; default acceptance uses `mount_smoke`.
- Airflow DAG `bio_nipt_docker` has task graph `validate_request -> prepare_nipt_docker_run -> run_nipt_docker -> collect_nipt_artifacts`.
- Runner writes `nipt_run_config.yaml`, `nipt_docker_compose.yml`, `nipt_airflow_request.json`, `nipt_docker.command.txt`, stdout/stderr logs, and `reports/qc_summary.tsv`.
- Airflow worker mounts the NIPT bundle and Docker socket; `group_add=${DOCKER_SOCKET_GID:-114}` is required on `fengxian` for socket access. Scheduler/API server do not mount the Docker socket.
- QC import parses NIPT `reports/qc_summary.tsv`, updates `qc_metric`, and refreshes `sample.qc_status`.
- Artifact API filters pipeline-specific artifacts; NIPT runs expose NIPT artifacts and no longer expose WES `wes_qc_summary`.
- Frontend Dashboard/Submit/Runs/Samples/Workflows/Failures support PGT-A and NIPT Docker only.

Remote validation on `ssh fengxian`:

- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `git diff --check`: passed.
- `docker build --target test -f frontend/Dockerfile frontend`: passed, 9 Vitest tests.
- `docker build -t airflow-demo/backend:t101-test -f backend/Dockerfile backend && docker run --rm airflow-demo/backend:t101-test pytest -q tests/test_nipt_docker_lifecycle.py tests/test_run_creation.py tests/test_run_submit.py tests/test_run_diagnostics.py`: passed, 31 tests.
- After artifact/QC refinement: `pytest -q tests/test_nipt_docker_lifecycle.py tests/test_run_diagnostics.py`: passed, 17 tests.
- `docker run --rm --entrypoint /usr/local/bin/python -v /home/jiucheng/project/airflow-demo/dags:/opt/airflow/dags:ro -w /opt/airflow airflow-demo/airflow:t101-test -m unittest /opt/airflow/dags/tests/test_bio_nipt_docker_dag.py /opt/airflow/dags/tests/test_nipt_docker_runner.py -v`: passed, 9 tests.
- `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler airflow-api-server frontend`: passed; frontend build ran `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend airflow-api-server airflow-scheduler airflow-worker frontend`: passed.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200.
- `/api/health` and `/api/health/airflow`: healthy after Airflow API server readiness.
- `airflow dags list-import-errors`: `No data found`.
- `airflow dags list` showed `bio_nipt_docker`.
- Initial smoke `NIPT_20260708_032949_C7F56B` failed because worker lacked Docker socket group permission; fixed by adding `DOCKER_SOCKET_GID=114` and worker `group_add`.
- Successful smoke `NIPT_20260708_033128_7B6386` proved Docker execution after socket group fix.
- Final smoke `NIPT_20260708_033450_8362A0` reached Airflow/backend `success`, QC `pass=96,warn=0,fail=0,unknown=0`, run list `qc_status=pass`, stdout `mount_smoke_ok NIPT_20260708_033450_8362A0 260414_TPNB500380AR_1065_AH32CCBGY2`, and artifacts `nipt_qc_summary`, `nipt_docker_compose`, `nipt_run_config`, `nipt_airflow_request`, `nipt_docker_command`.

Known caveats:

- `full_run` was not executed; this remains intentionally blocked unless the user explicitly approves a heavy NIPT batch.
- Historical failed smoke `NIPT_20260708_032949_C7F56B` remains in DB/Airflow history as evidence of the pre-fix Docker socket permission issue.
- T102 supersedes the T101 progress caveat: frontend progress now uses backend `/progress` with Airflow task instances plus runner rule events. Historical runs without captured rule events still show Airflow task progress.

## 16. T102 Airflow + Snakemake progress observability

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/progress/T102-airflow-snakemake-progress` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

Implemented:

- Backend endpoint `GET /api/runs/{analysis_id}/progress` combines biodemo run state, Airflow REST task instances, and `snakemake_rule_event` rows.
- `AirflowClient.list_task_instances()` reads `/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances`; no direct Airflow DB reads.
- PGT-A and NIPT Docker submit conf includes `backend_event_url=http://backend:8000/api/events/snakemake`.
- `dags/common/progress_events.py` writes runner events to JSONL and optionally POSTs to backend; POST failure is non-fatal.
- PGT-A runner emits target-level progress events and parses Snakemake stdout/stderr for rule blocks.
- NIPT Docker runner emits `nipt_mount_smoke` events and parses full-run Docker stdout/stderr when heavy mode is enabled.
- `sync-airflow` imports JSONL fallback events on terminal runs.
- Dashboard and Run Detail use `/progress`; Run Detail Workflow tab shows `Airflow tasks` and `Pipeline steps`.

Remote validation on `ssh fengxian`:

- `git diff --check`: passed.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- Backend targeted Docker tests passed: `29 passed`.
- Airflow DAG/runner Docker unittest passed: `35 tests OK`.
- Frontend Docker test target passed: `10` Vitest tests.
- Production build passed for backend, Airflow worker/scheduler/API server, and frontend; frontend build ran `tsc -b && vite build`.
- Recreated backend, Airflow API/scheduler/worker, and frontend without deleting volumes.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200.
- `/api/health`: ok; `/api/health/airflow`: metadatabase and scheduler healthy.
- `airflow dags list-import-errors`: `No data found`.
- Historical `/api/runs/PGTA_20260706_162150_00C4FD/progress` returned Airflow task timeline with `percent=100`.
- Historical `/api/runs/NIPT_20260708_033450_8362A0/progress` returned Airflow task timeline with `percent=100`.
- New PGT-A metadata smoke `PGTA_20260708_050811_A24E36` reached success with Airflow tasks and `metadata=success` pipeline event.
- New NIPT Docker mount smoke `NIPT_20260708_050843_B3B05E` reached success with Airflow tasks and `nipt_mount_smoke=success` pipeline event.

Known caveats:

- Historical runs before T102 cannot reconstruct missing Snakemake/runner events; they still show Airflow task-instance progress.
- NIPT `full_run` was not executed; it remains guarded by `NIPT_ALLOW_HEAVY_RUN=false`.
- Mail notification, WES qsub frontend restore, NIPT qsub, and WGS remain out of current deployable scope.

## 17. T103 PGT-A/NIPT batch scan and auto intake

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/intake/T103-pgta-nipt-auto-scan` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

Implemented:

- `POST /api/input/scan` supports `pipeline=pgta|nipt_docker`; `GET /api/input/roots` returns pipeline-specific scan roots.
- NIPT scan discovers chip folders with top-level `*.clean.fastq.gz` R1/R2 pairs and ignores nested adapter FASTQs in v1.
- New NIPT Docker create requests use `rawdata_root` and `selected_samples` from scan results; `template_id` is compatibility-only and no longer exposed in Submit Task.
- NIPT run params include `input_mode=nipt_docker_scan`, `source_batch_dir`, `source_batch_id`, `source_fingerprint`, `input_file_flavor=clean`, `chip_name`, and `selected_count`.
- `bio_nipt_docker` prepares a run-local chip CSV/config/compose and mounts the source batch read-only as `/input_batch`; no large FASTQ copy and no production bundle writes.
- Added `intake_discovery` table plus `/api/intake/status` and `/api/intake/scan-and-submit`.
- Added `bio_intake_scan`, paused on creation by default; bootstrap must record historical batches before unpausing automatic intake.
- Dashboard shows read-only Intake auto scanner status. Submit Task scans PGT-A/NIPT roots and creates one NIPT run per selected chip batch.

Remote validation on `ssh fengxian`:

- `git diff --check`: passed.
- Manifest check: `file_count=179`, listed files `179`, missing `0`.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker build --target test -f frontend/Dockerfile frontend`: passed, 10 Vitest tests.
- Backend Docker targeted pytest passed: 25 tests.
- Airflow DAG tests passed: 4 tests for `bio_intake_scan`/`bio_nipt_docker`; NIPT runner/progress tests passed: 12 tests.
- `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler frontend`: passed; frontend build ran `tsc -b && vite build`.
- Recreated backend, airflow-scheduler, airflow-worker, and frontend without deleting volumes; `alembic upgrade head` applied `20260708_0002`.
- Frontend HTTP 200 on `http://127.0.0.1:12959/`; `/api/health` ok; `/api/health/airflow` scheduler/metadatabase healthy.
- `airflow dags list-import-errors`: `No data found`; `bio_intake_scan` listed paused, `bio_nipt_docker` and `bio_pgta` listed unpaused.
- `/api/input/roots?pipeline=nipt_docker` returned `/opt/pipelines/NIPT/fastq`.
- NIPT scan of `/opt/pipelines/NIPT/fastq` returned clean FASTQ candidates grouped under chip folder `FQ2025/250103_NDX550692_RUO_0044_AH3H37BGYW`.
- Scanned NIPT mount smoke `NIPT_20260708_072349_4F942A` submitted to `manual__NIPT_20260708_072349_4F942A` and reached Airflow/backend `success`.
- `/progress` for that run returned `percent=100`, Airflow task instances, and `nipt_mount_smoke=success` rule event.
- `/qc` returned `pass=1,warn=0,fail=0,unknown=0`; stdout contained `mount_smoke_ok NIPT_20260708_072349_4F942A 250103_NDX550692_RUO_0044_AH3H37BGYW`; artifacts included NIPT QC/config/compose/command entries.
- Intake bootstrap with `bootstrap=true,max_samples=20` recorded existing PGT-A/NIPT batches as `observed/bootstrap`; it did not auto-submit historical batches.

Known caveats:

- `bio_intake_scan` remains paused until explicitly unpaused after bootstrap review.
- NIPT `full_run` was not executed and remains guarded by `NIPT_ALLOW_HEAVY_RUN=false`.
- Auto-intake currently uses PGT-A `metadata` and NIPT `mount_smoke`; production full-run automation needs a separate explicit approval/config gate.
## 2026-07-08 T108 validated

Current branch/worktree:

- Branch: `codex/frontend/T108-dashboard-run-detail-usability`
- Worktree: `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

Implemented and deployed:

- Dashboard Run Tracker is now an operator-readable table:
  Project/Run ID links, combined current stage, progress, runtime/ETA, and
  timezone-clean timestamps.
- Dashboard `QC / failure focus` was replaced by `Sample throughput` with
  `24h / 7d / 30d` period selector and sample-level counts.
- Intake scanner display was converted from card wall to compact table
  with discovery state semantics.
- Backend dashboard aggregation exposes sample throughput, sample trend,
  human-readable stage labels, elapsed runtime, and ETA estimate fields.
- Run Detail now renders selected samples as a manifest table, adds QC failure
  summary above the QC matrix, prioritizes Snakemake/NIPT config artifacts, and
  adds a controlled `Run action` modal.
- PGT-A reanalysis now has a controlled `rerun_stage` API path for
  `mapping`, `metadata`, and `baseline_qc`; arbitrary DAG/task trigger remains
  out of scope.

Remote validation:

- `docker compose -f docker-compose.yaml config --quiet` passed.
- Frontend Docker test target passed 14 Vitest tests.
- Backend targeted pytest passed 25 tests.
- Airflow DAG/runner unittest passed 28 tests in `airflow-demo/airflow:t108-test`.
- `docker compose build backend airflow-worker airflow-scheduler frontend` passed, including frontend `tsc -b && vite build`.
- `docker compose up -d --no-deps --force-recreate backend airflow-worker airflow-scheduler frontend` passed.
- Frontend `12959` returned HTTP 200 and backend `/api/health` returned ok.
- Dashboard overview/runs/resource/intake APIs returned T108 fields.
- Light PGT-A metadata smoke `PGTA_20260708_160227_EFAD64` reached backend/Airflow `success`.

Not changed:

- `bio_intake_scan` remains paused.
- Auto-submit remains disabled by default.
- NIPT Docker DAG is not split in this task.
- NIPT `full_run` and heavy PGT-A `baseline_qc` are not run without explicit
  approval.
# 2026-08-12 T131 WGS cloud orchestration Phase 1

- BS10610 candidate release:
  `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260812-wgs-orchestration-t131-candidate`.
- Input is now `batch_no + fq_path` with paired FASTQ links; Airflow creates
  manifest, sampleinfo, config and MD5 in its own workdir. READY is obsolete.
- biodemo is at Alembic `20260812_0008`; snapshot, review issue, transfer
  progress and OBS lease structures are live.
- `bio_wgs_cce` has 27 task nodes and six reschedule sensors. All WGS DAGs are
  paused. Pools are hash=2, OBS=1, Master=4.
- Backend/frontend/observer/Airflow run on BS10610. Network remains external
  `192.168.199.0/24`; only `172.17.106.10:12959` is published.
- Both real and mock execution gates are false. Synthetic smoke
  `WGS_20260812_152720_643D8D` created run artifacts and submit returned 409;
  no CCE or OBS command ran.
- Upstream `/mnt/biodevrwbi/33.chenjiucheng/project/wgs` was not modified.
