# WGS CCE / Local / SGE 统一提交与监控设计

日期：2026-09-15

任务：`WGS-LOCAL-SGE-20260915`

状态：设计已确认，2026-09-15 已授权隔离实施；Task 1 部分完成，功能未启用。

设计基线：Airflow `93069eb`；实施 worktree 从 main `4b5234e` 创建。BS10610 已做只读测试环境核对，未核验或变更生产。

### 原生合同核对记录（2026-09-15）

WGS-pipeline 任务提供候选源码 `ba7b27276a55ed3ce1fb2efe81c99c89b52d0f8b`
（`dev_CJC_4.2.1_cloud`），不是已发布/已部署 release。现有 Airflow catalog
`wgs-4.2.1-cc9bde3` 不在本次核对中切换。候选源码仅作为接口实现依据。
可读源码快照在 `D:/pipeline/task-artifacts/wgs-native-contract-ba7b272/`，不含私有 prepare 配置。

- `prepare_wgs_batch.py` 的 analysis 支持 `--run-mode local|sge`；携带 handoff-request 时仍分 sampleinfo/analysis，不使用 all。保留原生 Haplotyper 默认及样本选择。
- `runtime.py` 生成的 Step1 原样透传附加参数；平台可附加 logger，但插件安装及 SGE job ID 事件尚未验收。
- `WGS_ATTEMPT_ID` 是原生执行身份，不等于平台 attempt；平台需按 execution/generation 给出唯一值。
- 原生 `log/step1.<ID>.metadata.tsv`、`.exitcode` 供绑定读取；后台启动返回0不代表分析成功。没有 Local/SGE JSON identity receipt 或 ANALYSIS_COMPLETE，不能虚构 CCE 成功标记。
- local/sge profile 沿用 WGS；SGE 由原生 profile 投递子任务。现阶段无需 WGS 新增接口或算法修改。

当前仅完成平台配置确认时的冻结基础代码及定向测试。新任务合同标记尚未接入创建入口；原生准备路由/产物绑定完成前不开放该能力。

## 1. 已确认目标与边界

网页和后端程序使用同一套平台提交接口，统一创建 AnalysisRun，展示实际分析样本、rule、日志和 QC。Airflow 管项目级流程，WGS 管生信规则、依赖和增量执行。

| 模式 | 运行身份与位置 | 平台执行链路 |
| --- | --- | --- |
| CCE | ctapa；现有节点 200 云端入口 | 保持现有 Step1–6 |
| Local | ctapa；96 或 97 | 启动、监控、结果采集 |
| SGE | ctapa；18 启动 WGS 控制进程，原生 profile 调用 qsub | 启动控制进程、监控集群任务、结果采集 |

本轮包括：平台提交、完整监控，以及通过项目监控入口进行命令行续跑后重新同步前端。

本轮不包括：

- Local / SGE 面板取消和续跑按钮、自动取消 SGE 子任务。
- 自动接管任意终端命令、历史项目导入或事后推断全部 rule 时间。
- 自动选择节点、自动分流扫描任务、新资源调度算法或新限额。
- WGS 生信规则、样本选择、家系、数据量阈值或 pending 算法修改。
- 新锁系统、数据库交接服务、离线补注册系统或数据库反写 pending。
- 生产部署、真实分析启动、已有运行任务迁移。

原生终端入口仍然可用，但绕过监控入口的运行不承诺平台完整同步。

## 2. 当前实现与实际缺口

Airflow 已有执行选择记录、Local 分支、受控 local runner、logger、observer 和公共前端组件。Local 仍存在 node97 专用的校验、SSH 调度和命名；不能仅打开 node96 开关就宣称接入完成。

SGE 在 `bio_wgs` 中仍调用不可用占位函数；`sge-default` 枚举存在不代表实际可投递。

现有 prepare 命令固定使用 CCE。Local runner 随后转换配置并重写项目启动脚本。新接入应直接调用原生对应模式的 prepare，不在平台维护第二套转换算法。

