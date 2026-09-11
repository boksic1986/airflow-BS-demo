# WGS prepare 接口核对与开发任务边界

- 任务：`PREPARE-CONTRACT-REVIEW-20260912`
- 状态：第一步静态接口核对完成；下列缺口尚未修复，未运行真实准备或远端测试。
- 对应设计：[样本查阅与批次预登记](2026-09-12-wgs-sample-reference-intake-design.md)。
- Airflow 源码：`D:/pipeline/airflow-demo-worktrees/production-release`，HEAD `4c194cd91065d6fc0c7412d2bd28fa112d6a1d7a`；已有上轮文档改动保留。
- WGS 源码：`D:/pipeline/wgs-4.2.0-pending-fix`，HEAD `a5e7ada48646ba29af3eb8abfdbd96fd90310e5c`，工作树干净。
- WGS 已比此前 cc9bde3 多两个提交（默认 Haplotyper、空医院列表兼容）。本次比对发现 prepare 主文件差异仅算法默认值；receipt/pending/metadata 核对不等于批准这些新提交部署。
- 证据是本地代码与现有测试源码，不代表实时生产版本、上游接口行为或远端测试已经验证。

## 1. 结论

| 能力 | 核对结论 | 决策 |
| --- | --- | --- |
| selected/pending receipt | 已有，具备身份、generation、hash 和安全决策行 | 复用 v1，先修正消费端计数口径 |
| excluded | 字段存在，当前生产者固定输出空数组 | 明确仅针对 source_sampleinfo 的分析准备范围，不代表原始 Samplelist 全部排除原因 |
| 本地/云上 pending 文件合并 | 已共用带锁、原子替换入口 | 复用，不新写第二套 pending 算法 |
| 数据抓取内部函数 | 可组合调用，但不是独立预抓取合同 | WGS 封装无分析副作用入口，平台调用 |
| 现有 sampleinfo CLI | 会写正式 sampleinfo、普通模式还写回传脚本 | 禁止直接用于预下机预抓取 |
| 平台 selected-only 入库 | 当前仍将 candidate/pending/excluded 建为 Sample | 平台修改入库、审核和当前 attempt 范围 |

当前可开始平台 selected-only 开发与 synthetic fixtures；新自动预抓取功能必须等 WGS 只读入口及平台适配验收后启用。

## 2. Receipt 实际合同

### 2.1 生产者

WGS `prepare/prepare_wgs_batch.py`：

- `run_sampleinfo`（136 行起）：发布 `wgs.prepare-sampleinfo.receipt.v1`、sampleinfo SHA/行数及 `safe_candidates`。
- `_write_analysis_handoff_receipt`（298 行起）：发布 `wgs.prepare-analysis.receipt.v1`，包含 analysis_id、attempt、execution_id、generation、request_hash、release_id、源 sampleinfo snapshot/hash、pending 输入 revision/hash。
- `selected` 来自 selection.kept，`pending` 来自本次 selection.pending，`excluded` 固定为 `[]`。
- `final_sampleinfo.row_count` 是本次 selected 数量；零 selected 时允许 final artifact 的 hash 为空。
- `private_pending_payload.row_count` 是 update_pending 返回的合并后共享清单数量，可能包含其他批次。

WGS `prepare/handoff_contract.py`：

- `safe_decision_rows`（332 行起）仅输出 batch、family、sample、data、type、relation、sex、decision、reason 等白名单字段。
- 不包含完整订单/任务身份及完整样本列。`reason_code` 当前只有泛化的 pending；具体原因在 reason_message。
- `write_receipt`（282 行起）使用临时文件、fsync、硬链接发布，拒绝覆盖；不能因存在 receipt 字段就忽略身份与源文件校验。

范围决定：source_sampleinfo 内的分析准备决策与原始 Samplelist 资格筛选分开。前置 panel/platform/project/metadata 筛掉的记录不得由平台自行补成分析 excluded。未来预抓取需另行提供来源级缺失/过滤说明。

### 2.2 已确认的消费端不一致（优先修复）

