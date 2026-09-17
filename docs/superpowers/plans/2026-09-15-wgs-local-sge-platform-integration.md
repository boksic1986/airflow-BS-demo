# WGS Local / SGE 平台接入实施计划 R2

2026-09-16 最新检查点：R2已部署BS10610；定向6后端/5前端测试、构建、实际synthetic首跑与续跑监控通过，用户浏览器复测通过。main/BS96发布仍暂停，不扩大真实计算测试。详见 ../../releases/2026-09-16-onprem-bs10610.md。下文候选期限制和进度为历史检查点。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task。不要开启并行agent或扩大测试范围；最初仅授权文档，随后只授权先修正已有开发，不能由此自动开始完整R2实现。

**Goal:** sampleinfo → analysis可选接入 → 后台首次运行/改参续跑均可监控；同项目analysis_id稳定，每次执行新增execution_id与快照。

**Architecture:** WGS prepare只增加可选薄接入点，算法/pending/profile不动。平台登记、保存逐执行快照、监控/采集；后台任务不由Airflow再次启动，网页路径兼容。

**Tech Stack:** FastAPI、SQLAlchemy、Airflow、Python/Bash、WGS logger、React。

**Spec:** [R2设计](../specs/2026-09-15-wgs-local-sge-platform-integration.md)。任务WGS-LOCAL-SGE-20260915。

## Global Constraints

### 2026-09-16 latest R2-3 checkpoint

User next-step authorization completed this bounded candidate slice:direct-child
wait terminal receipt consumer, fixed/idempotent monitor DAG attachment, and
native_monitor_only protection against generic Airflow state overwrite.
BS10610 cached isolated tests:18backend+2DAG GREEN; includes one actual WGS679a3e
controller -> platform snapshot/claim -> receipt consumer check with synthetic
exit0 entry. Original Step1/runtime/sampleinfo/local+sge profiles unchanged;
WGS baseline34bfcbf, owner19checks log verified. No live enablement/deployment.
This supersedes older pending statements for terminal/attachment only; R2-4
execution-scoped sample/rule/log views and enabled-service acceptance remain.
The later R2-4 checkpoint below supersedes QC history with user-approved run-latest QC.

- 隔离分支jiucheng/feat/wgs-local-sge-20260915，main基线4b5234e，不操作main/生产；已有代码定向修正按下方单独进度记录，未授权完整R2发布。
- Local96/97、SGE控制器18、CCE入口200；平台托管仍ctapa，后台接入记录实际账号，不建设代登录/提权。
- 参数名建议为 `--platform-monitor`，未发布。sampleinfo不创建run；analysis准备成功后才可选登记。
- 同项目普通续跑保留analysis_id/平台attempt，新增execution_id/generation；新项目同路径也不能复用旧run。
- 允许启动/续跑前编辑config、样本名和家系，每次实际执行内容独立留档；不要求等于prepare哈希。
- 不改样本选择/basecount/pending/原生调度/重算策略，不自动forceall，不新增锁或资源限额。
- 不新增历史目录自动接管、样本改名映射、离线分析补录、面板取消/续跑按钮。
- CCE/GATK/扫描/自动分析和旧运行兼容。BS10610缓存synthetic定向验证，真实入口/多账号/生产另行授权。

## 旧工作如何承接

2026-09-15用户另行授权先修正已有开发：已修改启动时的config/sample冻结门禁，增加私有逐执行快照及有效Linux账号记录；13项BS10610定向检查和语法检查通过。原生prepare/Step1/profile及pending逻辑不变。这是R2-2启动库的部分基础，不包含新登记/目录身份/数据库投影；R2-1仍未完成，不自动扩大到后续任务。

4f90018冻结基础、e34bc45原生路由/绑定已提交，旧7+11+6项测试证据保留。
提交接线/共用启动库仍未提交，只有6项RED；GREEN曾被BS10610 SSH上传失败阻断。
旧Task 1–4不直接视为R2完成，不盲目先让旧哈希门禁测试转绿。
保留有用路由/证据代码，针对新入口修正固定配置与catalog按路径/批次复用的前提。
未授权删除任何既有源码/历史记录，也未启用新功能。

