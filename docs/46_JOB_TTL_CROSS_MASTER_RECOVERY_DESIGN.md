# Job 自动回收与跨 Master 续跑技术设计

## 2026-09-26 当前契约修正（仅设计）

当前依据为[P0统一生命周期R1–R7](superpowers/specs/2026-09-17-wgs-gatk-cce-connection-recovery-design.md)
及[修订实施计划](superpowers/plans/2026-09-26-p0-lifecycle-correction.md)。
下面2026-09-25的完成记录只表示当时组件/隔离测试范围，不证明新批次正常链路闭合。
独立审计发现登记生产者、Step1/Step2身份顺序、CLI当前owner和TTL下游兼容缺口。

- 静态部署信任与动态每运行登记分开；初始owner在Step1前可确定，不依赖未来Step2 ID。
- 资源锁使用实际存储与目标资源，不使用可重用批次名；操作ID与运行owner分开。
- 暂停保留占用；最终写入完成可RELEASED。RELEASED不代表云端已清理，清理另有凭据。
- 清理完成后新analysis/run可条件占用同名路径；旧锁、legacy guard及tombstone
  不得永久拦截。旧owner/清理回调仍必须拒绝影响后来同路径的新资源。
- 平台与普通CLI共用选定Master和持久终态解析；只读状态不取写锁。不能用
  “关掉P0”配合TTL100新模板绕过缺口，因为旧Step4/5仍可能要求活Job存在。
- TTL100、Worker终态、源头分类、预算及完整清单要求保留。不修改冻结历史bundle。
- 业务目录/脚本755、文件644，私有控制及凭据例外；不强制业务setgid/组写。
- 本轮纳入与暂停/删除的生命周期衔接，但没有执行它们。独立控制操作表是运行
  控制的必要持久化，不新增TTL数据库或另一套恢复预算表。

日期：2026-09-23；2026-09-25 状态更新：Tasks1–6 的隔离源码及对应 synthetic 验收已完成，
整条分支审查的一项终态冲突问题已修复（native1bc67fd，定向13项通过）。
Task6 生产运行门禁仍未完成，不代表生产发布或真实 TTL 回收验收；Task5 旧制品不包含
后续 Task6 源码，需要后续发布阶段单独构建、核验最终版本，不能直接用于完整 P0 发布。
实现分支：`jiucheng/runtime/CR01-cce-recovery-20260922`；原目标测试分支未自动合并。
详见[Task5 制品与验收记录](releases/2026-09-24-p02-task5-offline-artifacts.md)。

## 0. 华为云建议与必交付项（2026-09-23 修订）

P-02 与 P0-2 为同一优先交付，不另建重试项目。本节及第 3.1 节取代上一版
仅将回收作为兼容条件的安排：自动回收是 P0-2 必交付，不得留到后续优化。

| 工程师建议 | 本项目落实位置 | 验收证据 |
| --- | --- | --- |
| 设置 Job TTL 自动清理终态资源 | 插件 Worker、cce-pipeline Master、现有临时 reader Job 的 manifest 生成端 | 生成清单含 TTL；授权后确认 Complete/Failed Job 及其 Pod 被回收 |
| AP 集群控制规模 | 现有 Airflow 并发与 Snakemake jobs 配置的集群级容量核算 | 全部入口汇总及插件预留，不将每个批次各自的上限当集群上限 |
| Prometheus 数据上报 AOM | 按官方监控中心指导绑定 AOM 实例 | 实例、采集范围、时间戳和实际可查询数据 |
| 告警中心配置常用规则 | 按官方模板配置资源与事件告警，连接通知渠道 | 规则清单、接收人、通知验证记录 |

四项均是生产闭环门禁，不能因代码测试通过就标记全部完成。AOM、告警及真实
TTL 回收验证需要单独云端操作授权；离线验收不启用上述服务或真实云端 Job。
工程师给的 100 秒是示例，不是厂商强制值；1000 是官方默认 Pod 配额，不是
Job 数量上限，也不是允许积累无限历史 Job 的依据。参考链接见文末。
## 1. 背景、目标和边界

华为云工单反馈：snakemake-ns 积压 28,985 个 Job（975 Failed、46 Running，
其余主要是 Complete），大量 LIST/WATCH 请求伴随 API Server 内存增长及 OOM，
进一步导致控制器协调和选主异常。这是供应商诊断，不是本次独立性能测量；不能
据此断言某一个客户端承担全部请求压力。默认 1000 的 AP 配额是 Pod 配额，
不是 Job 历史对象上限。

