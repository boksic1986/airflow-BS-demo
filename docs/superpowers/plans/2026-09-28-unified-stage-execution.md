# Step1–6 公共执行器与 P0 收敛实施计划

2026-09-30 最新进度：UE01–05已验收；UE06的native0.8.9/7172573和AF03bab6c
隔离安装、真实trust/policy、普通/P0入口及共享SSH加载已获协调者原始证据审核接受，
最终AF状态3c094fc及28项证据索引已核对，UE06隔离安装验收与交接关闭。
见[UE06审核](../../reviews/2026-09-30-ue06-isolated-install-review.md)。
旧shared配对配置ENOENT是实际切换前条件，未批准修复旧环境或生产部署。

2026-09-30 WGS4.2.3 文档衔接：[W423 计划](2026-09-30-wgs423-upgrade-integration.md)
登记后续 group/QC/人工回传及异步 prepare。prepare 是 UE 配套完成后的受信 handler 增量，
不是本计划 UE-05 的附加范围；已验收 UE-01–04 不重开，当前 UE-05/06 收尾和门禁不变。
本链接是文档交接，不代表 W423 代码或 UE 剩余验收完成。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task.
> 用户已指定两个 owner 开发；由协调者分阶段派发和审核，不授权任意生产发布。

**Goal:** 以 GATK 现有异步机制为基准，主要迁移 WGS，修正当前 P0 缺口，不重开已验收项目。

**Architecture:** 将 GATK 已验证 dispatcher 的公共部分抽入 cce-pipeline，两个 gate 做薄调用，
WGS Step2/6 向它收敛。平台另共用派发/观察判定，允许修改两侧 Step2 callable；
GATK 暂保留 submit/wait 图是机制评估结果，不是禁止更改。两流程业务 handler 不重写。

**Tech Stack:** Python、现有受限 SSH runner、Airflow sensors、cce-pipeline；不新增常驻服务。

**Spec:** [统一阶段执行设计](../specs/2026-09-28-unified-stage-execution-design.md)。

2026-09-30最新授权优先于下文历史检查点：用户批准 SSH 四点方案，纳入 UE-05 公共连接
收敛；同时明确批准 R2/R4 最小受鉴权内部 native snapshot 通道。原接口阻碍已解除。
UE-01–04与已接受 F7/final-release 不重做；原两个 owner 继续 UE-05，源码审核后再进入
UE-06 测试端配对交付。本次不授权 BS96/node200 生产部署、真实批次或新的恢复操作。

状态（2026-09-29 18:27Z）：UE-01–04 源码配对及差量验收已完成，原两个 owner 已获准实施 UE-05。
UE-01：平台 `eac84ea` / native `254527c`，公共契约及摘要/handler 映射已接收。
UE-02：平台 `3d5174c` / native `6c0aee2`，公共内核与 gate 接线已接收，详见本步证据。
UE-03：query/Heavy 为平台 `e7610af` / native `6f5c120`；恢复 probe 期限接线为平台
`e840137`；native 目录重试为 `8dfcdee`，原始35/10/18项定向证据及静态接口配对已审阅。
UE-04：平台 `a6c31d1/7976f25`（前置 gate/共同 DAG 客户端见本步）与 native `4fa85874`，
原始差量及 Step5→共享终态验证源码链已审核闭合；不代表安装、真实全链或生产发布。
已通过项只引用、不重复测试；后续按 UE-05→06 的依赖和阶段审核推进，不授权生产操作。
前置兼容门禁的原则仍是当前能正常运行即无需补丁；新证实的 WES TTL 缺陷按下节单独处理。
已纳入 [覆盖审查 R1–R4](../../reviews/2026-09-28-wgs-p0-unified-execution-coverage.md)，
沿用 UE-01–06 正式实施顺序；本次新增用户指定的前置生产兼容门禁，不扩展 UE 功能。
文档闭环或任务派发不等于源码修复、部署或验收。
本版已按最新用户要求撤销 legacy reader、废弃 Resume 兼容、双流程大改和重复整体验收。
六个编号只是实施顺序，不是六轮验收；未来控制 handler 和第三 adapter 演示不在本轮开发。
最新澄清：正确的公共生命周期优先于少改文件；撤销“GATK 默认不改”的硬约束，
Step2 等待形式取舍及理由见 spec3.2。需要消除的共享契约差异不能以控制改动量为由保留。

## 2026-09-29 审查回写与继续开发授权

用户同意按原计划继续并交给原 owner。保留 UE-01–06，不增加开发阶段、功能或整体验收。
依据 [补丁/结构/性能审查](../../reviews/2026-09-29-airflow-patch-architecture-audit.md)，
将已知问题映射到真实调用点；以下是交付要求，不代表修复已完成或获准生产发布。

| 位置 | 纳入本任务的最小要求 |
| --- | --- |
| UE-01 收尾 / UE-02 前 | 两 owner 核对当前源码、单 fixture 原始证据和提交。已绿只引用；确实仍阻塞才由 native 修正、平台复验同一个节点。盘点本阶段依赖的生产/候选/测试差量，记录保留或替代关系，不整体复制 dirty 树。 |
| UE-02 | 从现有 GATK dispatcher 抽公共内核；gate/resolver 只加载受信选中 adapter，不依赖另一 gate 的导入。创建交接如触及私有 monkeypatch，先由 native 明确最窄接口及平台接线边界，保留身份/锁保护；不趁机重写插件系统或扩大 UE-01 字段。 |
| UE-03 | 原失败/活跃/成功全部 inventory 消费点继续落实；显式识别分析 Master 与 helper 的角色，修正 Heavy 采集将 helper 当配额 Master 的共同分类缺陷。不以名称猜测或忽略所有缺环境变量对象，不新增配额系统；普通资源卡和 SFS 图优化不在此步。 |
| UE-04 | 除 R1/R4、GATK 合法恢复 DagRun/action（F3）及 WGS 真实 Step6 门禁（F4）外，收敛 TTL 后 Step3→Step4/5 的持久终态消费，native 与两个 gate 配对交付。保留防旧回执回退、Master/rule/phase 投影；写入 helper 不隐式提交调用方事务。不新增废弃 JSONL/Resume 兼容或全仓事务重构。 |
| UE-05 | R2 已覆盖手动 queued 动作，不另建同义任务；受支持恢复请求的冻结摘要应使用既有版本正确的共同校验（F7），不重算历史登记，不降低现有 fence。 |
| UE-06 | 明确实际消费模块、挂载、selector/pin、提交和 wheel 的对应关系，防止丢失既有修复。仅配对安装差量核验，不重复 UE-01–05 或真实流程验收。 |

独立待办：初次提交的外部派发/数据库事务幂等（B1）、内部鉴权缺配置拒绝（B3）、
其他事务/一致性快照和 UI 缺陷、Batch Runs/Tracker 性能、SFS 时间桶/缓存/展示。
本次不顺带实施这些独立任务；B2 仅在 UE 直接改动的事务边界解决相关责任，其他路径另排。
原前驱摄取、动作生命周期、bulk inventory、unknown/fence 已在计划内，不重复拆任务。
若实施发现必须扩大接口、文件职责或配额/权限/时限，先向协调者报告并暂停相关扩大动作。

协调者维护本共享 spec/plan；平台 owner 更新自己 worktree 的源码、docs/08 和交接，
native owner 更新独立组件源码/交接，避免同时编辑同一契约文件。

## 2026-09-29 WES TTL 缺陷：当前修复与公共收敛

依据 [WES Step4/5 独立审查](../../reviews/2026-09-29-wes-step4-ttl-review.md)，
普通 Step4 发布检查和 Step5 日志导出仍要求在线成功 Master；Job 终态后 TTL100 回收即可
触发失败。这是真实下游消费缺陷，不是仅 UI 滞后，也不是需要重新计算的规则失败。
已异步并不代表这些 handler 已正确消费持久终态；修复归 UE-04，而非重开 UE-02。

两条线分开推进，不新增 UE 编号：

