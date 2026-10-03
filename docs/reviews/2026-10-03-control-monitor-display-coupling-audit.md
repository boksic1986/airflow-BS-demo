# 本地派发、云端监控与前端展示：耦合审查

日期：2026-10-03。任务：ARCH-CONTROL-MONITOR-20261003。性质：只读代码审查与文档总结，不是实施或生产恢复方案的批准。

后续状态（同日20:27）：F1/F2 的证据定位与原 Master 引用已由限定两处修复完成，
D-test1 真实 Step4–6 与平台/Airflow 最终成功一致，见原 owner 的
[完成记录](../releases/2026-10-03-dtest1-downstream-twofix.md)。下文是修复前审查证据，
不能再据“批次尚未恢复”重开操作；其他架构建议未因这次修复自动完成。

## 1. 结论

用户的主要担忧成立：**当前恢复路径把计算身份、监控进程、平台阶段代次和证据目录布局串联得过紧；局部补丁已增加恢复难度。** 当前阻塞不能简单归因于 SSH、目录权限或“锁太严格”。

但有三点需要纠正：

1. 没有发现前端直接按 node200/96 选择 CCE 监控路径。节点选择在 Airflow 派发层；此前进度闪烁是上游快照字段丢失，不是换节点换了 React。
2. 共享目录可读写，可以支持跨节点读取可信计算证据；不能证明另一节点上的旧进程已经停止，也不自动赋予重复 START、接管目录锁的安全条件。
3. 计算成功、监控成功、整条交付流程成功是三个不同事实。当前最新已记录的云端计算成功，不等于 Step4–6 已完成；平台红色 failed 也不必然代表需要重算。

应削减的是**重复定位、重复解释状态和观察者对计算恢复链的依赖**，不是取消精确计算身份、幂等和单写者保护。无需再造一套执行框架；原 UE 设计已要求这些边界，接线尚未完整落实。

## 2. 证据基线与限制

- 当前工作目录 `D:/pipeline/airflow-demo` 的 HEAD 为 `9b381eb`，不是这次生产修复源码基线。协调 worktree HEAD 为 `257931c`，含大量原有未提交改动；本轮不修改它们。
- 本次主要审查 AF owner worktree `C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo`，HEAD `5b50b8a3fc075be5c51468d3dd3020ccecf35034`。
- 本地重新核对 paired SHA `3fc179a9…6a79c9`、backend recovery budget SHA `55cb60de…bd594a`、native runtime SHA `af05ea22…ce5cb2b`、guard SHA `e99378dc…de6e6d0f`；与既有部署清单及交接记录对应。[部署记录][deploy]
- StageExecutor 源码 SHA `21b505da319cc752c5694f2b42e4082dd02dc47e3c7ddad895fdb87b08581bd2`，对应 10-02 03:20:43Z 已安装快照；不是本轮在线 hash。[安装快照][executor-installed]
- 本轮没有 SSH、生产 DB 访问、API 写入、测试、部署或 rerun。生产状态引用已保存的 10-03 05:41–05:51Z 记录，不冒充最新在线检查；React 是源码审查，不声明全部线上 bundle 与该 HEAD 相同。
- 旧版本只做相关代码差异对照，没有“旧版全流程始终可以安全恢复”的等价现场对照，不能据此承诺整体回滚即可解决。

## 3. 现在各模块怎样关联

```text
浏览器：Dashboard / Batch Runs / Run Detail
    ↕ FastAPI：读取业务状态与证据投影；受鉴权动作入口
业务登记、阶段请求、Airflow REST API
    ↓
BS96 Airflow：项目级任务与等待
    ↓ SSH alias + restricted command（WGS/GATK 各自业务入口）
选定控制节点：默认200，当前切换记录为96
    gate → 公共 StageExecutor → pipeline handler / paired runtime
    ↓ 创建/观察；计算身份与本机监控进程不是同一对象
CCE Master / Workers → 云端持久证据、日志与结果
    ↓ collector / 必要时 reader helper → 共享 runtime 的镜像与阶段回执
后端 observer / 回调 → 业务 DB 投影 → 前端
```