## R2-1 — 后台首次项目登记与WGS薄接入

最新验证：用户确认可登录后，同一BS10610别名SSH/scp恢复。平台8项登记+1项迁移+2项提交兼容共11passed（4.57s），语法检查通过；未部署、未执行在线迁移。WGS已接受精确合同，可开始薄钩子实施和synthetic验证，尚不具备真实API/monitored执行入口。

2026-09-15推进记录：WGS owner已确认薄钩子边界；[精确合同](../specs/2026-09-15-wgs-onprem-registration-contract.md)已写。平台schema/个人会话登记/UUID唯一字段迁移/普通启动防误用代码已写，8项RED复现缺少route；GREEN上传及SSH均在网关前握手中断，未运行。迁移测试未运行，未部署/启用。WGS仅审阅合同，等平台GREEN后才安排其实现。

**Owner:** 平台接口/数据；WGS-pipeline负责prepare接入。先确认协议，再分别开发。

**Files:** 新增backend/app/wgs_onprem_execution_service.py、backend/tests/test_wgs_onprem_execution.py；修改backend/app/main.py及必要models字段；同步docs/05_API_CONTRACT.md、docs/04_DATABASE_SCHEMA.md、docs/08_WORKFLOW_RUNTIME_INTEGRATION.md。WGS任务定位修改prepare_wgs_batch.py/runtime.py，平台不直接修改WGS仓库。

**Consumes:** 新项目登记UUID、path、mode/target、release证据、准备摘要、认证主体。
**Produces:** register_project语义：相同UUID幂等返回同analysis_id，新UUID即使同路径/批次也新建run；绑定和待启动状态。

- [ ] 与WGS任务确认参数名、请求/响应、补登记入口、认证机制/私有配置路径，并写入正式接口文档；不能宣称当前已有token接口。
- [ ] 写synthetic业务测试，在BS10610定向RED，至少含以下断言。

```python
# register_project表示本任务将实现的服务合同，测试不得走旧catalog路径去重。
assert register_project(uuid="P1", path="A").analysis_id == register_project(uuid="P1", path="A").analysis_id
assert register_project(uuid="P2", path="A").analysis_id != register_project(uuid="P1", path="A").analysis_id
# 未启用monitor时，平台请求为0；登记失败再补登记时prepare/pending写入次数不增加。
```

- [ ] 实现独立登记服务复用AnalysisRun，准备摘要不创建最终Sample。稳定UUID先保存，回复丢失按UUID查询。
- [ ] WGS仅在analysis成功发布后调用薄钩子；sampleinfo不登记；失败保留准备结果并允许单独补登记，不能重做pending交接。
- [ ] 项目生成独立监控入口，原Step1保持；绑定不含secret且不能代替服务端授权；原提交人与实际Linux账号分开。
- [ ] 同一测试集合GREEN，更新接口/DB/运行时和状态文档，再提交精确改动。

**Acceptance:** 无需网页预创建即可待启动；无开关无行为变化；重复登记不重复prepare；同路径新项目与旧run分开。

## R2-2 — 位置绑定和逐执行快照

2026-09-15小步推进：执行登记/移动绑定/private snapshot/独立DB输入范围已完成候选源码。
11项execution+8项原登记GREEN，0025/0026迁移各自SQLite GREEN。
[精确执行合同](../specs/2026-09-15-wgs-onprem-execution-contract.md)。WGS owner核对实际范围为config.sample数据编号，以sample_info关联元数据，new_sample_info不扩充范围；局部target不是全量QC重跑证明。
Sample/QC当前历史读取、真实argv透传/启动和monitor-only DAG仍未完成；API返回launch_allowed=false。
WGS R2-1薄钩子候选5485c8a已交付，尚未双方联合验证/部署。下方完整清单不能据部分GREEN全部勾选。

**Owner:** 平台；WGS监控入口调用同一登记合同。

**Files:** backend/app/wgs_onprem_execution_service.py、backend/app/wgs_stage_execution_service.py、backend/app/models.py及必要新增迁移；scripts/wgs_onprem_runtime.py、scripts/wgs_runtime_gate.py；backend/tests/test_wgs_onprem_execution.py、scripts/tests/test_wgs_onprem_runtime.py。同步API/DB/运行时文档。