目标：Job/Pod 可以自动回收；批次依据持久化证据与既有结果安全续跑，不依赖
原 MasterPod 永久存在。选择“现有回执扩展 + TTL + 现有恢复入口”，不新增
数据库表、锁服务、清理守护进程或通用重试系统。

实现范围为 Kubernetes 插件、Master 启动/终态制品、CCE runtime 和 Airflow
consumer。WGS/GATK 分别验收；不修改生信参数、Worker 镜像接口、Step7，
不重写原冻结 bundle，不重新 prepare 或上传成功的前置步骤，不使用 forceall。
本次不授权历史 Job 清理、生产发布、批次恢复或任何数据删除。

本文是现有 CCE-CONNECTION-RECOVERY-20260917 / CR-01–CR-05 的 TTL 补充，
不是替代整个 P0 方案。仅对“旧 Master 已不存在”的分支补充持久证据判定；
其他恢复白名单、预算和发布幂等约束继续沿用 P0。目标测试分支已有 P0 checkpoint
和 Step7 提交，本次不修改其完成状态，也不把主线恢复代码视为已并入测试分支。

## 2. 现状与具体缺口

当前 airflow 源码 `scripts/wgs_resume.py` 使用冻结 runtime，并复用
`recovery-<action_id>.json`。`resume_master` 在 Master 不存在且 journal 没有
deleting/deleted/submitting 状态时拒绝恢复；`fence_master_status` 也要求
原 UID 对应的 Master 存在。合法 TTL 回收因此可能被当作无法恢复的异常。

恢复中已经存在 UID/resourceVersion 删除前置条件、原生批次锁、Worker 检查、
START 交接及 journal，应扩展这些能力，而不是平行建立另一条恢复路径。
旧文档对监控对象的描述不是全部最新实现，开发应以目标测试分支为准。

Master 和 Worker 配置必须分别检查；不能把事故归结为全部对象都没有 TTL。
开发前记录实际生成的 manifest、插件版本、Master digest 和 consumer 版本，
不只看 current 软链接，也不通过修改生产 manifest 验证方案。

## 3. Kubernetes 插件与 Master

### 3.1 新制品默认配置

| 对象 | ttlSecondsAfterFinished | 重启策略 |
| --- | ---: | --- |
| Worker Job | 100 | 保留现有 rule 重试语义，不增加 Kubernetes 重试预算 |
| Master Job | 100 | backoffLimit=0，restartPolicy=Never |
| 现有临时 reader Job | 100 | 保留现有超时、只读挂载及主动清理；TTL 为兜底 |

TTL 从 Job Complete/Failed 终态计算，并级联回收所属 Pod；不清理 SFS、OBS、
本地项目或持久证据。到期是具备删除资格，不保证第 100 秒准确删除；finalizer
仍受正常处理，不强行摘除。Running/Pending Job 不因该字段而过期。
本修订采用工程师示例 100 秒作为项目拟定初值，替换上一版自定的 3600/86400；
不是声称华为强制 100 秒，也不是立即修改生产配置。不得设 0 或靠永久保留
Job 维持续跑。未来调整需记录终态产生速率、留存对象量及采集延迟依据。

具体修改点：Snakemake Kubernetes 插件写 Worker Job.spec；cce-pipeline
Master manifest 生成端写 Master Job.spec；现有 reader 生成端补齐同字段。
字段必须是 Job 的 spec.ttlSecondsAfterFinished，不是 Pod template 字段。
覆盖 WGS/GATK、正常创建和恢复创建；手工 CLI 使用相同生成器，不能仅在
Airflow 外层临时补丁设置。未知第三方 Job 不擅自修改，历史对象不批量补 TTL。

先完成持久证据与兼容 consumer，再启用这组模板；TTL 不会等待证据采集确认。
断连超过 100 秒、Master 崩溃或证据写入失败可能丢失 Kubernetes 终态：必须
返回 UNKNOWN 并停止自动派发，不能把 404 当成功、失败或无活跃执行的证明。
这个安全降级需纳入验收；不能承诺短 TTL 下任意故障均可自动恢复。

### 3.2 Worker 证据生产者与接口

证据生产者是 Master 内的 Kubernetes executor 插件，不要求每个生信 Worker
安装新的 logger。沿用 P0 创建前提交身份记录和同名对象核对逻辑。

在现有每次运行证据目录下新增内部子目录 `worker-terminal/`，文件名为
`<job_uid>.json`。每个文件只对应一个 Job UID，避免共享 JSON 并发重写。
内部 schema v1 必填字段：

```text
schema_version=1
run_id, attempt, execution_generation
master_uid, job_name, job_uid, submission_identity
terminal_state=SUCCEEDED|FAILED
reason, observed_at
```

