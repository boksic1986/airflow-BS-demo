# Airflow 补丁与前后端架构审查总结

日期：2026-09-29。任务：`AUDIT-PATCH-20260929`。

补充任务：`AUDIT-STRUCTURE-20260929`。第 9–14 节进一步检查代码结构、语法、接口语义、事务、权限、模块耦合及前后端协作，不限于历史补丁。

本轮只审查本地源码、Git 差异、已有测试源码及交接证据，形成总结；**没有修改产品代码、运行测试、连接生产/数据库、部署、恢复任务或删除数据**。下文生产状态引用 2026-09-29 06:56Z 及此前已记录的检查，不是本轮实时复验。

## 1. 结论

不能把这些修改一概称为“兼容补丁”，也不能因为某批次跑通就认为整体已经收敛。

1. **多项是有明确根因的真实缺陷修复，应保留。** 包括注册自锁、请求摘要生产/消费不一致、目录身份比较错误、上传恢复后首次 Master 被误判为替换、监控写入丢失 Master 进度、旧 Step4 回执覆盖 Step5，以及 GATK 跨 generation 的传输投影。
2. **另一些是合理但有边界的兼容措施。** WGS 同步 Step2/6 的终态读取、初始请求与恢复请求的不同摘要规则、限定 pre-START 恢复、旧 queued 动作在 Step4 的豁免，解决了当前协议差异，但不等于公共生命周期已完成。
3. **phase 注册、等待状态、恢复提示和文案属于平台展示职责。** 它们不是生信规则补丁，不应迁到 cce-pipeline。精确版本的 phase 映射应保留，不能为了去掉 Unknown 而默认套用最新流程。
4. **现在最显著的工程风险是版本来源与状态权威分散。** main/生产分支、本次最新候选、测试分支、未提交运维差异和实际挂载不是同一套源码；一次“从最新 HEAD 重建”可能丢掉已部署修复。
5. **仍有可定位的源码缺口。** GATK 恢复 DagRun 的合法名称会被同步器拒绝；恢复注册可能缺前驱摄取；手动 queued 动作可能挡住后续自动恢复；WGS 对账成功门禁弱于 GATK。见第 4 节。

建议不是推翻重写，也不是继续逐批次加例外：先归档并核对实际发布差量，再按已有 UE-01～06 统一执行、回执消费和控制权判定。保留已验证的业务 handler、规则、输入和输出权限；本报告不授权实施或推广。

## 2. 审查基线：不存在一个可直接代表全部现状的 HEAD

本表 commit/分支来自本轮本地 Git；没有 fetch，不能把本地 remote-tracking ref 当成远端即时状态。

| 简称 | 位置 / 本地版本 | 本轮用途与限制 |
| --- | --- | --- |
| D | `D:/pipeline/airflow-demo`，`9b381eb` | 默认目录仍是旧运维分支，不能单独代表当前代码。 |
| M | 本地 `main`、`jiucheng/release/production` 均 `613b095`；对应 origin 跟踪引用相同 | 已合入主线的审查基准，不等于生产全部 overlay。 |
| L | `C:/Users/11217/.codex/worktrees/gatk-r4-phases/airflow-demo`，`6d11712` | 本轮前后端主要源码基线；tracked clean，含已有未跟踪 artifacts。比 M 多五个提交，但不是所有工作树的超集。 |
| O | `C:/Users/11217/.codex/worktrees/wgs422-p0-integration-20260926/airflow-demo`，`257931c` + 原有 dirty 差异 | 运维事实、测试分支 P1、尚未提交的同步阶段/恢复/界面等修复。只读核对，不整体合并。 |
| E | `C:/Users/11217/.codex/worktrees/step3-fence-repair/airflow-demo`，`e634ca4` + 文案候选 | 英文文案工作尚未提交/启用；用户要求等当前任务完成。 |
| U | `C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo`，`dcd7390` + UE-01 dirty 候选 | UE-01 平台契约正在开发；其交接仍记录单 fixture 未绿、未提交。不是已交付公共执行器。 |

关键分叉：

- `613b095..6d11712`：`a3c177a` → `9c7fc93` → `e634ca4` → `a85cfb6` → `6d11712`。
- `613b095..257931c`：`5c29d86` → `257931c`。三项 P1 按此前用户要求仅提交测试分支；**不在 M 或 L 中**。这是发布范围尚未收敛，不应仅凭差异指责当时提交错误。
- O 的若干 runtime 修复和顶部 Resume 隐藏仍是未提交差异。已有交接记录它们的运维使用/部署，不能因此称已进入主线。
- 06:56Z 记录中 BS96 backend 为 `7ac6a8e6b412`，observer 为 `80f6d137f9ef`；实际 Compose 为 `/data/airflow-WGS/downstream-stage-20260929-control/compose.json`，`/app` 基础版本之上有独立模块挂载。旧 `current` 链接不是有效的全部发布基线。
- 已记录部署：`9c7fc93`、`e634ca4`；尚未推广：GATK transfer `a3c177a`、r4 phase `6d11712`、英文文案候选。`a85cfb6` 是把已部署 WGS phase baseline 收回源码，不是新生信功能。

因此，“某个分支很新”“wheel 已安装”“commit 已存在”“镜像构建成功”和“当前消费者已使用修复”必须分别报告。

## 3. 代表性补丁逐项判断

分类：**缺陷修复**＝修复可定位的错误条件；**协议兼容**＝适应仍在使用的不同契约；**局部补偿**＝缓解现象但未闭合公共模型；**展示/交互**＝平台职责的修正。一个修改可以同时属于两类。

| 修改 / 依据 | 判断 | 已解决什么；应如何保留或收敛 |
| --- | --- | --- |
| `84ef722`，WGS stage 注册自锁 | 缺陷修复 | 持有 `AnalysisRun FOR UPDATE` 时再次用独立 session 摄取同一 run，会争自己的锁。改为锁前摄取、锁内重验合理；不能再把 SSH 慢作为所有卡住的解释。正常路径已修，恢复路径另见 F2。 |
| `03dc8d7` 与 `9c7fc93`，请求摘要 | 缺陷修复 + 协议兼容 | 初始 WGS 在 hash 后追加 contract version，恢复/GATK 的包裹顺序不同。消费者按版本取正确 hash 范围，并继续校验版本，是纠错而非取消安全检查。重复消费者曾漏改，后续应共用 canonical digest。 |
| `03dc8d7`、`5c29d86`，request/control/workdir | 缺陷修复 | 请求存放目录、runtime 控制目录、生信工作目录不是同一个概念。应核对各自声明的根，而非把任意路径比较放宽。脚本修复与 backend 自动恢复修复是两处，不能混算。 |
| `5c29d86`，Step1 恢复后首次 Step2 | 缺陷修复 | 有 resume action 不代表已有旧 Master。仅在确实从未 CREATE、输入及锁身份成立时走首次提交，不应硬找旧 Master 做 replacement。仅测试分支包含该提交。 |
| O，CREATE deadline 与 pre-START 恢复 | 缺陷修复 + 受限协议适配 | 复用 native 已冻结 deadline，避免第二次读时钟导致不一致；pre-START 恢复限定 WGS 初始 Master、未发送 START、原期限已过且旧 writers 已静止。不是任意超时都能自动重建。 |
| `5c29d86` 与 O，Step3 监控重连及进度 | 缺陷修复 | 只读重连不应依赖自动计算替换开关；监控状态写入不能抹掉嵌套 Master 身份和 rule counts。查询失联与计算失败需要分开。 |
| O，WGS 同步 Step2/6 dispatcher 终态 | 协议兼容，解决真实契约缺陷 | 已同步执行的阶段没有异步 worker sidecar，强求它会卡住收尾。已持锁、身份匹配的明确终态读取是合理过渡；新公共执行器不继续扩展旧兼容 reader，活跃旧消费者切换前必须确认。 |
| O，275 个已回收 Worker 的 final inventory | 真实规模问题 + 局部补偿 | 完整列表交叉验证减少逐对象云 API 往返，优于扩大超时。但目前 bulk 仅 WGS 成功释放启用，失败恢复/活跃等待仍未统一，见 F6。 |
| `cce_publish_recovery` 的旧 queued / 上代 sidecar | 局部生命周期补偿 | 严格验证当前 successor 与上一代终态后忽略退休记录，当前场景合理；没有解决所有 action 的“已派发/仍有控制权/计算已终态”含义混用。 |
| `0ba2730`，恢复后的 failed/结束时间投影 | 缺陷修复 | 合法新 prepare generation 可以重开失败投影；failed→active 清除旧结束时间。不是见到 running 就覆盖真实失败，已变 running 的历史坏时间戳也不因此全部修复。 |
| `e634ca4`，Step4 回执覆盖 Step5 | 缺陷修复 + 读侧补偿 | 写侧按同 attempt 后续 execution 因果关系阻止回退；读侧修正旧坏投影。应保留，不应改为前端猜阶段，也不能从此推断所有状态写入口已统一。 |
| `9f98617` 等，上传/下载等待 | 必要展示协议适配 | 精确 slot marker、无已开始 execution/transfer 时显示 waiting 和空条，不再显示上一步 Stage complete。没有改变调度，也不是凭空生成真实百分比。 |
| `a3c177a`，GATK transfer retry generation | 缺陷修复 + 代际适配 | 同 attempt 稳定 transfer ID 下，新 generation 的 accepted/0 与旧成功文件投影冲突。验证新代及完整 manifest 后归并，避免旧失败记录遮盖续传；不是让文件重新上传。尚未部署。 |
| WGS phase baseline、`6d11712` GATK r4 | 有依据的版本登记 | r4 与已审计 r3 的 17-rule inventory 同 blob，增加 exact release key 合理；不明版本仍 Unknown。只修 phase 分类，不能修复漏采事件、running 数量或 native 规则计数。 |
| Completed、phase summaries、silent refresh | 展示/交互缺陷修复 | 整体成功与单阶段完成区分；phase 总结不随下方筛选分页变化；旧异步响应不覆盖新页面 scope。职责在前后端，不在 native。 |
| O 顶部旧 Resume 隐藏 | 真实防误操作修复，但不闭合旧动作语义 | 旧 `/actions/resume` 会增加 attempt 并重新准备，和 `/actions/resume-stage` 不同。隐藏按钮有价值，不能当成旧 API、Rerun failed 或通用暂停/续跑已修复。 |
| E 英文统一 | 纯文案一致性 | 不改变状态、恢复、计数或生信执行。应与执行修复分开发布；不是全站国际化。用户已要求暂缓。 |