- **当前生产修复**：用户已授权原修复线程 `01a09e7e-a0c5-7c30-a06f-e002662b0289`
  对 `GATK_20260929_024231_F246CD` attempt1 做限范围补丁和下游续跑。
  owner 已报告取得 SFS 同原 Master UID 的 RUN_COMPLETE、三阶段 exit0；协调者尚未验收
  补丁或恢复结果。保留43样本、原目录/输入/attempt，先核对真实证据，再处理 Step4/5
  共用缺陷，按原链进入 Step6；不重算、重传、换 Master、改 TTL/锁或重写历史摘要。
  该操作不授权将 UE0.8.9 候选部署到生产，也不扩展到其他活跃批次。
- **永久修复**：原 native owner 在0.8.9源码收敛验证/消费路径，原平台 owner 在 UE-04
  接入真实 gate/正常与受支持 P0 调用点；UE-05 复用它做下游恢复，UE-06 检查实际安装
  入口。当前补丁的 commit、应用位置、验证及回滚由修复 owner 提供，作为迁移清单输入，
  不照搬批次分支。UE-03 inventory/probe 照常完成，不夹带该项实现或追加同义测试。

前置 GATK-PROD-COMPAT 的“无需补丁”仅是当时 WGS paired 补丁适用性结论，不是
所有 GATK 下游 handler 的无缺陷承诺。本项补充不推翻已验收内核，也不能被旧结论排除。

## 开发协调与前置生产兼容门禁

| 责任 | 指定线程 | 本轮交付 |
| --- | --- | --- |
| 协调/审核 | `019fa8d1-0d81-7e92-abee-8154dd1cf0a7` | 方向、共享设计、阶段放行、审查及阻碍汇报，不直接大改 runtime |
| Airflow/platform | `01a0e728-4c99-71d0-87e9-987b311022c9` | GATK-PROD-COMPAT；UE 平台/gate/DAG/当前 P0 消费端 |
| cce-pipeline | `019f9d79-be3f-7701-af33-3595d72bbfac` | UE native 公共执行器、query/probe 和 release **0.8.9** |

Airflow 必须以核实后的当前 `jiucheng/release/production` 为基线新建独立 worktree，
在该 worktree 的开发分支分阶段提交。当前本地 ref 观察为744cd22，不替代 fetch 和部署
指纹核对。测试集成 worktree 的未提交修复不能整体复制；实际生产热修复若未入基线，
只纳入本任务需要的文件/差量并注明来源。协调文档与源码 owner 不同时编辑同一份文件。
native owner 已核实 canonical component `projects/huawei-cloud-runtime` 的
main/远端 main 均为417de597fe3e83cc42160cf14102ad78db789bf8。门禁关闭后已允许
从该基线建立 `jiucheng/cce-stage-execution-089`，实际建分支/源码结果由 owner 回报。
本次0.8.9要求替代候选沿用0.8.8的旧约定，不增加后缀、不覆盖生产0.8.8。

**GATK-PROD-COMPAT（UE 前置，非公共执行器提前上线）：**

验收标准是现有生产批次稳定运行，不是提前满足新公共协议。复用既有验收和相关源码/
必要只读运行证据，不为证明正常提交真实批次或重做整链测试。已知缺陷只有明确影响
当前运行路径时才最小修复；统一方案的契约差异/性能优化不能直接当作生产故障。
最新范围澄清：仅逐项核对0.8.8接入后 WGS 已实施的 P0 补丁对 GATK 是否适用，
不全面审计 GATK、不遍历历史故障，也不把 UE 的待开发缺口全部转为生产修复任务。
WGS 专属修改不移植；共享路径只有 GATK 实际可达且存在同类缺陷才修。
交付一个补丁适用性小表（证据/是否可达/结论）；不适用即止，必要事实缺失明确报 unknown。

- [x] Airflow owner 核对生产分支/相关部署差量、worktree，以及上述补丁涉及的 GATK 契约。
- [x] 证实 P0 接入/近期 WGS 修复对 GATK 的具体影响，再限定补丁；没有缺陷则提交
  核对依据，不为满足“有补丁”强行改代码。重点审阅 dispatcher/真实终态、最终 inventory
  及当前异步交接；不得把 WGS 同步特例直接套给 GATK。
- [x] 本次无适用补丁：保持生产协议/handler/权限/身份锁；没有代码变更，不运行
  synthetic 或提交分析、不引入新 executor/native 升级。仅归档审计文档。
- [x] 协调者检查缺陷与 diff、已有证据复用、定向结果、部署文件/服务和回滚清单。
  部署前停在审核点；生产兼容发布若需改 native、扩大服务范围或权限，先向用户报告。
- [x] 无实际缺陷时，以有依据的“无需补丁”及审计边界关闭门禁；有 bug 时记录最小修复
  的保障结果或明确阻碍。两者均可由协调者审核后放行 UE-01，不强制产生补丁/部署。

实际结论：生产 forced-command 指向私有 GATK gate（SHA b3230de8...），gate 无 paired
引用且 paired 模块/activation 均未部署；WGS 专属补丁不移植，共享 paired 路径当前不可达。
审计同时包含提交间和工作区未提交热修复；共享原 CREATE deadline 不误称为 WGS 条件分支。
这不是新版 GATK P0 或新整链路验收。UE-01 已派发，Airflow 从同一生产基线 worktree 的
审计提交建立 `jiucheng/airflow/UE01-stage-execution-contract`；不引入整个 dirty 集成树。

前置门禁、UE-01 契约与 UE-02 公共执行器配对审核已结束，原 native/platform owner
获准继续 UE-03；UE-04–06 仍按依赖和阶段审核放行，不提前安装或发布。
随后 UE-01 双方定契约，UE-02/03 由 native 产出配对接口、平台消费，UE-04/05 完成平台
收敛，UE-06 测试端配对交付。每阶段提交 SHA、文件范围、唯一差量证据及未验证项后由
协调者审核再前进；不能跨阶段自行改协议或把已完成测试反复执行。接口/权限/环境漂移、
超出范围、缺前置证据时立即报告并保留现场，不盲目重试。此门禁不授权真实批次/清理/DB修改。

## 全局约束

- 首次登记冻结 `cce.stage-execution.v1`；保持既有 v2 请求摘要及历史记录。
- 统一 accepted/后台执行/observe，不把 accepted、SSH 退出或 observer 停止当业务成功。
- 保留 attempt、输入/输出、原 deadline、自动恢复预算、锁、TTL100、权限与配额。
- 当前选择 GATK `submit_step2_master → wait_step2_master`，两者 callable 接入公共判定，不在 submit 内重复等待；
  仅 WGS 需要薄 submit-and-await 外壳保留原 pool 占用。不要求两者 DAG task 形状相同。
- `dags/bio_gatk.py` 的 `run_stage/stage_ready` 可修改以接入共同派发/观察及未知状态规则，
  不是只允许改 import。业务 handler/结果算法不重写；时限/预算不增加，改变业务/配额或
  大改多个层须先说明必要性。不得为少改 GATK 再给 WGS 单独维护一个控制/失败状态机。
- 本轮不实现/测试未来 pause/delete handler、控制 API/UI、CLI 前台改造或第三流程演示。
  现有有效 P0 控制 fence 不撤销。
- UE-01–06 限 BS10610 最小 synthetic 验证及测试端安装；无云 Job、无真实批次、无生产部署。
  前置 GATK 生产兼容补丁单独审核，不据此将 UE 候选推广生产。
- 无新依赖、无 WGS/插件/镜像改动；native owner 按 SOP 产出0.8.9配对候选。
- 开始实施前保存当前 dirty diff 清单；不得把既有生产修复覆盖、整体 reset 或混入无关提交。
- 保留当前 Step2 原始 CREATE deadline、只读重连、Run Tracker/Phase 的行为和已有验收。
  不新增旧同步 reader，不移植废弃 Resume；当前 P0 `resume_stage` / 同 attempt 续跑仍保留。
