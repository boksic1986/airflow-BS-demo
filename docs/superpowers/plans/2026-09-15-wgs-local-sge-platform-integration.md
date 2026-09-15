# WGS Local / SGE 平台接入实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not launch parallel agents or expand testing without applicable authorization.

**Goal:** 新任务通过统一平台提交运行 CCE、Local 或 SGE；Local / SGE 通过项目监控入口命令行续跑后，前端继续正确同步。

**Architecture:** 复用现有提交、执行选择、WgsStageExecution、observer 和公共 UI。调用原生 WGS prepare/Step1/profile；平台负责启动及监控，不接管生信规则或 pending 决策。

**Tech Stack:** FastAPI、SQLAlchemy、Airflow、受控 SSH runner、Python/Bash、Snakemake logger、SGE qsub、React。

**Spec:** [已确认设计](../specs/2026-09-15-wgs-local-sge-platform-integration.md)。任务 `WGS-LOCAL-SGE-20260915`，文档基线 Airflow `93069eb`。

## Global Constraints

- 2026-09-15 用户已批准从 main `4b5234e` 建隔离 worktree 开始实施；按任务顺序推进，不扩大测试范围，生产部署仍须另行授权。
- CCE 入口节点 200，Local 节点 96/97，SGE 控制入口节点 18；执行账号 ctapa。
- 不修改 WGS 生信、样本筛选、家系、数据量检查或 pending 算法；不重建交接数据库。
- 不增加 Local / SGE 面板取消/续跑按钮；不自动接管原命令、历史目录或未知执行。
- 续跑保持 analysis_id、平台 attempt、release、配置、执行目标、workdir；只新增阶段执行 generation 和审计，不重新 prepare。
- 不新增锁系统、调度算法、资源限额、全量文件哈希检查或离线补注册体系。
- 不改变现有扫描/自动分析开关、CCE Step1–6、GATK 和独立测试项目限制。
- 不在本地运行项目测试；BS10610 缓存环境定向验收，不下载镜像或重跑完整 WGS。
- 生产验收/部署另行授权；不把文档或源码交付当成已启用。

## Task 1 — 原生合同与准备路由

**Owner:** Airflow 平台；原生接口由 WGS-pipeline 任务确认。

**Files:** `backend/app/wgs_execution_dispatch_service.py`、`backend/app/wgs_submission_service.py`、`backend/app/wgs_runtime_adapter.py`、`scripts/wgs_runtime_gate.py`；相应定向测试。WGS 源码若确需接口适配，只交 WGS-pipeline 修改。

**Consumes:** 已有 release、样本审核、mode/target、expected_revision 和 prepare 请求。

**Produces:** 进入 prepare_analysis 前冻结的 mode/target；原生对应模式生成的项目、配置及启动入口。CCE 专用参数不传给非 CCE 模式。

- [x] WGS-pipeline 已核对候选源码 `ba7b27276a55ed3ce1fb2efe81c99c89b52d0f8b`：原生 local/sge、Step1 参数透传及 exitcode/metadata 可复用；不是已发布/已部署 release，不替换 catalog。详见设计的合同核对记录。
- [ ] 写最小参数化回归，覆盖三种模式和配置冻结竞态；先在 BS10610 运行失败用例。

```python
# 待新增 tests/test_wgs_onprem_contract.py 的核心行为断言
assert prepared.execution_mode == submitted.execution_mode
assert prepared.execution_target == submitted.execution_target
assert prepare_argv[prepare_argv.index("--run-mode") + 1] == submitted.execution_mode
assert selected_sample_ids == native_selected_sample_ids
# local/sge 不携带 --cce-config；准备开始后改 mode/target 返回冲突。
```

- [ ] 将新任务目标冻结提前到最终配置生成前，复用 revision/事务保护；拒绝配置生成后原地切换，不改历史任务。
- [ ] 直接调用原生 prepare；撤掉新 Local 任务执行路径中的 CCE 配置二次转换，不删除旧运行所需代码。
- [ ] 只运行本任务定向测试；更新 API/运行时文档中“计划”与“已实现”的状态，提交独立代码变更。