另外，精确清锁、Airflow clear、先读 stage-status 再重试、清理后重新提交、OBS 维护脚本等属于**运营恢复**。它们可以恢复指定批次，但不是公共产品缺陷已经消失的证明。新 wheel、匹配 Master 镜像及 profile 是部署修复，不能归为全部由 Airflow 实现。

## 4. 仍然存在的缺口与风险

以下 P1/P2 是本次审查建议的处理优先级，不是新增开发授权，也不是宣称当前生产已经出现所有触发条件。源码行号默认对应 L；标 O 的为运维工作树。

### F1 — P1：发布基线不是所有已验证修复的闭包

**证据**：第 2 节 Git 分叉；L 的 `frontend/src/pages/RunDetailPage.tsx:308` 仍显示旧 Resume；O 才有 `legacyResumeAvailable` 差异。L 的 `backend/app/cce_compute_dispatch.py:90` 仍将 control workdir 与生信 workdir 比较，`cce_recovery_policy.py:15,33` 仍将 monitor deadline 绑定自动恢复开关；测试分支 `5c29d86` 已修这两项。

**影响**：从 L/M 整树重建不等于保留当前生产行为；只补 phase/文案也可能把已部署的防误点或 runtime 修复覆盖掉。

**最小方向**：按已有实际挂载/selector/pin 记录，形成“路径→来源 commit/未提交 diff→文件 SHA→消费者→部署状态”清单，分别提交必要差量；不要 `git add .` 或整树覆盖。此前仅测试的修改仍需遵守其推广门禁，不为追求分支一致擅自全部上线。

### F2 — P1：恢复 Step3 注册仍可能缺少 Step2 前驱摄取

**证据**：`backend/app/main.py:2122–2165` 只对 `not resume_action_id` 做锁前 sync；`:2219–2232` 恢复分支直接登记返回。`wgs_resume_service.py:29–60` 无相应摄取，而 `wgs_stage_execution_service.py:248–264` 要求数据库中已有身份匹配的成功前驱和 receipt hash。

**触发**：node 的 Step2 已真实成功，但平台前驱行还没接收回执。恢复 DagRun 的 Step3 登记仍失败；让操作员先刷新/GET 再 clear 只是补救。

**方向**：沿 UE-04 使用已有摄取服务，仅在缺失/滞后时接收前驱，独立 session 结束后锁内重验当前身份。不能取消前驱检查，也不能凭 node task 退出直接伪造 DB success。

### F3 — P1：GATK 合法恢复 DagRun 被状态同步器拒绝

**证据**：`gatk_runtime_service.py:315,329` 创建并绑定 `analysis_id-aN-resume_...`；`gatk_airflow_sync.py:23–24` 却只接受 `analysis_id-aN`。adapter 在 `pipeline_registry_service.py:532–533` 注册，后台 `observer_airflow_sync.py:48–58` 和 `main.py:1734–1757` 的 sync-airflow 都可调用，并非死代码。

**后果**：合法 same-attempt 恢复后，对账抛 `MissingDagRunError`；不会直接停止 native 计算，但会失去该恢复 DagRun 的正确对账。当前新 WES 是正常初始提交，不能把此静态缺陷当成它已失败的证据。

**方向**：核对当前保存的 DagRun 与合法 recovery action 绑定，不靠初始名称模板做唯一判断；不放宽为任意后缀即可通过。可纳入 UE-04 对账接线的最小修复。

### F4 — P1：WGS 对账可绕过 runtime 的最终完成条件

**证据**：`diagnostics_service.py:105–145` 以 Airflow state 覆盖 run；success 只排除 failed/upstream_failed TI，空 TI 列表也可通过，然后设置 success/100%/Workflow complete。此处没有检查最新 Step6 成功回执/最新 runtime failure。对照 `gatk_airflow_sync.py:49–58,71–75` 有对应门禁，WGS 正常 finalize 在 `main.py:2333–2340` 也要求 Step6。

**限定触发**：Airflow 手工标记、skip/clear 后状态与 runtime 不一致，或拿到不完整 TI 列表时，另一个同步入口可能错误确认完成或重开失败状态。**正常 DAG 本身有 Step6 依赖；本报告没有发现证据证明当前已成功批次是假成功。**

**方向**：同一完成/重开判定由 finalize、对账和投影共用；adapter 提供其可信回执，而不是每条状态写入口再加一份判断。synthetic 覆盖不一致快照即可，不重跑已验收全链路。

### F5 — P2：queued 混用“已派发”和“仍拥有执行控制权”

**证据**：`cce_resume_dispatch.py:140–158` 派发后保留 queued；`cce_recovery_budget.py:176–178` 把同 attempt 非终态 manual action 当作阻挡；`cce_recovery_poll.py:23–26,49–56` 只处理 automatic action 的 compute terminal。`cce_publish_recovery.py:60–69` 的旧 action 豁免只解决 Step4。

**后果**：手动恢复后再次发生允许自动恢复的权威失败，仍可能被已确认派发的旧手动动作挡住。它是 fail-closed 的可用性缺陷，不是已证明会重复跑成功规则。

**方向**：沿 UE-05 分离派发结果、当前计算身份/终态、下游授权；保留历史及预算，不能全局将 queued 改 success，也不能删除互斥。

### F6 — P2：批量回收后的查询优化还没有覆盖全部消费者

**证据**：O `cce_paired_runtime.py:1248` 仅 WGS success 使用 bulk；`cce_recovery_workloads.py:183–202` 拒绝 failure/active-wait 的 bulk；`cce_recovery_inventory.py:500–506`、`cce_recovery_failure.py:89–94` 仍默认逐 Worker 查询。

**后果**：大量已 TTL 回收的 Worker 下，失败恢复/等待证明仍可能在固定 120 秒预算中耗尽查询时间。成功收尾的一次优化不等于恢复路径规模问题已解决。

**方向**：沿 UE-03 用 native 公共完整 inventory 覆盖实际消费者，保留 UID/owner、完整性、活跃对象保护和 CAS 前新鲜证明。不要通过延长 Master TTL、扩大超时或吞掉查询错误来替代证据闭环。

### F7 — P2：WGS 恢复输入没有在注册前重算原 frozen digest

**证据**：`wgs_resume_service.py:120–123` 读取原请求只核对部分身份；`:37–44` 比较文件自带的 hash 字符串与 execution；随后 `:50–60` 将 payload 重新注册并生成新摘要。GATK 的 `gatk_runtime_service.py:263–272` 会重算原 payload 摘要。

