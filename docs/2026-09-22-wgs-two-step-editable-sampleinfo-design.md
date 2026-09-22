# WGS 两步提交、sampleinfo 在线编辑与自动分析衔接

状态：研发方案已整理，纳入待开发队列；未实施。日期：2026-09-22。
本次只形成文档；不修改生产、prepare 生信规则或运行数据。

待开发分支：`jiucheng/test/wgs-local-main-sync-20260917`。
依赖关系：本方案可以独立开发；提交后的停止／恢复复用该分支已有运行控制与
CCE 恢复方案，不将通用恢复系统作为在线编辑或两步提交的新增实现内容。

## 1. 结论与改动范围

建议将手动提交收敛为两个用户步骤：

1. **选择批次／导入样本表**：准备候选 sampleinfo。
2. **复核样本与配置，提交分析**：编辑并保存候选表，最后一次确认后，
   自动完成原 analysis 准备、结果筛选和上传分析，不再停在第三次确认。

关键不是隐藏第三页，而是将写 pending、生成分析项目等副作用，统一延后到
最终提交之后。最终提交前可以取消；最终提交后属于已提交任务，适用运行控制，
不承诺“取消提交”会自动撤销 pending／目录。两步 UI 不等于合并 Airflow task。

本次涵盖 WGS 手动新建与导入 sampleinfo 两种入口、相应 runtime 输入交接，
及与自动批次认领的必要衔接。WES/GATK、Local/SGE、生信筛选算法、自动扫描
就绪条件和已提交任务的停止／恢复机制不在此方案内。

## 2. 已核实的 Airflow 代码边界

检查基线：本地 main `9b381eb`；文档工作区基于测试分支 `9333160`。
不是对 2026-09-22 现网版本的声明；本次没有连接生产。

| 位置 | 现状与影响 |
| --- | --- |
| `docs/superpowers/specs/2026-09-03-wgs-three-stage-sfs-monitoring-design.md` | 第一阶段 sampleinfo，第二次确认调用 analysis，第三次确认才放行执行 |
| `backend/app/wgs_submission_service.py::approve_wgs_config` | 写配置批准和 preparing_analysis，开始实际准备 |
| 同文件 `approve_wgs_execution` | 只在 execution_review/approved 且存在最终分析样本时批准 |
| `backend/app/wgs_submission_cancel.py::_load` | 目前已有 config_review 取消入口；配置批准后拒绝。不能笼统认为第二页一进入就不可取消 |
| `scripts/wgs_runtime_gate.py::build_prepare_command` | analysis 显式读取 `<analysis_project_root>/sampleinfo/<batch_no>.sampleinfo.txt` |
| 同文件 `_prepare_handoff_request` / `_validated_prepare_receipt` | 输入 SHA256、当前 attempt/generation 与回执关联；不能在冻结后直接改原文件 |
| 同文件 `_run_prepare_sampleinfo` | 已有正常文件和有效当前回执可复用；缺回执时归档后重建；回执内容／身份错误仍失败 |
| `backend/app/wgs_auto_dispatch.py::dispatch_ready_wgs_intake` | 按批次和任务身份去重。已有手动任务可能被认领，文件存在不是唯一阻断来源 |

0919B 维护事实说明副作用位置：analysis 选中 0 条仍能增加 pending；不能以
“尚未上传”或“尚未生成项目目录”判断可以直接取消并删除。

## 3. 两步提交的具体行为

### 第一步：准备候选表

保留现有生成／导入能力。候选表准备成功进入第二步；明确显示它是候选样本，
最终 selected/pending 由原生 analysis 决定。准备文件可以生成，不能提前执行
analysis、写共享 pending 或创建正式分析项目。

### 第二步：复核、编辑与最终提交

页面复用现有样本表、配置控件和状态样式，提供“保存修改”“取消提交”和
“提交分析”。展示候选数、批次、预期项目路径、配置及未保存提示。

“保存修改”只保存本次提交的工作副本和新的内容版本，不触发 prepare analysis。
“提交分析”必须针对已保存版本；有未保存修改则提示先保存。服务端一次事务
校验当前版本和阶段，冻结输入、配置和最终提交意图，并放行现有准备任务。
重复点击返回同一个提交，不创建第二个任务。

准备结束后：

- selected > 0：记录真实 selected/pending 结果，服务端根据已批准的最终提交
  意图继续执行，不再要求人工点击第三步。
- selected = 0：显示“无可分析样本”及原生原因，保留本次合法 pending 结果，
  不启动上传、不伪造执行成功，也不永远停留在等待确认。
- 准备失败：保留原因，沿用原准备重试／恢复入口。不能因异常重新生成另一任务。