普通命令行续跑目前不能保证同步：Local 终态会停止 observer；阶段终态不可直接回到 running；直接运行原脚本未必带平台 logger。

本地 WGS 候选源码 `88cbe35` 已可见 `--run-mode local/sge/cce`、原生 Step1 参数透传及 SGE cluster-generic qsub 配置。这只证明接口基础存在，不证明目标 release 和节点已验收。实施时由 WGS-pipeline 任务核对选定 release，不直接采用候选目录或升级运行环境。

## 3. 提交和配置冻结

复用现有提交、样本审核、配置审核、执行确认和操作权限。后端程序调用相同 API，不因非网页提交而跳过确认。

模式和目标沿用现有字段：

| execution_mode / desired_mode | execution_target / desired_target |
| --- | --- |
| cce | cce |
| local | node-96 或 node-97 |
| sge | sge-default |

默认 CCE。自动扫描、自动分析及独立测试项目的现有隔离限制保持不变，本轮不扩大其可选目标。

新任务在 `prepare_analysis` 前选定执行目标，并与最终配置一起冻结。选择更新与分析准备之间使用现有 revision / 行锁校验，禁止并发生成错误模式的配置。配置生成后本 attempt 不允许原地跨模式或跨节点切换；模式变化必须走另一次明确提交，不能偷偷重跑 prepare。旧任务继续遵守其原合同，不批量重写历史。

平台传递原生 `--run-mode`、release、现有配置及所需输入；CCE 专用参数不传给 Local / SGE。WGS 原生 prepare 负责生成配置和 Step1，平台不重新实现运行 overlay、FASTQ 链接变换或样本选择。

共享输出默认仍为已配置的 `/sg2/50.ctapa/project/HWcloud/WGS_Clinical`，pending 继续通过其 `prepare/pending_samples.tsv` 交接。实际路径来自受控配置而非前端任意输入。Sample 仅保存 selected；交接台账继续只读投影。续跑不触发任何样本选择或 pending 更新。

## 4. 启动与命令行续跑合同

### 4.1 共用入口

平台管理的 Local / SGE 项目提供独立入口：

```bash
cd <本次已登记项目目录>
bash Step1_run.monitored.sh
```

首次由 Airflow 调用；失败后用户可执行同一入口。它由平台接入层生成，调用冻结的原生 `Step1_run.sh`，附加平台身份、logger、日志位置和执行状态记录，不覆盖原脚本。入口不得包含 token、口令或临床资料；认证和节点环境由受控运行配置提供。

Local 在选定的 96 / 97 上后台运行。SGE 在 18 上后台运行原生控制进程，由其 profile 调用 qsub；不再为整个控制进程增加一层 qsub，不把每个 rule 建成 Airflow task。

保留原生资源参数、增量执行和已有同任务保护。不自动添加 forceall，不因监控故障触发重投。脱离 SSH 的控制进程不能随请求断开而终止。

### 4.2 登记和防重复

复用 AnalysisRun、RunAttempt、RunAction、WgsStageExecution 及已有 observer 记录，预计无新增数据库表。

- 本次执行保留 analysis_id、平台 attempt、release、配置、执行目标和 workdir。
- 首次启动注册阶段 execution；明确的命令行续跑注册新 generation，保留原失败历史。WGS 自身日志执行标识与平台 generation 一一关联，不能将时间戳形式的原生日志标识误当平台 attempt。
- 启动前完成认证登记及必要检查：身份/配置一致、没有同一任务的活动执行、必要输入可用。
- 复用当前内部阶段注册接口；增加来源 `airflow` / `cli`、幂等操作身份和运行身份关联。公开执行选择接口沿用现有 mode / target / expected_revision 合同。
- 重复请求或回复丢失时按操作身份查询；已活动则返回已有执行，不再次启动。不确定时停止启动并提示核对。
- 平台接口不可用时，监控入口在分析启动前报错；不设计离线补注册。原生非监控入口不受此门禁影响，但不承诺前端同步。
- SGE 续跑前核对该执行已有的活动子任务。仍活动或无法确认时拒绝新的控制进程；不自动 qdel，也不按用户、队列或批次前缀批量处理其他任务。