**后果边界**：如果原文件在保留 identity/hash 字符串的同时发生其他字段漂移，WGS 入口未在重登记前发现。下游 restricted gate 仍可能拒绝；本轮不能据此宣称可绕过权限或改变生信参数。

**方向**：使用与原协议版本匹配的共同 digest verifier。这是补齐已有冻结语义，不是新增一套 root 所有权/文件权限门禁。

### F8 — P2：旧 Rerun failed 的实际行为仍与用户预期容易冲突

**证据**：`RunDetailPage.tsx:309` 保留 Rerun failed，API 转入 `wgs_platform_service.py:270–297`；它和旧 resume 都 `attempt += 1`，三阶段提交重新进入 preparing_sampleinfo、清除 approval、再次提交。

**判断**：隐藏 Resume 解决了一个误点入口，但没有统一动作语义。该入口不保证“同 attempt 只续失败阶段”。这不等于 `--forceall` 或全部 FASTQ 重传，不能夸大后果。

**方向**：先明确保留能力的语义。废弃动作应从当前 capability/入口退出；若保留新 attempt 操作，则明确标注并确认。不要未经决定偷偷改成 same-attempt，也不为旧 Resume 新增兼容层。

### F9 — P2：前端仍有局部按文案/序号推断业务语义

- **进度颜色**：`frontend/src/components/RunProgressBar.tsx:54–66` 的实测分支不读 status，而靠 fail/error 文案和 percent。确定的输入组合“failed、40%、无失败英文 note/failedStep”会走 running 色；100% 也可能染成功色。应由结构化状态决定色彩，测量值不生成成功。
- **Step 编号**：`backend/app/gatk_stage_contract.py:14–22` 将 prepare 排为 1，导致 step1_upload 显示 2、step3_monitor 显示 4、step6_materialize 显示 7；`RunWorkflowTab.tsx:177–179` 直接展示该值。应区分图排序与 canonical Step1–6，prepare/finalize 可单独无业务编号，不改运行依赖。
- **实测/预估选择**：`CurrentProgressPanel.tsx:19,38`、`RunTracker.tsx:193` 对 linear model 优先，`wgs_stage_estimates.py:83–87` 无条件附加模型；与 `docs/06_FRONTEND_SPEC.md:408–409,566–567` 的实测优先描述不一致。用户已允许 Step4/6 使用估计，因此**使用估计本身不是缺陷**；应统一并明确来源优先级，避免相同数据在组件中各自裁决。尚未证明当前运行产生了该交叉组合。

这些是展示契约问题，不需要重启云端分析或修改 Snakemake。

## 5. 前后端和 runtime 分层是否合理

### 合理、应保留的部分

- Pipeline Registry 已有 adapter hooks；Run Tracker 能消费 adapter 的 progress/metadata，页面并非直接读取 Airflow/业务数据库。
- 生信依赖、CREATE/START、Worker 证据与目录写入保护归 runtime；Airflow 管项目级编排；前后端管理身份登记、状态投影、操作权限和展示。该分工总体正确。
- `attempt/generation/execution_id/request_hash/Job UID`、当前动作仲裁、原 deadline、上传租约和完整终态证据不是过度验证。即使只有一个人操作，也可能有旧任务、异步回执、重试和并发写入。
- Unknown/stale/last-confirmed 是必要状态，不能为了界面整齐统一改成 running/success；但应该有清晰来源、更新时间和下一步原因。
- GATK/WGS phase policy、release 元数据、Rules 聚合属于平台；不应迁移到 cce-pipeline 或按项目临时写死规则名。

### 当前不够合理的部分

- **状态写入权分散**：observer、sync-airflow、stage registration、finalize、recovery poll 均可影响同一 run；局部修复后另一个入口仍可能覆盖。F2/F4/F5 是具体结果，而不是单纯“文件太大”的风格评价。
- **协议重复实现**：初始/恢复的摘要、控制目录、dispatcher 证据和终态判定散落两流程及多个脚本。9c 的遗漏说明需要共同实现，不是再取消校验。
- **UI 双重投影**：后端已有 stage/status/source，前端仍存在分支推断颜色/来源；Tracker、详情、Transfers 的证据更新时间和代次不同又不够显式。native rules total 与已采集 rule rows 不一定同一统计口径，不能相除或强行改成同一值。
- **发布没有单一可复现来源**：overlay 是临时部署手段，不应成为长期唯一的真实源码；clean candidate 也未包含所有原有修复。
- **文档权威滞后**：`docs/00_PROJECT_BRIEF.md:9–13` 仍写 WGS only、GATK 为 compatibility target，与当前 AGENTS/环境边界和已启用手动 GATK 不符。应在来源收敛时一并修正，不由旧说明推翻当前批准状态。

### 关于 GATK/WGS 是否必须“完全一样”

应该统一执行身份、accepted/running/terminal/unknown、回执摄取、恢复及清理许可；不必统一所有业务 handler，也不要求 DAG task 外形完全相同。

现有方案的取舍仍合理：GATK 保留已有效的 submit + reschedule wait，WGS Step2/6 接公共后台执行器；WGS Step2 可保留薄等待包装以维持原 pool 占用，不新增跨 task 配额系统。关键是两者共用判定内核，不再各自实现控制状态机。这不要求两边生信流程同时大改。

## 6. 哪些可以长期保留，哪些应退出

| 处置 | 内容 |
| --- | --- |
| 长期保留 | 身份/摘要正确校验；单一原 deadline；正常 START handshake；真实回执；TTL100 后持久终态；代际保护；等待/恢复/最后确认进度；精确 release phase policy；规则全量摘要与分页分离。 |
| 随公共契约收敛 | 摘要实现分叉、同步 dispatcher 特例、Step4 独有 queued 解释、成功专用 bulk、读侧修复旧阶段回退、依赖时间戳猜 transfer 代次。先确认实际消费者，不直接删除活跃运行依赖。 |
| 不再扩展 | 已废弃的旧 Resume 执行 reader/新兼容分支、按批次硬编码跳过、把失败请求包装成成功、用延长超时/TTL替代正确终态读取。 |
| 不属于产品修复 | 人工 clear/退役旧锁/重提/搬 OBS 对象/删除旧目录。可以作为有界运维操作记录，不宣传为全场景自动恢复。 |

旧接口 404 才降级读取、旧 capability 响应兼容等只读展示措施，可以有明确的滚动升级用途；不能把它们与已决定废弃的旧执行路径混为一谈。也不应仅因为仓库保留未调用 helper 就判断生产仍在执行它。

## 7. 既定方案覆盖与最小下一步

统一方案文档已经覆盖主要方向，但**UE-01 的协议标记/类型候选不等于 UE-02～06 已完成**。U 当前 dirty 状态及交接显示同一 synthetic fixture 仍待 native SHA 正则问题解除；本轮未检查 native 源仓库，因此只确认平台尚未形成已通过/已提交交付物，不断言远端 native 现在仍未修。

建议依赖顺序，不新增大规模重构或测试矩阵：

1. **来源闭环（F1）**：盘点并归档实际已用补丁；把测试专属、已部署、待部署分别提交/标记。合并不能丢掉顶部 Resume 隐藏或其他 overlay，也不能顺带部署暂缓候选。
2. **UE-01/02**：完成已有公共身份/digest/执行器契约；保留 GATK 业务 handler，主要改变 WGS 同步外壳。只有直接改变的协议边界补证据。
3. **UE-03**：统一所有确实需要的 inventory/目录探测消费者，闭合 F6；不增加云 Jobs 或延长 TTL 来做验收。
4. **UE-04/05**：完成 F2 前驱摄取和 F5 控制动作生命周期；把本轮新增 F3/F4/F7 纳入已有“对账/终态/冻结请求”接线审查，不另开一套恢复系统。数据未知仍保留必要锁和配额保护。
5. **前端收尾**：待当前任务完成且按最新发布授权，归并已验文案与 phase 候选；F8/F9 单独明确产品语义并作小差量，不修改运行状态来配合界面。
6. **UE-06**：以配对制品、consumer/pin 和已有差量证据完成测试端交付记录；不把候选安装当生产全链路验收。

### 不重复验收的原则

