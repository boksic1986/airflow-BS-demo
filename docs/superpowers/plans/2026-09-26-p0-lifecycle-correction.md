# P0 生命周期修订实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 各仓库制品保持原 owner 分工，不自行构建替代镜像。

**Goal:** 修复初始登记与身份依赖，统一正常运行、恢复、暂停、云端清理和同名重建；业务输出保持755/644。

**Architecture:** 复用现有 Registry/adapter、受限 runner、原生锁与 journal；共享生命周期协议，不重写生信流程，不新增常驻重试系统。

**Tech Stack:** Python、FastAPI/SQLAlchemy、Airflow、cce-pipeline、Snakemake Kubernetes plugin、现有 React 操作区。

**Spec:** [P0 当前修订 R1–R7](../specs/2026-09-17-wgs-gatk-cce-connection-recovery-design.md)，[运行控制](../specs/2026-09-18-run-control.md)，[锁与TTL](../../46_JOB_TTL_CROSS_MASTER_RECOVERY_DESIGN.md)。

**Status:** 2026-09-26 仅文档交付。T1 的文档部分完成；T2–T5 未开始，不以历史 Task1–6 的组件通过替代本计划验收。

### 后续用户授权的首个实施切片（2026-09-26）

先修复审计 A1–A4 与相关新业务输出755/644，再成套部署 BS10610 测试。
本切片只取 T1 必要内部契约、T2 和既有恢复的兼容性验证，再执行 T5 中匹配的
制品/测试发布部分；不等待或实现 T4 的暂停删除功能，也不新增其 API/DB/UI。
保持原 Step1–6、冻结输入和恢复预算，原仓库 owner 负责必要制品。只运行受影响
的正常及恢复 synthetic 路径，不重复无关全套测试；生产和真实批次未授权。
这更新本计划先前“本轮仅文档”的执行权限，不代表源码或部署已经完成。

本切片最新进度：A1–A4 源码及匹配的远端 synthetic 验收完成；native33项、
平台WGS/GATK正常/恢复4项及最终受影响GATK3项通过，复用未变证据。
一次联合审查的3项Important问题全部关闭。原owner制作独立候选
`0.8.7+p0.dev1`（native90abacd）、新WGS Master及r3；测试部署尚未完成。
这不勾选完整T1–T5：T4和更广生命周期验证仍不在本切片范围。

## 全局约束与基线

- Airflow 工作分支 `jiucheng/test/wgs422-p0-integration-20260926`，文档前HEAD b17e1b6，功能954045a；保留生产修复和等待进度展示。
- Native候选 dcc1698/0.8.6，功能ae90b65；plugin功能5ffcb07/0.6.4+bs8.dev2。执行时先核对仓库当前状态，不覆盖其他owner工作。
- 本轮文档不授权代码、远端测试、安装、推送镜像、生产部署或真实批次操作。
- 后续验证仅BS10610隔离环境，先核对真实主机/挂载/执行身份；不在本地运行测试。不复制真实样本进Git。
- 不变：Step1–6顺序、Snakemake规则和依赖、既有并发/配额、同attempt断点、原自动恢复白名单与两次60/180秒预算。
- 本地数据由用户处理。Cloud cleanup、平台删除、人工新提交是三个明确动作；不引入本地迁移续跑功能。
- 无新流程上线、无Local/SGE控制实现；WGS/GATK参数化加第三个synthetic adapter验扩展性。
- 制品交给原Workflow/Infra owner按SOP；源代码修正不等于已发布，旧制品证据不自动覆盖新字节。

## 审查重点

1. 正常新批次不依赖测试fixture预写未来Step2 ID；原入口无需人工停顿。
2. 同名/同路径新运行不被旧锁阻止，迟到旧清理却仍不能删除新资源。
3. 暂停、自动恢复、部分删除并发时无重复派发，状态不伪成功。
4. TTL后普通CLI及平台均能继续下游，不只修其中一条路径。
5. 755/644在实际执行身份、原子替换和Pod挂载后保持；私有控制文件例外不得扩散到结果。

## T1 — 固定接口与状态契约（Coordinator / Backend / Workflow）

