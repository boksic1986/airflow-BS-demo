# Group rule-status 参数交接审计

## 2026-09-30 后续证据（不改写下文历史归因）

Master runner `ad7bd2d9c5fa62cb7c3fc330b6b92ca3dce45bfd` 已有参数修复及 Sentieon CCE
事件证据；其余四类现用 Worker 双规则 smoke 和 CNV CCE 事件也已通过。隔离 Rules API
已验证真实事件逐 rule 时间及重复摄取，未验证真实页面/4.2.3 最终绑定。
因此当前不能再以本历史审计要求五类 Worker 全面重建；最终 Master 的公共执行器配套
和页面中间态仍待收尾。报告索引、准确验收边界见 [W423 设计2–3](../superpowers/specs/2026-09-30-wgs423-upgrade-integration-design.md)。

核实时间：2026-09-29 14:52Z。只读源码、提交历史及既有验收记录；没有修改产品代码、测试、构建或生产操作。

## 结论与遗漏来源

这是**镜像专用修复没有收敛进通用 runner 的发布集成遗漏**，不是 P0 executor 有意废弃 Group logger。

- GATK 修复提交 `604ec11667c67587f7fb685023592244ec13548a` 的 `images/gatk-group-logger/enable_group_logger.py:6-16`，只在冻结镜像的 analysis 命令中加入两个 executor 参数。其 `docs/gatk-group-logger-20260917.md` 明确记录通用源脚本未改、仅 image overlay。
- P0 native 提交 `8323567ce2e7c713ed00c4e8232ea481b6537630` 的 `scripts/run_cce_master_job.sh:382-392` 仍保留 Master logger，但没有两个 executor 参数；`images/cce-pipeline-master/Dockerfile:6-9` 清理旧资产并 COPY 通用 runner。因此即使以修好的旧 GATK Master 为 base，后续 COPY 也会覆盖该修复。
- 已核对本地提交历史，通用 runner 路径没有引入这两参数的记录。准确归因是 **GATK 镜像升级回归、WGS 通用入口原有缺口未补**，不是已证明 P0 从通用源码删掉了两行。
- WGS owner 本轮提供的镜像检查为旧 GATK `ee93eaf2...` 有两参数，WGS `3d180a9f...` 和新 GATK `1a923e32...` 没有；本审计复用该镜像证据，独立核实源码原因，不声称再次读取镜像。

## 0.6.4+bs8.dev2 的准确合同

源码：executor worktree `D:/pipeline/snakemake-executor-plugin-kubernetes/.worktrees/p02-worker-terminal-20260923`，HEAD `4f10c27`；其代码与打包提交 `5ffcb07` 相同，差异只有验收文档。

| 参数 | 源码语义 | runner 应传值 |
| --- | --- | --- |
| `--kubernetes-rule-status-dir` | 默认 None；有值必须为绝对路径，不自动创建 SFS 挂载 | `"${evidence}/rule-status"`，Master/Worker 同一共享且可写路径 |
| `--kubernetes-rule-status-attempt` | 默认 attempt-1；非空、不超过64字符的 opaque label | `"attempt-${attempt}"`，与 Master logger 一致，attempt 来自 CCE_ATTEMPT |

`__init__.py:412-422,506-523,630-655,876-886`：只有 GroupJob 且 dir 非 None 时，executor 将 Worker 命令改为 `python -m snakemake_executor_plugin_kubernetes.rule_status_worker`，显式传 logger、同 dir/run_label/attempt、`role=worker`，并注入包含 rule 实例哈希与拓扑层次的 Group manifest。仅设置 Master 的 `--logger-rule-status-*` 不会设置 executor 参数。

Logger `__init__.py:110-188`：事件写入 `${dir}/raw/worker-<hostname-sha12>-<pid>.jsonl`，Master 为 `master-*`；attempt 是每条事件字段，不是自动创建的 attempt 子目录。该值不是 Master generation，也不是 Snakemake 单 rule 的重试次数。错误默认 attempt-1 在首次分析可能不明显，后续 attempt 会产生身份错配风险。

另一个既有行为不能遗漏：executor `__init__.py:699-718` 在 dir 有值时对**所有 Worker**使用 `/bin/bash` 和 `tee` 保留 `${dir}/pod-logs/<jobid>.log`，保留原进程失败码、同时检查 tee 失败。非 Group 的 Snakemake 命令本体不被替换，但外围日志包装会启用；不能称参数完全不影响非 Group。

这些事件与 P0 的提交账本、精确 Job receipt、原生成功终态不是同一合同，不能互相替代或据此改写成功判断。

## 最小修正边界与潜在阻碍

建议仅在通用 runner **analysis** 命令恢复上述两项，保持已有 Master logger 和运行标签；不扩到 preflight、unlock、final dry-run，不改 DAG/Step1-6、CLI 版本、TTL、锁或业务规则。本轮只给审计结论，由既定 owner 执行已获准镜像修复。