- 本轮没有执行 pytest/npm/云 canary；静态审查不能冒充动态复现，也不需要为写报告重跑已验项目。
- 已有 Step1–7、权限、TTL、phase、恢复边界的成功证据可引用；不能把一次正常完成扩大为所有故障场景通过。
- 后续真实改动才补最小 fixture：合法 GATK resume ID；真实 Step2 成功但 DB 滞后；DAG success/runtime 未完成；manual queued 后权威失败；frozen digest 漂移；失败/活跃 inventory 查询规模。共享判定验证一次，adapter 只验改变的接线，不做流程×阶段×故障笛卡尔积。
- 界面只需改变的确定输入组合；保持 BS10610 测试边界，不在本地跑运行时测试。文档、提交 SHA 或已验证文件的归档变化本身不构成重跑生信分析的理由。

## 8. 证据索引与局限

本轮根代理与三项只读审查分别覆盖版本/集成、backend、frontend、DAG/runtime，并交叉复核了主要发现。检查采用 `git status/log/show/diff`、`rg`、带行号源码阅读；没有复制真实样本表、凭据或患者信息进入本报告。

| 证据主题 | 源码定位（默认 L，行号按本轮基线） |
| --- | --- |
| hash 的生产与消费 | `backend/app/wgs_stage_execution_service.py:59`；`backend/app/main.py:2688–2698`；`backend/app/cce_publish_recovery.py:105–116`；`scripts/cce_paired_runtime.py:319–330` |
| request/control 路径 | `scripts/cce_paired_runtime.py:301–315`；`backend/app/cce_compute_dispatch.py:84–91`；测试提交 `5c29d86` |
| Step4 不回退到旧阶段 | `backend/app/wgs_observer.py:663–692`；`backend/app/wgs_timing_service.py:141–164`；`e634ca4` |
| GATK 新代传输 | `backend/app/wgs_observer.py:1235–1303,1673–1719`；`backend/tests/test_gatk_evidence_projection.py`；`a3c177a` |
| phase 版本 | `backend/app/workflow_phases.py:24–27,227–247`；`backend/tests/test_gatk_phase_revisions.py`；`6d11712/a85cfb6` |
| 等待与前端显示 | `backend/app/gatk_workspace_service.py:13–74`；`frontend/src/components/RunCompletion.test.tsx`；`frontend/src/features/run-detail/RunWorkflowTab.tsx` |
| 进度来源互不完全一致 | `backend/app/dashboard_service.py:243–259,315–339,778–785`；adapter 投影的 stage 与另行选择的 current_airflow_task 并存，不能只凭后者诊断实际阶段。 |
| 同步阶段/最终查询兼容 | O `scripts/cce_paired_runtime.py:345–365,510–516,1169–1180,1248`；O `scripts/cce_recovery_workloads.py`；本轮 Git dirty diff |
| 既有统一实施范围 | [统一执行设计](../superpowers/specs/2026-09-28-unified-stage-execution-design.md)、[实施计划](../superpowers/plans/2026-09-28-unified-stage-execution.md)、[之前的覆盖审查](2026-09-28-wgs-p0-unified-execution-coverage.md)；以其后续收紧章节为准，不能重放早期 legacy reader 建议。 |
| 部署和测试的历史证据 | O [HANDOFF](../../HANDOFF.md) 中 06:56Z monitor、GATK r4 phase、05:50Z downstream-stage、shared Step3/4、UI defer 条目；U 的 UE-01 最新交接。 |

已记录 native `377b3cb/e5752ea/57483541` 的 selected Master/终态传输修复与当前 WGS operator 部署，**本轮没有重新审查 native 源仓库**。WES 当前冻结 generic runtime 并不随新 wheel 自动更新；已有交接尚未证明它消费了同样修复。因此不能据 WGS 恢复成功宣布 WES 或所有 adapter 已全覆盖，也不能据潜在风险直接替换正在运行的 WES。

本报告是针对近期补丁和关键调用链的审查，不是全仓库形式化证明、全故障安全认证或新一次端到端验收。未在本轮重现的静态发现均已限定条件；没有新增测试成绩、代码完成比例或生产完成结论。

## 9. 补充结构审查：检查范围与静态结果

本次追加仍使用第 2 节 L/O/U 基线，不改变任何产品文件。使用 Python 标准库 AST **读取/解析源码，不导入项目模块、不执行其初始化、不连接服务、不产生 pyc**。这是本地静态检查，不是仓库禁止在本地进行的运行时测试。

| 检查项 | 本次结果 | 不能据此证明什么 |
| --- | --- | --- |
| Python 语法与仓库声明版本 | backend 基础镜像 Python 3.11.9，Airflow 镜像 2.9.3-python3.11；用解析器 3.12.14 的 `feature_version=(3,11)` 检查 L 的 175 个非 tests Python 文件：app107、alembic27、dags15、scripts26，未发现语法错误。 | 不证明实际 node200 解释器/依赖匹配，不证明 import 成功、类型正确、命令可用或逻辑正确。 |
| 其他当前差量语法 | O 的 8 个已修改产品 Python 文件，U 的 4 个产品 Python 候选（含新 contract 模块），同样通过静态解析。 | 不证明未提交候选已验收，也不授权推广。 |
| 静态路由重复 | L 顶层 app 装饰器提取到 100 个不同的字面量 method/path 组合，没有完全相同组合的重复注册。 | 未启动 FastAPI；动态注册、参数路由覆盖/顺序和 OpenAPI 运行时生成未验收。 |
| Python 模块依赖 | 107 个 app 模块的直接顶层 import 检出 `models ↔ sample_reference_models`；计入函数内 import 后，共有 6 个循环依赖组。 | 循环依赖不等于必定 ImportError，延迟 import 也不等于依赖方向已合理。详见第 13 节。 |
| 数据库迁移声明 | 26 个 Alembic revision 声明无重复、无缺失父版本，单 head `20260915_0026`。 | 只读 revision 元数据；未执行迁移、比对生产 schema，不能保证所有 ORM 字段与已安装数据库一致。 |
| TypeScript 类型约束 | `tsconfig.json` 已启用 strict、noEmit、isolatedModules；build 是 `tsc -b && vite build`，并非完全无类型约束。 | 本地没有对应 TypeScript/Babel parser 或项目 node_modules；未安装依赖、未运行 tsc/build/test。本轮不能声称全部 TS/TSX 语法/类型检查通过。 |
| 前端构建依赖 | package.json 虽用 latest，package-lock 已固定具体版本，标准 Dockerfile 使用 npm ci；因此不能声称每次构建自动更新全部依赖。 | 离线 builder 是否与 lock 完全匹配，仍需发布记录证明；本轮不复验镜像。 |

锁文件中 Vite8.2.1 声明 Node `^20.19.0 || >=22.12.0`，而基础 Dockerfile 只写 Node22 大版本。正常匹配的当前 builder 可以满足要求，但“Node22”四个字不足以证明所有旧离线 builder 满足最低小版本。应在已有发布 manifest 中记录确切 Node/lock/image，不为这项审查升级依赖。后端 requirements 顶层已 pin，传递依赖的可复现性仍依赖已批准基础镜像。

## 10. 公共接口是否真正统一

**当前是部分统一，不是完全插件化。** 接口名字相似、放在同一个目录、或一个入口按 pipeline 分支调用两份代码，都不能算“只维护一套通用实现”。另一方面，业务差异保留在 adapter 中是合理的，不应为了消除差异再造一个万能接口。