**文档：** 原P0修订R1–R7、运行控制、TTL配套、本计划及进度交接。
**代码落点（后续）：** 既有 `PipelineAdapter`、原生锁/当前执行解析、独立控制操作模型；不新增通用工作流引擎。
**Consumes:** 独立审计A1–A4及用户确认的本地保护、同名重建、755/644要求。
**Produces:** R2身份表、R3锁语义、R4操作语义、运行控制API和持久化契约。

- [x] 更新原设计并明确被替代的旧约束，保留历史验收范围。
- [x] 固定动态登记与静态部署分离、稳定owner与阶段ID分离、查询不取写锁。
- [ ] 实现前将适用的版本化内部类型/锁序列化契约同步到docs08；新控制表/API分别同步docs04/05，并通过字段一致性审查。
- [ ] Registry增加控制能力钩子，业务接口根据adapter而非pipeline名称选择；声明不支持的目标不得出现可执行控制按钮。

**验收：** 状态/身份表无循环依赖；第三个synthetic adapter可提供同一契约，不修改共用层流程名分支。接口设计不能仅用“后续决定”占位。

## T2 — 自动登记、正常链路与权限（Workflow / Backend）

**Files:** 平台既有 `scripts/cce_paired_runtime.py`及WGS/GATK gate；native `cce_writer_guard.py`、`cce_batch_runtime.py`、`shared_permissions.py`及相关生成端。
**Consumes:** T1身份/资源/权限契约及已成功prepare的冻结输入。
**Produces:** 幂等登记、稳定初始owner、统一当前执行解析；CLI/平台均可完整走正常阶段。

- [ ] 扩展现有 `scripts/tests/test_p02_selected_monitor.py` 的正常路径案例：通过真实登记边界先Step1持锁，再生成Step2 ID，禁止fixture中途改policy来帮助通过。
- [ ] 在BS10610只运行该受影响案例记录缺口；实现每运行动态登记和当前执行解析，移除全局批次binding依赖。
- [ ] Step2条件绑定UID；初始与恢复view传播同一稳定运行身份，操作ID仅用于操作幂等与证据核对。
- [ ] 普通CLI状态查询不申请写权限；写操作解析当前owner并与平台互斥。两入口均使用持久终态处理TTL后的Step3–6。
- [ ] 在新生成业务产物边界统一755/644和非root owner；私有spool隔离。去除强制业务setgid/组写及重复递归权限归一化，不修改历史树。
- [ ] 同一正常案例加入TTL后Step4/5/6和模式/实际读写断言；受影响测试通过后提交源码及契约文档。

**最小验收：** 正常Step1–6无人工策略修改、无第二次prepare、冻结配置不变；平台和CLI读取同一当前Master；TTL后不误失败。业务结果755/644、凭据仍私有、历史哨兵权限不变。

## T3 — 将恢复接入同一生命周期（Workflow / Airflow / Backend）

**Files:** 既有 `cce_recovery_*` 模块、native恢复入口、plugin源头错误/终态生产者；仅修改新契约实际影响处。
**Consumes:** T2登记/当前执行与T1操作身份；原错误分类、预算及终态证据。
**Produces:** 有界恢复和一致状态投影，不增加第二套分类/重试服务。

- [ ] 参数化现有错误案例，复用已通过且未变的producer断言；补正常登记到恢复的连接断点。
- [ ] 验证0918A创建断线、0919B准入超时、存储RPC、配额只读失败；拒绝权限/业务/混合错误及仅BackoffLimitExceeded。
- [ ] 创建/发布响应丢失查询同一对象和动作；Master活跃只接回，不替换；恢复推进计算generation而非analysis/attempt。
- [ ] 控制进程重启、重复点击、旧回调使用原journal/预算/截止时间；确认错误不会在runtime和Airflow重复获得预算。
- [ ] 上传/下载退出后的人工续传保留checkpoint；缺失输入报告差异，不自动修改样本或伪造完成凭据。
- [ ] 运行受影响参数化集合一次；若仅fixture修正则只重跑失败节点。更新docs07/08及源码进度后提交。

**最小验收：** 一次可恢复故障只产生一次替代执行，配置/成功输出保持；未知结果不盲重放；非白名单显示正确失败或待确认。

