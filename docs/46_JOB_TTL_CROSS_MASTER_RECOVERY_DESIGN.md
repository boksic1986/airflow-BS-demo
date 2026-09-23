# Job 自动回收与跨 Master 续跑技术设计

日期：2026-09-23。状态：待开发；本次仅文档，不代表实现、验收或生产发布。
目标分支：`jiucheng/test/wgs-local-main-sync-20260917`。

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
| Worker Job | 3600 | 保留现有 rule 重试语义，不增加 Kubernetes 重试预算 |
| Master Job | 86400 | backoffLimit=0，restartPolicy=Never |

TTL 从 Job Complete/Failed 终态计算，并级联回收所属 Pod；不清理 SFS、OBS、
本地项目或持久证据。上述值是首版默认值，不是容量保证。短 TTL 上线前必须
用实际 Job 产生速率估算保留量并确认集群容量；未完成该检查不得生产启用。
不默认套用示例的 0/100 秒，也不为历史对象批量补 TTL。

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

### 4.4 批次锁

本轮不删除所有批次锁、不新增超时租约。Airflow 管平台投递；现有工作目录互斥
继续防止 CLI、测试、生产入口同时写同一目录。批次名本身不能作为唯一隔离键；
核对规范化目录与运行身份，避免同名不同目录误冲突。

同一运行换 Master 可继承保护，但接管前必须确认原派发进程、Master 和 Worker
均不会继续写入。身份冲突拒绝；SSH 断连、task 失败或锁存在时间长都不是解锁依据。
目录互斥不能仅靠 generation 标记：generation 只拦截回调，无法停止旧 Worker。
上传、下载和 heavy-slot 配额保持不变。

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
不新增缓存/监控服务；AOM 及告警为独立运维工作，不作为本次云端操作授权。

无新公开 API、数据库表或前端页面；内部新增 Worker 终态文件契约，并扩展原
Master 回执和恢复 journal。正式开发同步 runtime/DAG 契约，不将本文当作已实现说明。

## 6. 开发顺序与一次集中验收

1. 插件/Master：提交身份、终态落盘和 TTL 模板；产出独立测试制品及版本溯源。
2. CCE runtime：读取证据、跨 Master 接回、Worker 安全检查、原锁继承。
3. Airflow consumer：接入原 P0 状态/预算和下游推进，不新增平行恢复服务。
4. BS10610 隔离 mock 集中验收；消费者兼容通过后，才允许后续发布启用短 TTL。

最低用例：
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
