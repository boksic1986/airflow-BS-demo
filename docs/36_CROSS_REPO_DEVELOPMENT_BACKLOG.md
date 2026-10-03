# 跨仓库开发与运维待办索引

## 0. 最新状态覆盖历史快照（2026-10-03，Asia/Shanghai）

- `W423-DTEST1-DOWNSTREAM-20261003` 已完成：`WGS_20261002_095408_323D3F` / `20260927D-test1` / attempt1 的 Step1–6、结果落地及 Airflow/public/workspace success 已有终验记录。自动监控已按人类要求停止，未重建；Step7 skipped，无后续恢复或自动清理待办。依据 [CURRENT_STATE 最新完成记录](../CURRENT_STATE.md) 与 [HANDOFF 2026-10-03 20:28 最终交接](../HANDOFF.md)，本次仅整理既有证据，未新做运行时检查。
- 下方 `W423-A468E9-HOURLY-20261002` 是 **历史已取代（superseded）** 的 2026-10-02 快照。后续运行和最终范围以 323D3F 完成卡为准；旧失败、回执、once 和授权审计保持，不按旧“唯一活动运行”描述重建监控或重放动作。
- Airflow 唯一产品 Git writer 当前承接 `GIT-AF-3TARGET-20261003`：负责将已完成的代码/文档普通同步至 main、production、test，核对远端 SHA 后按精确保护清单清理无用分支/worktree。Git 整合仍以最新状态文件为准；当前没有监控任务、产品新需求开发或生产部署。详见 [本轮整合记录](reviews/2026-10-03-repository-integration-and-cleanup.md)。
- native owner 报告 main 已普通 push/readback 至 `96278362dae9fc412a87906f267efd13ec2c80c1`，包含已完成 `e0202c5` 源码与文档；这是 owner 报告的 Git 收口，未安装或部署运行时。旧 `NATIVE-MAIN-CONVERGENCE` 源码待核卡由此取代；当前安装/消费者身份不能由该 Git SHA 推断。出处为 [owner 报告汇总](reviews/2026-10-03-repository-integration-and-cleanup.md#results)。
- QC 的 **WGS 4.2.x family 合同** 已记录，旧每 patch 单独注册设计已被用户决定取代；消费者实现/验收仍 pending。Submit Step2 简化复核需求已记录，仍 planned/pending；本轮不开发。见 [QC family 合同](2026-09-18-wgs-qc-two-source-contract.md) 与 [Step2 需求](06_FRONTEND_SPEC.md#submit-run-step2-compact-review-2026-10-03-planned)。merge prepare、QC2、CRAM、LIMS/delivery、options 与 English-copy 的延期/暂停边界继续有效。

> 以下第1–5节保留 gov `e1fe6cd` 的 2026-10-02 历史快照。整理时间：2026-10-02（Asia/Shanghai）；表内源状态来自各 owner 当时已提供的快照，实际观察时间以引用记录为准。本文是 airflow-demo 的导航与优先级建议，不取代各源仓库契约、发布记录或运行证据，也不授权开发、测试、远端操作或发布。最新已完成状态以上方第0节及当前状态文件为准。

## 1. 历史状态口径与核查基线（2026-10-02）

- 本索引历史核查基线：airflow-demo `51a2c941e4ede10bdf68b14fa10da71ca464a212`。状态摘要所有者提交 `3e7d3b5776732ac03713c58a3993e93b16f47b38` 仅增加状态沟通说明；它不是产品代码变更或本索引的技术证据。
- 独立文档工作分支：`jiucheng/docs/GOV-BACKLOG-20261002`。汇总只读快照，不表示各源仓库已经同步到该提交。
- “已完成”须有对应源仓库、提交/版本及适用验收证据；“候选”不等于已批准任务；“延期/待决策”不得因排序自动解冻；“历史待核查”不能直接登记为当前 bug。
- 当前环境和源代码证据优先于旧计划与历史未勾选项。需要远端或生产证据时，按 `docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md` 重新核验；本索引不替代该门禁。
- 本文中的 P0 是运行保障事项，不是功能开发等级。排序仅供协调，不构成范围、资源、测试、数据变更或部署授权。

## 2. 历史推进建议（2026-10-02；不是当前活动任务）

| 条目与排序理由 | 建议 owner / 协作者（接受后指定唯一执行人） | 实现 / 验收 / 部署状态 | 依赖或用户决策 | 证据与下一步 |
|---|---|---|---|---|
| 历史已取代 `W423-A468E9-HOURLY-20261002`：当时唯一运行保障事项 | Airflow owner `01a0e728-4c99-71d0-87e9-987b311022c9`；当时仅该运行 | 历史实现：Step1成功；Step2 deadline-wrapper平台修复候选 `1c6b2742a05daedebe7628370495fe201876b800` 已经协调者及独立只读源码审核，无阻断，source ready。历史验收：既有真实BS10610 RED repro、GREEN19、1 existing-intent skip、negative 4通过；复用既有证据、未重复跑。原handoff未确认，Master已回收，Job/Pod/锁由owner直接取证；普通resume-stage不处理该initial-abort状态。当时部署：未合并、未部署、未恢复 | 历史范围固定于 `WGS_20261001_210659_A468E9` / `20260927D-test1` attempt1。当时无重传/重提/gen2/清锁/删除/改旧deadline；单独native initial-abort调解方案当时仍须人类新增授权。Step3–6当时未开始。该条已由第0节后续完成状态取代 | [历史运行交接](../HANDOFF.md)。修复细节/证据见 owner worktree `docs/reviews/2026-10-02-wgs-a468e9-step2-deadline.md`；source/status commit `7c826cd803edb39a368f8e3e33f984e2eab27430` 仅为文档状态。当时状态来自owner/协调者报告，不重放旧小时监控 |
| P1 候选 `BACKEND-PHASE-FENCE`：防止已批准阶段回退 | airflow-demo Backend owner，待协调者确认唯一执行人 | 实现：曾观察到风险，修复状态未重核；验收：回归未验证；部署：未授权/未知 | 先评估风险路径是否仍可触发；不得通过活动运行的有副作用查询来复现 | 入口 [`_post_prepare_submission_phase`](../backend/app/main.py)。若仍成立，独立任务加阶段单调性回归测试，先核对其余影响再排期 |
| 历史已取代 `NATIVE-MAIN-CONVERGENCE`：避免源码/安装来源分叉 | WGS/native runtime owner `019f9d79-be3f-7701-af33-3595d72bbfac` | 2026-10-02历史实现：开发分支 `jiucheng/cce-stage-execution-089` HEAD `1f5e1e0`/0.8.9；本地`main`=`417de597`且不含`1f5`。当时远端main尚未核对；0.8.9安装验收已有证据。2026-10-03源码普通同步见第0节 | 保留旧源码/安装区别；当前绑定须新鲜核验，不能据旧本地main重复收口源码或重建安装 | 源仓库路径 `/mnt/biodevrwbi/33.chenjiucheng/project/wgs-cloud-platform/projects/huawei-cloud-runtime`；见[Group consumer audit](releases/2026-10-01-w423-group-test-consumer-audit.md)。不得据本地main推断生产缺包，也不得因此重建/发布镜像或wheel |
| P1延期 `QC2-01..03`：需先冻结适用来源，避免错配指标 | airflow-demo Backend/QC projection owner，随后Frontend；WGS pipeline owner提供原始来源/适用性合同；QA做获批验收 | 实现：合同/任务设计已有，消费者实现状态待核；验收：延期；部署：无授权 | QCstat.tsv是常规QC来源；罕见病适用样本的multi.QCstat.tsv为补充来源；来源/适用性遵循最新4.2.x family合同，当前不解冻 | [QC2来源合同](2026-09-18-wgs-qc-two-source-contract.md)及历史`QC2-01..03`卡；owner核现状和输入合同后再提议排期 |
| P1延期 WGS merge/公共 prepare 异步接入：新能力进度 | WGS pipeline owner提供原生merge合同/进度；平台接口owner待协调者指派；Local/SGE/CCE分工需讨论 | 实现：现有FASTQ合成本身已实现；新原生merge进度观察及公共prepare异步接入增量延期；验收/部署：延期，未授权 | 仅用户重新开启后讨论；不把延期异步增量误报成合成逻辑缺失或全面重写 | [联合发布状态](releases/2026-10-01-wgs423-airflow-joint-release.md)；保持延期，先讨论执行目标分工 |
| P2 候选 `W423-02` CRAM布局/索引：与QC2/LIMS独立 | WGS producer owner；runtime consumer owner核对合同 | 实现：新producer布局未由快照证明；验收/部署：未授权 | 给出布局兼容性和消费端证据后单独排卡 | [联合发布状态](releases/2026-10-01-wgs423-airflow-joint-release.md)、[CRAM边界设计](superpowers/specs/2026-09-30-wgs423-upgrade-integration-design.md#7-cram-布局与发布边界) |
| P2待业务决策 `W423-05` LIMS接收/回传：需避免误判真实送达 | 用户业务owner + WGS producer owner，平台集成owner待确认 | 实现/验收：当前状态未证实；部署：默认关闭 | 用户确认字段、成功语义和失败处理后再设计 | [联合发布状态](releases/2026-10-01-wgs423-airflow-joint-release.md)、[LIMS设计](superpowers/specs/2026-09-30-wgs423-upgrade-integration-design.md#6-人工审核与-lims-回传合同) |
| P2候选 options展示/启用：避免未审阅能力被意外开启 | WGS/native + platform owner，执行owner待指派 | 实现：保持未启用；验收/部署：未授权 | 先提供候选内容、兼容性与风险供审阅 | [联合发布状态](releases/2026-10-01-wgs423-airflow-joint-release.md)；该索引不授权启用 |
| P2候选 preview/inventory：需先知道源内容 | WGS/native owner | 实现/验收/部署：待inventory决定 | 先做只读源清单和来源核对 | 待源内容清单；不得从旧未勾选项推断当前缺失 |

开发排序是建议。一个条目只有在明确 owner、范围、验收和对应授权后才成为可执行任务；部署另需独立门禁和审批。

## 3. 历史源仓库快照与技术证据路由（2026-10-02）

| 源 | 快照身份 | 主要证据 |
|---|---|---|
| airflow-demo / Airflow platform | 本索引历史基线 `51a2c94`；历史产品发布 `fd855934`。Airflow owner当时报告文档收口 `c41450a26105b4f81518741fe8f926c60b26e0a7` 已正常快进同步 main/production，服务镜像、门禁及当轮产品代码无变化 | [STEP7 发布验收](releases/2026-10-02-step7-run-pages-fix.md)、[DNAscope panel配置](releases/2026-10-02-wgs-dnascope-panel.md)、历史A468E9及后续323D3F实况见[HANDOFF](../HANDOFF.md) |
| WGS 4.2.3 | `/mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0`；`dev_CJC_4.2.3_cloud` 历史HEAD `3f986821172e5fbd5f5abd1213baea64c6b976f9`，release `wgs-4.2.3-3f98682` | [DNAscope配置/注册](releases/2026-10-02-wgs-dnascope-panel.md)、[WGS423联合状态](releases/2026-10-01-wgs423-airflow-joint-release.md)；后续Git收口见[整合记录](reviews/2026-10-03-repository-integration-and-cleanup.md#results) |
| native/cloud runtime | `/mnt/biodevrwbi/33.chenjiucheng/project/wgs-cloud-platform/projects/huawei-cloud-runtime`；历史`jiucheng/cce-stage-execution-089` @ `1f5e1e0`，version0.8.9；历史本地`main` @ `417de597` | [native consumer audit与版本对比](releases/2026-10-01-w423-group-test-consumer-audit.md)、[UNIFIED089验收](releases/2026-10-01-unified-native089-candidate.md)；当时远端main状态未知，已被第0节owner源码收口报告取代，安装状态未由该报告重验 |

这些均为带观察日期的 owner/status 快照。源 HEAD、安装内容和实际运行绑定在开发前仍需新鲜核验；不要将不同日期的提交、安装回执或挂载视为同一状态。

## 4. 历史已完成/已发布，避免重复开启

- 2026-10-02历史：Airflow `6C78D5` 精确范围的线上记录恢复/重提、profile 权限修复和 prepare 接受已完成；原 `5035B0` 和其他运行均受保护。A468E9 当时是其后唯一活动运行；现已由第0节后续完成卡取代。
- WGS-PANEL 配置/发布、native0.8.9安装验收、profile权限 `2775/0664/0775` 修复和 readback 已有对应记录；不要重复构建、安装或变更。
- STEP7-PERF 与 Batch Runs/Detail 页面修复及 BS96 发布验收已完成；不得因 backlog 汇总重新打开。
- WGS Group Master 相关完成项、UNIFIED089、UE01–UE06、2775权限恢复均按既有记录保持关闭。
- 2026-10-01/02 的 WGS423 联合发布材料明确：merge进度观察/公共prepare异步接入、QC2、新CRAM布局及LIMS等仍按各自延期/待决策状态处理；现有FASTQ合成本身已实现，不能把延期增量表述为合成能力缺失。
- A468E9 标准提交到执行审批过程见 [HANDOFF 历史运行记录](../HANDOFF.md)；这不是在线sampleinfo编辑、文件同步或pending台账编辑的验收。
- 已部署native0.8.9/WGS423最小验收见[UNIFIED089记录](releases/2026-10-01-unified-native089-candidate.md)和[DNAscope配置记录](releases/2026-10-02-wgs-dnascope-panel.md)；Step7与Batch Runs/Detail完成见[发布验收](releases/2026-10-02-step7-run-pages-fix.md)，Group展示与延期边界见[consumer audit](releases/2026-10-01-w423-group-test-consumer-audit.md)。

## 5. 旧未勾选项：仅待 owner 核实，不是活动 bug

历史 `TASKS.md` 和可靠性计划里的未勾选条目年代、适用版本和当前实现状态不一。以下仅在 owner 对照当前源码/部署后登记状态，不自动转成开放卡片：

- 生命周期 pause/recovery、云端清理与平台删除能力（历史 `TASKS.md` 约1006–1019、1688–1710行附近）；
- 三阶段等待与60秒上限；
- Registry展示与冻结历史；
- 资源过滤、容量/AOM观测；
- 日志搜索、预览刷新；
- 受控CNV lazy-load；
- 2026-09-22 两步提交、可编辑sampleinfo、prepare路径pending台账编辑设计与 `SUBMIT2-01..03` 历史卡：当前实现覆盖尚未逐项核对，不能转写为“未实现”或待开发承诺；pending目录边界及移出台账/允许重新生成语义可作为owner核查输入。见[设计稿](2026-09-22-wgs-two-step-editable-sampleinfo-design.md)和[TASKS](../TASKS.md)；本轮Step2简化需求另见第0节，仍pending；
- Local/SGE/GATK的历史待办或TTL Step5/6勾选项。

不得据旧勾选项声称当前功能缺失。先由相关 owner 写出当前版本、证据、影响和建议，再由协调者决定是否建任务。

## 6. 当前任务/线程路由（2026-10-03）

| 责任 | 当前已知线程 | 说明 |
|---|---|---|
| 协调与方向 | `019fa8d1-0d81-7e92-abee-8154dd1cf0a7` | 范围、顺序、跨仓库整合和评审；不是默认远端执行者 |
| Backlog/状态文档 owner | `01a0b254-07b5-7352-99aa-871b117459ad` | 仅在用户指定的文档整理授权内维护状态索引 |
| Airflow | `01a0e728-4c99-71d0-87e9-987b311022c9` | 平台后端/前端/DAG集成owner；当前 `GIT-AF-3TARGET-20261003` 唯一产品Git writer，负责普通三目标源码/文档同步与精确清理，没有活动运行监控、开发或部署授权 |
| WGS pipeline | `01a09149-ad9d-7e92-b98a-16d9cae075e2` | WGS pipeline源码和候选设计；需重新确认具体实现授权 |
| WGS cloud/native | `019f9d79-be3f-7701-af33-3595d72bbfac` | CCE/native runtime源码与来源收敛；已报告main普通push至96278362，无本轮安装或部署 |
| Frontend / QA / Infra | 本快照未确认固定owner thread | 由协调者为具体任务指派，不推定已承接 |

线程标识和状态可能变化；开始行动前重新核验其当前负责人及消息。状态报告可以由授权 owner 执行，但不因此获得源代码、远端或部署写权限。详见[职责路由](15_MULTI_AGENT_BOUNDARIES.md)。

## 7. 更新协议

每项只维护一个索引状态和一个源仓库/权威记录链接。出现提交、验收、失败、漂移、用户决策或owner变化时更新该卡与 `CURRENT_STATE.md`、`TASKS.md`、`HANDOFF.md`；无变化时保持安静，不重复广播。提交文档快照时注明source HEAD、观察日期、证据来源、未知项以及未执行的测试/远端操作。已完成监控不得由历史快照自动重建。