**Consumes:** 项目绑定、实际config及其样本引用、启动argv、mode/target/account、幂等operation_id。
**Produces:** register_execution语义：analysis_id/attempt不变，execution_id/generation及snapshot引用；网络重试复用同execution。

- [x] 核对Sample唯一键/历史查询；复用WgsStageExecution，新增0026执行输入引用表避免覆盖Sample历史。
- [ ] 用同一synthetic项目覆盖V1首跑、V2改参/改样本家系续跑、移动和复制冲突，先RED。

```python
assert second.analysis_id == first.analysis_id
assert second.attempt == first.attempt
assert second.execution_id != first.execution_id
assert second.generation > first.generation
assert load_snapshot(first.execution_id).sample_ids == ["SYN_A"]
assert load_snapshot(second.execution_id).sample_ids == ["SYN_RENAMED"]
assert load_snapshot(first.execution_id).config == config_v1
assert retry_same_operation.execution_id == second.execution_id
# A移动B携带P1，A新建P2对应R2；两处同时携带P1则返回冲突。
```

- [ ] 新监控启动不要求config/sample哈希等于prepare旧值；替换为当次文件一致性、身份/权限/目标检查。保留旧CCE合同。
- [ ] 每次启动前在受控独立位置保存config、实际样本、参数、版本来源和执行身份；敏感项排除，不复制大数据；采集中变化则重新采集，未注册成功不启动。
- [x] RunDetail当前/历史配置样本按execution读取；QC按用户最新决定仅保留同run最后结果，不做逐执行QC分母或改名映射。不重复pending选择。
- [ ] 无活动执行时核对绑定后更新位置；旧位置不存在或已归P2可确认P1新位置；两处P1拒绝猜测。历史读取不得回退到未知同名目录。
- [ ] 同集合GREEN，核对快照/历史不被当前修改覆盖，更新文档并提交。

**Acceptance:** 正常改参/改名后续跑不被旧哈希阻断；稳定analysis_id、新execution；mv后原路径复用不串数据。不增加参数影响分析/重算算法。

## R2-3 — 共用启动和仅监控Airflow路径

新增检查点：用户要求WGS测试以部署34bfcbf为基线，WGS任务已隔离薄接入
为b07bbc4，保留新版。原runtime/sampleinfo/profile无差异，15项定向测试通过。
平台完成受generation隔离的原生start/result采集，以及独立暂停的
bio_wgs_native_monitor（不修改原CCE图）；当前展示清理上次执行的进度/错误。
本轮不因native result文件放行新执行，真实控制器退出证明、自动挂接DAG和
历史视图仍待后续；没有启用服务或真实分析。

2026-09-15检查点：一次性claim候选已完成，独立默认关闭门禁；仅当前模式
profile两文件纳入输入指纹。BS10610隔离缓存环境14 claim+11 execution通过。
WGS已核对原生pipeline为项目内副本；独立薄caller接线中，observer和仅监控DAG
尚未完成，不将该检查点标为整步交付，不开启真实分析。

**Owner:** 平台runtime/DAG；WGS原生profile继续负责执行规则。

**Files:** scripts/wgs_onprem_runtime.py、scripts/wgs_local_runtime_gate.py、新增scripts/wgs_sge_runtime_gate.py；backend/app/wgs_runtime_adapter.py、backend/app/main.py、backend/app/wgs_observer.py、dags/bio_wgs.py、config/wgs_stage_contract.yaml；对应runner/DAG测试。同步docs/07_AIRFLOW_DAG_SPEC.md和docs/08_WORKFLOW_RUNTIME_INTEGRATION.md。

**Consumes:** R2-2注册成功的execution和实际入口。
**Produces:** 原生启动一次、分execution的日志/终态、后台首次及续跑均适用的monitor-only DAG/observer绑定。

- [ ] 参数化Local96/97、SGE18定向RED：重复启动、活动执行、旧事件、监控失败；只使用synthetic脚本。