| 公共责任 | 当前实际结构与证据 | 评价与最小收敛方向 |
| --- | --- | --- |
| adapter 注册与能力发现 | `pipeline_registry.py:51–81,190–264` 校验声明/adapter 是否存在；hooks 多为可选 `Callable[..., dict[str, Any]]`，没有完整的 capability→实现配对校验。`main.py:947–950,1826–1829` 各入口仍补查 hook。 | 注册机制有用，但还不能保证声明能力可执行。只为必要能力建立明确 Protocol/DTO 和注册校验，不要求所有 adapter 实现所有功能。 |
| workspace / run detail | `main.py:1875–1889` 为 GATK 特判，否则默认 WGS；调用 route 函数再开 session 组装，见 B4。 | 第三个 adapter 不能只新增 YAML。应由 adapter 提供 workspace projector，缺实现明确 unsupported，不能默认套 WGS。 |
| evidence / lease / estimate | GATK 调用 `wgs_observer.ingest_bound_pipeline_evidence_once`、`wgs_platform_service.release_obs_transfer_slot`、`wgs_stage_estimates`。相关入口有意设计为共享。 | 这是确实复用，不是 GATK 错用 WGS 生信流程；但公共能力借居 WGS 模块，依赖方向和变更影响不清楚。只抽取真正共用的 primitives，保留特有 handler。 |
| stage 进程执行 | `wgs_runtime_gate.py:2966–3191` 与 `gatk_runtime_gate.py:1151–1323` 各自维护锁、进程身份、sidecar、归档及后台派发；后缀分别 `.worker.json` / `.worker.state.json`。 | 公共控制还在维护两套。应按 UE-02/04 抽一个进程执行内核和 observation 契约，不重写分析/落地算法。 |
| paired gate 接口 | `cce_paired_runtime.py:246–267` 无条件 import 两 gate，再选择 pipeline，调用 `_request_path/_load_binding/_materialize_to_approved_root`。 | 是了解两端私有实现的协调器，不是薄 adapter；一个入口也承受另一 gate 的导入故障。按受信 registry 仅加载被选实现，提供窄的 resolver/handler 接口。不是已发现跨流程错执行。 |
| native 提交与交接 | `cce_paired_runtime.py:485–508` 临时替换 native `_create_job_from_path`，并理解其内部 handoff、目录锁和 journal。 | SHA pin 保证所读字节，不保证私有函数调用顺序/语义兼容。由 native 定义显式 intent/created/handoff 接口或回调，平台绑定授权及执行身份；保留现有 pins，不直接删保护。 |
| API 数据与错误 | 共享 hooks/response 多为 dict，WGS stage request 与 GATK 的 extra-field 策略不同；前端泛型是静态断言，422 数组错误未被共同解析。 | 已有 service 身份校验应保留，但 OpenAPI/TS 难表达完整约束。优先窄类型化 identity、progress、observation、error；流程特有配置仍独立校验。 |
| 前端能力与组件 | submission UI registry 检查 deployed/enabled/submit_enabled/capability；详情 tab 和若干动作仍按名称分支。 | 专用提交表单是合理差异。共享详情用 capability→组件/请求映射，角色、能力、允许状态统一组合；不要强迫 WGS/WES 配置表单完全一样。 |

统一后的责任应是：**adapter 决定业务处理与数据映射；公共服务决定执行身份、观察状态、幂等、终态及控制许可；UI 渲染结构化语义。** 流程名称不应决定公共恢复算法，但也不能让未声明支持的流程自动获得恢复/删除能力。

## 11. 新增后端组合缺陷：不是只做命名或目录整理

以下 B1–B4 是源码可证明的条件性缺口；没有本轮生产复现。它们独立于第 4 节的 F1–F9，不应全部打包进 UE 或直接上线。

### B1 — P1：GATK 初次提交在外部派发后才持久化身份

`gatk_submission_service.py:326–330` 锁 draft，`:362` 随机生成 analysis_id，`:393–405` 只 flush run/sample，`:413` 写请求文件，`:431–437` 调 Airflow，`:442–447` 才绑定 draft 并 commit。`airflow_idempotency.py:15–28` 对 409 可读回，但接受后响应丢失的 TransportError 不会闭合本地事务。

**触发/影响**：Airflow 已接收，而响应丢失或随后 DB commit 失败，数据库回滚不了外部 DagRun 和请求文件；重新确认 draft 会生成另一 ID，无法用原确定性 DagRun 名称找回上次操作。可以产生孤儿 DagRun/请求，不据此断言已经重复云端计算，后续登记门禁可能阻止执行。

**最小方向**：参照已有 WGS/CCE 恢复模式，先持久化 submission identity 与派发意图，再发请求；回复不确定时用同一身份对账。不是要求引入消息队列或全面重写提交系统。

### B2 — P1：事件 helper 会提前提交调用方事务、释放其锁

`diagnostics_service.py:82` 取得 run 的 FOR UPDATE；`:149` 调 `import_snakemake_events_jsonl`；后者 `rule_event_service.py:152–175` 对每行调用 `record_snakemake_event`，该函数在 `:53` 直接 `session.commit()`。这会连同父流程已写状态一起提交并释放原行锁；父流程返回后仍在 `diagnostics_service.py:168–182` 使用此前 authoritative_status，未重新验证原 attempt/DagRun。

**限定**：需要有非空旧格式 JSONL 被导入，并与恢复/attempt 切换交错，才出现跨执行回写风险；未检查当前 CCE 是否有该文件。helper 提前提交父事务这一调用事实是确定的。

**最小方向**：公共写入 primitive 由上层操作统一 commit，底层默认 flush；必须独立提交时显式表达事务边界，返回后重验当前身份。不能靠再加一个外围锁掩盖内部 commit。

此外，`cce_resume_dispatch.py:90–134`、`diagnostics_service.py:82,105,109` 在行锁内调用 Airflow GET/POST，网络延迟会延长同 run 控制操作的等待。它有 HTTP 时限，不应叫“无限死锁”。可用持久化 intent/冻结快照拆开 I/O，再锁内重验，不撤销最后的派发 fence。

### B3 — P1：内部 token 缺失时的鉴权没有 fail-closed

`config.py:113–114` 的 token 默认空；`main.py:265–276` 的 `require_internal_service_token` 遇空直接 return，而 `:2112` stage mutation、`:3519` event ingestion 等依赖此函数。相邻 native monitor 依赖在 `:280–284` 缺 token 会明确拒绝。

**限定**：没有读取生产 secret，不声称生产漏配或匿名可调用。在 AUTH_REQUIRED=true 且认证数据库正常、但 internal token 漏配时，中间件仍允许有合法 cookie+CSRF 的普通登录用户通过身份层；缺少独立 role 限制的内部入口不再要求服务身份。后续运行身份/执行 gate 仍然存在，不能据此推断已任意执行命令。

**方向**：内部认证未配置应拒绝运行时调用；测试通过依赖注入模拟身份，不在生产函数保留 fail-open。另需明确 `sync-airflow` 的角色：`main.py:1734–1757` 没有 operator dependency，但确实修改业务状态。统一列明只读/operator/admin/internal-service，而非仅按 GET/POST 或按钮名称判断权限。现有服务 token 映射 admin 是信任模型选择，是否收窄 scope 需另行决定，不在本报告擅自修改。

### B4 — P2：workspace 一次响应可能混合两个执行身份

`main.py:1864` 先调用自行开 session 的 `run_detail`，`:1865–1870` 再开 session 读 run；WGS/GATK workspace 用第二个 run 的 attempt 读取 stage/rules/transfer，却把第一次的 detail 放回同一响应（`wgs_workspace_service.py:40–51,164–165`；`gatk_workspace_service.py:79–93,126,135–139`）。

**触发/影响**：两次读取间切换 attempt/DagRun，会组合旧 detail 身份与新进度，虽然字段合法且 snapshot_at 很新。浏览器 route fencing 无法修复服务端已经混合的响应。

**方向**：route 只作传输入口，把详情投影抽为接受明确 run/identity 的组合服务；固定 attempt/DagRun 后组装并重验。一个 session 并不自动等于数据库快照隔离，不必为只读页面增加长写锁，应明确一致性策略。

## 12. 新增前端协作缺口

| 编号 / 判断 | 确定调用链、影响与边界 | 最小方向 |
| --- | --- | --- |
| U1 / 刷新时序缺陷 | `useSilentRefresh.ts:31–36,68` 在已有请求进行时直接 return；`RunDetailPage.tsx:267,283,291` 的 mutation 后 `await refreshDetail()` 不会排队一次新读取，也不使旧请求失效。操作成功后可能继续发布旧 snapshot，通常直到下一轮轮询才纠正；这不能单独解释数小时不动，更不是重复执行。 | 保留 single-flight，增加 mutation revision/invalidate，并合并一次后续刷新；await 的应是该次更新，不新增并行轮询。 |
| U2 / Native Rules 筛选接线缺陷 | `NativeExecutionPanel.tsx:64–67` 没有传 filter_options；`RunWorkflowTab.tsx:64–65` 从当前页取选项；`wgs_onprem_views.py:291–295` 已先过滤、截25行；SearchableSelect 只能选已有选项。页外或当前状态页未出现的样本/家系不能直接精确筛选。 | 服务端提供独立于筛选/分页的合法选项并透传已有类型；不抓取全部规则，不扩大模糊查询范围。 |
| U3 / 权限展示不一致 | Dashboard `:170–182` 的 Submit 只看能力，App `:30` 的 submit route 只给 operator；Tracker `:179–180` 和 RunDetail 若干动作也未统一 role。后端 operator gate 仍拒绝普通用户，所以是误导入口/错误体验，**不是已经发生后端越权**。 | 共用 role + capability + allowed-state 谓词；viewer 隐藏/禁用并解释，后端鉴权不能省略。 |
| U4 / capability 查询失败不能自愈 | `PlatformCapabilitiesContext.tsx:50–66` 只 mount 查询一次；503 后没有 retry/refresh，AppShell 提示等待恢复但不会重新请求。临时后端重启可能令已打开页面一直无可用提交能力，直至重新加载。 | 显式 Retry 或仅失败时有界重试，成功后停止；继续 fail-closed，不能猜测已部署能力。 |
| U5 / 错误数据契约缺口 | `api.ts:1241–1247` 支持 string/detail object，不支持 FastAPI validation 的 detail 数组，字段级原因退化成笼统422。HTTP错误仍被拒绝，不是误当成功。 | 统一安全 error envelope/数组解析，只提字段路径与说明，不把原始 input 或敏感值显示/记录出来。 |