- 不迁移或重写历史记录。历史只读展示保持现状；不支持的执行请求明确拒绝而非兼容回退。
  若切换时仍有依赖退出路径的活跃运行，停止切换并报告，不能为此临时开发兼容层。
- historical policy/timeout 缺失或禁用不授予计算恢复权；不增加新错误类别或扩大 pre-START 恢复。
- WGS 输出保持2775/0664/0775，GATK 和私有凭据沿用自己的批准权限；不通过 root/chmod 绕过。

## 审查重点

1. Step2 真成功但前驱滞后才接收；已验证当前记录直接复用，两者锁内均再核对身份（R1，UE-04）。
2. 当前 P0 阶段续跑仍 queued 但计算已终态：准确结束计算互斥，保留下游授权与预算；停止请求优先（R2，UE-05）。
3. 回复丢失/进程死亡/观察超时：六阶段 unknown 均不得触发重复派发、错误失败投影或提前释放（R4，UE-02/04/05）。
4. Step2 worker 退出不等于云 Master 静止；保留当前有效 P0 和进度行为，不做废弃 Resume 兼容（UE-01/04/05）。
5. 无关批次不能阻断；TTL 回收后使用充分持久证据，CAS 仍需新证明，缺必要证据不放行（R3，UE-03）。
6. 普通 Step4/Step5 与当前 P0 下游共用真实终态绑定；分析成功后不依赖原 Master 存活，
   也不凭404/进度100%推进（TTL-DOWNSTREAM，UE-04；恢复/安装由 UE-05/06 消费）。

## 文件边界与最小验证入口

以下是实施文件边界，不是本次已修改清单。平台路径相对 airflow-demo；native 路径
相对其 Python 包 `cce_pipeline/`，物理源码仓库由原 owner 按 SOP 核对，不从安装目录改源码。
不为统一命名重构整个仓库，也不复制一份已有门禁或重试引擎。

| 任务 | 实施文件与职责 | 最小测试位置 |
| --- | --- | --- |
| UE-01 | native `stage_execution.py` 公共类型；平台 `scripts/cce_paired_runtime.py`、WGS gate/注册生产者；GATK 只做必要的类型/调用映射 | `scripts/tests/test_cce_stage_execution_contract.py` 仅新增协议缺口，不测废弃 reader |
| UE-02 | 从 `scripts/gatk_runtime_gate.py` 的 `start/_execute` 等抽取公共进程管理到 native `stage_execution.py`；保留 `_execute_stage` 业务处理，gate 薄委托；`assets/cce_batch_runtime.py` 仅必要 handler 接入 | native `tests/test_stage_execution.py` 只补抽取改变的边界，原异步验收引用 |
| UE-03 | native `assets/cce_batch_runtime.py` 的 `_recovery_query`、`assets/cce_writer_guard.py` 的目录 probe；平台 `scripts/cce_recovery_workloads.py`（含 bound probe）、`cce_recovery_inventory.py`、`cce_recovery_failure.py`、`cce_paired_runtime.py` 的全部相关查询入口 | 扩充 `scripts/tests/test_cce_final_bulk_inventory.py`，复用 `test_p02_failure_evidence.py` 的失败/活跃等待 fixture 和 `test_p02_resume_final.py` 的 native CAS fixture；native 新增 `tests/test_directory_probe_retry.py` |
| UE-04 | WGS/GATK gate、paired runtime；`dags/common/stage_execution.py`、两 DAG；backend 当前登记/观察/必要 GATK 接收点。native `assets/cce_batch_runtime.py` 仅终态收集、`_recovery_native_success` / `_bound_downstream_master` 的共享消费及 Step4/Step5 日志入口，不重写发布/下载算法 | 原 `scripts/tests/test_unified_stage_adapters.py`、DAG/R1 节点；TTL 复用 native `tests/test_master_handoff.py` 夹具及已有身份负例，只补普通下游接线缺口；不重开全链路 |
| UE-05 | `scripts/cce_recovery_inventory.py`、`cce_publish_recovery.py`、`cce_paired_runtime.py`；backend `cce_publish_recovery.py`、`cce_compute_dispatch.py`、`cce_resume_dispatch.py`、`cce_recovery_budget.py`、`cce_recovery_poll.py`、`cce_monitor_observation.py`；`main.py` 仅相关回调/清理调用点，不要求每个文件都改 | 仅 recovery_poll / recovery_cleanup_fence 的 R2/R4 差量节点；原手动/自动恢复、预算和 fence 已验收证据引用 |
| UE-06 | 测试部署配置/配对清单和交接文档；不新增生产发布脚本 | 候选/pin/入口接线检查，汇总证据，不再验收六阶段链路 |

### 单次差量验证规则

已验收项目不重开。实施前在既有交接记录列出“直接变更点、已验收证据、缺口、唯一测试节点”；
没有直接变更或新缺口的项只引用证据，不因分支合并、提交 SHA 变化或安装新 wheel 就复验。
以下各任务的断言是证明责任，不是要求逐项重跑已通过用例。新增/改变的行为优先在既有
fixture 内补断言，针对缺失行为 RED/GREEN 一次；不把环境/导入失败算 RED。

定向执行仅在 BS10610 的批准 synthetic 环境，使用该环境解释器；本地不运行 pytest。
共享逻辑测一次，adapter 只测本次改变的接线；不做流程 × 阶段 × 恢复模式 × 故障矩阵。
已有手动/自动恢复全链路、旧同步凭据、历史 phase/权限/TTL 不作为本轮重复运行的任务。
275 Worker 夹具只构造内存对象，重试用假时钟，不创建云 Job 或真实等待120s。
UE-06 只做安装边界检查，引用 UE-01–05 已有结果，不再整链路验收。
产物按任务分次提交指定文件，不使用 `git add .`。接口字段统一来自 spec 3.1，禁止各任务另定义同义状态。

## UE-01：公共接口与当前支持边界

Owner：平台/Workflow 契约负责人；native owner 审阅其消费部分。

修改：配对入口、WGS 请求转换和当前注册生产者；GATK 仅公共类型映射，以及 docs/08。
不在本步把任何真实批次改成新协议。

接口：`submit(execution_ref)`、`observe(execution_ref)`；执行引用解析到受信登记。
统一字段和状态以 spec 3.1 为准；`control` 仅保留设计说明，本轮不实现。
协议选择由首次登记持久化；不支持/废弃的执行入口明确拒绝，不新增 legacy reader。
公共 snapshot 优先映射当前 GATK 回执，不为统一名称重写其业务字段或既有文件格式。

跨仓实现前双方须一次定清可信 resolver/handler 的部署位置、完整序列化字段、原 deadline
权威及既有 success/failed/canceled 的精确映射。native API 由 node200 已配对的 gate/runtime
在批准的 operator Python 内调用；不能假设 Airflow 容器可 import 远端 wheel，不增加任意
SSH/路径/命令入口。当前没有新增取消能力，历史 canceled 不能伪装成功或授予重发。

已定稿：snapshot 增加只读 canceled 以无损映射已有终态，不增加取消 handler/DB 枚举；
使用同一 serialization fixture 一项断言。新 request 顶层扩展固定为
`stage_execution: {"protocol":"cce.stage-execution.v1"}`，在新请求首次 hash 前冻结。
不回填历史请求，不扩 native platform_execution 七键，不把 registration_sha256 塞回自身摘要。
完整 ref/摘要/runtime identity 定义见 spec3.1 的 UE-01 对齐决定。
公共 pipeline 类型是受信 registry key，不硬编码两流程 enum；部署启用清单仍保持现状。
canonical JSON 固定 ensure_ascii=False/allow_nan=False、UTF-8、无尾换行，envelope 八个
身份字段加 runtime_binding，不复制 deadline 对象。非 ASCII 编码/canceled/未知 registry key
仅补入同一个新的 serialization fixture，不新增测试矩阵或第三 adapter 实现。
不新建全阶段 absolute deadline：原 Step2 intent、Step3 recovery、Step4 publish 及其余
Airflow/handler 时限各保留来源和计时起点。原来没有 absolute 值就不补算；CREATE 才产生的
期限不是首次登记字段，不反写 immutable envelope。共同客户端的 optional deadline 只
约束原观察等待，None 仍受既有 Airflow task/sensor 限制，不解除恢复 fence。