**Acceptance:** 三种模式配置与审核结果一致；selected 不变；原生 pending 行为不被平台接管；CCE 当前路径回归不变。

**2026-09-15 进度：** 冻结基础代码已完成：使用 AnalysisRun 行锁和现有 dispatch
revision，在配置确认事务中保存 attempt/mode/target/revision；重复确认幂等，确认后切换拒绝，
新 attempt 清除旧冻结。仅对 `native_prepare_contract=1` 生效，创建入口尚不赋该标记，
不会提前开放未完成的原生路由。旧任务保留原有合同。BS10610 离线缓存镜像验证
5个新增用例（含三模式参数化）及2个相关既有用例，共7 passed；先行红测4 failed/1 passed。
这里验证的是事务入口的顺序与幂等行为，不宣称已完成 PostgreSQL 双会话并发或实际节点验收。
下一项仍为 Task 1：原生 prepare 参数、产物绑定、创建入口/自动预批准接线；完整 Task 1 未完成。

## Task 2 — Local / SGE 共用启动与证据入口

**Owner:** Airflow 平台运行接入；WGS 仅提供原生入口能力。

**Files:** `scripts/wgs_local_runtime_gate.py`、新增 `scripts/wgs_onprem_runtime.py`（共用实现）、新增 `scripts/wgs_sge_runtime_gate.py`（薄入口）、`dags/bio_wgs.py`、`config/wgs_stage_contract.yaml`、`backend/app/main.py`、`backend/app/wgs_observer.py`；定向 runner/DAG 测试。

**Consumes:** Task 1 的冻结项目与执行目标；已有 execution_id / generation / request_hash。

**Produces:** `Step1_run.monitored.sh`、明确的控制进程身份、分执行保存的 logger/日志/状态证据；Local 的 `local_analysis` 和 SGE 的 `sge_analysis` 阶段。

- [ ] 写 runner 路由、身份传递、后台执行和去重测试。相同有效执行重复调用只返回已有身份，不再启动。

```python
# 待新增 scripts/tests/test_wgs_onprem_runtime.py 的行为边界
assert observed_target == frozen_target
assert native_entry.name == "Step1_run.sh"
assert original_step1_bytes == step1_bytes_after_launch
assert new_control_processes_after_duplicate == 0
assert not prepare_calls and not forceall_args and not cloud_transfer_calls
```

- [ ] 将 Local 的 node97 专用调度参数化为受控 node96/node97 映射，保留旧入口兼容；不改变 SSH 权限边界。
- [ ] SGE 在18启动原生控制进程，由原生 profile 投递子任务；替换占位 task，增加监控/收集依赖，不额外包外层 qsub。
- [ ] 共用入口附加 logger、平台身份和状态采集，后台进程独立于 SSH 生命周期。脚本不包含密钥或患者资料。
- [ ] API/observer 按执行目标和 generation 接受证据，禁止将 SGE qsub 成功或进程消失直接标为分析成功。
- [ ] 跑同一定向集合转绿；同步 DAG、运行时、安全和未来部署配置文档，独立提交。

**Acceptance:** Local 96/97 路由正确；SGE 子任务仍由 WGS 管理；重复请求不会双开；logger 和终态带当前执行身份。

## Task 3 — 命令行续跑登记与监控恢复

**Owner:** Airflow 平台。

**Files:** 新增 `backend/app/wgs_onprem_execution_service.py`、Task 2 共用 runner、`backend/app/main.py`、`backend/app/wgs_stage_execution_service.py`、`backend/app/wgs_observer.py`、`dags/bio_wgs.py`；新增 `backend/tests/test_wgs_onprem_execution.py`。

**Consumes:** 原项目监控入口、冻结平台身份、现有执行记录和当前活动进程/子任务证据。

**Produces:** 同平台 attempt 的新 generation；与其绑定的仅监控 DagRun；旧 DAG 和旧状态保留为历史。

- [ ] 写一组失败/续跑/重复调用回归，先验证失败；不以仅测试 mock 返回值代替业务状态断言。

