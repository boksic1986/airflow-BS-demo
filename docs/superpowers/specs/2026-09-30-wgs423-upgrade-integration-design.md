# WGS 4.2.3 升级与平台接入设计

日期：2026-09-30。状态：用户批准的设计，文档落地；**不是代码实现、运行验收或发布记录**。
实施顺序见 [W423-01–06 计划](../plans/2026-09-30-wgs423-upgrade-integration.md)。

## 1. 范围与唯一职责

本轮只修订研发文档、旧计划和 SOP。产品代码、部署、重新分析、真实 LIMS 发送均不在本轮。
WGS 正式源码在服务器 `/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0`，目标分支
`dev_CJC_4.2.3_cloud`；本地 `D:/pipeline/WGS-noncoding-model` 不是正式源码。

WGS 仓库对应入口：`docs/WGS_4.2.3_UPGRADE_DESIGN.md`（原生职责）、
`docs/superpowers/plans/2026-09-30-wgs-4.2.3-upgrade.md`（owner 实施顺序）、
`docs/WGS_4.2.3_CCE_SOP.md`（发布门禁）；旧 `docs/CCE流程SOP.md` 与 README 指向新入口。
WGS 文档引用本设计的公共接口，平台只引用 WGS 冻结的原生合同，不各自维护公共执行器副本。

| 所属 | 唯一职责 | 不应复制的逻辑 |
| --- | --- | --- |
| WGS | 原生样本选择、FASTQ 合成、QC 规则/配置、产物布局、固定 LIMS 入口与接收合同 | 不另造平台执行器或 Rules API |
| native / cce-pipeline | 公共后台执行、同执行观察、重复派发保护、身份和持久终态验证；Master 参数集成 | 不决定生信合成条件或临床 QC 放行策略 |
| Airflow / backend | 受信 adapter 调用、审核鉴权、证据摄取、投影与动作登记 | 不复制合成算法、native 成功判定或两套规则状态 |
| frontend | 展示既有 API 的规则、合成、QC 和审核回传状态 | 不推导未发生事件、不传命令/地址、不自行判定 QC 放行 |

沿用 [公共执行器设计](2026-09-28-unified-stage-execution-design.md)。异步 prepare 是 UE 完成后的
4.2.3 增量，不重开 UE-01–04，不插入 UE-05 收尾，不为废弃 Resume 增加兼容。
文档版本、候选版本、已安装版本分别登记；旧批次继续使用各自冻结制品，不迁移历史运行。

## 2. 证据与发布组合

本轮 WGS owner 经 BS10610 复核的文档编辑起点为 `dev_CJC_4.2.3_cloud` /
`1b7047d46147e258b1c4cd8ec27fdf3fc157afc0`；业务基线仍为
`f27a9ca1e674e9f7e4fae3e7d6f7e72b5efe4204`。这不是完整业务4.2.3整合。
旧 CRAM 计划记录的 `release_V4.2.3` ref `2042425a` 仅作历史来源，实施前需重新核实稳定 ref，
本轮未 fetch/merge。当前4.2.2制品与未来4.2.3发布分别登记，不能因分支名推断升级已完成。

下表引用已有报告，不要求重复执行。报告证明范围之外保持未验收。

| 证据 | 已证明 | 不能据此宣称 |
| --- | --- | --- |
| `master-rule-status-20260929/ACCEPTANCE_REPORT.md`，runner `ad7bd2d9c5fa62cb7c3fc330b6b92ca3dce45bfd` | Master 参数修复，8 项定向测试及现用 Sentieon Group CCE 双规则事件 | 最终公共执行器配套镜像已完成 |
| `wgs422-group-logger-smoke-20260930/REPORT.md` | 另四类现用 Worker 双规则 smoke；CNV 现用 Worker CCE 事件 | Report/VEP 各自真实 CCE/生物学全链已验收 |
| `airflow-rule-timing-20260930/BS10610_AIRFLOW_RULE_TIMING_TEST_20260930.md` | 真实 8 事件摄取为 2 规则；重复新增 0；隔离 Rules API 个体时间 | 4.2.3 绑定、真实 PostgreSQL/页面时区或中间运行态已验收 |
| [旧 QC 交付](../../releases/2026-09-17-qc-all-counts-bs96.md)、[QC2 合同](../../2026-09-18-wgs-qc-two-source-contract.md) | 已有指标列、单位、数量补充与双来源设计可以复用 | QC2 已实现或 4.2.1 阈值自动适用于 4.2.3 |