前端不通过 SSH 读项目，不直接连 Airflow DB。Airflow 位于96，也不意味着所有后台监控进程在 Airflow 容器内。改变 SSH alias 只改变后续调用路由，不会迁移已经启动的后台进程。

WGS/GATK 已共用公共执行客户端和执行器，但仍保留业务 adapter、gate 与独立节点环境变量。保留不同生信 handler 合理；共用控制节点还要成对修改两个变量，则是尚未收敛的配置责任。[WGS 路由][wgs-route]、[GATK 路由][gatk-route]、[成对切96记录][node-release]

### 目录不能全部视为一个“项目目录”

| 类别 | 当前形态（省略公共前缀） | 作用与边界 |
|---|---|---|
| 业务项目 | `/sg2/50.ctapa/Clinical/WGS_Clinical/<batch>` | 输入配置、业务产物、交付；适合持久业务证据和可定位索引 |
| 请求 spool | `airflow-wgs/runtime/runner-requests/<id>/attempt-1` | 请求、冻结登记、派发状态和本机进程控制；初始 submission journal 也在此 |
| runtime control | `airflow-wgs/runtime/runs/<id>/attempt-1` | 平台运行控制；WGS recovery journal 写在此 |
| 云端 SFS | `/workspace/wgs/runs/.../evidence/<id>-a1/master/<UID>` | Master/Worker 真实云端证据；共享 `/sg2` 不代表宿主直接挂载了这个路径 |
| 部署信任配置 | `/home/ctapa/.config/airflow-common/...` | 受限入口、策略、凭据引用；不应当作普通项目可写文件 |

“业务证据、log 可从项目稳定定位”是合理目标；“全部物理文件都搬到项目目录”不是必要条件。建议一份稳定运行清单引用批准位置，避免各模块猜目录。不能把凭据、私有登记随意开放到业务目录；2775/0664/0775 的业务权限要求不等于取消私有控制文件边界。

## 4. 具体发现

### F1 / P1：恢复 journal 的写入、读取和 native 注册使用不同根

这是真实契约缺陷，不是 ctapa 权限不足。

- paired `register_initial` 把 `request_path.parent` 固定为 native `control_root`；`_registered_request` 明知 request 与 runtime control 是两个批准根，仍返回 request path。[注册][paired-register]、[分根声明][paired-roots]
- `wgs_resume` 把 recovery journal 写到 `payload.control_workdir`。[写入][recovery-write]
- `prepare_monitor_registered` 从 spool 查找 producer；guard `resolve_current_owner` 也只枚举冻结的单一 `registration.control_root`。`selected_bundle` 仅约束结果，不扩展搜索根。[观察入口][monitor-entry]、[guard resolver][guard-resolver]
- 因此会出现真实 owner/证据存在，却报 `current owner has no unique native submission`。只改 paired 一个 locator，后续 `writer.validate` 仍会在同一 guard 卡住。

结论：重复维护“证据在哪里”的约定，产生了不必要的部署布局耦合。长期应收敛为一个受信解析入口和明确计算引用；不能靠逐层增加 glob、复制 journal、改旧登记来掩盖矛盾。

### F2 / P1：观察者失败后，恢复入口继续依赖前一观察代次来寻找计算生产者

`_created_monitor_journal` 使用 `resume_previous_execution` 寻找创建 Master 的 journal。上一代如果只是失败观察者，就不能等同于真正的 producer；当前链是 producer3 → observer4，下一请求的 previous 会变成 observer4。[producer 定位][producer-chain]

已有 `_observe_registered_source` 正确保留 producer binding，并未要求把观察者改成 producer；问题是所有入口没有始终消费这份稳定关联。[已有分离][producer-preserve]

结论：**监控重连应该换观察会话，不应不断扩大计算恢复历史的解释成本。** 计算重跑和监控重接可以共享安全内核，但应使用不同动作语义。当前调用 `prepare_monitor_registered` 后回退到 `resume_registered`，使两者在实现上纠缠；这次实际失败发生在校验阶段，不代表已偷偷重建 Master。

### F3 / P1：监控阶段的真实失败，被投影成顶层 run 失败；计算终态没有独立呈现