```python
assert resumed.analysis_id == original.analysis_id
assert resumed.attempt == original.attempt
assert resumed.generation > original.generation
assert resumed.release == original.release and resumed.workdir == original.workdir
assert previous_execution.status == "failed"
assert not recovery_dag_calls_prepare and not recovery_dag_launches_analysis
assert late_old_failure_does_not_close_current_generation
```

- [ ] 内部阶段注册复用现有记录，附带来源、幂等操作身份和明确执行身份；事务持久化后才允许启动。回复丢失先查询，不能自动盲目重投。
- [ ] 平台不可用、冻结配置不符或旧执行活动状态不能确定时，在新分析启动前失败；不建设离线登记补偿。
- [ ] SGE 仅核对已关联到本次执行的子任务。存在活动子任务时阻止重投，不自动 qdel，不全队列猜测。
- [ ] 新执行建立仅监控/收集的 Airflow 路径，更新当前监控绑定；旧失败 DAG 保留，不将旧终态直接改 running，也不 clear prepare/启动任务。
- [ ] 监控和采集可幂等恢复：旧 evidence 被 generation 拒绝，重启 observer 不启动分析；采集异常与分析失败分开。
- [ ] 跑同一定向集合转绿；更新 API/DAG/运行时和运行手册，提交独立变更。

**Acceptance:** 原目录运行 `bash Step1_run.monitored.sh` 后，前端可从旧失败展示转到新执行状态；未改变样本、pending、配置及既有结果。

## Task 4 — 共用页面与最小联合验收

**Owner:** Airflow 平台前端与验收。

**Files:** 现有 `frontend/src/features/wgs/ExecutionTargetSelector.tsx`、RunDetail 的公共阶段/规则/日志/QC 组件、`frontend/src/api.ts` 及相应测试；不另建 Local/SGE 页面。

**Consumes:** 当前 mode/target、当前执行身份、真实 stage/rule/log/QC 投影。

**Produces:** 按执行方式显示的同一页面；不适用的云端操作隐藏。

- [ ] 定向测试 Local/SGE 的节点、排队/分析/收集状态和历史执行筛选；旧失败不覆盖新执行，规则不重复计数。
- [ ] 保留公共表格样式、分页和最新 UI 默认值；不把早期文档中的25行覆盖当前源码设置。
- [ ] 隐藏 Local/SGE 的 OBS/SFS/CCE 操作，不增加面板取消或续跑按钮。
- [ ] 使用当前 release 的 QC 解析和 provenance；缺失证据不伪造，旧 QC 不冒充本次完成。分析成功而采集失败单独展示。
- [ ] BS10610 使用缓存镜像跑新增定向后端/runner/DAG/frontend集合及一次构建；不跑全套、不下载依赖、不挂真实临床数据。
- [ ] 另获实际环境验收授权后，执行一次 Local、一次 SGE synthetic 小流程，覆盖首次启动、人工命令行续跑及前端同步。SGE仅两个轻量依赖rule，限额按已批准环境，不自行扩大。
- [ ] 同步 API、DAG、运行时、前端、部署、CURRENT_STATE/TASKS/HANDOFF；分别记录代码完成、测试通过、入口启用。

**Acceptance:** 同一前端可查看三种方式；Local/SGE 命令行监控入口续跑可重新收口；CCE/GATK 无无关功能变化。

## 发布与交接

每个任务提交仅包含本任务文件和文档，不合并无关研发提交。工作分支基于实施时核验的主线；本次文档分支不代表实现分支或部署版本。

部署到 BS96、配置96/97/18真实入口、启用新能力须另获授权并核对实际主机、release、容器挂载和活动任务。关闭新启动开关不应停止已运行控制进程；回滚保留必要采集，不删除运行身份、pending、台账和结果。

当前执行 Task 1；先落实配置生成前的模式/目标冻结，再连接原生准备产物。仅定向测试，不触发真实分析。Task 2–4 尚未实施，不宣称 Local/SGE 已接通。