插件确认 Kubernetes Job 终态后，先原子保存证据，再将结果交给 Snakemake。
写入采用同目录临时文件、flush/fsync、原子发布；已存在的相同身份终态可重读，
冲突终态不得覆盖。证据只记录必要执行信息，不包含凭据或样本临床内容。

持久化失败须报告异常，不能宣称证据已完整保存。API 404 不等于成功：
对象已回收时仅接受身份匹配的终态证据，否则结果为 UNKNOWN，停止自动派发。
这也覆盖 Master 断连时间超过 Worker TTL、尚未来得及观察终态的情况。

### 3.3 Master 证据与启动交接

扩展现有 Master 终态记录，增加/明确 UID、execution_generation、冻结配置
摘要和结果分类：success、rule_failed、P0 白名单基础设施故障、unknown。
不得根据日志关键词推断允许自动恢复的类别。

正常完成、可捕获的启动检查失败均写入终态记录；SIGKILL/OOM 等不能保证写入，
必须保留 UNKNOWN 分支。控制端观察到 Kubernetes 终态时保存绑定 UID 的快照，
并将证据镜像到现有控制端目录。Kubernetes Failed 本身不证明是可恢复故障。

保留 WAITING/START 协议，不借本任务重构上传交接。记录 Job 已提交、Pod 就绪、
START 已发出和 START 已确认；恢复交接必须查询原 UID，而不是另建 Master。
START 检查失败、交接超时要有结构化原因；未知响应不能触发第二次投递。

## 4. Runtime 恢复算法与锁

### 4.1 状态判定

| 当前对象/证据 | 行为 |
| --- | --- |
| 原 Master 活跃且身份一致 | 接回原交接或监控，不创建第二个 Master |
| 成功终态证据可信 | 补齐状态、推进下游，不重新分析 |
| 失败证据可信且符合恢复规则 | 完成 Worker 安全检查后允许替换 |
| Job 消失但持久终态证据可信 | 采用上述成功/失败分支，不要求曾由本 journal 删除 |
| 查询失败、证据冲突、无证据或身份未知 | 记录待确认，停止自动派发 |

consumer 必须校验 run/attempt/代际、Job UID 和配置摘要。原始退出码、文件存在、
进度百分比不能替代可信终态。实时对象与证据冲突时停止，不按优先级强行择一。

### 4.2 替换前 Worker 检查

同时读取原提交清单和该运行标签的完整 Job/Pod 清单（含全部分页）。仍存在的
Worker 必须终止；已回收 Worker 必须有相应终态证据。无证据不等于无执行。
未知 Worker、活跃 Pod、在途创建、分页不完整或 API 错误均阻止替换。
不能只使用 Master 标签，也不能用空的查询结果吞掉请求失败。

### 4.3 journal 与幂等

扩展原 journal，记录原 Master UID、目标执行代际、配置摘要、终态证据摘要、
替代 Master UID 和恢复步骤。顺序固定为：

```text
核对原执行 → 核对 Worker → 保存恢复意图
→ 必要时精确删除旧终态 Master → 创建/查询替代 Master
→ 完成交接 → 接续监控
```

存在旧对象时继续使用 UID/resourceVersion 删除前置条件。创建结果不确定时，
查询原提交身份，不增加 action 或重复创建。journal 的 submitting/created
状态覆盖控制端崩溃后的接回。新 Master UID 确认后绑定新代际，旧回调不能回写。

旧冻结 bundle 不修改。缺少新证据契约的旧任务不自动获得“消失后安全恢复”能力，
只允许保留原行为或人工核对，不为历史任务伪造回执。

### 4.4 批次锁职责、接管与释放（P0-2E 必交付）

这部分是项目恢复契约，不是华为要求取消锁。取消“旧 Master 必须永久存在
才能继承批次”的依赖，不取消全部互斥。复用现有锁与操作记录，不新增锁服务、
租约守护进程或数据库表，也不通过人工删除锁绕开活跃执行检查。

| 现有控制 | 修订职责 |
| --- | --- |
| Airflow 并发及后端操作记录/事务 | 平台批次投递、重复点击去重和恢复预算；不是 CLI 的目录互斥 |
| runtime 批次占用（现有 cce-batch-lock ConfigMap） | 保护同一目标目录，绑定逻辑运行；Master UID 是当前执行绑定，不是永久锁主键 |
| launch/worker 进程锁 | 原派发在途或后台进程活跃时只能接回，不启动第二个执行进程 |
| status 写锁与 generation 检查 | 原子写状态、拒绝旧回调；不能阻止旧 Worker 写分析输出 |
| 上传/下载/heavy-slot 配额 | 保持原职责和额度，不在本任务取消 |

