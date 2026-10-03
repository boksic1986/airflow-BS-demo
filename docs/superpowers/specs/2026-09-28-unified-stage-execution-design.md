# Step1–6 公共执行器与统一生命周期设计

2026-09-30 当前状态：UE05的AF03bab6c/native7172573源码配对及最小差量验收完成。
用户要求检查后继续，原两个owner已完成UE06测试端隔离安装及实际入口/pin检查，
协调者已读原始exit0证据接受，最终AF状态提交3c094fc及28项证据索引均核对通过，
UE06隔离安装验收和交接已关闭。详见
[UE06审核](../../reviews/2026-09-30-ue06-isolated-install-review.md)。
旧shared0.8.8的配对policy/platform指向BS10610不存在的/home/ctapa：准确旧wheel
已保留且匹配，但实际旧policy回滚未验收，留待实际切换前原环境owner确认。
本轮不选择候选供服务使用；下方早期“UE06待审核”是历史记录，不要求回退。
生产、真实批次、前序全套复验和W423实现均不包含，不能声称生产已就绪。

2026-09-30 后续扩展：[WGS4.2.3 设计](2026-09-30-wgs423-upgrade-integration-design.md)
在 UE 配套完成后接入 prepare 的受信前置登记/后台 handler。prepare 尚无最终 batch binding，
不得直接要求已完成 bundle；沿用本公共执行/观察/身份保护，不另造调度层。不改变 UE-05
当前范围，也不提前宣称新 handler 或最终 Master 已交付。

2026-09-30 最新授权：用户批准下述3.5的公共 SSH 连接修复，并明确允许 UE-05 在现有
受鉴权内部回调、轮询和清理请求传递可选 native 执行快照。复用 UE-04 身份/终态校验，
不新增 route/DB 表；Worker 探测证据保持独立。原 R2/R4 接口等待已解除，UE-01–04
不重开；源码与 BS10610 最小差量验证继续，生产发布不在本次授权内。

状态：2026-09-29 18:27Z UE-01–04 源码配对与差量证据已审核接收，
UE-04 平台a6c31d1/7976f25 / native4fa85874，普通Step5共享终态验证源码链已闭合；
原两个 owner 已获准实施 UE-05，仅源码和 BS10610 隔离 synthetic，UE-06 仍待阶段审核。
不重开已验收项目，不提前安装/部署或跳过后续审核。统一方案尚未整体完成；
最新审查回写、独立待办及 owner/审核点见实施计划，不增加新阶段。

本轮先完成生产 GATK 兼容保障，再按 UE-01–06 开发；平台从当前生产分支新建 worktree，
native 以 release0.8.9交付。生产兼容补丁与 UE 测试候选分开，不提前推广新架构。
本文替代此前“保留 WGS 同步/GATK 异步两套执行形式，
分别补兼容”的建议，并细化 [P0 R1–R7](2026-09-17-wgs-gatk-cce-connection-recovery-design.md)
的公共内核要求。既有生产成功记录仍有效，但不代表本设计已验收。
实施队列：[UE-01–UE-06](../plans/2026-09-28-unified-stage-execution.md)。

本次修订已纳入 [WGS/P0 覆盖审查 R1–R4](../../reviews/2026-09-28-wgs-p0-unified-execution-coverage.md)：
前驱回执入库、手动恢复动作生命周期、失败路径批量查询及全阶段失联保护。
这些是原六项任务的必要收敛，不增加功能或表示对应源码已修复。

2026-09-29 审查补充固定以下消费责任：UE-03 区分实际分析 Master 与 helper 的角色，
避免辅助探测污染 Heavy 配额配置判断；UE-04 接收绑定合法 action 的 GATK 恢复 DagRun，
WGS 最终成功必须有当前运行真实 Step6 完成证据，不以 Airflow 终态替代；UE-05 保留
冻结请求的版本正确摘要验证。现有字段/回执足够时直接复用，不为此扩展 UE-01 协议。
真实进度、旧回执不得回退当前阶段、事务所有权及现有身份/锁/期限保护共同保留。
首次提交事务幂等、独立鉴权、列表性能和 SFS 图表优化不转为公共执行器的附加功能。

最新用户授权当前 WES 以限范围补丁恢复，同时将已证实的 Step4/Step5 TTL 缺陷收敛到
本方案。生产补丁由指定修复 owner 单独交付；永久修复称为 TTL-DOWNSTREAM，主归
UE-04，UE-05/06 仅消费/核对，详见4.3及实施计划。不重开 UE-02 或扩大正在进行的 UE-03。

本次范围收紧优先于前一版方案及历史兼容建议：**已验收项目不做二次整体验收；
以 GATK 现有异步实现为基准，主要迁移 WGS；废弃执行/Resume 不纳入新代码兼容。**
既有验收结论直接引用，仅新增或直接改变的边界需要定向证据，不因换提交 SHA 或
统一方案而自动重开全部测试。以下已合入比例审查的四项修正。

进一步澄清：**减少双流程同时大改是实施约束，不是 GATK 不准改的架构约束。**
正确的公共生命周期与已知故障覆盖优先。以下 Step2 选择基于代码、资源占用和恢复机制，
不是要求原样保留 GATK，也不是为统一外观强制改变两套 task 图。

## 1. 目标、依据与范围

目标：WGS、GATK 的 Step1–6 共用执行协议和后台执行器，为启动、暂停、续跑、
取消提供同一控制基础；后续流程通过受信 adapter 接入，而不是复制调度代码。