建议为新任务增加一个提交界面流程标记（例如 `submission_flow=review_submit`）
及最终提交意图字段，复用现有 run params、审批记录和两个人工 gate；不改 WGS
v2 调度契约。第二个 gate 仅在新流程的最终提交意图存在、输入版本一致且准备
成功后自动通过。旧 three_stage 任务继续原行为，不批量改审批字段。
保存编辑、提交、取消使用同一个 run 行锁和版本检查，避免提交旧表或取消后放行。

## 4. 在线编辑 sampleinfo

### 输入、编辑与分析产物不是同一个文件

`sampleinfo/*.sampleinfo.txt` 是 analysis 输入；项目内 `sampleinfo.tsv` 是筛选后
生成的实际分析清单。编辑入口对应前者的当前提交工作副本，不编辑后者。

保留首次生成／导入的原始快照。在服务器私有、当前 run/attempt 的目录内维护
可编辑副本。原始导入文件不改写。保存时按既有 TSV 列顺序序列化，不对用户未
修改的字段做空值填充或重新查询覆盖。

第一版采用表格单元格编辑，不做任意文件编辑器、批量样本增删或路径编辑：

- 允许修正家系编号、家系人数、家系关系、性别、样本类型、是否患者、
  重新实验/暂停分析、注意事项等实际业务字段。字段枚举采用 WGS 现有约束。
- 样本／数据身份、上机批次、分析批次、版本、订单／任务系统 ID、输入路径、
  pending 系统字段保持只读；变更这些身份需要新建提交。
- 临床等其他列完整保留；第一版不扩大患者资料的浏览器返回范围。
- 服务端验证必需列、空值、枚举及样本身份重复；不在前端复制家系选样算法。
  缺失资料允许保留为缺失，不能补造家系信息或放宽 ready/basecount 检查。

读取／保存接口返回表格和 revision；保存提交 expected_revision，冲突返回409
并提示重新加载，不能覆盖他人更新。复用认证及 run 权限。审计保留操作者、
时间、版本、变更字段，不在普通日志写完整临床值；工作副本仅在服务端存储，
不写 localStorage、DAG conf 或 Git。

### SHA256 与启动命令

冻结顺序必须是：保存编辑 -> 冻结该版本 -> 计算 SHA256 -> 创建 analysis 请求
及回执 -> 原生 analysis 读取同一份字节。不能绕过 hash 校验，也不能把编辑
内容与第一阶段旧回执强行当作相同文件。

runtime 最小补齐：只允许服务端生成并归属当前 run/attempt 的编辑副本成为
`analysis --sampleinfo <frozen_copy>` 输入。同步更新 handoff source snapshot、
source hash、回执校验及导入模式的 hash 校验点；未编辑任务仍走既有输入。
WGS 原生不需要新的 TSV 格式或重写业务逻辑。不得让前端指定执行路径。

分析阶段可能筛选／生成新的项目 sampleinfo，这是正常派生产物，应分别记录
输入 hash 与最终清单 hash；不要求二者相等。提交后禁止编辑该次冻结输入。

## 5. 自动分析与已经存在的 sampleinfo

必须分清三个层次，不能把所有失败都归因于文件存在：

1. WGS 原生 sampleinfo 的已有文件策略：WGS owner 已核实服务器源码，
   `sampleinfo` 和 `all` 遇同名文件会失败，不会自动复用；`analysis --sampleinfo`
   可以直接消费有效的已有文件或编辑副本。准确版本与证据见下节。
2. Airflow runtime：目前已有有效回执复用／缺回执归档再生成的恢复分支。
   该分支不等于无条件复用手工编辑文件，已有无效回执也不能当缺回执处理。
3. 自动派发：就绪检查通过后还会检查数据库里的同批次任务。保留着一个未提交
   或已取消的手动任务，可能阻止创建自动任务，与磁盘 sampleinfo 无关。

建议保持最小行为：

| 场景 | 处理 |
| --- | --- |
| 只有旧 sampleinfo，无正式项目、无活跃同批次提交 | 已确认输入可走 analysis；需要重新获取资料时沿用平台归档／回执恢复策略，不能直接重复调用原生 sampleinfo/all |
| 同一执行已有合法冻结输入及回执 | 复用既有输入，避免重新生成覆盖编辑 |
| 手动草稿尚未提交 | 提示已有手动草稿；自动流程不能偷偷使用它的未确认编辑 |
| 手动草稿明确取消且从未提交 analysis/执行 | 释放该草稿的自动批次占用；自动流程从原始上机来源重新准备，保留取消审计 |
| 已准备、已启动或已完成的同批次任务／项目 | 继续去重，转入原任务处理；禁止覆盖、自动删除或另起重复分析 |
| 身份／hash／回执冲突 | 明确报错，不自动覆盖 |