旧 GATK biosan3 的 Group 入口为 `wgs_cce_worker_support.rule_status_worker`；bs8.dev2 Master 生成的入口名为 `snakemake_executor_plugin_kubernetes.rule_status_worker`。实际执行时加载的是 **Worker 镜像自身**的同名模块及依赖，不是 Master 镜像中的模块。bs8 wheel 内该模块要求 Snakemake `9.24.0+biosan1`，不能将此版本要求直接套到现有 Worker：owner 的 BS10610 原始输出 `exec-dc01703b-c7df-4b87-b376-f1736faeb544` 已证明冻结 WGS Sentieon Worker（digest `6aaeb3c5254c1c0dd195c32ac372a3eb499e623dd8436690a5fbe71c92897d17`）内同名模块要求 `9.23.1`，而非 bs8 模块。结合其既有入口检查，不构成直接不兼容或升级 Worker 的依据；仍需核对实际生成的 argv/manifest 与 Worker 自身入口的事件合同。也不能仅凭旧 support 模块存在推断同名新入口可用。复用各真实 Worker digest 的现有证据，未知项先报告，不擅自扩大 Master 两参数修复成 Worker/依赖改造。

同时确认已有 bash/tee、共享路径映射和非 root writer 的原权限可写。不递归改权限，不碰当前运行中 Master/Worker 或冻结 attempt。

### 补充：已有 Worker 检查与 args/schema 差异

WGS owner 随后提供五类冻结 Group Worker digest 的实际检查：均用 `/opt/snakemake/bin/python -m snakemake_executor_plugin_kubernetes.rule_status_worker --help` 返回0；Sentieon help 包含两类参数。这已排除这些镜像的入口/CLI 缺失，不要求再做同一检查，也不能据此推定需要升级 Worker。它仍不等于实际生成命令与事件写入成功；GATK Worker 不在这五个 WGS digest 的证明范围内。

独立对比 biosan5 `5dd176af` 到 bs8.dev2 `5ffcb07`：两参数定义和验证、`format_job_exec`、`build_group_rule_manifest` 四段逐段相同；`rule_status_worker.py` 无差异。manifest 仍为 schema_version `"1"`，通过 `SNAKEMAKE_RULE_STATUS_GROUP_MANIFEST_B64` 传递，成员字段仍为 `rule_name/rule_instance_id/layer`。Logger 的 P0 新增 failure-summary 只在 Master/recovery 环境启用，不是 Worker 事件 schema 换代。没有发现需要新增参数/schema兼容层的依据；此结论限定源码版本比较，不冒充对所有实际 Worker 内部源文件逐个做过比较。

两个 `--kubernetes-*` 是 Master executor 设置。生成给 Worker 的是 logger 参数、REMOTE/group 目标参数及 manifest 环境变量，不需要将这两项 executor 设置再传给 Worker 来启动 Kubernetes executor。

候选激活门槛：实际镜像 runner 的 argv 检查、锁定 Master 生成的完整 Group 命令与 manifest 的最小事件链验证、准确 Master/Worker digest 与正常 profile 登记。五类 Worker 若入口/logger/依赖合同已有相同证据，可复用一次共同合同验收；差异只做定向检查，不重复全套。只对新运行或明确授权的恢复绑定生效，不改当前冻结 attempt；本审计不授权激活。

## 已有测试覆盖及必要最小验收

1. 旧 GATK `tests/gatk_master_group_logger_check.py:11-44` 已执行真实 analysis shell 片段，拦截进程启动，验证 attempt1/7、含空格路径、两 executor 参数、Master role、run_label 和目标。它是**显式镜像检查**，不属于默认 pytest 收集；旧镜像通过不能代替新镜像。
2. P0 `tests/test_recovery_final.py:200-201` 只断言 `--logger rule-status`，没有两 executor 参数及 Worker 事件链断言。bs8.dev2 最终 wheel 的4项验收也不覆盖 runner 传参。原早期 `k8s-rule-status-logger` 分支有 Group 参数传播测试，但不是 P0 最终 source suite 中的测试文件，不能算作新 Master 集成验收。
3. 后续最小验收：在候选**实际镜像 runner**复用旧 argv 检查；确认非 Group 原命令/退出码和日志包装；使用确切目标 Worker 上的实际生成入口做一次两规则 synthetic Group 事件链检查，核对 role/run_label/attempt、started/info/finished 关联和同根输出。可复用同制品已经获得的入口/事件证据；旧 module smoke 不能冒充新 module 验收。
4. 不重跑全套 P0、完整临床流程、已验收 TTL/配额/恢复负例，也不为本次只读审计运行任何测试或构建。

## 来源和检查方式

- native Git：`D:/pipeline/cce-pipeline-worktrees/gatk-master-logger-20260917`；P0 linked worktree `D:/pipeline/cce-pipeline-worktrees/p0-validation-artifact-20260925`。后者既有 `tests/test_recovery_monitor.py` 修改保留。
- `D:/pipeline/cce-release-simple-088` 只是可读源副本，不是 Git 仓库；归因使用上述真实 Git 提交，不将该副本作为主线证据。
- 本轮执行 `git show/log/diff/status`、定向 `rg` 和文件读取。没有安装、import、pytest、Docker、SSH、数据库或云端操作。
- 已将结论、Worker 新入口风险和最小验收点交给 WGS owner `01a09149-ad9d-7e92-b98a-16d9cae075e2`；不产生并行实现 owner。
