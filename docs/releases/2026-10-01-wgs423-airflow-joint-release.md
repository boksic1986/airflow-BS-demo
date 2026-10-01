# WGS 4.2.3 / Airflow / cce-pipeline 0.8.9 联合发布协调单

状态：2026-10-01 已向三位原 owner 派发；基线收口中，未宣布安装、验收或上线。

## 1. 授权与发布范围

用户要求：配合 WGS 4.2.3 云上发布与 Airflow 升级，协调各 agent 整体更新。
此要求推进既有 [W423 实施计划](../superpowers/plans/2026-09-30-wgs423-upgrade-integration.md)，
不是重新设计 UE、重演旧批次恢复或重新验收所有 P0。

- 当前推进：源码整合、云端候选制品、BS10610 与 node200 测试入口配套、差量联合验收。
- 已向用户询问最终是否包含 BS96；回答前不切换 BS96 生产。候选上传不等于生产启用。
- nipttest 是共享 NFS 环境，实际替换须先通过消费者影响及配套回滚审核；不能将测试包安装
  视为无条件隔离，也不能以 BS10610 不存在 `/home/ctapa` 判定 node200 配置失效。
- 生产旧批次维持冻结制品；不迁移、不重提、不改旧 attempt，不删除数据或执行 Step7。
- 不发送真实 LIMS、不猜测 QC 放行阈值、不升级无关依赖、不增加版本号后缀。

## 2. 单一负责人和写入边界

| 范围 | 原 owner thread | 本轮责任 |
| --- | --- | --- |
| WGS | `01a09149-ad9d-7e92-b98a-16d9cae075e2` | W423-02 原生合同、正式云分支；最终 pipeline/resource/profile/Master 制品发布 |
| native | `019f9d79-be3f-7701-af33-3595d72bbfac` | 0.8.9 wheel/runtime、W423-03 trusted prepare 增量、共享包安装与包回滚 |
| Airflow | `01a0e728-4c99-71d0-87e9-987b311022c9` | 单一隔离集成分支；平台 prepare/group/QC2/默认关闭回传；测试 gate/selector/服务配套 |
| 协调者 | 本线程 | 范围、跨仓合同、差异/证据审核、发布清单与阻碍汇报；不并行改 owner 产品代码 |

同一目标只有一位执行 owner。Master 由 native 提供需要集成的参数/运行资产，WGS owner
统一构建登记，不能双方分别发布不同的“最终镜像”。测试入口文件由 Airflow owner 管理，
共享包由 native owner 管理，两者先确认同一切换/回滚窗口再操作。

## 3. 已知起点，不冒充最终组合

| 项目 | 已核实/已验收起点 | 本次必须收口 |
| --- | --- | --- |
| Airflow 主线/生产远端 | `ce497d61efaa725a4a45266e76dd996d7767fe74` | owner 刷新；与 UE 分支及必要候选进行语义整合 |
| Airflow UE-06 | `3c094fc4c8789444abbbd3aa939955d73c98fbe3`，产品 `03bab6c768a2c84537ee4e4a6189072256841b63` | 尚未进入上述远端主线；不能遗漏已上线 TTL 修复 |
| GATK phase 候选 | `6d117123a0aff94dac34db33791c748cc131110e`，前置 `a85cfb6` | 检查必要性与等价提交；不重复叠加 WGS 映射 |
| WGS cloud | `dev_CJC_4.2.3_cloud` 的 release 合并 `df6bbfcdf7493aa63413bb321dae86317138300f` | owner 当前发布可能已推进，先接收新清单；不重新合并 |
| native 0.8.9 | source `7172573223308f1ca89616a5f81d14fec995a659` | 若 W423-03 产生实际源变更，重新固定产物，不能沿用旧 wheel 摘要声称覆盖 |
| 已验收 wheel | SHA256 `bda21dd22fd5fbcea23c40ae5ed9e3fc324b41ff2f56bf31c59022acacd8f6d4` | UE-06 是隔离安装验收，不是 nipttest 实际升级或生产启用 |
| 共享 nipttest | 原 0.8.8 / `417de597fe3e83cc42160cf14102ad78db789bf8` | 当前消费者与 node200 测试 policy 必须新鲜核对；配套后安装 |

WGS 当前已审阅的 merge 保留 Haplotyper 默认。旧 `pipeline_root=4.2.2`、
`resource_set=wgs-4.2.2-r1` 与 4.2.2 profile 是需要 owner 核实/替换的云候选绑定，
不是已发布的 4.2.3 配套结论。最终清单必须写明完整路径、commit、SHA/digest 及生效入口。