核实的历史：234bcfe（2026-08-27）已有 WGS Step2/6 同步模式；4dc577b
（09-04）补同步阶段的锁；e55b9d7（09-08）接入 GATK 后台派发；caf87e4
（09-24）的 P0 公共检查误要求全部阶段都有异步进程凭据。没有找到原同步
选择的书面动机，不能把合理猜测写成历史事实。

采用 GATK 已有的异步 submit/worker/wait 形式，复用其已验证的派发与进程管理，
只抽取公共部分，不另写一套内核再让两个流程大规模迁移。WGS 向这套执行契约收敛，
各自的业务顺序和完成条件不变，不把 WGS 参数、目录或结果规则强加给 GATK。

### 改动预算

- WGS：主要调整 Step2/6 同步外壳、公共回执消费与已确认的 P0 交接缺陷；其他阶段
  只改公共调用点，业务 handler、规则、配置、上传下载和结果落地算法不重写。
- GATK：业务 handler、参数、输入输出和落地算法尽量不动；Step2 及 DAG 的派发/观察
  callable 可按公共契约修改，不能以“已经异步”为由保留不一致的失败/身份判定。
  当前推荐保留 submit/wait 拆分，理由见3.2；这不是禁止改图或禁止改 `dags/bio_gatk.py`。
- 新公共执行器以现有 GATK dispatcher 的可复用部分为基础；不保留双重 Popen、
  双层 worker 或额外持久化相同业务结果。公共快照可映射现有回执，不强改 GATK 文件格式。
- 小范围 Step2/公共接入修正属于本方案；如需改变业务结果、配额或大幅重构多个层，
  先说明收益、风险和替代方案，不用“统一”或“少改”代替论证。

- 本轮实施目标：公共执行器、两个流程接入、P0 适配、必要 native 修复和测试端验收。
- 暂停/取消的操作语义及执行器扩展点在本设计中固定；完整控制 API、UI、真实停任务
  验收仍属于 [RC 后续任务](2026-09-18-run-control.md)，不得提前宣称可用。
- 不增加新流程上线、常驻重试服务、Local/SGE 控制、数据库迁移或生产数据操作。
- 保留 Snakemake 规则、Step1–6 顺序、配额、传输租约、原恢复白名单及预算。
- Step7 删除不并入普通执行链；本地项目/结果/FASTQ/pending/证据保护不变。

## 2. 分层：一个执行内核，不再两套 dispatcher

| 层 | 职责 | 明确不负责 |
| --- | --- | --- |
| Airflow / backend | 注册请求、鉴权、调度、租约、操作仲裁、sensor 等待、状态投影 | 根据 SSH 退出直接推断云端结果、再次启动活跃任务 |
| cce-pipeline 公共执行器 | 持久派发、后台进程、身份/回执、阶段生命周期、只读查询、受控停止与恢复扩展点 | 访问业务 DB、选择患者样本、另设自动恢复策略 |
| 流程 adapter | 受信阶段 handler、配置/镜像、输入输出、结果落地、检查点和停止能力 | 自建 worker 管理、重试循环、锁或另一套状态机 |
| 原生 workflow | 规则依赖、计算、文件级断点 | 平台 UI / Airflow 状态管理 |

公共执行器落在 cce-pipeline 源码，由 native owner 维护和打包；WGS/GATK
gate 保留入口鉴权、冻结请求验证和参数转换，委托同一内核，不各自 Popen/写进程回执。
现有 paired runtime 保留平台授权、当前 Master 绑定和 native 调用桥接。
CLI 本轮不重做前台体验或命令；既有受信调用由公共接口承接，不建立第二条无登记写入路径。
内部同步 subprocess 可以继续使用，但只能在公共后台 worker 的管理范围内执行。

## 3. 公共协议与阶段完成条件

### 3.1 新执行协议

内部执行协议标识为 `cce.stage-execution.v1`，独立于既有平台请求
`orchestration_contract_version=2`；不重新解释或重算历史请求摘要。

固定受信接口：`submit(execution_ref)`、`observe(execution_ref)`；未来控制使用
`control(execution_ref, operation_ref)`。执行器只接受已登记的引用，通过部署管理的
resolver 获取内容；请求不得传任意 executable、模块路径、shell 命令或策略文件。

公共执行记录至少绑定 pipeline、analysis、attempt、stage、execution_id、stage generation、
request_hash、协议、注册内容摘要和运行身份。进程身份绑定 boot_id/PID/starttime，
并记录受控子进程组。计算 generation/Master UID 与阶段 generation 分开。
后台 worker 通过受信 handler 注册表执行阶段；未知 adapter/协议拒绝，不按名称猜测。

- `submit`：验证及持久化派发意图后，启动后台 worker，返回 accepted 和原执行身份。
  同身份重入返回已有状态，不另起进程；同幂等身份不同摘要拒绝。
- worker：在相同 launch/worker 互斥规则下接管，写 running，执行 handler，持久化终态。
  原子更新并 fsync，不能先投影成功再补关键完成证据。
- `observe`：只读返回 accepted/running/succeeded/failed/canceled 或 unknown；监控健康独立。
  暂停功能启用后增加 pause_requested/pausing/paused 等控制投影，不提前扩展现有 DB 枚举。
- 接收回复丢失、SSH 断线或 worker 异常退出：先观察原 execution；无充分证据则 unknown。
  unknown 不等于 failed，也不授权新 CREATE、接管锁或放行后继阶段。
- dispatcher 终止、阶段业务成功、全运行无活跃写入是三个不同事实，不能互相代替。