- [x] 仅补公共映射缺口 `test_current_execution_contract`：当前注册身份映射无损、同身份异摘要和不支持协议拒绝；不加入旧 Resume 重放。
- [x] 引用已验收的 request/control root、原 CREATE deadline 和当前请求摘要结论；只有本次直接改变序列化的字段才纳入上述同一 fixture。
- [x] 实现公共执行记录及 gate 转换，handler 从受信注册表选择，不接受任意可执行路径。
- [x] 同一受信操作内传递已验证引用，避免层层解析/重复摘要或目录查询；保留入口及跨信任边界验证、锁内可变身份复核，不为此新建校验框架。
- [x] BS10610 运行这组定向 RED/GREEN；通过后只提交本步源码、测试和接口文档。

审核依据：平台当前三份输入 SHA 与 owner 最终远端证据一致，diff whitespace 检查通过；
native UE-01 模块与提交、原始日志/JUnit 已核对。平台最终日志 `pytest-final.log`
SHA e8c2ebdecc6c68bd31c948de0b0c1dd4c57dd47d093194a6c1d241c65727824d，
结果 1 passed；精确路径/配对哈希见本次 HANDOFF。登记生产者仅静态审阅，后端运行接线
未在本步验收，归后续实际改动阶段；没有安装、真实批次或生产推广。

定向节点：`python -m pytest scripts/tests/test_cce_stage_execution_contract.py::test_current_execution_contract -q`。
产物：当前 adapter 共用的内部执行契约，无可执行的废弃协议兼容层。

## UE-02：native 公共后台执行器

Owner：原 cce-pipeline native owner，代码位置为该包的公共阶段执行模块；不编辑已安装 site-packages。

2026-09-29 最新验收：native `9272f2c` / `6c0aee2` 与平台实际接线
`3d5174ca7b53a6b304b39f5a74c76eff6af617c2` 配对完成，**UE-02 源码范围已完成**。
两个 gate、Step4 与 `_inactive_dispatcher` 已真实接入；可信冻结登记、逐代最小终态及
旧 writer 静止由共享内核/适配层协作。BS10610 新接线四文件30 passed、0 skipped；
协调者核对原始日志/JUnit和9个输入SHA一致，没有重跑。native单生命周期1 passed、
selected-adapter `7b199f0` 的4/4 GREEN直接复用。
独立审查的4项 Important（successor误拒绝、null协议降级、WGS缺请求证据漏检、
普通Step4被强制要求恢复opt-in）均已修正并差量复核Ready；无剩余阻断。
不从数据库投影补造旧终态、不放宽旧 writer 静止条件、不重写现有业务回执或另建状态机；
接口实现先明确再接线。既有通过项只引用，只有该直接变化的缺口补必要断言。
本记录不扩展阶段、wire 字段、权限、时限或生产授权，原 owner 继续既定 UE-03。

已确定的内部接线约束：`StageExecutionBinding.status_path` 可由受信 resolver 指向
request 目录外的逐代私有终态；dispatch 与 request 同目录，但不得复用旧
`.worker.state.json`。现有两把阶段锁继续共用。`writer_quiescent(ref)` 是三态只读快照，
不是业务成功或锁租约；`locks_held=True` 仅允许调用方真实持有两把精确锁并维持到决策结束。
None 必须继续核实旧 writer，False 不允许接管。只为新协议首次 submit 保存必要的不可变
登记及最小控制终态，observe/resolver 的读取路径不创建目录或补历史；不复制全部业务结果。
真实 handler 保留原业务回执，私有控制文件0600不改变 WGS 共享输出的批准权限。
WGS 旧归档不得挪走新 worker 日志；缺历史/缺终态维持 unknown，不借此开放旧批次迁移。

2026-09-29 已放行。native owner 先明确从现有 GATK 抽取的内部 resolver/worker 接口，
平台 owner 沿用现有 worktree 做 gate 薄接线，不另造 dispatcher；共同 wire 契约不扩字段。
平台先回报可复用函数/差量来源，待 native 内部接口固定再接入，不能猜测 API。
本阶段唯一共享内核 fixture 由 native owner 在 BS10610 执行，平台引用该证据，
仅自身直接改变且尚无覆盖的 gate 接线补必要断言；双方不重复执行 UE-01 或同一节点。
UE-02 配对协调审核已通过；DAG/后端消费迁移仍归 UE-04。

消费 UE-01 的执行引用；以现有 GATK `start/_execute` 中的通用机制为基础抽取，
不另造 worker 状态机。产出统一进程状态、不可混代回执、submit/observe 实现。
共用 launch/worker 锁、写前派发意图和受控进程组；handler 调用发生在已绑定后台 worker 中。
观察保持只读。重入不另起 worker；不能确认旧 worker/子进程静止则返回 unknown。
现有 CLI/受信 handler 调用不绕开登记/目录锁，本轮不新增前台模式或旧 CLI 兼容层。
`StageExecutor.submit(ref)` / `StageExecutor.observe(ref)` 使用 UE-01 的签名及
`ExecutionSnapshot`；CLI 与平台只做调用转换，执行器不依赖业务数据库。

- [x] 标出 GATK dispatcher 可直接复用的函数和已验收证据；仅抽取公共进程管理，保留业务 handler。
- [x] 对抽取产生的未覆盖接线补 `test_extracted_dispatch_preserves_lifecycle`：一次启动、重复 submit 接回、终态来源正确；原幂等/身份/锁故障套件不重跑。
- [x] 若受控子进程静止判断或 unknown 处理存在本次新增缺口，在同一 fixture 补断言；不重做已验收状态机。
- [x] gate 直接薄委托，不先起旧 worker 再起新 worker；不增加控制 handler 或第三 adapter 演示。
- [x] 仅 BS10610 差量 RED/GREEN，记录原证据复用及新增节点；提交源码和测试。

定向节点：`python -m pytest tests/test_stage_execution.py::test_extracted_dispatch_preserves_lifecycle -q`（native）。
产物：复用 GATK 的一个执行内核，两 gate 薄调用，不重构其业务；两侧 DAG 消费修正在 UE-04。

## UE-03：公共 inventory 与目录探测

Owner：native owner 负责查询/probe；平台 Workflow owner 负责 inventory 校验调用，不改彼此文件。

2026-09-29 16:06Z 最终状态：UE-03 源码验收完成，以下15:16Z未交付描述为历史过程。
配对为平台 `e7610af/e840137` 与 native `6f5c120/8dfcdee`。原35项 query/Heavy、10项
期限接线、最终18项 native probe 定向 GREEN 均已读取原始输出；没有协调者复验。
最终静态核对 writer 可选关键字及实际转发一致。权限错误按首个服务端 status 分类，
不扫描正文命中暂态词；操作超时仍按本设计有界重试，不擅自排除原 Step6 超时场景。
120s预算包含原最多60s Ready等待；不重置 helper600s生命周期、100s终态TTL或原恢复期限。
没有安装/云Job/真实批次/生产发布。具体命令、提交与限制见 CURRENT_STATE/HANDOFF。