当前设计的锁定位使用实际存储身份及规范化资源路径，owner绑定pipeline、
analysis_id、attempt、runtime_run_id、计算generation及Master UID；配置摘要
用于冻结输入核对。操作action独立，不要求owner绑定某个阶段execution_id。
同名且实际输出资源不交叠的运行互不阻塞；同目录有OWNED运行时其他analysis拒绝。
旧运行已释放且该输出资源已清理后，新analysis可以条件重占，不要求删除历史记录。
不对现有锁键做在线批量迁移；若旧键无法表达目录身份，先在开发中明确版本化
映射及双入口冲突检查，未验收不得启用，不能同时产生两个互不识别的锁域。

沿用 wgs_resume 对原生 _claim_batch_lock 的调用及原 journal，修改其源端
契约并对齐 WGS/GATK consumer，不绕过原语。接管顺序：
1. 接回同一 action，核对锁身份、原派发进程和完整 Master/Worker 证据。
2. 原执行活跃或创建结果未知：只监控/待确认，不释放、不替换、不抢锁。
3. 原执行成功：保存成功并推进下游；允许恢复的失败且旧执行全部停止：
   先持久记录交接意图，再对旧锁版本/owner 做条件更新，绑定新 generation。
4. 使用现有 ConfigMap resourceVersion 条件更新（本地原语使用既有互斥）；
   不做“先删锁再创建”的无保护窗口。竞争失败重读身份，不能覆盖他人。
5. 新 Master 创建响应丢失按原 action/journal 查询；进程重启沿记录接回，
   不增加业务 attempt，不重置预算。旧 generation 不得释放新 owner 的锁。

锁不随 Master Job TTL 级联删除；实现前核对 ownerReferences，禁止依靠旧
Master 的 GC 释放目录保护。仅当该锁保护的写入阶段结束、无在途派发或活跃
写入者、终态已持久化后，由当前 owner 条件释放。成功后续阶段仍可能写入时
继续保护到其原生命周期结束。失败待恢复保留可接管占用，不保留旧 UID 硬依赖。
TTL 后缺证据、API 不可达、空 Worker 清单、SSH 断开或锁龄过长均不是解锁理由。
历史任务缺少身份时返回待人工确认，不补造回执、不自动删除旧锁。

2026-09-23 Task2 源码落点：已加入可选目录锁原语、旧锁快照保留的 CAS guard、
交接 intent 和条件 RELEASED 记录。用户提到的 5 个失败批次仅用于讨论兼容，
未授权本轮运行操作。升级后的恢复入口必须保留其冻结输入与 attempt，完成旧
运行到目录/owner 的可信映射及完整静止检查，再交接新 generation。guard 能阻止
旧 CLI 继承同一旧键，但不能解决旧 CLI 改用另一批次键写同目录，因此必须先统一
该目录所有 CLI/平台/后续阶段写入入口。实际映射、验证器、journal 持久化及
冻结 runtime 外部兼容调用仍由 Task3/4 接入；未通过前不启用新锁/TTL，旧冻结
文件不修改。详见现有 P0-2 implementation plan 的 historical-run compatibility。

## 5. Airflow 对接与查询负载

复用认证恢复 API、resume_stage、操作记录及事务注册 generation，禁止用直接
调用底层 helper 的方式绕开调度。重复请求接回同一 action/journal。

自动替换预算复用 P0：同 attempt 最多两次，等待 60/180 秒，保留原总截止时间；
普通查询重试不额外创造替换预算。仅 P0 白名单基础设施故障允许自动恢复，
真实 rule 失败、缺输入、认证失败和未知结果不自动恢复。自动恢复默认关闭，
WGS/GATK 分别验收；成功前置步骤不重复运行。

插件状态查询限定当前运行中尚未确认终态的 Worker；已持久化终态退出重复查询集合。
Airflow 读取控制端状态，不新增 Worker 逐个查询。完整清单检查只在恢复门禁执行，
不放到页面刷新路径。异常查询采用现有有界退避，不高频重扫 namespace。
不新增缓存/监控服务。AOM 和告警是必要运维交付，不是可省略的后续建议；
但本文不构成云端操作授权。