接口类型：`ExecutionRef` 为已有登记可解析的不透明引用；`ExecutionSnapshot`
包含原引用、上述完整身份、state、证据引用及独立 observation_health。
`submit(ref: ExecutionRef) -> ExecutionSnapshot` 与
`observe(ref: ExecutionRef) -> ExecutionSnapshot` 返回同一种结构，终态重入返回
已有终态而非重新返回 accepted。共同投影将 succeeded 转成既有平台 success；
unknown 表示证据/观察不足，保持最后已确认的业务状态并标注观察异常，不伪造 failed。
新协议请求在首次 request_hash 计算前冻结顶层扩展
`stage_execution: {"protocol":"cce.stage-execution.v1"}`；原请求保持原字节和摘要，不回填。
native 原 `platform_execution` 精确七键对象不扩展。完整执行引用/registration_sha256
不塞回参与自身计算的请求扩展，避免摘要循环。
未来 `control(ref: ExecutionRef, operation: OperationRef) -> ExecutionSnapshot`
只消费已授权操作引用；未启用能力明确返回 unsupported，不降级为杀进程。

校验位置按职责收敛：同一受信操作内，已解析并验证的不可变登记内容使用引用传递，
不在每层/每次轮询重复解析、重算摘要或做目录探测。入口鉴权、跨信任边界验证，以及
写入/接管/释放前对可变身份和活跃 writer 的锁内复核保留；它们不是同一项重复校验。

**UE-01 对齐决定（2026-09-28）：**

- 无路径引用字段固定为 protocol/pipeline/analysis_id/attempt/stage/execution_id/
  stage_generation/request_hash/registration_sha256。pipeline 为受信 adapter registry 的
  string key，不在公共类型写死 WGS/GATK enum；当前部署仍只注册这两种，未知/未启用项
  由 resolver 拒绝，不加第三流程演示。attempt/stage_generation 为正整数（不是 bool），
  两摘要为 lowercase64-hex，其余身份为字符串。
- snapshot 精确键：schema（固定 cce.stage-execution.snapshot.v1）、execution_ref、state、
  evidence_ref、runtime_identity、compute_identity、observation_health。evidence_ref 是
  null 或不透明字符串，不是路径；runtime_identity 为 null 或 boot_id/pid/starttime_ticks/
  process_group_id 对象；compute_identity 为 null 或 compute_generation/master_uid 对象，
  两计算字段可各自为 null，不能与阶段 generation 混用。完整身份仅在 execution_ref，
  不重复 identity 对象。observation_health 为 healthy/degraded，unknown 必须 degraded。
- registration envelope 精确顶层键为上述引用除 registration_sha256 外的八个身份字段，
  加 runtime_binding。binding 仅来自受信 resolver 的已冻结绑定，不含可变状态/运行证据。
  原 request 中冻结的期限由 request_hash 覆盖，不新增重复 deadline 对象；若原冻结
  binding 已有期限，原位保留。不能把 CREATE 后才出现的事实提前纳入登记。
- registration_sha256 为上述 envelope 的 canonical JSON SHA256，编码精确为
  `json.dumps(envelope, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')`，
  无尾换行，不含摘要自身。受信 resolver 从已批准 request root 定位登记，handler 按固定
  pipeline/stage 绑定，不接受请求自带路径或可执行命令。
- 原 success 映为 succeeded；failed/canceled 无损保留，平台分别映回现有状态。
  canceled 仅表达已有终态，不新增取消能力/DB 枚举，不放行后继或授予自动重发。
  dispatcher canceled 也不证明云计算静止，仍保留原 writer/quiescence 条件。
- 不新增全阶段 absolute deadline，不用 created_at + timeout_seconds 改变原计时起点。
  Step2 CREATE/START600s 由 native 首次 intent 冻结；Step3 recovery、Step4 publish 各用
  原已冻结期限。其余阶段保留原 Airflow task/sensor 与 handler 超时。不存在已冻结
  absolute 值时不补算，也不因为重入重置已有期限。
- CREATE 才生成的 deadline_epoch 属后续持久 runtime 证据，不反写不可变登记/摘要。
  UE-01 envelope 只纳入首次登记时已经冻结的原字段/绑定，不强制通用 deadline 字段。
  共同 DAG 客户端 deadline 是已有观察期限，不是新业务截止时间或恢复授权；无该值时
  允许 None，由现有 Airflow task/sensor 期限约束。到期不据此推断计算失败/静止。

### 3.2 阶段语义

| 阶段 | 后台工作 | succeeded 的必要条件 |
| --- | --- | --- |
| Step1 | 上传输入 | 上传清单及原校验通过，传输终态真实 |
| Step2 | Master 创建与启动握手 | 精确 UID 的原生握手 START_CONFIRMED；不是 Job 创建成功 |
| Step3 | 观察工作流执行 | 选定 Master 的绑定终态、完整计算证据确认成功；不是 observer 退出 |
| Step4 | 发布结果 | 当前执行的发布清单及校验/完成凭据成立 |
| Step5 | 下载与校验 | 下载清单完整，校验通过；不是进度条到 100% |
| Step6 | 落地与收尾 | materialization 验证通过，必要生命周期收尾完成 |

Step2 的本地 worker 可以结束而云端 Master 继续计算，这是正常交接。
Step3 的本地 observer 停止不代表 Master/Worker 静止。
Airflow 每阶段均执行“提交 → 观察 → 确认”的协议，不要求一律拆成两个 task。
#### Step2 取舍：公共生命周期相同，等待调度策略可不同