平台 `scripts/wgs_runtime_gate.py:829` 附近将 private_pending_payload.row_count 与 len(receipt.pending) 强制相等。WGS 生产者分别输出“共享合并清单”和“本次 pending”，两者语义不同。

例：共享清单原有 4 条其他批次，本次新增 6 条 pending，未解决其他记录时私有文件 10 条、本次 pending 6 条；当前条件将抛出 `WGS prepare handoff analysis decision count mismatch`。

这是代码路径可推出的错误条件，尚未在远端复现，不宣称当前任何生产失败由此造成。

修正合同：

- selected 数量与 final_sampleinfo 实际内容、descriptor 行数一致。
- private_pending descriptor 行数与其实际完整 TSV 行数一致，不与本次 pending 数量相等比较。
- 本次 pending 与共享快照的关系通过受控原始行身份核对；允许共享快照存在其他批次记录。
- 保留 hash、路径、请求/attempt/generation 和互斥集合校验；不能通过删除整个校验来绕过问题。
- gate 当前主要检查 descriptor/hash、决策字段和重复 sample_id；完整 source 集合覆盖校验目前在 `sample_selection_repair.py` 中体现，正常入库链路也必须具备等价校验。

不要把安全 receipt 扩充为临床全量表。完整身份校验在受控文件边界内做，平台只保存不透明身份与必要脱敏字段。

## 3. Pending 文件入口与剩余风险

`prepare/pending.py:213` 的 update_pending 已有 flock、读最新、冲突检查、fsync/原子替换，返回合并后的完整清单。身份键为订单组 + 样本编号 + 上机批次 + 数据编号。

还已有受限的空批次记录完成匹配（276 行起）：必须同一订单/样本/数据/来源，且唯一真实批次明确入选，才清除原空批次观察；多个批次、来源不同或身份不足时保留。设计中的“精确身份”应包含这一既有受控补全规则，不退化为按 sample_id 或家系删除。

run_analysis 中本地与 handoff 都调用 update_pending。零 selected 也维护 pending，但不创建分析目录。

需单列故障边界：有 selected 时 update_pending 在目录最终发布、权限归一化及 receipt 写入之前（主文件565行起）。因此“pending 已更新”不能证明整个 prepare 已成功；后续失败可能出现文件已变但没有成功 receipt。已有锁只能保证清单写入，不是整个 prepare 的跨文件事务。

本轮不改事务实现。WGS 后续需要验证失败重试/可恢复证据，平台必须保留最后可靠分析状态，不因 pending 消失推断成功或放行 Step1。

已找到的测试源码：test_pending_ledger.py 覆盖并发、幂等、冲突、replace失败；test_pending_recovery.py 覆盖空批次补全、跨批次及旧输入复活防护。这些文件本轮只阅读，没有执行。

## 4. 资料预抓取入口

### 可以复用的内部能力

- `prepare/samplelists.py`：parse_batches、read_samplelist、load_batch_samples；校验 batchNo/sampleId，并按平台、panel、排除项目筛选。
- `prepare/metadata.py`：build_metadata_provider、preload_samples、records_for_sample/order；读取 HTTP/Mongo 并做家系扩展。
- `prepare/sampleinfo.py:371`：generate_sampleinfo 返回 DataFrame；内部不写项目目录或 pending，但会抓取外部资料、输出提示并生成面向分析的家系/样本编号。

### 不能直接复用为预抓取的部分

- sampleinfo CLI 必须提供 analysis-batch；run_sampleinfo 会写版本化正式 sampleinfo，文件已存在时拒绝覆盖。
- 普通模式会生成 task_callback.sh（不会在该函数中执行它）；handoff 模式不生成该脚本，但要求真实分析身份并发布分析阶段 receipt。
- 缺失 metadata 的样本可以被 generate_sampleinfo 跳过并只打印提示；当前没有足够的结构化逐来源行诊断。
- load_batch_samples 对重复批次/样本保留 first，SamplelistRepository 有对象内缓存及按文件名排序选择行为；长期预抓取不能直接复用缓存而不按内容版本失效。
- provider 的 refetch 选择不同上游 URL。源码显示 HTTP 请求，不足以证明远端 POST 查询完全无副作用；不得把重取/重分析接口当预抓取接口。