前三份原始报告本地归档根为 `D:/pipeline/task-artifacts/`，BS10610 原始证据根为
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/` 的同名目录。
旧候选 Master digest `8c6090bafe7f0db742fb934fc68327a5afe18bbc9683128168f22a501e7d8312`
用于上述验证，其旧资产组合不能直接作为最终 4.2.3 公共执行器发布。
事件 SHA256 为 `cba66784947bd89161fb72e62bae3941f213d29c6bfea4b98e679403953f7458`。
这些是可追溯历史证据，不是本轮重新读取生产环境的结论。

最终发布清单分别填写并互相绑定：

1. 稳定的业务 `release_V4.2.3` commit 与实际整合后的 cloud commit。
2. WGS bundle、原生 merge/QC/回传脚本和配置摘要。
3. 公共执行器源码、wheel/安装产物及实际 selector/pin；不能只写 `0.8.9`。
4. 含已验收 logger 参数修复的最终 Master digest、每类实际 Worker digest 和 profile 摘要。
5. QC policy ID、原生来源摘要、适用样本规则和平台实现 commit。
6. 测试/生产各自实际挂载、有效门禁、批准记录及回滚组合。

以上未最终冻结的项保持 pending，不填写猜测 SHA。凭据配置问题、资源文件缺失及 release
仍在变化的风险保留为发布前置条件；不得据本文轮换凭据、替换资源或原地改冻结制品。

## 3. Group 内逐 rule 状态与时间

关键修复为 Master 显式传递 `--kubernetes-rule-status-dir` 与
`--kubernetes-rule-status-attempt`，与 Master logger 的路径/attempt 一致。
最终 Master 必须集成已验证修复并与最终公共执行器配套，不能因 COPY 公共 runner 丢失参数。
五类现用 Group Worker 暂无必须重建的证据；撤销“全部重建才能采集”的硬前提。
仅将来出现精确镜像/接口不兼容证据时，定点修对应类别，不为统一版本而重跑全部 smoke。

复用 Worker 事件、规则实例标识、持久摄取和 `GET /api/runs/{analysis_id}/rules`：

- 从已登记的规则计划展示等待；事件缺失且没有计划则是证据不足，不猜测 queued/running。
- Group 被调度不表示所有成员同时运行。逐条开始、成功、失败来自该规则事件。
- 起止时间沿用 Rules API 的 `started_at` / `ended_at`，取自对应规则事件；不以 Pod、采集、
  整组完成时间填空，不为命名差异新增第二组 API 字段。
- 沿用现有 run/attempt、执行身份、Worker stream/job/规则实例关联；logger attempt 不能当成
  Master generation。不同执行代次不能拼成一条时间线。
- 重复摄取、刷新、迟到的旧代次事件不得改写当前代次；同一实例已确认事件时间不能被
  观察时间覆盖。冲突证据保留来源并显式提示，不按到达顺序任意改历史。
- 保留单规则页面列与筛选，只补必要 group 关联信息。已成功但历史未采集开始时间的规则
  保留缺失原因；不追溯伪造。状态事件也不能替代 native 分析成功回执。

后续只补已有验收未覆盖的分段回放等待→运行→终态/失败、代次与迟到重复边界，以及页面
与事件/API 时间一致性；不重新逐类启动已验收镜像 smoke。

## 4. 长 prepare / FASTQ 合成

### 4.1 受信准备登记与阶段门禁

当前源码 `prepare_analysis` 仍同步执行。已有等待 task 不代表 node 上已具备公共异步 handler。
W423-03 接入 UE 公共执行器，不复制旧 dispatcher，也不单靠 SSHOperator/长连接解决。

顺序固定为：冻结准备输入 → 短连接登记/派发 → 后台判断并合成 → 最终样本清单/bundle/prepare
receipt 全部成功 → 生成最终 batch binding → 正式 Step1 上传。**不增加合成同时预上传。**

prepare 前尚不存在最终 batch binding，不能复用一个要求已完成 bundle 的 resolver 作为前置：

- 受信 prepare resolver 使用已冻结 release、样本表内容摘要、merge 配置、批准输出位置及
  当前 analysis/attempt 身份登记；handler 和执行入口由服务器 allowlist 选择。
- 使用公共执行登记/同执行观察/互斥幂等能力。重复请求观察同执行，不能再次创建合成任务。
- WGS 负责原生合成判断；平台冻结并透传选项，不从 FASTQ 目录推断替换样本范围。
- prepare 成功后才把真实最终样本选择和 bundle 绑定到此执行；样本选择不符合已批准输入合同
  时停止，不悄悄按目录内容扩大分析范围。冻结文件变化不能通过覆盖摘要继续同一执行。
- 合成输出沿用 WGS 原有完整性依据复用；未完成文件不得进入上传清单。不新建 gzip 字节级
  续写算法。最终清单/bundle/receipt 任一缺失都不能放行 Step1。

### 4.2 等待、期限与展示

Airflow 短连接提交后使用现有等待任务观察；传输断开后查原 execution，不让 SSH 持续等待
约 20 分钟/文件的合成。不把“请求可能已到达”当作可再次 dispatch 的证明。

连接/握手预算与业务期限分离：普通 prepare 沿用当前期限；merge-enabled 新请求使用可配置
业务期限，**默认 24 小时，首次登记冻结绝对 deadline**，重连不重置。到期/观察超时进入明确
需核实状态；未证明后台停止前不能标记业务失败、取消进程或新建执行。
业务重试继续遵守公共身份/终态/锁合同，不增加宽松回退。

展示 `Merging FASTQ`（合成中）、完成/总文件数、当前安全文件标识、更新时间与证据新鲜度。
计数来自 WGS 真实进度证据；无可靠字节进度不显示百分比。不能把等待界面进度当作成功回执。
新增字段的精确名称由 W423-03 在现有 prepare 请求/回执合同上最小冻结，不另起并行状态 API。

## 5. QC：准确版本绑定与双来源

源码检查发现 policy 只登记部分 4.2.1 组合，未覆盖截图 `wgs-4.2.2-441d5e7`，因而可能出现
“有数值但逐项 unknown”。这是源码依据，**不是已核验生产实际挂载或重现生产根因**。
修复不能通过版本前缀、默认通过或复制旧阈值抹掉 unknown。

接续 [QC2 原合同](../../2026-09-18-wgs-qc-two-source-contract.md)，保留已完成的列、单位、
SNV/CNV 数量补充和来源汇总；4.2.1 的样本 predicate/阈值只描述旧版本，不自动继承：

| 来源 | 适用与用途 | 边界 |
| --- | --- | --- |
| 批次 `QCstat.tsv` | 所有选中样本，常规临检 | 原生普通 QC 值/判定，不被补充来源覆盖 |
| 批次 `multi.QCstat.tsv` | 仅冻结 release 声明适用的罕见病样本 | 独立 g2/WgsMetrics 值/判定，不用同名普通深度或覆盖度代替 |

WGS owner 提供冻结 4.2.3 原生 QC 脚本/配置及适用规则，平台准确注册对应 release/policy。
保留现有受限 artifact 解析和选中样本匹配。原生来源汇总状态与平台逐项判定分开，平台
不能擅自修正原始 warn；同一指标附带来源、单位、适用性、判定与安全原因。

显示语义至少区分：数据缺失、策略未登记、不适用、仅供参考，以及明确 pass/warn/fail。
具体 API 编码由 QC2 接线复用既有字段并补足原因，不能把所有情况渲染为相同 unknown。
普通批次隐藏罕见病标签；适用但缺补充证据时保留标签并说明缺失，不冒充普通来源已经满足。
文案沿用页面统一英文（Routine clinical / Rare disease），而非再建中英混用状态体系。

同一证据内容/摘要只解析一次供同批页面复用；变化后按真实证据版本更新，不能用旧缓存
覆盖新 QC。列表读取已存摘要，不在每次列表刷新重新加载所有 QC 文件或逐样本重复解析。
此项仅收敛 QC 直接消费链，不扩展成全站性能架构改造，不修改原生阈值或 GATK QC。

## 6. 人工审核与 LIMS 回传合同

WGS 临检 `Step2_upload.sh` 不等于 CCE Step2。Run Detail 的 Result delivery 区域使用
`Review and send`（审核并回传），不是云资源释放按钮；Step7 清理保持独立。
当前业务 QC 放行标准及可靠接收合同尚未确认，能力默认关闭。

### 6.1 拟议动作接口（未实现）

`POST /api/runs/{analysis_id}/delivery-actions`，受鉴权并进行运行范围/审核权限检查。
必需 header `Idempotency-Key`；复用现有动作登记与读取，不另建通用恢复框架。

| 字段 | 合同 |
| --- | --- |
| `attempt` | 必须为当前受审核的分析尝试，不接受跨 attempt 套用 |
| `expected_revision` | 与服务端当前审核/交付状态一致，防过期页面 |
| `result_manifest_sha256` | 绑定审核的已落地结果清单 |
| `qc_snapshot_sha256` | 绑定审核时的 QC 来源、判定与策略版本快照 |
| `review_decision` | 明确审核决定；服务端 allowlist，具体枚举与业务策略一并冻结 |
| `review_note` | 审核意见，受长度、权限和隐私约束，不进入公共日志 |

审核人来自登录身份；样本范围、LIMS 目的地、固定脚本和凭据来自服务端冻结配置。客户端
不得传任意命令、地址或另选样本。相同 key/相同冻结请求返回同一动作；相同 key/不同请求
拒绝，不再发送。重复点击、并发页面不能产生第二次副作用。

服务端在登记/派发边界原子核对 revision、结果/QC 摘要、审核权限、分析成功及真实结果落地，
并执行独立业务放行策略。**策略未配置返回清晰不可执行原因且不派发**；本设计不决定异常
QC 是否可豁免、不默认放行，也不把缺数据当作已批准。
接受后异步返回动作标识/状态，前端按既有动作观察方式显示。精确响应/错误编码在 W423-05
实现前补入本合同；未实现前不得宣称 route 可调用。

### 6.2 回执与独立生命周期

- 复用现有动作记录及 `downstream_release` 投影。原状态 PATCH 只是登记，不能作为实际发送。
- WGS 提供固定入口、退出语义与接收回执合同；平台负责审核/鉴权/派发/展示，不解析日志
  中模糊的“success”或仅凭进程 exit0 断言 LIMS 收到。
- 可靠接收确认必须能对应审核动作与冻结结果/样本范围；接收侧去重/查询能力在启用前明确。
  请求超时但可能送达时进入待核对状态；未解决响应不明之前不自动重发。
- 分析成功、结果落地、回传成功分别记录。回传失败不改写已成功分析；前端显示回传独立错误。
- 业务策略或确认合同任一未明确则后端拒绝执行，UI 隐藏或禁用并给出原因；不能只有前端禁用。

## 7. CRAM 布局与发布边界

复用 `D:/pipeline/task-artifacts/wgs423-cram-delivery/IMPLEMENTATION_PLAN.md` 对应 WGS 正式
计划：CRAM 独立 payload，CRAI/CRAM MD5 在结果包 `00_PreCalling/`；manifest 只列实际传输
对象。Step5 校验，Step6 解包/硬链接还原，保留路径、成员、冲突、身份与原子性检查，不额外
重算 CRAM MD5，不重建另一套 Step5/6。W423-02 只接续尚未实现的 WGS 生产者布局改动。

固定最终组合只补受影响接口的一次集成核验；旧 smoke/P0 验收引用，不全量重跑。测试环境
遵守 [环境边界](../../34_TEST_PRODUCTION_RELEASE_BOUNDARY.md)，synthetic 证据放批准的
`WGS_test/cce-evidence`；不启动完整临床批次、不试发真实 LIMS。生产必须另行批准，既有
运行制品不原地更新。回滚是撤回新组合的启用，不删除数据、不重跑旧批次。