源代码依据：`dags/bio_gatk.py` 的 Step2 已拆为提交与 `mode="reschedule"` 的 sensor；
`dags/bio_wgs.py` 则把 Step2 放在带 `wgs_cce_runs` pool 的单个 runner 内。
另外 GATK `run_stage` 当前按 SSH 非零退出抛异常，零退出直接返回 accepted，未使用
拟议公共快照判断派发不确定性。这是接入需要收敛的差异，不是新发现的线上故障结论。

| 选择 | 收益与代价 | 本轮判断 |
| --- | --- | --- |
| 两流程都在提交 task 内等待 | 外形相同；GATK 原可 reschedule 的等待变为持续占用 worker/default pool，原 wait 还需删除或降为重复确认；未解决额外生命周期问题 | 不选 |
| 两流程都拆提交和 reschedule wait | 调度形式一致、等待不持续占 worker；但 WGS 提交结束即改变原 pool 持有区间，需要额外启动配额所有权设计，不能靠给 sensor 配同名 pool 等价替代 | 不是本轮最小充分方案 |
| 公共异步执行器、公共派发/观察判定，task 仅选等待策略 | 解决身份/终态/断线/恢复差异；GATK 保留有效 reschedule 结构，WGS 暂留原 pool 持有方式，只允许薄等待包装 | 推荐 |