实际链路为：同身份 stage failed → native stage terminal 校验通过 → DAG failure fence 放行 → `run.status='failed'`。类型校验能证明“这个阶段确实失败”，不等于证明“原 Master 的计算失败”。[终态 gate][terminal-fence]、[协议校验][terminal-contract]、[平台写入][run-failed]

adapter `_publish_terminal` 当前写 `compute_identity: None`；公共内核预留了 ComputeIdentity，并不意味着各个业务 handler 已正确填入和解释计算终态。[adapter][adapter-terminal]

反证也需要保留：源码已有独立 observation health、query-unconfirmed 和保留最后进度逻辑，WGS/GATK 都不是完全没有分离设计。缺口在于正式 native stage failure 走另一条权威终态路径。[健康状态][health]、[WGS 保留][wgs-health]、[GATK 保留][gatk-health]

若顶层 failed 表示整条交付链未完成，并非一定错误；但页面应明确“计算成功／监控或交接失败／后处理未完成”，不能只留下诱导重算的红色失败。当前 recovery projection 对 failed run 直接返回空，Batch Runs 只渲染 run.status，使解释进一步丢失。[提示消失][recovery-view]、[Batch 状态][batch-status]

### F4 / P2：只读观察、刷新证据、ACK 对账和计算控制被同名封装掩盖

StageExecutor `observe` 确实纯读，不创建 worker、锁或业务结果。[纯观察][pure-observe]

但 native Step3 `read_only=True` 只跳过计算 writer 的 enter/claim；其内部仍可能创建/删除 SFS reader Job、写本地 mirror。ACK 对账还会经过 writer.validate，并持久化 START_CONFIRMED。[guard 边界][readonly-guard]、[reader helper][reader-helper]、[mirror][mirror-write]、[ACK 路径][ack-path]

这些操作不等于重新分析，部分也是 TTL 回收后取证所需；不能一律删除。但是应分别标记：纯读取、证据刷新/对账、计算启动/恢复。否则“仅启动监控”意外依赖写锁、云端 helper 和完整激活校验，网络故障面和理解成本都会扩大。

### F5 / P2：6/333 与 Waiting 闪烁是共享状态的写入协议缺陷

原 healthy 查询写入只带部分字段，丢掉 WGS nested `master`；后端无 master 时清空计数，正常 collector 下一轮又补回。React只是显示当时 API 的事实。[清空路径][counter-clear]

`4fc2999` 的唯一产品修改是 paired runtime，35 行差量，无 React 产品修改；当前 3fc 用同次完整 validated observation 发布计数。这是修真实缺陷，不是为了节点切换做的显示兼容。[完整观察发布][progress-write]

该修复与 F1/F2 是不同问题。不能为了消除恢复复杂性，把已经证明必要的快照完整性修复一并回滚；也不能据此声称整个恢复链已修好。

### F6 / P2：三个页面的进度投影不是完全同一条链，权威与展示仍有反向依赖

- Dashboard `/dashboard/runs` 使用 progress service，活跃 run 可读取 Airflow task instance，再调用 adapter 投影。[Dashboard][dashboard]
- Batch Runs `/runs` 使用 summary；Run Detail 优先 `/workspace`，404 才回退多接口。[列表][runs-page]、[详情][detail-page]
- workspace 与 timing service 各自选择当前阶段；observer 的 stage upsert 还会调用 execution transition。[workspace][workspace-stage]、[timing][timing-stage]、[反向写入][projection-transition]

不同页面 API 不必强行合成一个，也不代表所有读取都冗余。问题是相同“当前阶段／失败种类／最后确认进度”有多处判定，且展示阶段曾被恢复选择使用。应由一个公共业务投影解释事实，页面只消费；控制动作读取执行登记，不反向依赖页面 current_stage。

### F7 / P1（恢复可用性）：跨节点读取能力与本机进程接管能力被混为一谈

ExecutionRef 无 hostname；RuntimeIdentity 是 boot ID/PID/starttime/process group，ComputeIdentity 则是计算代次/Master UID，三者已概念分离。[身份定义][identities]

不过 adapter 仍把整个 frozen binding 与原请求摘要纳入登记，路径耦合可能间接进入不可变摘要。“不含 hostname”不等于可以随意移动原请求。[冻结 binding][frozen-binding]