2026-09-29 15:16Z 协调澄清：UE-01/02 不重开。query/Heavy 配对为平台 `e7610af` /
native `6f5c120`，owner 已提供 BS10610 35 passed/0 skipped；复用原证据，目录重试仍待交付。
普通 Step1/6 没有冻结 absolute 不是新造 deadline 的理由，也不阻止局部有界只读重试。
按设计3.1/5保留现有 task/sensor/handler 期限及静止判断；120s只限制一次 probe。
15:21Z 实码复核修正：Step4 `publish_deadline` 仅在原 `worker_command` 持锁 fresh launch
时校验，不能当后台业务完成期限传给 writer；原已启动执行与到期只读接回不变。
仅对 probe 实际适用的既有期限才裁剪；不存在调用点就不新增可选 API/平台接线。
不新增 wire/env 旁路，不反推外部超时，原 helper 生命周期不重置，不重试 CREATE/DELETE。
剩余验收仅新增 probe 及其实际改变的内部调用差量；平台若无产品代码变化则记录语义
审核并复用证据，不新建同义测试，不能重跑 query/Heavy 或普通六阶段验收。
最终找到的真实消费者是 `resume_registered` 的 writer.serialize/validate：沿用已认证
`cce_recovery_deadline`，与原 `monitor_wait` 和 `RecoveryCapability.compute_deadline`
同值，仅新增这处内部 `probe_deadline_epoch` 接线及定向断言，不改普通业务阶段。

修改：native `_recovery_query`/目录 probe；平台 `cce_recovery_workloads.py` 及现有调用点。
native 完整清单查询支持固定 `(jobs, --chunk-size=0)` / `(pods, --chunk-size=0)` 形式，
返回现有结构，继承 typed errors/4MiB 限制；平台删除自己的旁路 `_run/_kubectl` 清单实现。
公共 native 接口可复用原内部查询实现，不为“public”重写 kubectl 或全量改名。
消费接口仍为现有 `probe_final_workloads` / `probe_bound_workloads`，观察事实与能否恢复分开。
改动包括 `collect_failure_evidence`、`RecoveryCapability.inspect`、活跃 Worker 等待及 final
writer release；仅供成功 WGS 的 bulk 开关不作为新公共算法的流程/终态准入条件。

- [x] `test_reclaimed_inventory_consumers_share_bounded_queries` 只覆盖新接入的失败恢复/活跃等待调用点；275 Worker 共享夹具只跑一组，不再乘以 WGS/GATK 和全部阶段。已验收 WGS 成功收尾直接引用。
- [x] 无关 namespace 批次不阻断；只拒绝声明属于当前运行或与绑定 name/UID/owner 冲突的对象。旧 Master 被回收时充分持久证据有效，不要求在线旧 Pod；必要证据缺失仍拒绝。引用已有相关正/负例，查询逻辑实际改变且缺覆盖才在同一夹具补断言。
- [x] 将旧 `test_bulk_mode_cannot_be_used_for_active_recovery` 更新为 `test_active_bulk_observation_cannot_authorize_replacement`：允许公共只读观察，仍断言活跃 writer 禁止替换/释放；不是直接删掉负例。
- [x] 复用已验证清单索引并接入公共 native 查询，不重写成功路径；持久诊断足够不重复读取旧 Pod，普通进度观察不执行全清单/helper Job；120s 总预算/30s 单次不变。
- [x] CAS 保留最新证明；公共 fixture 已覆盖新鲜查询（含CAS实际调用），引用旧验证器证据，不重跑整文件。
- [x] 失败用例：只读 probe 瞬时故障再成功；三次耗尽；权限错误不重试；重试中 UID/存储改变拒绝。
- [x] 实现最多三次、2s/5s 延迟、总120s 且受原剩余 deadline 限制的 probe；只重复只读操作。
- [x] BS10610 定向 RED/GREEN；native 和平台分别提交配对修改，记录兼容接口和 SHA。

R3 差量节点：`python -m pytest scripts/tests/test_cce_final_bulk_inventory.py::test_reclaimed_inventory_consumers_share_bounded_queries -q`；
native 仅新增 probe 重试节点 `python -m pytest tests/test_directory_probe_retry.py -q`（不包含旧 probe 全套）。
CAS 仅在上述直接变化时选 `scripts/tests/test_p02_resume_final.py::test_inventory_is_refreshed_at_cas`。
必须加载固定版本的真实 native 模块，不能因缺少 `CCE_PLUGIN_SOURCE` 跳过后计为通过；不重跑该文件整套。

产物：不依赖流程名、不会因优化跳过身份验证的公共查询；可解释且有界的目录探测故障处理。

## UE-04：WGS 异步迁移与 GATK 薄接入

Owner：平台 Workflow / Airflow 负责人；native owner 负责 TTL 下游共享消费的必要源码差量。
依赖 UE-01/02/03；先固定 native 可复用调用与证据来源，再由平台接线，不各写一套验证器。

2026-09-29 16:06Z 已由协调者放行原两个 owner 按本节实施；当前未验收。
WGS 原同步 Step2 handler 已承担启动握手，不能把“没有独立wait task”当成原本没有等待。
迁移后的 submit_and_await 保留 START_CONFIRMED/权威终态及原pool；不为图形对称新增sensor。
GATK保留已有submit/wait图。native TTL共享入口先明确，平台独立的共同客户端/R1可先推进；
每个最小源码提交和唯一差量证据回交协调审核，不等待无关生产任务，不部署候选。

主要修改 WGS Step2/6 外壳和当前 P0 交接；已异步阶段只换公共调用。GATK 只接入 UE-02
抽取函数还不够，其 DAG `run_stage/stage_ready` 同时改为共同派发/观察判定；
保留业务回执/handler/落地算法。图保留 submit/wait 的理由是避免重复等待和资源占用回退，
不是要求源码不动；若局部 task 调整能消除具体控制缺陷，可在给出影响分析后纳入。
新执行不回退到两套旧 dispatcher，也不开发废弃旧同步/Resume 适配。
公共客户端置于 `dags/common/stage_execution.py`，调用参数均来自受信 adapter：
`submit_stage(*, execution_ref, dispatch, observe, deadline) -> ExecutionSnapshot`；
`observe_stage(*, execution_ref, observe) -> ExecutionSnapshot`。
前者统一处理派发响应/不确定结果的同身份观察，后者负责单次观察及相同状态解释；
不新增自动恢复策略或重发预算。GATK 的 submit 与 sensor 分别调用这两个函数。
WGS 的薄 `submit_and_await(*, execution_ref, dispatch, observe, deadline, poll_interval=30)`
只组合以上函数返回 `ExecutionSnapshot`，不另写状态机。成功必须匹配本执行阶段证据；
deadline 若存在使用适用的原已冻结观察期限，不能从调用时重新计时；允许 None 由原
Airflow task/sensor 期限约束。不得把 Step2握手/Step3计算/Step4发布期限改为全阶段统一时钟。

R1 交接依照 spec3.3：当前正常/P0 恢复登记均先校验请求资格；已验证且匹配当前前驱的
平台成功记录直接使用，不重复接收或访问远端。仅缺失/滞后时复用
`wgs_observer.sync_runtime_stage_artifacts(*, session_factory, request_root, transfer_spool_root,
analysis_id, attempt, stage)`；GATK 已有接收机制不重复新增，只在共同缺陷确实影响处薄适配。
独立写会话不得嵌套在同运行写锁中。
登记事务重新读取并校验当前 action/attempt/前驱成功及 receipt hash，再幂等登记后继。
`main.py` 当前 P0 阶段续跑早返回不能绕过此过程，不恢复废弃的跳转 Submit 入口；
不复制接收逻辑或借前端 status GET 修复时序。
公共 `ExecutionSnapshot` 到原进度/终态字段的投影也在本步完成，回调/清理 fence 在 UE-05。

### TTL-DOWNSTREAM：正常链与恢复链共用下游终态

1. native 先盘点当前补丁与既有 `_recovery_native_success` / `_bound_downstream_master`、
   终态收集实现，复用已经正确的验证器。Step3 对外提供可推进前驱时，真实成功终态必须
   已持久可读并绑定当前选中 Master 的 UID/Pod、attempt、计算 generation 与冻结摘要；
   不能把各 stage 的 generation 数字强行设为相同。缺失时补收集已有终态或报告待核验，
   不用平台 success/规则100%/MIRROR_COMPLETE 代替，不把已证实计算成功改成计算失败。