[Airflow sensor 文档](https://airflow.apache.org/docs/apache-airflow/2.11.2/core-concepts/sensors.html)
说明 reschedule 在检查间不持续占用 worker。此处是机制依据，非当前部署版本的现场验证。
不为本轮引入新的跨 task 启动租约系统；WGS 占用一个等待 worker 是明确保留的现有代价，
不是长期最优声明。今后若有实际容量问题，应针对配额生命周期单独优化，而非回到两套执行逻辑。

据此，本轮实施如下：

- GATK 的 `submit_step2_master → wait_step2_master` 图本轮保留，但两个 callable 接入
  公共派发/观察实现；submit 不再独立根据 SSH 退出判断执行状态，wait 用共同完成条件。
  不再新增一段 submit 内等待，也不把原 sensor 降为重复确认。
- WGS 远端 Step2 改为同一异步内核。原 `submit_step2_master` task 用薄等待客户端
  发一次 submit、通过短请求 observe 至握手确认，保留 `wgs_cce_runs` 原占用范围；
  不增加同义 sensor、不保持长 SSH、不要求 GATK 也使用这个等待外壳。
- WGS Step6 使用已有提交/等待边界；其他已异步阶段只接入公共函数，不重做业务步骤。

两流程均只有握手成功才放行 Step3；GATK 不新增专用配额。
公共客户端同时供 sensor 单次观察与 WGS 薄循环等待使用，统一身份验证、观察健康、
终态解释、原 deadline 和当前控制动作判定。WGS 循环不得复制一套失败/恢复策略。
派发回复丢失只能先观察同一 execution；已存在活跃/终态执行接回，unknown 保留不确定性。
超时结束等待不等于云端计算失败或静止；不能因此创建新 generation、解锁或再次发 START。
WGS/GATK 已有批准的传输/恢复预算由原 owner 执行，公共客户端不增加独立重试额度。
鉴权/身份/配置拒绝仍按明确错误处理，不用 unknown 吞掉确定性错误。派发异常的观察
结果与 Airflow task 状态分开，后继仍必须过原生终态及平台前驱屏障。
等待受适用的已有阶段原始 deadline 或现有 Airflow 等待期限约束，不新增全阶段期限，
不用每次查询重置预算。Airflow task 重试先
接回同一 execution，不能新派发；任务进程崩溃后的 pool 行为不作超出现状的保证。
Step1/5 的持久传输租约仍由原机制承接，不因 accepted 提前释放。
展示标签和计数单位允许 adapter 提供，accepted/成功判定不允许流程各自定义。

### 3.3 前驱回执入库屏障（审查 R1）

Step2 原生 START_CONFIRMED、匹配成功回执和平台前驱记录可见是连续的交接条件。
仅等待 native 成功、仅结束 Airflow task，或由操作者刷新页面触发同步均不满足交接。
正常提交、当前 P0 阶段续跑、自动恢复的 Step3 登记共用以下按需接收屏障，
不为已验证前驱重复同步、读取远端或重算摘要：

1. 只读验证请求、attempt、当前 DagRun/action 和可登记阶段的资格。
2. 已有平台记录匹配当前前驱 execution/generation/receipt_hash，且已经过接收验证并
   确认为成功时直接使用；缺失、滞后或引用已变化时才复用现有接收服务读取对应证据。
   接收本身不触发完整云清单或目录 helper Job；独立写会话不能嵌套在同运行写锁内。
3. 登记事务持锁后重新读取当前 attempt/action、前驱 execution_id/generation/receipt_hash
   和终态。身份未变且匹配成功时才登记 Step3；并发暂停/接管或前驱变化则拒绝。
4. 重入返回同一已登记执行；回执未到仍返回前驱待确认，不能凭重试新建 generation、
   伪造 success、延长 deadline 或重复派发 Master。

WGS 的正常入口和当前 P0 恢复早返回入口必须同时覆盖，不修复废弃的旧版 Resume。
GATK 保留现有接收和 wait；只有共同缺陷实际影响其调用点时才做薄适配，不能以统一
为由再做一遍前驱同步。只调整已有事务边界，不引入新回执数据库或后台同步服务。

### 3.4 全阶段状态投影与清理保护（审查 R4）

UE-04 F4 的 finalize 既需要已接收的当前Step6 receipt，也需要同执行native完整成功
snapshot，避免business status先写而私有control receipt尚未生成时被直接POST越过。
沿用内部认证调用和已有`worker_observation`载体，由DAG受限只读observe后传入；后端
锁内检查当前attempt/action/ref、成功状态及evidence_ref与实际receipt摘要，不新增route、
DB字段或私有读取权限。观察健康与业务终态独立，不能仅因degraded否定已验证的成功。
普通sensor和finalize共用现有snapshot语义，不各自扩展一个控制协议。

Step1–6 均将观察健康与业务状态分开，不仅保护 Step3。查询超时、断线、进程证据缺失
产生 unknown 时，保留最近一次同执行已确认的业务状态，并通过现有诊断字段标识待核验；
不能把这种保留显示当作新的成功证据。无需新增 DB 状态枚举或页面功能。

Airflow 失败回调、后台状态接收、传输租约释放、observer drain 和最终 writer 释放必须
核对当前 DagRun/action/attempt/execution/generation。仅凭 unknown 或 task 退出，不得
投影计算失败、推进后继、申请替换 Master 或释放仍可能活跃的写入/传输所有权。
已经持久验证的匹配终态仍按原成功/失败规则处理；真实业务失败不能被 unknown 长期遮盖。
过期回调只能报告过期，不覆盖新一代状态，也不释放新一代的锁。

共同 snapshot 桥接必须保留现有 Master UID/namespace/run-label、nested master、当前阶段
及 rule 进度字段。Run Tracker 的当前阶段优先级和 release-specific Phase 映射继续由平台
消费，不迁入 cce-pipeline、不回退到“启动已完成”或 Unknown。已验收展示直接引用
原证据；只有本次直接改变字段投影时才选受影响断言，不重新验收历史 phase policy。

### 3.5 公共 SSH 连接层（2026-09-30 用户批准，归 UE-05）

WES 当前批次已完成；Step5/6 先后出现的 banner 超时是 SSH 会话前故障，不能通过
重跑生信、增大 Master TTL 或复制批次热补丁解决。保留 OpenSSH 和受限入口，不为此
增加 SSHOperator/provider 依赖。两 DAG 与当前 P0 的阶段派发/只读观察共用一份连接实现，
复用原 WGS pre-session allowlist；adapter 只提供已受信的命令、配置及原调用预算。

- 连接/握手默认30s，最多3次 SSH 连接，间隔5s/10s；OpenSSH ConnectionAttempts=1，
  避免内外层相乘。一次调用的总期限包含所有连接、命令等待和退避，不在重连时重置。
  新公共短派发使用局部120s上限；已有更短调用上限或适用的原 deadline 优先裁剪。
  已有只读 probe 的30s/150s调用上限保持原语义，不改内部120s云查询预算。没有已冻结
  absolute 值时不补造全阶段期限；握手等待与命令/计算时限不是同一参数。
- 只有 exit255、空stdout、完整stderr均命中已核实的会话前暂态诊断才允许再连。
  认证/host-key/权限失败不重试。混合或未知输出、命令超时、会话后中断、回复丢失均
  不满足写命令重放条件。总预算耗尽不意味着远端失败/静止；日志不泄露凭据或临床输入。
- 同次重连复用原 command/execution/generation/request_hash，不再次登记、不增加恢复
  预算、不创建新 attempt。派发结果不确定时复用 UE-04 同身份 observe；accepted/running/
  已有终态接回，unknown 保持待核验，不根据缺文件或失联直接再发。已有 P0 新派发许可
  仍由原受鉴权仲裁、最新事实及预算决定，连接层无权授予。
- SSH 只提交后台工作或执行短只读观察，不承载上传/分析/下载全生命周期。不加 DAG
  整任务 retries、不建立常驻重连服务，不改变 pool、lease、锁、TTL100 和正常 Step1–6。

代码 owner 是原 Airflow agent；native owner 只配对检查现有 submit/observe/幂等语义，
没有实际 native 缺口不改 cce-pipeline，也不在 native 复制 SSH 重试。范围限当前阶段执行
及其现有 P0 调用，不扩展到 metrics/scanner/邮件/Step7 或服务器 sshd 配置治理。
验证只补共享连接差量和两 adapter 必要接线；未知派发原有测试直接复用，不重新运行全链。

## 4. P0 与后续运行控制

### 4.1 P0 必改项

UE-05 内部快照通道已于2026-09-30由用户明确批准：沿用现有认证 route/request，
可选执行快照须复用 `cce.stage-execution.snapshot.v1` 和 UE-04 校验；字段不得与
带 nonce 的 Worker probe 混用。消费时绑定当前 DagRun/action、attempt、冻结请求、
execution/generation及实际匹配终态回执，不能只信调用方声明 state。缺失/错代/unknown
不给解除计算互斥或提前清理的许可；也不能以 blanket 延期掩盖已验证真实失败。
不扩公开 API、不新增数据库字段或恢复状态机；实际字段与受影响调用点写入 docs/05。

- 注册和 request 读写桥接：生产者与消费者共同选择协议，不能只将 Step2/6 填入异步列表。
- 当前受支持执行的进程判断收敛到公共记录；不新增旧同步 reader 或旧 Resume 回退。
- Step4 发布重连、Step3 监控重连、终止回调、租约/目录锁释放共同消费新的执行身份。
- 当前 P0 手动与自动恢复使用同一动作仲裁；同受支持运行的前序 queued 动作不得永久
  阻塞已核验后继，活跃动作仍互斥。这不是为已废弃 Resume 恢复执行能力。
- 保留当前 Master 解析、generation fence、原始 deadline、恢复配额、CAS 和完整持久证据。
- 启动前超时证据、START_SENT 不确定性及 TTL 后恢复边界不在本轮放宽。

手动恢复动作必须区分三个事实（审查 R2）：**派发是否确认、对应计算是否终态、后续阶段
是否仍受该动作授权**。`queued` 仅是派发记录，既不能永久等同于活跃计算，也不能全部改成
success。backend 在原运行锁/事务内，用绑定到当前 DagRun、attempt、阶段 execution/generation
的可信计算终态，结束该动作的计算互斥角色；动作本身及 downstream scope 保留用于后续授权。
单凭旧 Airflow DagRun 失败或原始 action 存在时间，不能确认云端计算已停止。

当前 P0 阶段续跑后出现符合白名单的真实 Step3 失败，且现有完整证据/静止证明、策略、预算和
deadline 都允许时，自动恢复只能预留一次剩余额度。重复轮询复用该预留；未知派发、仍活跃
的计算、错误代次及 pause/delete fence 继续阻挡。此判定同时用于动作轮询与预算仲裁，不能
只修 Step4 的旧动作特例，也不增加恢复次数或移除互斥保护。

历史缺失 policy/timeout、禁用自动恢复或 attempt 不匹配的记录不补造预算；正常查询重连仍
与计算替换授权分离。原生初始 pre-START 恢复的窄边界按已有能力处理，不把 WGS 的
generation1 特例自动推广为 GATK/其他流程的任意启动恢复。

### 4.2 控制语义与扩展点

Step6 收尾边界补充（2026-09-29）：结果已物化与目录所有权已安全释放是不同事实。
物化校验完成后，最终清单查询的 typed 暂态失败只能在现有单一查询预算内重读，不能
重复物化、按 task/DagRun 状态伪判业务成功或提前释放。跨执行接续仍需当前身份/归属
及真实释放凭据；锁/journal 缺失且无匹配可信释放证明时保持待核验，不凭404/空清单
重建锁或补成功回执。UE-04 保留进度并约束 finalize，UE-05 收敛实际最终查询/释放入口，
UE-06 只核对安装接线。不增加锁找回功能、DB状态或自动恢复预算；源代码定位和唯一
差量证据要求见实施计划 UE-05。该补充不授权改动已冻结生产批次。

由 adapter 提供受信 `observe_work`、`request_quiescence`、`resume_checkpoint` handler，
返回静止证据/检查点或明确不支持；没有 handler 不显示可用控制按钮。
公共内核负责操作身份、串行仲裁、停止优先级和状态，不让 adapter 自行更新平台状态。
上述未来 handler 仅记录语义，不在本轮开发/测试。现有 P0 的控制 fence 继续生效；
不为了未来暂停功能新增接口、控制状态机、第三流程演示或独立控制故障测试。

本轮必须留下可复用的控制基础，而不只是让正常流程跑通：每阶段操作绑定同一执行引用，
可解析到实际本地进程/云端 Master 与 Worker；业务终态、观察健康和写入静止分别表达；
已完成阶段/断点及停止仲裁使用持久记录；下游派发与接管沿用同一当前身份/fence。
后续暂停/续跑/删除据此判断，不绑定某个 Airflow task 名或“一个 task/两个 task”的形状。
暂停 observer 不能证明云端暂停，task 超时不能证明可删除；具体停止和删除 handler 仍由 RC 实现。

| 操作/阶段 | 约束 |
| --- | --- |
| 请求暂停 | 先持久阻止新阶段和自动恢复派发，再核对正在执行的工作；中途断线保持暂停中/待核验 |
| Step1/5 | 停止受控传输，保留可验证断点；重入验证 checkpoint，不能仅依赖同名文件 |
| Step2 | 仲裁 CREATE/START 中途的不确定结果；停止请求不能与新 Master 创建并发 |
| Step3 | 先阻止 Master 新派发，再处理精确 Worker；仅停止 observer 不能报告 paused |
| Step4 | 不能安全取消的外部发布等到安全边界，不能强行杀死后声称已回滚 |
| Step6 | 等待安全文件提交边界，残留不能变成有效 MATERIALIZED 标记 |
| 续跑 | 活跃执行接回；已静止的失败执行按完整证据恢复，同 analysis/attempt/config/output，跳过成功阶段 |
| 暂停完成 | 所有相关写入已静止且证据持久化；保留目录归属，不释放给另一个运行 |

替换 Master 使用新 UID/计算 generation，不要求原 Pod 存活；缺少证据仍不能自动替换。
取消、云端清理和平台删除保持独立操作，不能作为“暂停”的隐含副作用。

### 4.3 错误覆盖与 TTL 边界

保留现有 Step3 白名单：Worker CREATE transport、admission timeout、storage RPC unavailable，
以及精确 HeavySlot/Worker-Pod read API unavailable；仍要求冻结授权、原预算/deadline、绑定
终态和完整工作负载证据。统一执行器修复的是这些错误的恢复通路，不把所有失败变成可重试。
BackoffLimitExceeded 不是独立根因；OOM/SIGKILL、START_SENT 不确定或终态证据缺失不能据此
自动替换。缺 FASTQ、校验/配置/权限或规则错误需要先修正；PVC 丢失不自动重建绑定。

Master/Worker/helper 保持 TTL100。TTL 在 Job 终态后计算，不等待平台接收证据；持久终态与
Worker 快照应使后续操作不依赖旧 Pod 存活。硬崩溃或失联跨越 TTL 后证据不足，保持 unknown/
人工核查，而不是延长 TTL、假定404成功或重建全部计算。本轮不增加 Master 保留时间。

**TTL-DOWNSTREAM（UE-04）：** 持久证据不仅服务失败恢复，还必须接入正常下游。
本次 WES 实际故障为普通 Step4 发布及 Step5 日志导出仍查询已回收的成功 Master。
优先复用 native 现有终态收集、`_recovery_native_success` 和 `_bound_downstream_master`
的正确实现；通过受信 resolver 让两个 gate 的普通/受支持 P0 路径共用它，不另造业务
成功验证器。只改缺陷可达的入口，不因统一而重写发布、下载、日志或落地算法。

Step3 提供可推进前驱时，真实终态应已持久可读并绑定当前选中计算的 UID/Pod、attempt、
计算 generation 和冻结摘要；下游 stage generation 不要求与计算 generation 相等。
缺失则补收集原真实终态或返回待核验，不抹掉已证实计算成功；平台 success、规则100%、
MIRROR_COMPLETE 和404均不是替代证明。有充分证明且确实已回收时可发布/导出日志；
在线身份/活跃/失败等冲突仍阻止推进，查询错误不可当作不存在。保留必要精确查询和
原有导出核验，不为每次接续增加全云 inventory、helper Job 或第二份业务状态记录。

分析成功后的下游失败属于发布/下载接续，不要求替换 Master、重传或消耗 Step3 重算预算。
UE-05 沿用既有 action、fence、幂等及授权边界；UE-06 核对安装模块和真实普通/恢复入口。
不新增公开协议字段、错误白名单或自动恢复次数。现有冻结 WES 的补丁按独立授权处理，
不补造历史登记或自动迁到0.8.9；将其源码差量/应用方式/退役条件列入候选交付清单。

## 5. 公共查询及目录探测修复

### 工作负载查询

成功收尾、手动恢复、自动恢复的活跃 Worker 等待和精确绑定检查共享查询算法。
采用 run-label Job/Pod 完整清单、namespace Job/Pod 完整清单及当前 Master 精确 GET，
建立内存索引，消除逐个已回收 Worker 的网络往返。每次完整证明通常 5 次查询；
CAS 前需要的新证明重新取数据，不缓存旧证明。原 Master/Pod 被 TTL 回收后，匹配身份且
足够完成失败分类/终态证明的持久记录可替代在线对象；不要求旧 Pod 必须存活。
缺少本次操作必要的持久证据仍阻断，404 本身不是成功或静止证明。

native `_recovery_query` 增加固定 namespace list 形式，沿用类型化错误与 4MiB 响应限制；
平台不得绕过它另调 `_run/_kubectl`。总预算 120s、单查询 30s，受原阶段剩余时间约束。
超过大小上限、分页未完整或结构不可解析均拒绝，不谎报空清单。对象冲突仅针对声明属于
当前运行，或与绑定 name/UID/owner 冲突的对象；namespace 中无关批次不能阻断当前批次。
查询间合法变化维持 InventoryMoved；活跃对象只允许观察等待，不能通过恢复/释放门禁。
优化也适用于当前 `probe_bound_workloads`；精确身份和必要证据要求不降低，不添加废弃入口适配。
不宣称支持无上限集群规模，本轮不增加分页子系统。

审查 R3 的全部消费入口必须接入：`collect_failure_evidence` 的失败终态收集、
`RecoveryCapability.inspect` 的手动/自动恢复证明、自然活跃 Worker 等待、
`probe_bound_workloads` 及最终 writer release。不能只保留 WGS 成功路径的 bulk opt-in。
活跃清单可用于观察等待，不代表通过替换门禁；将活跃观察与恢复/释放许可分开，
并在 CAS 需要的新证明处重新查询。确需补充且对象仍存在时才取原 Master Pod 诊断，
已持久化且满足当前判断的诊断不重复远端读取；“通常5次”不是省掉必要诊断的硬限制。
网络查询不随已回收 Worker 数线性增长。普通进度观察不得因此每次执行全云清单或 helper Job。

### 目录探测

native 公共只读 probe：首次加最多两次重试，间隔 2s/5s；单操作最多 30s，
包含 UID/存储复核的总探测预算最多 120s，并受现有 stage/helper 原始 deadline 限制。
2026-09-29 调用点澄清：这里的120s是一次只读探测的局部上限，不是新增阶段期限。
普通 Step1/6 没有已冻结 absolute deadline 时传 None，维持3.1的原 task/sensor/handler
计时语义；不能把 Airflow 超时反算成阶段原始期限，也不能据此认定后台 worker 已停止。
仅复用对该操作实际适用的原期限，不因字段名称相似改变作用域。Step4 opt-in
`publish_deadline` 是 fresh launch 的派发门禁，在现有 `worker_command` 持锁处校验；
不是后台业务完成期限，不传给普通 writer probe，不阻断到期后同执行的只读接回/观察。
没有其他适用原值的调用点不添加空泛可选参数或配套平台接线。不要为了凑齐期限而
改变已启动 worker 的行为；不新增 wire 字段，不用调用时刻加 timeout 补造阶段期限。
helper 保留已有生命周期，重用不重建、不重新启动其600s；不能以该600s替代原阶段期限。
已确认的期限接线仅是 `cce_paired_runtime.resume_registered`：认证恢复请求后，复用
现有 `deadline_epoch(payload)` / `monitor_wait(payload, 0)` 的 `cce_recovery_deadline`，
通过 writer 的内部 `probe_deadline_epoch` 约束同一恢复操作里的目录检查，并与
`RecoveryCapability.compute_deadline` 保持同值。普通 Step1/4/6 不消费它；不扩展请求契约。
仅超时、连接中断和明确临时服务错误可重试；认证、权限、命令/响应错误及身份冲突立即失败。
每次使用同一绑定 Pod，前后重新核验 UID、挂载及存储绑定，不使用历史 probe 结果。
不重发 CREATE/START/DELETE、不新建 helper 来重置预算。清理保留精确对象及原有 TTL100。

## 6. 废弃能力退出、部署和权限

- 新协议在一次运行首次登记、Step1 写入前冻结；后续所有阶段及恢复沿用，不随部署变化。
- 已废弃的旧版 Resume（含跳回 Submit/重新 prepare 的旧入口）、旧同步恢复和 legacy-v2
  执行 reader 不纳入新方案开发、兼容分支或重放测试；新路径只支持当前公共契约。
  不因相同名称而删除当前 P0 的 `resume_stage` / 同 attempt 断点续跑能力。
- 历史记录与证据保留现状，已有只读展示无需为本方案重写；这不是维护可执行旧协议。
  缺少当前必需字段的执行请求明确不支持，不补字段、不伪造 worker.json、不重算原摘要。
  当前仍有效的 `orchestration_contract_version=2` 不能仅凭版本号被当作废弃 Resume。
- 测试端使用隔离候选。将来切换前若发现仍活跃且依赖退出路径的执行，停止切换并报告，
  不迁移它、不临时加兼容层。历史成功项目不因新方案重跑或重新验收。
- 回滚保留原制品与配置，不在新代码内维护双执行器；候选执行未静止前不得切回旧制品，
  新协议记录不能交给不认识它的程序，也不能删除控制记录解除阻塞。
- WGS 业务权限沿用环境边界最新 2775/0664/0775 契约；GATK 保留自己的已批准权限。
  私有凭据/进程控制文件保持私有；不统一改成 root/0600，不递归改既有输出。
- native 制品由原 owner 在 nipttest 相关批准环境按 SOP 处理；本轮无 WGS 仓库安装、
  Snakemake 插件改动或 Master 镜像重建需求。按用户最新要求，候选版本为 **0.8.9**，
  源码提交在 owner 核实的对应 release 开发分支，记录 commit/制品 SHA；不擅自追加后缀
  或覆盖生产0.8.8。若实际依赖迫使改变这些边界，停止并报告。

## 7. 验收与未交付项

用户选择：BS10610 真实模块 + synthetic 证据最小验收、测试端安装和接口检查；
不创建云端 Job，不提交真实分析，不运行本地/全量冗余测试。

验收以“已有证据复用 + 本次直接变更的缺口”为准，不按 UE 任务数组织六轮全链路测试：

- 已验收 Step1–7、P0、GATK 异步链路、权限、TTL、进度/Phase 不重开整体验收。
  引用既有结论即可；提交/制品 SHA 改变不自动使无关结论失效。
- 对新增或直接改变的行为，先列“变更点 → 未覆盖断言 → 单一测试节点”，只补差量。
  共享内核断言测一次；WGS 测被迁移外壳，GATK 只在薄接入实际变化时补一个接入断言，
  不展开流程 × 六阶段 × 恢复方式 × 故障的组合矩阵。
- R1–R4 的必要结论仍需有依据，但能由原验收和未变代码覆盖的直接引用，不要求重新执行。
  275 Worker 是内存 synthetic 性能夹具，不创建云 Job；重试用假时钟，不真实等待120s。
- UE-06 仅核对安装候选、pin 和真实入口接线，引用前面已有证据；不再运行第二轮
  WGS/GATK 六阶段提交/等待/恢复或全套故障矩阵。
- 删除旧协议/废弃 Resume 重放测试要求。第三 adapter 演示和未来控制 handler/fence 新测试
  本轮不做；保留当前有效 P0 的互斥、安全及失败许可边界，未来控制验收归 RC。
- phase policy 未改则不重跑4.2.0/4.2.1/4.2.2历史映射；只有投影被直接改变时选择
  必要的当前4.2.2断言，且同一断言只验一次。

审查缺口绑定下列证明责任；实施时只对尚未覆盖的直接变更补测，不叠加整套回归：

| 审查项 | 必须证明 | 实施归属 |
| --- | --- | --- |
| R1 | 已验证当前前驱不重复接收；缺失/滞后按需接收后登记同一 Step3；缺失/错代拒绝，锁内身份再核对；只覆盖当前受支持入口 | UE-04 |
| R2 | 手动恢复后的可信计算终态能解除旧计算互斥，符合条件只预留一次原预算；活跃/unknown/停止请求仍拦截，下游授权保留 | UE-05 |
| R3 | 各受支持入口共用有界查询；无关批次不阻断，TTL 后充分持久证据有效；CAS 用新证明，必要诊断/冲突/完整性检查保留 | UE-03 |
| R4 | 六阶段 unknown 不触发失败推断、派发或提前释放；匹配真实失败仍显示失败，旧回调无效；进度/Phase 不回退 | UE-04 投影、UE-05 回调/清理 |
| TTL-DOWNSTREAM | 正常 Step4 与 Step5 日志入口在真实 Master 回收后消费匹配终态；旧镜像/未知查询不放行；实际 gate 接入同一路径，无重算/重传 | UE-04 单一共享差量夹具及必要薄接线；UE-05/06 复用，不重验历史 TTL |

完成仅代表公共执行/恢复基础及测试端兼容通过。真实云端暂停、跨故障网络条件、
完整 RC API/UI、生产推广及新流程上线仍未验收。本轮不把它们标为完成。