### 4.3 监控恢复和终态

首次执行沿用正常 Airflow 路径。命令行续跑创建与新 generation 绑定的仅监控执行，复用本 pipeline 的监控/收集函数，不再次运行 prepare 或启动任务。保留原失败 DAG 的历史，更新当前监控绑定；旧 DAG、回执和旧 generation 不能覆盖当前执行。

复用 `local_analysis`，新增 `sge_analysis` 及其终态收集入口。只有真实启动证据才能显示 running；阶段排队期间不累计实际运行时长。证据和 rule 默认按当前执行过滤，历史可查询，不重复计数。

状态规则：

| 证据 | 展示与动作 |
| --- | --- |
| 已登记，尚未证明启动 | 等待启动，不宣称分析运行中 |
| 控制进程和本次运行证据有效 | 分析中；SGE 子任务可分别显示排队/运行 |
| 监控连接失败 | 监控异常，保留最后可靠状态，不判定分析失败 |
| 原生控制进程失败 | 当前执行失败，保留已有结果，不自动重新 prepare |
| 原生成功及必要结果证据齐全 | 转入结果/QC 采集，完成后显示完成 |
| 分析成功但采集失败 | 分析成功、采集异常；不重新分析 |

qsub 返回成功、qstat 中任务消失、进程 PID 消失都不能单独证明分析成功。SGE 证据使用原生 logger 和本次明确关联的 job ID；缺少关联时显示未采集，不扫描全队列猜测归属。

## 5. 前端与共用采集

- CCE 保持现有 Step1–6；Local 显示等待节点、分析、结果采集；SGE 显示控制进程、集群分析（含子任务排队）、结果采集。
- 复用当前任务、样本、rule、日志、QC、筛选和分页组件，不新建 Local / SGE 页面，不改变无关 UI 默认值。
- 展示执行方式、节点和当前执行身份；本次执行与历史可区分。
- rule 的样本、开始/结束及耗时仅使用真实证据。缺失不补造，排队不当作开始。
- QC 读取本次 release 的规则与项目结果，复用已有解析和展示。历史 QC 不伪装成本次新采集结果。
- Local / SGE 隐藏 OBS、SFS 释放、CCE Master、云端 resume_stage 等不适用的操作与卡片。

## 6. 分工、验收和发布

Airflow 平台任务负责提交、调度、监控入口、执行登记、observer、监控恢复和页面。WGS-pipeline 任务 `01a09149-ad9d-7e92-b98a-16d9cae075e2` 负责确认或必要适配原生 prepare 模式、参数透传、logger 和终态证据；不改生信及 pending 算法。

定向测试只覆盖本次接口、节点路由、SGE 分支、重复提交、命令行续跑、新旧执行隔离、监控失败和 QC 收集。前端运行相关测试及一次构建。不跑全套测试矩阵或完整 WGS。

BS10610 使用缓存环境和 synthetic 数据做隔离验收，不拉取 Docker Hub。后续另获授权后，一次 Local、一次 SGE 小型流程验证首次启动及失败续跑；SGE 使用两个轻量依赖 rule，资源和任务数遵守批准限额。node96/97 路由用定向测试覆盖，不为证明路由重复跑完整分析。

96/97/18 实际入口验收、BS96 部署和启用另行授权。生效前核对当前 release、运行身份和实际挂载；不得把本地候选源码当作部署证明。回滚先禁止新启动，保留活动进程所需采集，再恢复代码；不删除任务、pending、日志、台账和结果。

实现步骤见 [开发计划](../plans/2026-09-15-wgs-local-sge-platform-integration.md)。每次交付分别记录文档完成、代码完成、测试通过、环境启用，禁止互相替代。