2. 普通 Step4 发布及 Step5 的 `download_snakemake_logs` 消费同一受信下游绑定，保留
   结果/日志导出核验。真实404且持久证明充分可继续；在线同名异 UID、活跃/失败等冲突
   仍拒绝；查询超时不是404。沿用必要的新鲜精确查询，不为每次读取新增全云 inventory、
   helper Job、数据库表或重复持久化一份业务结果。不改 TTL，不为导出日志新建 Master。
3. 平台核对实际 GATK/WGS gate 的 handler，而不仅 DAG 或 CLI 声明：普通提交和当前
   P0 续跑都通过受信 resolver 使用上述公共路径，不能仅在 opt-in 恢复分支可用。
   不接受任意 bundle/UID 参数、不补造旧登记；只改实际受影响调用，原本正确的 WGS 路径
   引用已有证据。该项不扩 UE-01 wire 字段或引入新公开 API，Step6 仍沿用已有落地门禁。
4. 当前生产补丁与永久实现逐项登记“保留/被公共实现替代/仅当前批次”，不将临时
   批次特判纳入新执行器。生产冻结运行不自动改指向候选，退役临时应用须等该批次结束，
   按独立生产授权执行，而不是 UE-06 顺便清理。

唯一新增共享行为节点计划为 native `tests/test_master_handoff.py::test_bound_terminal_survives_ttl_for_downstream`：
复用原 handoff/terminal 夹具，加载真实 Step4/Step5 入口，仅替换云 I/O；覆盖无在线 Master
但匹配终态可接续、旧非终态镜像不足以放行，以及查询故障不冒充404。已有错 UID/摘要/
冲突终态负例直接引用；直接改变其验证且缺覆盖时才在同一夹具补断言。不 mock 掉待验证
的 `_recovery_native_success` 或日志入口来制造通过。实际测试文件如已存在等价节点，
优先复用并在交接记唯一节点，不另建同义用例。
平台在原 `test_gatk_thin_binding` 内补真实 handler 到共享下游路径的接线断言；WGS 未变
不重测。BS10610 一次差量 RED/GREEN，不等真实 TTL、不创建 Job、不重复 Step1–6 批次测试。

### UE-04 交付清单（原迁移与新增缺口合并）

2026-09-29 16:58Z 源码切片：平台 `7ee7d7c` 公共DAG客户端/两DAG接线已审阅，
原始 BS10610 差量16项和两DAG真实导入证据已读取；未重复执行。
前置 exact-submit 为 `0feec868/5fd01a9`。native TTL 切片 `4fa85874` 已审阅实际diff及
单一共享fixture最新GREEN，runtime SHA256 `ae52b7601c3ea59e5e294bb3bf695802efc69f3d5b60333bd6b422c47bd14c53`。
18:27Z 平台R1/F3/F4、exact status与无XCom观察在 `a6c31d1` 完成，最终交接 `7976f25`。
协调者已阅原始差量日志/hash；native普通Step5到已验收log-export共享验证的源码链、
平台selected bundle/UID及固定入口均已核对。UE04源码验收闭合；不声称已部署pin、
直接Step5 fixture或真实TTL全链验收，也不为未改薄调用重跑TTL矩阵。

- [x] 仅覆盖迁移的 WGS Step2/6：`test_wgs_migrated_stages_use_shared_execution`，accepted 不是业务成功，终态来自 observe；公共幂等结论引用 UE-02，不重复测。
- [x] `test_wgs_step2_wait_preserves_handshake_and_pool`：WGS 握手未确认不放行 Step3，保留原 pool；GATK 原 submit/wait 验收不重开。
- [x] 在当前 WGS P0 测试增加 `test_predecessor_receipt_visible_before_step3_registration`：已验证前驱的接收调用次数为0；滞后时才调用真实接收服务后登记同一 Step3，缺失/错代拒绝。正常/手动/自动共用屏障，不复制三套场景；GATK 接收点未改则不新建其同义测试。
- [x] 同一 fixture 增加 `test_predecessor_ingestion_rechecks_current_identity`：接收与登记间切换 action/attempt/停止请求，登记重新核对后拒绝，不派发、不修改新身份；不把 synthetic 交错测试宣称为真实 PostgreSQL 并发验收。
- [x] 两侧调用共同客户端：GATK submit 不再独立按 SSH 返回码推出业务状态，wait 用共同完成条件；
  WGS 薄循环调用同一观察函数。超时/失联先观察同一 execution，活跃只接回，unknown 不授权重发/放行；
  鉴权/身份错误仍拒绝，不吞成普通等待。使用 `test_gatk_thin_binding` 覆盖实际改变的调用和不确定结果，
  同一 fixture 引用公共判定证据，不为 GATK 另验收六阶段全链路。
- [x] 保留 WGS `submit_step2_master` 的 `wgs_cce_runs` pool 与原正常占用范围；GATK 不新增
  专用 pool。等待受原阶段 deadline 约束，任务重试仅接回；不保持长 SSH、不新建配额系统。
- [x] WGS Step6 不完整不 finalize 的断言放入迁移用例；后端在原运行锁内核对当前
  attempt/DagRun/action、最新Step6成功执行及匹配的已接收receipt/marker身份摘要，
  复用现有摘要与evidence校验。business status先于native control receipt写入的窗口
  不能只靠DAG图约束：marked finalize通过已有`worker_observation`发送受限只读observe
  取得的同Step6完整snapshot；后端要求succeeded、匹配当前ref和receipt摘要，缺失/
  unknown/错代拒绝。复用认证内部调用边界，不新增字段/route、私有证据读取权限或
  第二套native协议；GATK若有同一窗口使用同校验薄接线，不重写业务算法。
  stage-status投影确切执行tuple供sensor比对，
  不能只以retry_no代替。Step1/5 租约未改则引用原证据，不重做传输测试。
- [x] 只在 snapshot 映射新增/改变时补共享 `test_snapshot_preserves_stage_evidence_and_observation_health`：unknown 不制造终态、真实失败仍投影、旧身份不覆盖新状态；不在每流程每阶段重复测试。实际共同契约断言与精确ref消费者差量已审核，未变映射复用既有证据。
- [x] 保留 nested master/UID/namespace/run-label 和 rule counts/current_step；已验收 timing/Phase 直接引用，不改 policy/前端，不重跑历史4.2.0/4.2.1/4.2.2映射。投影直接变化且缺证据时才选当前4.2.2必要节点。
- [x] native 终态来源及普通 Step4/Step5 共享消费、平台真实 gate 接线按 TTL-DOWNSTREAM 配对完成；记录当前补丁的来源/替代关系和上述唯一差量证据，不将旧镜像或404当成功。
- [x] BS10610 定向 DAG/consumer 检查；更新 docs/07 和 docs/08，提交本步代码及证据。

R1 定向命令：`python -m pytest backend/tests/test_wgs_resume_stage.py -k "predecessor_receipt_visible or predecessor_ingestion_rechecks" -q`。
迁移节点：`scripts/tests/test_unified_stage_adapters.py::test_wgs_migrated_stages_use_shared_execution`、
`dags/tests/test_stage_execution_wait.py::test_wgs_step2_wait_preserves_handshake_and_pool`；
GATK 接线节点为 `scripts/tests/test_unified_stage_adapters.py::test_gatk_thin_binding`，覆盖 gate 与 DAG 公共调用变化。
以上均在 BS10610；通过应证明新增断言及原展示行为，不能用伪造成功前驱让用例绕过故障。

产物：同一执行及派发/观察/恢复判定；WGS 完成主要迁移，GATK 完成必要契约修正，
两套 task 调度包装不拥有独立生命周期。后续控制依赖执行引用与真实静止证据，不依赖 task 图。

## UE-05：P0 控制/恢复消费收敛

Owner：平台恢复负责人；依赖 UE-04。