```python
assert original_step1_bytes == step1_bytes_after_launch
assert original_profile_bytes == profile_bytes_after_launch
assert duplicate_request_control_processes == 0
assert monitor_dag_prepare_calls == 0
assert monitor_dag_launch_calls == 0
assert old_generation_event_does_not_change_current_execution
# 不额外注入forceall、cores/jobs或外层qsub。
```

- [ ] 共用入口透传原生参数、注入logger和execution对应WGS_ATTEMPT_ID；按execution收集日志，后台返回0不当完成。
- [ ] 参数化Local节点路由；SGE在18启动原生控制器/替换占位监控，不改变profile资源和qsub逻辑。
- [ ] 后台首次及续跑只建立监控/采集DAG，不prepare/启动第二遍；网页仍平台启动但共用快照/证据。
- [ ] 相同operation幂等；活动或无法确认结束时拒绝新执行；SGE仅核对关联子任务，不自动qdel。失联不重启/停止原分析。
- [ ] 以本次exitcode/metadata及必要结果采集终态，分析成功/采集失败区分；GREEN后同步文档并提交。

**Acceptance:** 后台首跑/续跑自动展示同项目，无双重调度；原生逻辑/资源不变、旧回调不覆盖新状态。

## R2-4 — 当前/历史页面及最小联合检查

2026-09-16用户明确解除此前QC阻碍：续跑保留同run，只展示最后生成的QC。
候选现已实现：逐执行配置/样本快照和准确主日志；Rule仅据可定位文本；
QC读取config.batch对应07_QC/{batch}.QCstat.tsv并缓存最后可靠值，明确run_latest。
不要求QC执行归属，不新增WGS logger、跨文件QC归档或修改prepare/Step1/profile。
日志来源为log/step1.<native_id>.log，非prepare projection.jsonl；配置范围不等于
实际调度或QC完成。3后端+3前端定向检查及一次生产构建通过，功能尚未部署。

**Owner:** 平台前端/验收。

**Files:** 现有RunDetail/样本/rule/日志/QC组件、frontend/src/api.ts、backend/app/run_service.py及相关样本投影服务/测试；同步docs/06_FRONTEND_SPEC.md、docs/11_DEPLOYMENT_RUNBOOK.md、docs/02_ENGINEERING_SPEC.md和状态文件。

**Consumes:** analysis_id下当前execution与历史快照/证据。
**Produces:** 同项目同analysis_id，当前/历史配置范围独立；QC为同run最新结果。

- [x] 复用R2-2 fixture定向RED/GREEN：默认V2、历史V1，改名不串入旧范围，两次执行共用同run最新QC，半写入保留可靠缓存。
- [x] RunDetail展示执行/监控状态、原提交人/当前操作者和冻结参数；隐藏云操作，复用StatusBadge/LogViewer及分页样式。
- [x] 历史按execution读取；原路径身份变化禁止读取其他项目未知日志和QC。
- [x] BS10610新增3后端测试+3前端测试和一次构建通过；未重跑旧完整集合或WGS。
- [x] 已记录代码/测试/未启用状态。真实Local/SGE、多账号权限、BS96验收另获授权。
- [ ] 完成启用候选环境的接口/页面验收；核对现有列表接线，不自动填充全局Sample行或扩展测试范围。

**Acceptance:** 首次后台登记、编辑后续跑、移动/同名新建与历史切换可用；未接入原生路径、CCE/GATK无无关变化。

## 文档交付与后续

- [x] R2设计与计划更新：首次登记、可选参数位置、逐执行快照、稳定analysis_id与目录复用。
- [x] 区分旧源码证据与新需求，同步CURRENT_STATE/TASKS/HANDOFF及接口/运行时规划提示。
- [ ] R2-1至R2-4完整实现/定向验收（尚未完成）。
- [x] 后续单独授权的已有代码修正：native launch可变输入、逐execution快照、不覆盖历史、有效Linux执行账号；13项定向检查通过，未启用。

最初文档修订仅检查Markdown链接、任务编号、术语和git diff；后续已有代码修正的BS10610测试证据见上方记录和HANDOFF。
下一次获准继续实现，从R2-1双方合同开始，不直接启用WGS_NATIVE_PREPARE_ENABLED。
回滚停用新接入，保留活动分析所需采集、绑定/快照/历史、pending和结果，不删除分析数据。