取消后释放占用需要一处有边界的去重修正：只跳过被确认取消、未进入 analysis
的手动草稿。若 intake 已绑定它，按相同证据解除该草稿绑定；不能将全部 failed/
cancelled 历史任务从去重中忽略，也不能改动已消费的正式批次。

### WGS owner 返回的源码证据（2026-09-22）

核实位置：server10610
`/mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0`，HEAD
`ebf1f4bf2512feecdc3762e463145130192ca8bb`；
`prepare/prepare_wgs_batch.py` 最近修改提交
`9f4f3590fed90d78affeb6a77a8605874d202192`。以下行号属于该服务器版本。
WGS owner 也确认 4.2.2 开发 checkout 的此脚本无额外差异。此结论不证明生产
runner 当前绑定相同 SHA；实施／发布前按实际 runner 绑定核对一次即可。

- `run_sampleinfo`：188–196 行构造输出并拒绝已有文件，带生成后缀还检查
  `.txt.true`。167 行 refetch/reanalysis 不绕过此限制。737–740 行 `all`
  先调用 sampleinfo，因此同样失败；不存在原生 auto 子命令。存在检查发生在
  metadata 获取后，不能将失败理解为未发生任何 provider 读取或缓存副作用。
- `run_analysis`：383–389 行从 `--sampleinfo` 读取；238–253 行验证必需列和
  单一非空分析批次。普通模式可接收有效编辑副本；handoff 模式在读取前核验
  请求内 source SHA，必须更新 snapshot/hash/request，不能沿用旧 hash。
- 源文件不直接改写；395–398 行仅在内存补 version。492 行输出筛选后的表，
  CCE 正式目标为项目 `sampleinfo.tsv`（483–484）。306–345 行发布 final
  snapshot 并记录 final/source 各自的 hash，支持本方案区分输入与派生产物。
- 副作用：403 行可创建 output root；421–427 行检查分析目录，普通非空目录
  禁止覆盖，空目录可能移除。全 pending 时461–479 行更新 pending 后返回，
  不生成项目；有 selected 时592 行先更新 pending，596 行才 rename 正式目录。
  因此准备失败或目录尚未出现不代表 pending 没有变化。

据此在线编辑不需要修改原生选样逻辑；必要改动集中在平台的编辑副本、冻结
交接和启动参数。自动链路应保留原生禁止覆盖，复用平台已有恢复能力；不得为
绕过 FileExistsError 删除文件或引入无条件覆盖开关。

## 6. 取消边界与历史任务

复用现有 config_review 取消机制，在最终提交前停止该草稿的审批等待，保留
必要审计。在线编辑副本失效，不要求删除原始导入文件。准备样本表仍在写入时
使用已有安全边界，不承诺立即删除正在生成的文件。

已通过旧第二步的 execution_review 任务仍需原有恢复／专项处理；本方案不
为它们自动反向修改 pending，也不扩展为通用取消回滚系统。
相关既有文档 `docs/submission-cancel-design.md` 中“准备后撤销”作为独立后续
需求保留；本设计通过延后副作用避免新任务落入该人工确认停顿。

## 7. 开发拆分与最小验收

- `SUBMIT2-01` Backend/Airflow：最终提交事务、新流程 gate、零 selected 终态、
  提交／取消竞态和取消草稿释放自动占用；旧流程保留。
- `SUBMIT2-02` Backend/runtime：受限表格读取保存、revision、冻结副本、启动
  命令和 hash/receipt 串联，导入源保护。
- `SUBMIT2-03` Frontend：两步页面与编辑保存、取消、提交，复用现有表格样式。
- `SUBMIT2-04` WGS owner：原生已有 sampleinfo 行为及 handoff 输入兼容已确认；
  实施／发布前核对生产 runner 实际绑定 SHA。只有发现真实缺口才另列最小
  修改，不预设升级 release 或镜像。

实施后在 BS10610 用 synthetic 数据完成一次针对性验证：

1. 保存／取消前 pending 和正式项目无变化；保存后 analysis 读取编辑后的字节。
2. 旧 revision、重复提交、保存与提交／取消竞争不会重复启动或提交旧内容。
3. 原生筛选后仅选中样本进入项目；0 selected 不上传且有清楚终态。
4. 只有旧 sampleinfo、合法当前回执、无效回执分别走预期分支；原导入文件保留。
5. 已取消未提交草稿允许自动批次继续；已提交／活跃同批次仍被去重。
6. 旧三步任务及未编辑导入任务的行为不变。

只运行改动涉及的测试文件一次，不启动真实分析或做全量回归。实施时同步
API、前端、DAG 和 runtime 四份契约文档；本次不把提议写成已上线能力。
生产发布另行安排，不能在有旧待审批任务时移除其 gate。方案回退仅撤销文档；
实现回退应停止接受新流程提交并保留已提交任务的输入和处理能力。