2026-09-30 修正结项：`03bab6c` 已关闭下面两项 Important；协调者接受 AF 源码及
原始隔离差量证据：14个唯一通过用例、两文件 DagBag import、18项证据摘要、11项
测试输入与提交一致。首轮R4的审计动作计数fixture失败保留，只修正/重跑该节点。
不重复原全审或已验收用例。最终 native owner 已确认当前AF/已接受`7172573`无真实
配对缺口：SSH不明结果仅观察原ref，R2/R4终态合同与独立Worker证明保持一致。
UE05源码与差量验收完成；UE06实际安装/加载仍未开始，本结项不授权merge/安装/生产部署。

以下为原审查时点记录，缺失GREEN/草稿状态已被上述结项覆盖，不要求回退或重跑。

2026-09-30 最新源码交接：原 owner 已提交 R2/R4及生产者接线检查点 `8617dfa`，
状态交接为 `a9a326d`；共享 SSH仍为前置 `06bf30a`。协调者核对19路径摘要与原始
交接证据，一次跨调用点只读审核发现两处 Important：Step1/2入口action必须绑定真实
Step3登记而非入口代次；初始native终态许可必须支持同预留的独立Worker续报。
详见[源码审核](../../reviews/2026-09-30-ue05-source-handoff-review.md)，归原R2/R4，
只扩展既有fixture的两个缺口，不新增阶段或完整测试矩阵。以下未提交草稿描述是历史，不要求回退。
最终源码 GREEN和两DAG import仍未取得，UE-05验收不勾选、UE-06不启动。
新鲜BS10610文档访问已成功，但不能替代owner的环境预检和剩余唯一差量验证。

2026-09-29 19:03Z 实施状态：F7 版本正确摘要及平台最终只读查询已局部提交
`4cb6e0d`/`be0adb8`；native 最终释放 `7172573` 已提交并通过原始差量核验。
两侧共享截止时间内只读退避统一为首次2s、之后5s；单次<=30s，总预算不重置，
CAS最多一次，证据不足仍阻断。仅源码/隔离synthetic通过，不代表安装或生产。UE-05 尚未结项。
R2 初步 GREEN 在审查中被判不足：不能只凭 action generation 和数据库终态
放行计算结束，仍缺冻结执行/真实 native 终态绑定。R2 草稿未提交；R4 未实现。
最小候选是在现有认证内部 poll/失败回调/清理请求传递同执行 snapshot，复用
UE-04 校验，不新增 route/DB/恢复框架；Worker probe/nonce 及原等待预算独立保留。
该内部接口修正已于2026-09-30获用户明确确认；先前等待记录仅为历史。不以 blanket
延期或 UI 观察状态替代。UE-06 仍待 UE-05 源码及差量审核。

### UE-05 SSH 连接收敛与 R2/R4 继续顺序

2026-09-30 恢复检查点：用户在暂停后重新要求继续开发。共享 SSH 源码已独立提交
`06bf30a`；原 AF 工作树保留12个未提交、未集成的 R2/R4 草稿文件。由原 owner 完成
R4 fence/生产者接线，并补欠缺的 BS10610 SSH/R2/R4 差量；先核实连接及环境，不能把
用户报告网络恢复当作测试 GREEN。下列三文件草稿描述为较早起点，不要求回退现有草稿。
已验收部分不重做，UE-06 仍以 UE-05 审核通过为前置，不授权生产部署。

1. 原平台 owner 保留现有 UE05 worktree/分支和三文件 R2 草稿，先完成共享 SSH 差量
   独立提交，再完成获批 R2/R4；不回去操作已完成 WES 的旧 Step1。协调者维护本 spec/plan。
2. SSH 文件边界：新增 `dags/common/ssh_transport.py`；仅调整 `dags/bio_wgs.py`、
   `dags/bio_gatk.py`、`dags/cce_publish_dispatch.py`、`dags/cce_worker_wait.py` 中当前
   Step1–6/P0 实际 SSH 消费点；`dags/common/stage_execution.py` 只在异常接回确有必要时
   薄接线。不为已废弃入口新增兼容，也不统一扫描全仓所有 SSH 调用。
3. 公共内部入口建议 `run_ssh(command, *, timeout_seconds, deadline_epoch=None)`，返回
   原 CompletedProcess或原超时异常，不能自己登记/判断业务终态。按 spec3.5固定30s握手、
   三次连接、5s/10s退避和单一调用预算，原固定命令/配置/host-key保护不变；未知派发仍
   交现有同身份observe。移除消费点重复重连循环/冲突的ConnectTimeout，禁止嵌套重试。
4. 唯一共享差量文件 `dags/tests/test_ssh_transport.py`：用假时钟证明 banner暂态后成功
   （原命令/身份不变）、三次与总预算耗尽、认证/host-key/混合输出及命令超时不重放。
   复用已有 WGS allowlist 与公共 uncertain-observe 断言；两 DAG 只补必要的实际接线断言，
   不做流程×六阶段矩阵，不跑旧 Step1/整批/全量测试。BS10610 RED/GREEN一次；本地仅Git。
5. 更新 docs/07、docs/08 中连接/观察职责；无外部接口改变的 SSH 部分不修改 DB/API。
   R2/R4 则按下面既定节点补最小共享断言，docs/05记录获批内部快照字段与精确绑定。
6. native owner 审核 SSH 异常到 submit/observe及终态的边界，不复制连接实现；保持
   release0.8.9和现有已接受7172573。只有证实的配对缺口才提出最小源码变更，无缺口不做测试。
7. 各项提供精确提交、文件差量、原始定向日志/输入SHA和未验证项，协调审核后进入UE-06。
   UE-06只增加共享SSH实际加载/安装接线核对，不重跑上述行为测试或已通过UE阶段。

- [x] 共享 SSH 行为与当前两 DAG/P0 消费接线完成、最小差量证据通过并提交。
  源码检查点 `06bf30a` 已独立提交并完成只读审查；共享预算耗尽后重入的
  pre-spawn guard 已补。最新03bab6c交付的9个SSH、2个薄接线用例和两DAG import通过；
  先前会话前连接失败仅为历史，不代表当前差量未执行。安装效果仍属UE06。
- [x] R2/R4 按获批内部快照通道完成，Worker probe/nonce独立，真实终态与冻结身份绑定。
- [x] 原两个 owner 配对审核并交接 UE-05；AF03bab6c/native7172573确认无配对缺口。
  本项只完成源码配对与既定差量验收，实际安装/部署不随之执行。

2026-09-29 Step6 现场补充：WGS `WGS_20260929_010715_9502F1` attempt1 的结果物化
已验证，但最终 CCE 清单查询因 typed `TRANSPORT` 失败；后查原锁/journal 缺失，原因未明。
行政 Airflow DagRun success 并未改变失败 TI、native Step6 或业务 finalize，不能作为验收。
本项归现有 R4/最终释放责任，不重新开发物化算法或重开 UE-03 验收，也不授权修复该批次。

- UE-04 F4/投影保留已验证物化事实，但只有匹配当前执行的 native Step6 终态与必要释放
  证明才能 finalize；100%、MATERIALIZED、DagRun success 都不能单独替代它。
- UE-05 平台 owner 负责 `cce_paired_runtime._release_registered_writer` 的 `evidence()`
  到 `cce_recovery_workloads.probe_final_workloads/_live_inventory` 的实际最终查询调用；
  native owner 仅核对现有锁/released journal及物化断点语义，按真实缺口薄接线。
  只补当前最终收尾实际缺失的只读暂态重连；复用 typed query 和现有总120s/单次30s上限、
  适用的原 deadline，不重置预算、不重发写操作、不复制查询引擎。CAS 前仍重取新鲜
  完整证明，不拿首次清单充当释放时证明；两次读取本身不是要删除的冗余校验。
- 同一次收尾的暂态查询重试不得重新物化。跨执行接续先核对已验证结果、当前归属和
  原释放证明；有可信同执行 release receipt 才能使用既有幂等路径。仅404、空清单或
  丢失锁/journal不能推导已释放，也不能重建锁绕过身份。无法证明时返回待核验并阻断
  finalize，明确剩余人工核查条件；不实现孤儿锁修复或任意历史批次迁移功能。