### WGS 交付要求

提供独立的资料预抓取入口，复用内部解析/抓取，不调用 run_sampleinfo/run_analysis，也不要求伪造 analysis_id、attempt 或分析批次。

输入：受控 Samplelist 快照及其内容版本、明确批次/平台、已批准 metadata 配置；默认非重分析、非 refetch。

输出：版本化资料快照、来源记录标识、逐记录抓取/过滤/缺失/冲突诊断、样本资料和原始身份映射。分析派生编号与源样本编号须区分，不能把生成的 R 后缀当成新下机样本。

仅允许向指定资料快照目录原子写入；不写正式 sampleinfo 目标、不写 pending、不创建分析项目、配置、CCE 文件、回传脚本或任务。配置由受控执行边界选择，浏览器不能传任意路径或程序。

平台负责来源发现、稳定性检测、版本登记、调用和查阅入库；WGS 负责生物信息/订单解析及缺失原因，不在平台复制 generate_sampleinfo。

## 5. 可直接交接的任务清单

### Airflow 平台

| ID | 任务 | 验收/依赖 |
| --- | --- | --- |
| AF-01 | 修正 gate 的本次 pending 与共享清单计数校验，补完整文件与集合校验 | 其他批次4 + 本次6=私有10不误拒；伪造行数/hash/foreign attempt仍拒绝 |
| AF-02 | sync_prepare_handoff_decisions 与其他 Sample 写入口改为 selected-only | 当前主入口536/540行包含candidate/pending/excluded；预览改走快照，12→6，迟到预览不覆盖final，保留历史 |
| AF-03 | 当前/历史 attempt 查询与完整范围验证统一 | 复用 selected_clause，避免仅覆盖latest metadata导致历史丢失；审核/取消不依赖候选Sample |
| AF-04 | 新资料表、受控文件同步、只读API与离线重试 | 复用原始身份而非安全receipt重建；无DB→文件写入；依赖WGS-01资料合同 |
| AF-05 | Samplelist版本发现、批次Intake和目录绑定 | 保留提交后run关联；不调用分析prepare做预抓取；依赖WGS-01 |

### WGS prepare（不是生信 rule / CCE）

| ID | 任务 | 验收/依赖 |
| --- | --- | --- |
| WGS-01 | 封装独立预抓取入口和结构化诊断 | 无伪造run；无pending/项目/正式sampleinfo/回传脚本写入；上游接口用途确认；源身份与分析派生身份分开 |
| WGS-02 | 固化 receipt 范围、清单与安全投影合同及 synthetic fixture | selected+pending覆盖source；excluded=[]口径明确；私有快照允许其他批次；与AF-01共享fixture |
| WGS-03 | 验证并补齐 pending落盘后项目发布/receipt失败的恢复边界 | 故障注入后不漏样本、不覆盖他批次、不伪造成功；无需改生信rule或Master |

建议先做 AF-01/AF-02/AF-03，WGS-01 是新增预抓取启用门槛。WGS-02 和 WGS-03 在正式同步发布前验收。现有正常分析无需为文档核对而停止、重新准备或重跑。

## 6. 核对范围与下一步

本轮仅源码检索、提交差异、现有 synthetic 测试源码审阅及文档链接/差异检查；没有运行测试、访问上游 metadata、SSH、数据库、真实 sampleinfo/pending，也没有修改两个仓库的运行代码。

探索中出现的路径错误：Airflow仓库无prepare目录、WGS工作树无AGENTS.md、PowerShell下tests/test*作为rg路径失败、Airflow无顶层tests。已改查实际WGS prepare和明确测试文件、平台backend/tests；无运行副作用。

下一步实施使用BS10610隔离synthetic验收。已确认的接口问题不等于生产故障根因；生产版本与修复部署仍需独立授权和实时指纹检查。