类型方面，`requestJson<T>` 的类型断言不能证明网络 payload 符合 T，当前 adapter hooks 的宽字典也无法自动生成完整前端契约。宜先统一少量高风险 DTO，而不是为全部页面添加重复校验框架。未发现足以单列的键盘选择控件问题：现有 SearchableSelect 有 combobox/listbox、上下键、Enter/Escape；此结论只是代码阅读，不是浏览器可访问性验收。

## 13. 模块耦合与项目串联：哪些不合理，哪些必须保留

### 13.1 需要收敛的依赖

- **主 DAG 兼任 transport 库**：`bio_wgs_maintenance.py:16–19,79–80`、`bio_wgs_native_monitor.py:13` 借用主 WGS DAG 的 HTTP 函数/异常；GATK maintenance 同样借主 GATK DAG。延迟 import 已解决重复 DagBag 发现，但执行辅助 task 仍需加载主 DAG 模块。抽纯 transport 到不创建 DAG 的模块即可；没有证据表明普通 GATK 主 DAG 直接导入 WGS 主 DAG。
- **控制模块循环**：将函数内 import 计入后的依赖组有 `cce_publish_recovery/cce_recovery_budget/cce_resume_dispatch`，以及 `wgs_platform_service/wgs_test_project`、`operator_resources_service/wgs_onprem_projection/wgs_onprem_views`、`sample_reference_config/sample_reference_service/wgs_cloud_reference/wgs_file_reference`、`wgs_sampleinfo_upload/wgs_submission_service`；另有 models 两模块循环。图不含动态 import，数量不是质量评分。应根据调用责任抽纯常量、DB Base 或最小共享服务，不能靠搬 import 到函数内宣称解耦完成。
- **transport 与 retry 分类重复**：WGS/GATK 的 `_backend_json`、Step4 publish SSH、worker probe 分别处理超时与可重试错误（`bio_wgs.py:804–841`、`bio_gatk.py:35–68`、`cce_publish_dispatch.py:21–44`、`cce_worker_wait.py:18–38`）。应共用只读/幂等协调/可能派发的操作分类和错误类型；不可把 HTTP、SSH、观察期限、业务期限、自动恢复预算合并为一个大 timeout。
- **业务、进程与观察状态混在附加字典**：两个 gate 通用 worker 异常写 failed，再由 Step3 特例补 monitor_reconnect/monitoring_health（WGS `:3146–3170,522–532`；GATK `:1083–1085,117–131`）。当前有保护，但新增阶段容易漏接。公共 snapshot 应分别表达 dispatcher、业务状态、观察健康及证据身份，不把 true failed 全改 unknown。
- **模块体积不是单独缺陷**：main 的多个路由和大量服务导入、observer 承载多个 adapter，确实使改动影响难追踪；本报告只在上述真实事务/投影/依赖链上提出拆分，不按行数要求重构整个仓库。

### 13.2 不应为“统一”而抹掉的合理差异

- WGS 和 GATK 的提交表单、source/release 格式、业务 handler、参考数据及结果落地算法可以不同；公共接口统一身份与生命周期，不统一临床业务细节。
- GATK submit + reschedule wait 与 WGS 为保留 pool 的薄等待可以并存；不能因为 task 数目不同判断不兼容，也不能将两边都改成长 SSH。
- `RunStageState` 当前投影与 append-only generation 执行记录职责不同，不需为类名统一迁移历史证据。
- `ALL_DONE` 的资源释放成功不等于业务成功。两 DAG 已保留直接成功依赖（GATK `:368–375`、WGS `:1112–1119`）；lease retained 时不应停止保护。WGS observer drain、结果 finalize、破坏性 Step7 必须继续是独立动作和授权，不能变成一个 `finally` 全清理。
- 前端 GET 的有限自动重试不等于 mutation 重放；现有 API 客户端不自动重放 mutation，应保留。未知状态不默认 success、无能力不猜测开放，均符合项目安全要求。
- 单平台角色模型不等于多租户患者 ACL；没有当前需求依据引入完整多租户权限系统。内部鉴权缺失拒绝与普通按钮角色一致性则属于现有职责，不能因此推迟。

## 14. 补充后的总判断与实施边界

**语法层面暂未发现上述 Python 源文件的错误；语义和结构层面仍存在实质缺口。** Python能解析、TypeScript启用strict、单条API返回200、某批次完成，都不证明事务幂等、并发快照、公共生命周期和模块替换兼容正确。

建议将处理对象分成三组，而不是再做一次全仓大改：

1. **条件确定缺陷，单独决定最小修复**：B1提交意图持久化、B2事务所有权、B3内部身份缺失拒绝、B4一致性快照；U1–U5按影响和正在运行任务排期。它们不自动成为本轮生产操作授权，也不全部塞进既定UE任务。
2. **按原 UE 收敛的结构债务**：单一dispatcher、窄adapter接口、native显式交接、共享状态/摘要/transport分类与inventory。以真实消费者接入为完成条件，不以新增了一个“common”文件为完成。
3. **保留且不重复验收的合理结构**：workflow业务算法、身份/锁/原deadline保护、资源释放与业务完成分离、Step7独立授权、已有phase/UI成功证据。没有改变的路径只引用证据。

后续改动的最小验证应围绕新增边界：Airflow已接受但回复丢失、helper不能提交外层事务、缺内部token拒绝、attempt切换时workspace不混合、mutation发生在轮询中、capability一次失败后恢复、页外筛选与安全422。使用现有synthetic fixture或组件断言，不新增真实批次/云Jobs，不为结构整理重跑Step1–7；本次没有执行这些建议测试。

本轮额外检查了权限、事务/外部副作用、幂等、并发读取、依赖/版本、迁移链、刷新与错误恢复、分页过滤和共享能力。**未做**实际部署指纹复验、运行时import/typecheck、数据库迁移执行、负载压测、全量安全扫描、浏览器端验收或第三流程上线。因此这是有证据的结构审查和待办边界，不是“全仓已兼容/无隐藏bug”的保证。

## 15. 性能与加载故障补充：2026-09-29 07:46–07:55Z 只读检查

用户进一步指出前端卡顿、Batch Runs 加载不了、Cloud Resources 的 Heavy 显示不完整，并要求检查 Python 的逻辑、重复读取和效率，而不仅是语法。本节及后续章节补充真实请求测量、生产者/消费者调用链和算法评估。前述“未访问生产”仅描述前两轮审查；**本轮进行了限定生产只读诊断，没有实施修复或重启。**

### 15.1 实际来源与测量边界

- BS96 确认为 `server96 / chenjc`，控制根 `/data/airflow-WGS`；backend `7ac6a8e6b412` 实际组合仍为 `downstream-stage-20260929-control/compose.json`，基础源码挂载 `20260927-p0-local-84510df/backend` 加既有单文件 overlay。旧 current 链接仍指向 0912，不能代表运行源码。
- frontend `6ebebed41eba`，当前 index 引用 `index-BEj4th8A.js` / `index-D4g5ndFq.css`；读取到的 bundle 已包含 Heavy 字段级 freshness 处理，并非仅根据总体 available 隐藏占用。
- 当前 backend 的 `platform_resources_service.py`、`dashboard_service.py`、`run_service.py` SHA256 与 L 一致；timing overlay 为已记录 `edc5d8f3…`。未将 O 未提交源码误当全部生产源码。
- 请求使用运行容器内既有内部认证，只读 HTTP GET；不输出 token、完整业务响应、患者字段，不直接连接数据库。内部 API 测量不代表用户浏览器网络/渲染耗时。另从本机访问生产 gateway health 返回 200，约 0.060s。
- 浏览器工具只发现空的 Codex 浏览器，没有用户已登录的故障标签页；未捕获用户页面的 console、Network waterfall 或 React 渲染轨迹。因此**没有宣称复现/修复了用户“整页加载不了”**。已询问 Loading、空白还是错误提示以缩小差异。