- 唯一必要差量 fixture 复用现有 final inventory/release 测试：物化已完成后查询一次
  typed TRANSPORT 再成功应只重读不重物化；预算耗尽/结果不明及缺锁无释放证明均不得
  成功。使用假时钟及 synthetic 记录；共享逻辑只测一次，平台只补变化的接线断言。
  已绿 query/目录探测/CAS 用例引用，确切节点由 owner 随源码调用点定位写入交接。
- UE-06 只核对实际安装的最终收尾入口；不重跑此 fixture、不重算/重传生产结果。

前置条件：UE-04 完成、native 对最终调用点的源码定位及窄接口配对完成后，才实施上述
UE-05 差量；若需新增持久状态/接口或放宽锁，停止扩大并向用户确认。独立凭据泄露处置
按安全运维流程评估，不混入本计划代码或记录任何凭据值。

消费公共执行记录，只覆盖当前 P0 阶段续跑、Step3 查询恢复、Step4 派发恢复、
同受支持运行的前序动作隔离和最终释放；不开发废弃 Resume 兼容。
动作授权/预算仍由现有 backend 持有；执行器不新增另一套 retry policy。
R2 具体消费：`poll_compute_recovery` 接收绑定的手动/自动计算终态，
`reserve_compute_recovery` 共用该判定；保留当前动作后续阶段授权、原 attempt 配额及
deadline，不把全部 queued 改终态。重复 poll 只得到同一预留，active/unknown/control fence 拒绝。
R4 具体消费：`dag_failure_fence_reason`、`require_current_dag_cleanup` 与既有观察投影辅助逻辑
读取 UE-04 的同执行快照；六阶段观察失联不等于业务失败或 writer 静止，不能只检查 step3_monitor。
TTL-DOWNSTREAM 的恢复只消费 UE-04 已核验终态及当前 action/fence：分析已成功而发布或
日志导出失败，只接续未完成的下游阶段，不申请计算替换、不消耗 Step3 重算预算、不重传。
这里不新增错误白名单、恢复次数或自动恢复引擎；下游重入仍需既有授权、幂等及无活跃
同阶段操作证明。UE-04 的 TTL 夹具直接引用，仅恢复调用实际改变且缺证据才补接线断言。

- [x] 原代次/CAS/活跃互斥验收直接引用；公共回执消费若引入未覆盖变化，只补对应节点。
- [x] 在 `backend/tests/test_cce_recovery_poll.py` 增加 `test_manual_terminal_allows_one_budgeted_recovery`：手动 Resume 后匹配 Step3 失败且证据/策略允许，预算仅增加一次，重复 poll 不再派发；后续阶段授权不丢失。真实终态缺失、错代或活跃仍阻挡。
- [x] 实现当前动作的派发/计算/下游权限分离，轮询与预算共用判定；不能用已失败 DagRun 替代计算终态。原预算/禁用策略/fence 验收引用，不重跑全套手动/自动恢复或历史记录测试。
- [x] 在 `backend/tests/test_cce_recovery_cleanup_fence.py` 只补 `test_unknown_stage_cannot_fail_or_release`：共享保护覆盖新接入阶段，不因观察超时释放租约/drain 或授权替换；匹配真实终态按原规则处理。不乘以两个流程或重复 UE-04 展示断言。
- [x] 实现全阶段回调/清理 fence，复用 UE-04 的观察健康和身份；不创建新 DB 状态，不删除后台锁，不以无限延期掩盖错误。
- [x] 公共路径统一消费 dispatcher/回执，移除其 WGS 同步特例；不留 legacy reader 或废弃 Resume 重放分支，不顺带做全仓历史代码清理。
- [x] 保留现有控制 fence 的优先级，不实现未来暂停 handler/新按钮/第三 adapter 演示，不新增它们的测试。
- [x] 定向 RED/GREEN，更新 docs/05 中受影响的已有行为说明（不新增公共 route），提交。

R2/R4 定向命令：`python -m pytest backend/tests/test_cce_recovery_poll.py::test_manual_terminal_allows_one_budgeted_recovery backend/tests/test_cce_recovery_cleanup_fence.py::test_unknown_stage_cannot_fail_or_release -q`。
通过必须同时证明许可与拒绝两侧；合并执行受影响节点并去重，不为每个正例另跑全套 P0。

产物：维护一套执行/恢复控制逻辑；完整 RC 控制功能仍未上线。

## UE-06：测试端配对交付与回滚

Owner：原 native 制品 owner + 平台部署负责人；不自行重建 WGS/插件/Master 镜像。

2026-09-30 用户已要求检查无问题后进入下一步。UE05已结项，AF产品源码03bab6c及
状态a0666e5/native7172573配对无已知缺口，现批准原owner启动本节测试端隔离安装/
真实模块入口检查。先做新鲜BS10610预检并登记精确候选、安装和回滚路径，不覆盖
共享nipttest/生产0.8.8或活跃pin，不重跑前序用例。现已接受本节隔离安装/真实加载
原始证据及最终AF状态3c094fc/28项证据索引，隔离交付结项；生产另批。
旧shared指向/home/ctapa的policy/platform
在BS10610不存在，不能声称实际旧配对配置回滚可用；本轮回退为不选择隔离候选、
保留当前服务/shared/pin不动，准确0.8.8回滚wheel逐文件核对通过。实际切换前须确认
环境自身的回滚配置，不以本节技术接线验收代替。

- [x] 记录 source commits、候选 wheel SHA、平台依赖文件和配对策略；安装使用批准的 nipttest 路径/测试身份。
- [x] 开始远端操作前核对 BS10610 hostname、control root、真实挂载与 gate；scanner/dispatch 保持关闭。
- [x] release0.8.9候选使用隔离安装根与内容摘要，保留原制品/配置作为回滚资产，不新增旧协议兼容入口；不覆盖生产0.8.8或共享冻结资源。
- [x] 只核对实际安装候选的版本/SHA、pin 和真实模块入口接线；不重新执行 WGS/GATK 六阶段提交/等待/恢复，不 mock 掉要核对的入口。
- [x] TTL-DOWNSTREAM 核对普通 gate 与受支持 P0 下游确实加载已修复模块，而不只是版本号正确；引用 UE-04 唯一行为证据，登记当前补丁已上游收敛/仍仅服务冻结批次的边界，不改活跃生产项目。
- [x] 汇总 UE-01–05 单次差量证据和既有已验收结论，已通过项只引用。缺口仅补安装引入/改变的边界；不因发布或 SHA 变化重开项目验收，不运行全套或创建云 Job/真实批次。
- [x] R1→UE-04、R2→UE-05、R3→UE-03、R4→UE-04/05 各引用唯一证据；原 deadline、预算、权限、TTL、进度/Phase 继续有效，不重跑；旧批次成功也不能冒充新变化已经通过。
- [x] 引用已验收版本/策略拒绝结论，仅检查本次安装；准确旧wheel可达且匹配，旧shared配对policy/platform不可达已记录，实际切换回滚未验收；不执行旧协议回放或删除证据。
- [x] 更新 CURRENT_STATE、TASKS、HANDOFF 和环境记录，准确区分源码、隔离安装验收与未验证的真实激活/旧policy回滚能力；最终AF状态3c094fc与28项索引已核对。

通过条件：UE-01–05 的直接变更缺口有一次有效证据，未变已验收项目沿用结论；
公共调用无双 worker/独立失败状态机，GATK 改动限于有依据的契约/接线修正而非业务重写，
测试端配对安装可回滚。真实云端控制与生产部署
不得记为通过。UE-06 不是第二轮全链路验收。

## 后续独立任务（不包含在本轮验收）

按既有 RC 设计实现真实暂停/取消 handler、控制 API/UI、确认/审计和精确停止验收；
再单独批准生产发布。若需要新增持久控制表，先更新数据库设计和迁移方案，不临时塞入
RunAction 作为删除后唯一审计。本计划不授权删除、Step7、CLI批量操作或重跑真实任务。