StageExecutor 优先接受可信终态；无终态时检查本机 `/proc`。共享目录来自另一 boot，`_group_quiescent` 返回 unknown，不能证明旧 worker 停止；换代 submit 因此拒绝。[跨机静止判断][quiescent]

这是必要的防重执行约束，也是当前“任意节点接管”尚未完整实现的边界。应让新观察者读稳定计算证据而不接管旧计算；真正需要替换活进程时，才要求受控停止或跨节点可验证的所有权交接。不能把本机找不到 PID 解释为旧节点已停。

### F8 / P2：测试数量与部署拓扑覆盖错位，发布状态又分散在多份记录

现有 fixture 把 REQUEST_ROOT/RUNTIME_RUN_ROOT 设为同根；ACK fixture 也把 recovery journal 放到 request parent。测试通过是真实的，却没有覆盖生产分根布局；反复跑同组身份负例不会发现 F1。[同根 fixture][fixture-root]、[ACK fixture][fixture-ack]

多 worktree、native 安装资产、不可变 paired release、backend overlay 和前端 bundle 不能由一个 HEAD 代表。当前累计日期补丁条目使“源码有了／已部署／当前批次可用”容易混淆。

本次协调过程也有责任：此前逐层追踪报错、补齐局部条件，却未在恢复前把真实目录布局和 observer→producer 关系作为组合验收；发现跨层契约不一致后，应该先收敛责任边界，而不是再把每个拒绝点当成独立补丁任务。

## 5. 哪些要保留，哪些应减少

| 必须保留 | 应减少或移出普通观察路径 |
|---|---|
| 精确 attempt、冻结输入、计算代次与 Master UID | 从观察失败历史反复倒推计算生产者 |
| 入口鉴权、受信代码/凭据、跨信任边界验证 | 同一受信操作每层重新解析同份不可变登记、重算同份摘要 |
| CREATE/START 幂等、防旧 callback 覆盖新执行 | 普通查询依赖完整计算恢复或 writer 激活链 |
| 目录单写者、写入/接管/释放前新鲜 CAS 校验 | 多模块自行拼 journal 根、扫描并猜“最新”证据 |
| 真实终态、结果校验、Worker 静止与安全清理 | UI 当前阶段反向决定恢复目标；三个页面各自解释同种状态 |

不是每次重复校验都冗余：入口到远端、写入前可能已发生并发变化，必须再次验证。原设计第3节已明确“不可变内容复用；跨边界和可变身份锁内复核保留”，应落实这一条，而非笼统削减检查。[原设计][ue-design]

## 6. 建议顺序（未授权实施）

1. **先固定事实与责任**：列清计算身份、观察会话、编排/交付状态及一个受信证据定位入口；WGS/GATK共用语义，生信 handler 保留差异。无需重开 UE-01–04 或新建恢复框架。
2. **当前阻塞单独处理**：保留成功计算；用明确受限的既有证据关联完成交接。当前无已证实可用的“忽略恢复记录直跳Step4”入口；不复制 journal、伪造前驱或改冻结注册。具体改动及生产恢复另行决定，本报告不批准之前的双根/递归链方案。
3. **再收敛长期路径**：稳定 compute reference 与可替换 observer；同一控制节点配置供WGS/GATK消费；公共后端投影供多个页面使用。取消重复定位与状态推断，而不是扩大历史兼容范围。
4. **最后整理发布信息**：维护一份当前组件/摘要/部署位置清单，历史修复条目归档；不把全部历史 HEAD 当成当前生产版本，也不在本轮顺手合并或重构。

只补实际未覆盖的边界：真实分根；producer 后接两个不同观察代次；云端成功而监控失败；跨节点读取终态与旧活进程不确定；完整/迟到快照不清空进度；WGS/GATK同节点路由。复用既有验收，不重跑临床批次、全套P0或全部镜像 smoke。本轮未执行这些测试。

## 7. 当前批次与本轮交付

已保存记录显示 `WGS_20261002_095408_323D3F/attempt1` 的当前 cb75 Master 于10-03 04:19:05Z真实成功；observer generation4 于05:44:26Z失败，Step4–6尚未启动。它不是“目前又发生了同一个生信rule错误”的证据；也不能把计算成功直接写成整批完成。[阶段记录][current-stage]