| 实际 GET | HTTP | 本次服务端耗时 | 响应未压缩大小 / 数量 |
| --- | --- | --- | --- |
| `/api/health` | 200 | 0.019s | 15 bytes |
| `/api/runs?pipeline=deployed&limit=20&offset=0&sort=created_desc` | 200 | 2.707s | 84,904 bytes；20 行，总计 27 |
| `/api/dashboard/runs?pipeline=all&limit=10&offset=0` | 200 | 1.521s | 20,523 bytes；10 行，总计 25 |
| `/api/platform/resources?history_period=1h` | 200 | 0.114s | 9,176 bytes；3 个资源 |
| 同上 `24h` | 200 | 0.101s | 58,170 bytes；3 个资源 |
| 同上 `7d` | 200 | 0.194s | 54,515 bytes；3 个资源 |

这是一组有界诊断，不是 p95/压测成绩。检查前 20 分钟、至多 1500 行的 gateway/backend 日志：已匹配的 overview/tracker/resources 请求为 200，未匹配到所检索的 upstream timeout、connect failed、Traceback 等错误。日志截断、未包含用户准确故障时刻和浏览器错误，故不能排除间歇性失败。两列表总数不同也不能仅凭数量认定数据丢失，筛选语义不完全相同。

### 15.2 为什么静态语法通过远远不够

本次按“用户操作 → 请求 → service → SQL/文件/网络 → 数据投影 → 浏览器刷新”的顺序评估：调用次数、输入规模、事务占用、是否重复读相同证据、异常是否扩散、是否存在取消/截止时间、输出是否真被使用。下面 PERF-1～5 是本报告的性能发现编号；每项单列确定性和影响。未重新运行 Python 语法检查，未重跑生信或 P0 测试。

## 16. Batch Runs / Dashboard 的语义和效率问题

### PERF-1：轻量列表耦合完整 QC 计算，且每轮重复读取

**代码确定，当前测到列表 2.707s，但未做 profiler，不能把全部耗时都归给 QC。**

`main.py` 的 `/api/runs` → `run_service.list_runs:16–117` 已在数据库分页，并批量读取部分 sample/workflow/lifecycle；前端 `RunsPage.tsx:42–52` 只有一个列表 GET，**不是逐行请求详情**，也不等待 Cloud Resources。不能笼统称它“没分页”或“因为 Heavy 不可用所以无法加载”。

但 `run_service.py:97–101` → `pipeline_registry_service.py:220–228` 对页内每个 WGS 调 `wgs_sample_projection.get_wgs_batch_qc_status:99–109`：

- 每批再次查询 Sample，虽然上层已经查询页内 sample 信息，形成额外逐批查询。
- 只需要 batch QC status，却调用完整 `_read_qc:207–243`，包括全指标 judgments 和缺失计数的 variant fallback。
- QCstat 先 `read_bytes` 算 SHA 再打开解析（214–215）；manifest 同样双读（298–300）；每样本 multiQC 先解析再读字节算 SHA（319–321）。这些不按文件版本缓存，每次轮询重新进行。
- variant 计数有真实的 256 项 LRU（263–278），不能说“每次都扫描所有 variant”。但冷缓存、文件变化或超过容量产生淘汰时，仍在列表请求内完整扫描相关表；高频列表不应承担详情/证据摄取的全套计算。
- 在仅普通 WGS、当前调用分支下，列表 SQL 数约为 `8 + W`（W 为页内 WGS 数），不含认证查询；20 个 WGS 即约 28 次。此为源码计数，不是生产 SQL trace，混合/native 分支另计。
- QCstat/manifest/multiQC 的异常未在逐 run 的列表投影边界隔离；一个文件读取/解析失败可导致整页失败。NFS 延迟也不是 HTTP 客户端 timeout 可以中断的底层磁盘读取。

**最小方向**：列表读取已摄取的 batch QC 摘要；若必须读文件，按严格文件版本/发布身份复用，单次读字节同时解析与算 hash，单批失败返回明确 unavailable 而不掩盖其他行。不得为了加速返回旧 success、弱化 QC 证据来源，或直接删除 QC 展示。

### PERF-2：无产出收益的查询，以及 Tracker 的串行外部 I/O

- `qc_highlights.py:11` 的 `PIPELINE_METRICS={}` 在检查的 app 代码中没有配置写入；`19–31` 仍查询整页全部 QcMetric 并构建分组，`37` 按空配置输出空 highlights。这是可证明的无效工作，不是主观“可能重复”。明确没有启用的 metrics 应在查询前短路，不要随意重新启用废弃指标。
- `dashboard_service` 为活跃 run 构建行时调用 `progress_service.get_run_progress`；其 `:50` 调 Airflow `list_task_instances`，各行串行，耗时按实际请求累加，且异常可中止整份 Tracker。历史终态已跳过 Airflow，是应保留的优化。
- Airflow client 默认 HTTPX timeout=10，不等于整个列表的硬 10 秒截止。首个异常就返回失败，不能声称每行都等待 10 秒、固定 N×10 秒。围绕整份 service 的 SQL session 在外部 I/O 期间仍存活，可能增加数据库连接持有时间；**未观察到本次 DB pool 耗尽**。
- `rule_event_service.py:76` 的规则读取先加载该 run 全部事件，再在 Python 过滤/limit；Tracker 活跃行也用无 limit 版本。部分 workflow/lifecycle/recovery 批量查询会读页内 run 的历史 attempt/generation 再选当前。页内 run 数有限不等于展开的规则/历史成本固定；这是随单批规模增长的开销，不是全库无界扫描。

**最小方向**：用已有 observer 的权威快照投影列表，允许携带 freshness/last-confirmed；必要实时查询也应有整体预算和逐项错误隔离。不可为了取消慢请求，把 stale/unknown 改成 success。无需再新增一套 observer 或未经测量全面并发打 Airflow。

### PERF-3：客户端无截止/取消，且各模块独立重复刷新

`useSilentRefresh.ts:7–68` 确实有单组件 single-flight、路由结果隔离、隐藏页放慢、错误退避，**未发现无限请求循环**。但 `api.ts:1194–1197` 的 fetch/body 没有 timeout 或 AbortController；hook `35–36` 等旧 pending 结束：若旧 GET 长期不结束，初次 Loading 不退出，新的筛选也等旧请求。页面离开只停 timer，不取消已发 GET。这是确定的条件性卡住路径，尚未证明就是用户此次故障。

正常 WGS/all Dashboard 一轮至少有 6 个 GET：overview、tracker、intake、scanner state、resources、incomplete。它们是独立刷新器，完成后约 10 秒再发，隐藏时约 60 秒，错误 20/40/60 秒退避；资源失败不会直接阻塞 Tracker。不要把“6 个 GET”误称为同一个请求重复六次。

存在具体可收敛的冗余：

- Tracker 搜索每次键入同时改变 tracker 和 intake key，并再次请求与搜索词无关的 scanner state（`DashboardPage.tsx:74–116,144–147`）；Batch Runs 已有 300ms debounce，二者不一致。
- incomplete 每轮从 offset0 串行读完所有 100 条分页（`api.ts:1630–1638`），随草稿积累增长；概览只需摘要时不必为显示计数下载全部细节。
- 初始 overview 尚空时，GATK 视图也可能短暂启动 WGS incomplete 请求；带 pipeline 参数的 RunsPage 在 capability 尚未加载时先取 deployed、随后取指定流程。
- 各标签页/组件没有共享请求去重或结果版本缓存；新页面重新取，已离开的旧 GET 继续完成。

**最小方向**：有界且可取消的只读请求、合并 mutation 后刷新（U1）、搜索 debounce、scanner 与关键词解耦、按实际需要获取摘要。不要一开始就合并所有 Dashboard 为大接口，也不要取消失败保护或增加无限重试。

## 17. Heavy slots：本次已定位的是采集对象分类问题

### 17.1 真实观测与因果链

07:47Z `/api/platform/resources` 返回：

- `used=0, limit=25`，两字段均 fresh，快照时间 `07:46:42Z`。
- `waiting=null, mode=null`，原因均为 `master_configuration_inconsistent`；总 `available=false`。
- 这不是 25 个 Lease 消失、真实占用未知，也不是整个资源 API 失败。`used` 表示有 holder 的 reservation 数，不直接等于 Running Worker 数。

随后以已核对的 `node200=t640 / ctapa` 只读查询 Master 标签 Job，发现同时存在：