## 4. 顺序与审核点

1. **JR-01 基线与责任收口**：各 owner 给出当前分支/HEAD/dirty、有效制品和正在进行的动作。
   Airflow 先给提交清单/等价分析，在干净 worktree 整合，不导入协调 worktree 的无关 dirty。
2. **JR-02 源码与合同整合**：W423-02 提供 merge 完整性/进度、QC 来源/策略/适用性、交付合同；
   W423-03 消费该合同。W423-04 可并行处理不依赖未定字段的部分；字段未定不得自行发明。
   保留已有 TTL/SSH/P0 修复；替代旧逻辑时注明覆盖关系，禁止重复维护两个执行框架。
3. **JR-03 固定配套候选**：收齐最终 WGS/native/Airflow commit、wheel、Master digest、Worker
   digest/profile、resource-map/READY、QC 策略及 gate/selector 摘要。只重建确实受影响制品。
   merge-enabled 请求在公共异步 prepare 就绪前不得进入可用发布配置。
4. **JR-04 测试端切换与最小联合验收**：先审阅 BS10610/node200 实际身份、挂载、消费者和
   活跃执行；核对既有 shared bootstrap/policy 与新包配套及回滚；再由原 owner 协同切换。
   若发现未隔离生产消费者，先报告，不能直接覆盖共享包或关闭校验。
5. **JR-05 发布审核**：对照 W423-06，确认差量证据、未启用能力、回滚和旧批次影响。
   待确认 BS96 授权；若只做测试发布，明确停在测试验收，不声称生产完成。

LIMS 业务策略/接收合同未明确时保持默认关闭，不真实发送；这不代表 W423-05 已验收。
如果需要将该项移出本次交付，必须在清单中明确并向用户确认，不默默省略功能。

## 5. 复用证据与最小新验证

- UE-01–06 复用已接受原始证据；只验证合并冲突/实际改变入口和最终加载组合，不重复全套。
- Group 复用已有事件与 Master logger 参数验证，不按五类 Worker 重跑旧 smoke。
- 新 prepare 使用 synthetic 合成与可控时钟验证短连接、同执行观察、去重、产物门禁和期限；
  不真实等待 20 分钟、不启动完整临床批次。
- QC 按 W423 四类差量场景；绑定最终原生脚本/配置摘要，不用旧阈值或版本前缀消除 unknown。
- 回传只做 synthetic receiver/拒绝行为；真实策略未登记时不可执行。
- 最终组合只追加一次受影响接口联验。每项写明所用源码/镜像和环境，stub 不冒充真实 native。

## 6. 回滚与交接

安装前保存/核实 exact old wheel、原 policy/selector/bootstrap 和实际部署组合。
已核实 0.8.8 回滚 wheel SHA256：
`45c99c0c8fb2d39442088d5c5ee7ad6c7be004d2c30495d80d96a4e8a20672c8`。
不能仅回滚 pip 而遗留新 policy，也不能回滚 selector 却保留不匹配的 native。
平台回滚依据真实容器挂载/Compose/镜像，不依赖可能过时的 current 链接。

各 owner 返回精确提交、制品摘要、实际改动/未改动、原始最小验收、未解决项及回滚步骤。
协调者审核后写入此单与 CURRENT_STATE/TASKS/HANDOFF。任何未验证项保持明确未验证状态。

## 7. 本轮协调记录

- 已向三位原 owner 发送配套发布任务，要求先回传现状/阻碍并按上述顺序继续。
- 生产范围问题已发给用户；回答前不部署 BS96。
- 此记录本身没有进行安装、运行测试、镜像发布或生产操作。
- WGS owner 新鲜回报：正式仓库仍为 `df6bbfc`，release 已合入，无其启动的在途构建/
  上传/SFS 发布；Haplotyper 默认不变，prepare 原生 minimum/merge threshold 均100G，
  W423 文档已有修改保留。4.2.3 云绑定与原生合同正在整理，未声称完成。
- 三位 owner 均已进入工作。Airflow 首次 fetch 使用了简称 `production` 而失败，协调者
  已纠正为远端完整 `refs/heads/jiucheng/release/production`；不扩大到别的生产仓库。
  已跟踪文件干净的原 UE worktree 可复用，但保留原 UE 分支、在准确基线开本次集成分支。
- 文档局部 `git diff --check` 通过；新增协调单/原计划的4个 Markdown 相对链接全部存在。
  一次协调消息工具调用因 JavaScript 括号语法错误未执行，修正后3条消息均发送成功，
  未因此产生重复远端操作或产品改动。