## T4 — 暂停、云端清理与同名重建（Backend / Workflow / Airflow / Frontend）

**Files:** 原运行控制设计指定的现有API/Registry/model、受限runner、拟建 `bio_run_control` 控制DAG及现有run详情操作区。独立操作表不随AnalysisRun级联删除。
**Consumes:** T1控制协议、T2 owner解析、T3恢复仲裁；云端资源的精确归属清单。
**Produces:** pause/resume/cleanup/delete操作记录及回执、清理后资源重用、明确UI状态。

- [ ] 按运行控制设计实现preview/confirm/status/retry，数据迁移只新增必要操作记录与约束，不删除旧表。
- [ ] 仲裁覆盖各attempt、自动恢复、Step7和普通派发；停止先持久化栅栏，控制端重启接回原操作。
- [ ] 分阶段停止/等待并验证静止才paused；继续分析保持原attempt，未完成rule可重做，不恢复进程内存。
- [ ] cleanup仅清理已确认云端项目资源；delete额外明确处理平台关联。成功Step7和失败清理共享执行器但保留各自前提。
- [ ] 清理先记录意图再逐项执行，响应丢失核对原UID/版本；失败保留残留和下一步，不提前删除支撑修复的业务记录。
- [ ] 清理成功退休精确旧资源占用/兼容guard，保留非阻塞审计；新analysis可使用同名云路径，旧回调不能影响它。
- [ ] scanner删除抑制保留，但明确的手动新提交允许重建；本地目标仍存在则不覆盖，本地腾空由用户负责。
- [ ] 验证暂停/恢复竞争、部分清理重入、云清理成功后DB失败、同名新建和旧动作重放；更新docs04/05/06/07/08与源码共同提交。

**最小验收：** 旧运行已静止且授权范围清理完，新提交不需手删锁；原本地文件及共享输入保持不变。部分成功不显示全部完成。

## T5 — 有限集成与发布交接（QA / Infra / 各仓库原owner）

**Consumes:** T2–T4精确源码提交与各自受影响验收；原生产修复和已有SOP。
**Produces:** 测试分支完整来源记录、最简验收和待发布/已发布的准确状态。

- [ ] 仅按下表检查增量场景缺口，不把各任务已通过测试全量再跑一遍。
- [ ] native/plugin必要制品由对应owner按SOP构建发布；记录版本/hash/来源。不能复用旧制品名称声称包含新修正。
- [ ] 测试端成套切换兼容producer/consumer/profile，核对API、DAG、挂载与默认关闭开关；不单独启用TTL模板。
- [ ] 如确需真实小项目，只使用明确隔离目录和当次授权；不启动历史失败批次作测试。
- [ ] 提交协调记录；main/生产合并、BS96发布、真实暂停删除另按用户当次授权执行。

## 最小验收矩阵（按行为分组，不是六套全量测试）

| 组 | 断言 | 所属任务 |
| --- | --- | --- |
| V1 正常/TTL | 真实登记边界、Step1先锁、Step2新ID、TTL后CLI/平台下游到Step6 | T2 |
| V2 分类/幂等 | 白名单/非白名单、响应丢失、双预算不放大、无重复派发 | T3 |
| V3 控制 | 暂停与恢复竞争、进程重启接回、同attempt继续 | T4 |
| V4 清理重用 | 部分失败重入、同名新运行、旧锁/旧回调不阻塞或破坏新运行 | T4 |
| V5 权限保护 | 755/644、私有凭据、原子替换/挂载后仍正确、历史/本地/共享输入不变 | T2/T4 |
| V6 多流程 | WGS/GATK参数化、第三adapter无名称特判、不支持目标拒绝控制 | T1/T4 |

## 回滚与完成口径

每任务独立提交；运行中的操作保留journal和栅栏。回滚关闭新派发并恢复制品配置，
不删除审计、不擅自恢复暂停任务。新协议已登记任务必须由兼容consumer接回，
不能让旧代码忽略新锁继续写；TTL删除的Job或清理的数据不能靠代码回滚恢复。
当前只完成文档一致性/路径/任务ID检查，不声称P0已满足运行要求或算法全局最优。
无完整V1–V6证据不得把T5或整项P0标为完成。