1. 正常分析 Master 带 `WGS_HEAVY_SLOT_LIMIT=25 / MODE=enforce`；
2. GATK Master 没有 WGS Heavy 配置，采集器已有明确排除逻辑；
3. `cce-evidence-e38cee634cc34548b60b578c`，UID `02140027-d048-4373-8d9f-f61761141a22`，处于 active，command 为 `/bin/sh -c sleep 600`，没有 Heavy env，却带 `app.kubernetes.io/component=snakemake-master`、`profile-id=wgs-4.2.2`。

独立生产采集器 PID58165 的代码在 `heavy_global_snapshot.py:112–114,127–130`，与 L 对应分类相同：只排除符合条件的 GATK，将其余非终态、非 suspended 对象视为活动分析 Master，缺 env 即令 waiting/mode unavailable。07:54:48Z 再读既有快照，updated_at=07:54:37Z、complete=true、无refresh_failed，仍是相同reason及fresh0/25。**证据 helper 被算入分析 Master 是本轮确认的当前触发器**；它创建于07:49:52Z，不能声称这个具体UID造成了更早07:47Z的快照，只能证明当前同类错误链。Helper 存续/回收还会使该现象间歇出现。没有把它删除或为它补假的配额配置。

### 17.2 应修的边界，不应做的兼容

这需要生产者与观测器使用显式 workload role / quota participation 契约，区分 analysis Master 与 evidence/helper。不得仅按 `cce-evidence-` 名字忽略所有对象，或把任意缺配置的真正 Master 当无事；未知参与者仍应报清晰原因。具体 native/helper 生产端变更交给对应 owner，不在本轮直接修改。

当前 API 已正确保留 fresh used/limit；读取已部署 JS 也确认它按字段判断而非 `available=false` 整体隐藏。因此“整条 Heavy 标签不见”尚不能归因于此分类问题；用户当前浏览器是否卡在首个 resources、旧缓存或渲染异常仍待截图/请求轨迹。

另一个明确 UI 缺口：Cloud 卡标题时间与 badge 使用 SFS 的 `source_updated_at/status`，却没有展示 Heavy 自己的更新时间和安全 reason。`DashboardResourcePanels.tsx:45,83–94` 允许 “SFS healthy / waiting unavailable”，但不解释为什么，容易被误认为整张资源卡坏了。应分别呈现，不用假0填 waiting，不放宽 freshness。

Heavy API 只读取 ≤64KiB 的快照，不会每次请求现场 kubectl；collector 每轮做 Lease 和 Master 两次查询（各 timeout30），再读各 attempt 的 quota snapshot，结束 sleep60。修遥测不是再次清理 quota holder、重启 Master 或修改 Airflow pool 的理由。

## 18. SFS I/O 三个范围的实际加载与算法

### 18.1 采集、返回点距、横轴刻度、刷新是四个不同概念

三个按钮共用同一份历史，并非三个独立 Cloud Eye 采集器。`collect_sfs_cloud_eye.py:46–95` 每轮串行查询7指标、近10分钟、`period=1/filter=average`，每指标只拿最新一点，然后默认 sleep60；平台 collector 也约60秒读 spool。实际间隔还包含查询耗时与源延迟，不能把 period1 解释成 UI 每秒有一个点。

| 范围 | X轴刻度 | API策略 | 本次真实响应 |
| --- | --- | --- | --- |
| 1H | 15分钟，5 ticks | 限窗后保留原点，最多600 | 59点，06:45–07:44Z |
| 24H | 6小时，5 ticks | 超600则等索引抽600个原点 | 600点，09-28 12:00–09-29 07:44Z |
| 7D | 1天，8 ticks | 同样最多600个原点 | 600点，09-23 00:00–09-29 07:44Z |

因此**1H 通常更密，7D 更稀，但不是固定 1min/5min/30min 的分桶聚合**。如完整窗口内一分钟一条，24H/7D 抽样后理论平均约2.4/16.8分钟；不能把理论数当此次严格点距。本次24H和7D实际跨度也因刻度对齐短于完整窗口。

前端只请求选中的范围，切时段不会同时请求三份或触发 Cloud Eye；切节点不发新资源请求。三个范围的浏览器刷新目前都约10秒一次，并不是7D自动降低刷新频率。

### 18.2 PERF-4：限制响应点数不等于避免重复计算

`platform_resources_service.py:96–123,148–168` 每个 GET 先加载完整 ORM 行（SFS最多10,080点JSON，node历史也被加载），Python重做时间解析、排序和过滤，最后才抽600点。每次还读取Heavy与BSS文件；BSS reader接受的文件上限为8MB，不代表当前实际文件有8MB。

源通常一分钟更新一次，但浏览器每10秒重新传、解JSON、重画相同历史。现有 `memo/useMemo` 有效避免**无关 Tracker 更新**造成重算，不能避免每份新响应的 history 引用变化。nginx gzip 减少传输，不是查询/投影缓存。

**方向**：复用按资源版本+范围生成的有界投影，浏览器按采集节奏刷新或利用版本条件返回；共享 current/Heavy 与历史可分刷新职责，不强制新增服务。此次资源 API 仅0.10–0.19s，未证明它是当前整页卡顿主因，不以潜在成本宣称已发生严重性能事故。

### 18.3 PERF-5：时间序列存在语义不准确的条件

- **等索引抽点不是平均或保峰**：短暂尖峰可被丢弃；前端只在null值断线，不会因长时间没有采集点断线（组件133–141），因此会跨采集空洞连线。这张图只能代表抽样趋势，不能直接用于峰值验收。
- **时窗锚定最后样本而非现在**：后端 `:162` 与前端 `chartWindow:146–152` 向上对齐下一tick；采集停了，图的窗口也不随当前时间移动。1H/24H/7D右侧可能分别有最多15min/6h/24h未来空白；“最新1H”真实已采历史可能只有约45–60min。UTC存储、上海时间显示不等于tick按上海午夜对齐。
- **一个点混用多个采样时刻**：Cloud Eye 各指标独立取最新点，整点时间却取各指标时间的max（脚本83–94），丢失字段时间。较新的容量值可能令较旧 read/write 看起来新鲜，计算的 read+write也未必同一时间桶。
- **云 spool 摄取缺少单调性保护**：`platform_metrics_collector_cli.py:143–169` 每轮upsert，不像 node分支跳过旧/相同时间。`platform_resources_service.py:48–55` 只对最后一个字符串timestamp去重：旧spool可回退current，交替timestamp可能重复；同timestamp更正只更新current、不更正末历史点。10,080是点数上限，也不是精确七天时间保留策略。

**建议语义（待实施决策，不是已改）**：保留一套源采集；1H可用1分钟桶，24H可用5分钟桶，7D可用30分钟桶（完整窗口约60/288/336点），明确avg与max、缺点不补0；以服务器now确定rolling window，横轴刻度独立排版；字段对齐/保留真实时间，窗口缺采断线。若只需趋势也可保留现有≤600原点，但必须标注“抽样趋势、截至最后观测”，不能称平均/峰值。不为UI再新增三套collector或更改云端分析。

## 19. 本轮结论、优先级与最小验证

1. **已定位的当前问题**：Heavy collector把 evidence helper当analysis Master，导致 waiting/mode不可用；应修共享工作负载分类与可观测提示，不做单批次兜底。
2. **尚未复现的用户症状**：Batch Runs这次200/2.707s，服务端有确定的重复QC工作和单文件拖垮全页路径；客户端也有挂起GET阻塞后续请求的条件。需用户实际失败请求/console才能把其中某条定为这次“加载不了”的根因，不能宣布恢复正常。
3. **确定的性能/逻辑债务**：不产出结果的QC查询、N+1样本查询、QC双读与完整计算进入列表、Tracker串行外部查询、搜索触发无关scanner读取、资源同版本历史重复投影。
4. **确定的时间序列语义债务**：采样/刷新/tick混淆、抽点漏峰、缺采连线、混合指标时间与旧spool回退。不是Python语法检查能覆盖的问题。

后续只围绕改变的边界验证：helper与真实Master混合清单、单run QC不可读仍能返回其他行、同文件版本重复列表不再全算、挂起GET可取消/新筛选不无限等待、同资源版本历史复用、三个时间窗/缺口/旧timestamp的synthetic例子。配合一次授权环境中的实际请求耗时和浏览器错误复核即可；不重复Step1–7、TTL或生信全流程验收，不为报告新增云Job。

本轮仅记录诊断和修复方向；没有更改前后端、collector、quota、监控、批次、数据库或发布。采集器分类根因可由对应owner按既定范围处理，不能借此将全仓效率优化都塞入P0/UE迭代。