本轮只新增本文并更新协调 CURRENT_STATE/TASKS/HANDOFF；产品源码、线上运行、锁、数据库、自动监控均未改。已有未提交改动保留。文档校验限于差异、路径/行号和范围一致性，不冒充运行时验收。

## 源码与记录索引

[deploy]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/.codex-artifacts/wgs323d3f-tmp-recover-20261003/ack-progress-deployment-manifest.safe.json
[executor-installed]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/.codex-artifacts/wgs-6c78d5-prepare-20261002/initial-recover-20261002-1119-node-fingerprint.jsonl:1
[wgs-route]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/dags/bio_wgs.py:316
[gatk-route]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/dags/bio_gatk.py:164
[node-release]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/docs/releases/2026-10-02-common-control-node-bs96.md:118
[paired-register]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/scripts/cce_paired_runtime.py:242
[paired-roots]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/scripts/cce_paired_runtime.py:309
[recovery-write]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/scripts/wgs_resume.py:154
[monitor-entry]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/scripts/cce_paired_runtime.py:1341
[guard-resolver]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/.codex-artifacts/wgs323d3f-tmp-recover-20261003/actual-c8-guard.py:867
[producer-chain]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/scripts/cce_paired_runtime.py:1013
[producer-preserve]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/scripts/cce_paired_runtime.py:1121
[terminal-fence]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/backend/app/cce_recovery_budget.py:459
[terminal-contract]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/backend/app/stage_execution_contract.py:85
[run-failed]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/backend/app/wgs_submission_service.py:624
[adapter-terminal]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/scripts/cce_stage_execution_adapter.py:360
[health]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/backend/app/cce_monitor_observation.py:40
[wgs-health]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/backend/app/wgs_observer.py:1002
[gatk-health]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/backend/app/gatk_runtime_service.py:503
[recovery-view]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/backend/app/cce_recovery_projection.py:60
[batch-status]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/frontend/src/components/RunTable.tsx:51
[pure-observe]: D:/pipeline/WGS-noncoding-model/.codex-artifacts/w423-03-native-20261001/inspection/stage_execution.py:606
[readonly-guard]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/.codex-artifacts/wgs323d3f-tmp-recover-20261003/actual-c8-guard.py:1175
[reader-helper]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/.codex-artifacts/wgs323d3f-tmp-recover-20261003/ack-native-candidate.py:2313
[mirror-write]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/.codex-artifacts/wgs323d3f-tmp-recover-20261003/ack-native-candidate.py:3067
[ack-path]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/scripts/cce_paired_runtime.py:1081
[counter-clear]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/backend/app/wgs_observer.py:1487
[progress-write]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/scripts/cce_paired_runtime.py:1547
[dashboard]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/backend/app/dashboard_service.py:243
[runs-page]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/frontend/src/pages/RunsPage.tsx:43
[detail-page]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/frontend/src/pages/RunDetailPage.tsx:115
[workspace-stage]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/backend/app/wgs_workspace_service.py:76
[timing-stage]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/backend/app/wgs_timing_service.py:123
[projection-transition]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/backend/app/wgs_observer.py:1511
[identities]: D:/pipeline/WGS-noncoding-model/.codex-artifacts/w423-03-native-20261001/inspection/stage_execution.py:125
[frozen-binding]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/scripts/cce_stage_execution_adapter.py:112
[quiescent]: D:/pipeline/WGS-noncoding-model/.codex-artifacts/w423-03-native-20261001/inspection/stage_execution.py:447
[fixture-root]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/scripts/tests/test_p02_registered_recovery.py:25
[fixture-ack]: C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/scripts/tests/test_ack_monitor_reconnect.py:39
[ue-design]: C:/Users/11217/.codex/worktrees/wgs422-p0-integration-20260926/airflow-demo/docs/superpowers/specs/2026-09-28-unified-stage-execution-design.md:147
[current-stage]: C:/Users/11217/.codex/worktrees/wgs422-p0-integration-20260926/airflow-demo/HANDOFF.md