容量核算包括共享集群内 WGS/GATK、手工/测试入口、Master/reader、插件 Pod
及未回收 Pod；以实际集群配额为准，在默认 1000 内预留余量。沿用现有并发
和 jobs 配置控制投递，不新增调度服务。估算保留量约为终态产生速率乘 TTL，
再加活跃对象和删除延迟；同时监控 Complete/Failed Job 积压，TTL 不能限制
活跃并发。无法确认剩余容量或控制面异常时停止新增投递，不能高频重试。

发布检查单：按官方监控中心打开普罗数据上报并选定 AOM 实例；核对数据新鲜度；
按告警中心常用模板配置 CPU/内存、容器重启等可用规则与通知渠道。另核对
Job 终态积压、Pod 配额使用、API 错误/延迟和控制面健康的可观测覆盖。
托管控制面指标未开放时请华为工程师确认获取方式，不虚构指标或以空数据通过。
阈值和接收人写入部署记录，以实际配额和供应商模板为依据；不增加自建采集器。
AOM 成本与权限在启用前确认。验收至少保存一次通知渠道测试记录，不做故障压测。
不得将业务 MasterPod 资源调大当作 kube-apiserver OOM 的修复，也不重启共享控制器。

无新公开 API、数据库表或前端页面；内部新增 Worker 终态文件契约，并扩展原
Master 回执和恢复 journal。正式开发同步 runtime/DAG 契约，不将本文当作已实现说明。

## 6. 开发顺序与一次集中验收

1. 插件/Master：提交身份、终态落盘和 TTL 模板；产出独立测试制品及版本溯源。
2. CCE runtime：读取证据、跨 Master 接回、Worker 安全检查、原锁继承。
3. Airflow consumer：接入原 P0 状态/预算和下游推进，不新增平行恢复服务。
4. BS10610 隔离 mock 集中验收；消费者兼容通过后，才允许后续发布启用短 TTL。

最低用例：

- 检查全部三类生成模板、两条 pipeline 和恢复路径含 TTL=100；验证终态回收
  后凭证据接续、断连跨 TTL 无证据停止，不重复派发。
- mock 不能证明集群 TTL 控制器有效。生产启用前另行授权一次合成 Job 验证，
  覆盖 Complete/Failed 及所属 Pod 回收；不使用真实批次、不执行生信分析。
- 集群容量核算、AOM 数据与告警通知记录未齐全时，生产闭环保持待验收。
- Worker 回收后有证据可读取，无证据不误判；写入中断/冲突不能生成可信终态。
- Master 回收后成功推进下游、允许恢复的失败换 Master；未知结果停止。
- 活跃 Master 只接回，活跃/未知 Worker 和不完整清单阻止替换。
- 创建响应丢失、重复点击和进程重启不重复派发，START 交接可接回。
- 两次预算重启后保留，旧回调被拒绝，成功前置和已有结果不重跑。
- 查询范围限本运行，已确认终态退出重复查询；WGS/GATK 分别通过。

只运行受影响用例及一个 mock 联调，复用不变的 P0 结果；不做全量回归或真实分析。
BS10610 更新前核对 hostname、实际挂载、制品、数据库和活跃任务；影响任务则停止。
本次文档任务不需要运行上述测试。

## 7. 交付、发布与回滚

文档提交仅包含本文和必要 CURRENT_STATE/TASKS/HANDOFF 条目，保留其他改动。
后续交付应记录插件版本、wheel 校验值、Master digest、consumer 提交和测试结果。
不得覆盖生产共享 wheel、同名镜像或配置。生产合并、发布、历史批次迁移和自动恢复
启用需另行授权，不能通过本次设计提交隐式执行。

回滚恢复制品与配置，不清空证据或修改分析结果。TTL 已删除的 Job 无法靠代码回滚
恢复，所以必须先具备持久证据和兼容 consumer，再启用短 TTL；不能以回滚到只读
Kubernetes 的旧 consumer 作为完整回滚保证。

参考：
- https://kubernetes.io/zh-cn/docs/concepts/workloads/controllers/ttlafterfinished/
- https://support.huaweicloud.com/intl/zh-cn/productdesc-cce-autopilot/cce_12_0006.html
- https://support.huaweicloud.com/intl/zh-cn/usermanual-cce-autopilot/cce_11_0789.html
- https://support.huaweicloud.com/intl/zh-cn/usermanual-cce-autopilot/cce_11_0798.html
- [环境边界](34_TEST_PRODUCTION_RELEASE_BOUNDARY.md)
- [Runtime 契约](08_WORKFLOW_RUNTIME_INTEGRATION.md)
- [Airflow DAG 契约](07_AIRFLOW_DAG_SPEC.md)
- [P0 连接恢复方案](superpowers/specs/2026-09-17-wgs-gatk-cce-connection-recovery-design.md)
