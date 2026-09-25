# WGS 4.2.2 + P0 测试发布实施方案

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to execute the assigned task sequentially. Retain the existing owner agents; do not create a parallel implementation of P0. Track steps with checkboxes.

**Goal:** 按用户最新顺序完成新版 cce-pipeline 安装、WGS Master 推送、新 profile 绑定，随后发布 WGS4.2.2 SFS、对接 Airflow API/面板，最终同步 Airflow main/生产分支并做最小验证。

## 最新执行裁定（2026-09-25，优先于下方历史顺序）

用户最后收窄本轮为：**先完成 cce-pipeline 安装 → 新 WGS Master 推送 SWR → 新 profile 绑定**。
保留原任务编号避免丢失交接，实际先执行 R2，再执行 R3 的候选绑定部分；R1 的 SFS 发布放在后面。
R2 不再依赖 R1 已成功发布，只依赖已冻结的 WGS4.2.2 源码/资源合同和兼容性核对。
R3 可以绑定预定不可变 SFS 路径，但必须明确资产未就绪、candidate 未启用，不能宣称可提交分析。

- 安装和发布按正式 SOP 核实；已有本次测试约定为 nipttest。若 SOP 与当前授权范围实质冲突，报告准确依据，不猜测或擅自切换生产环境。
- 原 native/Infra owner 执行安装、推送和 profile 落地；原 WGS owner 提供合同/兼容性确认。协调员不接管 wheel/Master 构建。
- 复用已验收 dev3 wheel 和 WGS Master，仅做安装路径/version/hash、SWR digest、profile 绑定的必要验证，不重复源码/TTL/生物流程测试。
- 本轮暂不执行 SFS apply、Airflow 服务更新或分支合并。用户已授权后续 Airflow main/生产分支同步；这不是 BS96 服务部署授权，也不是另外两个 P0 仓库的主线合并授权。
- 本节覆盖下文旧的“R1 发布后才能 R2”及“最终不合 main/生产”限制；其他数据保护、旧批次冻结和范围限制不变。

当前三步状态：已派发原负责人，安装、推送、profile 均待实际回执；不以派发代替完成。

**Architecture:** WGS owner 管不可变流程/资源，native/Infra owner 管 wheel/Master 和实际部署，平台负责把已有生产修复、测试专有修复及 P0 合为同一测试版本。发布制品与切换运行选择分开；第3步交付候选 profile，第4步完成版本配套后才用于测试。

**Tech Stack:** WGS/Snakemake、cce-pipeline、Kubernetes executor/logger、SFS/OBS/SWR、FastAPI、Airflow、Git。

**Spec:** 用户2026-09-25四步要求；P0功能范围沿用 `2026-09-25-p0-validation-corrections.md`、`2026-09-22-p0-joint-recovery-progress.md`；环境遵循 `../../34_TEST_PRODUCTION_RELEASE_BOUNDARY.md`。

状态：用户2026-09-25明确授权“继续完成，开始执行”。R1由原WGS owner开始，R2/R3等待其发布合同，R4随后整合测试版本；未有回执的步骤不记为完成。此方案替代“直接将fdace86部署到旧测试环境”的顺序，不推翻已完成的源码/制品验收。

执行更新：R1新候选20260925.1-wgs422已上传13对象和SOURCE_READY，尚未发布SFS。
BS10610无法读取私网OBS；现有CLI支持从node005校验并SSH到BS10610执行kubectl，
但node005管理配置使用的工作站BS10610别名无法解析。用户已指示直接使用现有本地
SSH/节点直连IP；本地BS10610返回server10610已验证，Infra正在核对现有node005直连
配置，不把新增全局别名作为前提，不改路由/凭据或绕过校验。R2只读准备完成，R2–R4未部署。

## 范围与交接负责人

| 步骤 | 负责人 | 必须交付 |
| --- | --- | --- |
| R1：WGS4.2.2到SFS | `WGS-pipeline`，任务01a09149-ad9d-7e92-b98a-16d9cae075e2；Infra按既有发布职责协作 | 源码冻结、更新后的资源清单、SFS发布回执/校验值，明确未启用 |
| R2：nipttest和WGS Master | `huawei-cloude`，任务019f8355-2b77-7413-9553-6670c35a1a2f | 实装wheel版本/hash、回滚副本、新SWR RepoDigest、与R1兼容结论 |
| R3：新profile | WGS owner确认内容；native/Infra生成安装；平台登记候选 | 精确revision/hash，绑定R1资源与R2制品；不覆盖旧profile |
| R4：整合与测试部署 | 平台协调源码整合，原Infra部署，定向QA验证 | 测试分支集成commit、既有服务实际挂载、最小验证回执 |

协调员维护本仓库计划/CURRENT_STATE/TASKS/HANDOFF；组件owner只维护自身交接物，避免多人同时编辑状态文档。

## 全局约束

- 本轮目标是BS10610测试平台及其node200 WGS测试入口；发布共享SFS/SWR新制品不等于切换BS96生产。保留4.2.1、旧profile、旧镜像和所有冻结批次。
- 不测试GATK/WES、不更新其gate/profile/image；共享后端保留GATK代码不是越界，不为此拆出第二套API实现。
- 不扩展到五类WGS group Worker升级、logger新功能、配额/算法/pending修改；沿用已接受的P0，不重写重试机制。
- cce-pipeline只安装到约定nipttest，不装WGS环境，不升级Python或无关依赖。确认共享解释器的实际消费者后才写入；无活跃进程不等于无生产消费者。
- 新共享输出目录2770、文件0660并符合实际组/ACL；私有凭据另行保护。不强制root、不递归调整旧目录权限。
- OBS私网传输在BS/node005进行；CCE操作在BS10610，凭据不复制进制品/日志。证据放任务专属WGS_test目录，不使用/tmp。
- 扫描、自动派发和全局自动恢复保持关闭；正向恢复验证只在隔离synthetic用例中显式开启策略，不借此启用服务全局开关。
- 不做生产部署、真实批次续跑/删除、全量生信回归、新TTL/真实Master替换测试。若最小验证暴露新增修改需求，先报告，不扩范围。

## 当前版本事实与执行时复核

| 项 | 已有证据 | 执行要求 |
| --- | --- | --- |
| WGS4.2.2 | upstream `ca71cd6f615e3a2fd0f43f39cc7c472c5d76d903`；CCE适配 `3b1dae513dbca1938ed89d982e2c3553856862b3`，分支dev_CJC_4.2.2_cloud | owner重新核对HEAD/dirty并冻结准确发布commit，不把9/22记录当当前HEAD |
| Native | 功能ae90b65；build45323e4；0.8.5+p02.dev3 | wheel SHA256 `004348233d18815ac8763eb38e07e67e22f5b7a0281ec65dbe36c8310cb4ec45` |
| 插件 | 5ffcb07，0.6.4+bs8.dev2 | 复用已交付制品，不重建插件 |
| WGS Master候选 | 本地image ID `sha256:05888c3ac82e1a9b149c2bbd42788d227269787d5042c1af3287daa6d16be367` | 不是SWR RepoDigest；R2推送后填写真实digest |
| 平台P0 | 功能fdace86；当前工作分支jiucheng/runtime/CR01-cce-recovery-20260922 | 保留最终P0修复，不直接整包覆盖测试 |
| main/生产分支 | 本轮git ls-remote均43cd0c51a0ff44cc368579a397ba5ddb5ebc611a | 执行整合前fetch并冻结最新refs；这不是本轮生产主机验收 |
| 远端测试分支 | jiucheng/test/wgs-local-main-sync-20260917，781877e8a862bbe7a4bf2924e817d3657d81468f | 包含43cd0c5；ae416fa不是祖先，但255be59已纳入其代码，backend/dags/scripts/config/frontend与ae416fa一致，不重复合入 |
| 实际测试挂载 | 后端20260923-step7-ae416fa；WGS DAG/common来自20260915-main-359df11 | 必须保留ae416fa测试修复；按服务挂载核对，不只看current链接 |

## R1：先发布WGS4.2.2代码和资源

**输入文件：** WGS owner的 `D:/pipeline/task-artifacts/wgs-422-update-20260922/WGS_4.2.2_UPDATE_PLAN.md`、`WGS_4.2.2_RUNTIME_IMAGE_UPGRADE_PLAN.md`、`PUBLICATION_STATUS.md`。旧联合镜像计划中五类Worker升级不纳入本方案。

- [ ] owner核对独立checkout `/mnt/biodevrwbi/33.chenjiucheng/project/worktrees/wgs-4.2.2-cloud-group-logger` 的源码身份；沿用既有发布工具，不修改WGS生信逻辑。
- [ ] 重新冻结增量资源。9/22五项数据库共6,111,924bytes只是旧快照；将9/24已变化的常规whitelist VCF及其tbi纳入增量，核对配对与源SHA，不能直接复用旧候选20260922.1-wgs422。
- [ ] 从已验证4.2.1资源清单继承未变资源，重新生成asset manifest、UPLOAD_PLAN、resource-map和READY相关摘要；旧121键是核对基线，不硬编码为未来通过条件。
- [ ] 通过既有私网发布路径上传、核验SOURCE_READY，再发布独立SFS路径 `/workspace/wgs/pipelines/4.2.2` 与 `/workspace/wgs/resources/wgs-4.2.2-r1`。目标若已有不同内容，停止，使用新的不可变revision，不覆盖。
- [ ] 发布不等于平台启用，但现有 `assets apply` 会更新共享 `/workspace/wgs/.cce-assets/ACTIVE_ASSETS.json`；不能把它描述为纯staging。先核对实际生产消费者和旧4.2.1 status读取语义，明确本次资产指针更新不改变生产运行选择才执行。无法证明时暂停报告；若要求指针保持4.2.1，现有apply不满足，需要调整发布方式/顺序，不能手工伪改或回写指针。
- [ ] 交付源码commit、pipeline/resource/VCF/index SHA、SFS准确路径、resource-map/READY、发布回执和兼容性摘要。记录ACTIVE_ASSETS前后值，与生产平台/profile选择分开，证明现有批次仍绑定原版本。

**最小验收：** 复用既有六个新rule的资源/镜像映射与脚本依赖证据；仅检查此次变化的资源/清单及SFS发布回执，不重复完整DAG/镜像测试。

**回滚：** 未激活的新发布保留审计；旧4.2.1不动。不删除旧文件或改已有批次。

## R2：更新nipttest并推送WGS Master

**输入：** R1已冻结源码/资源合同（不要求SFS已发布）；`docs/releases/2026-09-25-p0-validation-dev3.md` 和原owner dev3制品回执。

- [ ] 原native/Infra owner确认dev3与R1兼容：overlay不复制WGS源码，Master通过CCE_PIPELINE_DIR读取SFS；仍需核对base运行时与4.2.2所需接口。符合则复用dev3，不为版本标签重建；不符合则说明缺口再决定必要改动。
- [ ] 临写前核对BS10610/node200/BS共享nipttest消费者、活动任务和实际挂载，记录精确旧package/dist-info字节、元数据、ACL、依赖快照及恢复命令。存在生产/活动消费者无法隔离时停止该安装，不另建环境或绕过。
- [ ] 将精确dev3 wheel用离线、无依赖升级方式装入 `/sg2/33.chenjiucheng/software/miniforge3/envs/nipttest`；校验实际导入路径/version和关键资产hash。paired bootstrap在R4成套激活前保持未启用，不以安装成功冒充P0接入完成。
- [ ] 把通过兼容核对的WGS Master推送到新的、不覆盖现有的SWR测试标签；读取registry manifest，记录真实RepoDigest和本地config ID关联。不推GATK候选。
- [ ] 交付安装回执、回滚位置、wheel/hash、plugin版本及WGS Master RepoDigest给R3。

**最小验收：** 一次安装路径/版本/hash确认、一次推送digest核对。复用dev3既有wheel3pass/1skip与image smoke，不把skip算通过、不重跑源码111项/TTL验收。

**回滚：** 恢复原package/dist-info与权限/依赖状态；不切换现有批次，不清理镜像。

## R3：生成并部署新的候选profile

**文件范围：** 外部WGS profile新revision；平台 `config/wgs_releases.yaml`、`config/pipeline_profiles.wgs.yaml` 中必要条目及版本化测试配置。不是任意改默认值。

- [ ] WGS owner与native owner共同冻结R1流程/资源路径、R2 Master RepoDigest/native版本、原有Worker digest和资源配额。维持snakemake-ns、cce-pipeline-worker-v1及已验证PVC合同。
- [ ] 采用现有cce-pipeline profile生成/摘要规则，生成新的4.2.2 revision。拟定路径 `/bi/biodevrwbi/33.chenjiucheng/project/cce-pipeline-profiles/wgs/wgs-4.2.2-r1.yaml` 必须先现场确认可达且未发布冲突；已存在则新revision，不覆盖。
- [ ] 关联同一份pipeline_build/resource_manifest/profile SHA与源码commit。只写候选catalog条目；不提前切换current_release_id或让旧后端接受新批次。
- [ ] profile放到实际测试消费者可读位置，记录其解释器、所有者和路径；SFS路径与node200主机路径不能混用。

**最小验收：** 一次profile解析/渲染检查，确认工作流4.2.2、资源清单、Master digest、native版本和Worker映射全部一致；无真实提交。

**回滚：** 保留旧profile及catalog选择，候选不启用即不影响旧流程。

## R4：整合生产修复和P0到测试分支，小范围验证

**集成方式：** 在隔离worktree从最新测试分支建立 `jiucheng/test/wgs422-p0-integration-20260925`，保留原P0分支。整合完成后提交/推送回既有测试分支；不合并main/生产。

**关键文件：** `backend/app/main.py`、`config.py`、`cce_*.py`、WGS注册/恢复/观察/Step7/transfer服务；`dags/bio_wgs.py`、`bio_wgs_maintenance.py`、`cce_publish_dispatch.py`、`cce_worker_wait.py`；`scripts/wgs_runtime_gate.py`、paired/recovery/resume完整依赖；R3候选catalog/profile。保留已有前端与非冲突修改，不整文件选择ours/theirs。

- [ ] fetch并冻结测试、main/生产、P0、ae416fa修复的commit。先保留测试历史并补齐真正未包含的生产修复，再合并P0。781877e已通过255be59包含ae416fa代码，不能只看祖先关系重复合入；若refs更新，重新比较内容后确认。
- [ ] 只处理真实合并冲突：保留P0身份/代次/锁/预算/失败回执保护，同时保留Step7独立维护DAG、冻结target/前次action、观测接口、上传/下载waiting进度与workspace证据。
- [ ] 整合R3候选条目，固定最终集成源码hash。P0已有代码共享GATK部分保留，但不修改GATK外部gate/profile/image、不运行其参数化测试。
- [ ] 在BS10610隔离验证中仅运行下表；不得本地运行测试。发现合并造成的新故障，只补对应回归用例。
- [ ] Infra记录现有服务的实际mount/回滚，成套发布后端、必要DAG/helpers、node200 WGS测试gate及完整模块依赖、成对bootstrap/policy和R3 profile。后端API可用后再更新调用方；不只部署worker_wait。只重建确实需要的既有服务，不建新Compose项目、不重启数据库/Redis/无关服务。
- [ ] 同一窗口完成版本与路径核对，保留暂停/自动开关关闭。验证通过后将R3设为测试新批次选择，旧批次继续冻结版本。记录“已安装”“已推送”“已发布”“测试已选择”各自证据。

### 小范围验证清单（一次，失败仅复测受影响项）

1. **版本配套：** 实装wheel/guard、SWR RepoDigest、profile、SFS manifest、平台源码和实际挂载一致；现有API route与DAG导入可用。
2. **P0 WGS恢复：** 复用 `backend/tests/test_cce_recovery_dispatch.py` 的单次预算/同attempt恢复及不确定POST只查询两例；`test_cce_publish_caller.py` 的已有认证路由与丢失begin不重发两例；`dags/tests/test_cce_recovery_poll.py` 的WGS旧链退出用例。只选WGS参数，synthetic临时DB/外部传输替身，不跑整文件中的GATK矩阵。
3. **保留原修复：** `backend/tests/test_wgs_maintenance_observation.py` 的success receipt优先与stale callback拒绝；`test_wgs_shared_transfer_progress.py` 的upload/download queue用例。文件与用例来自ae416fa/main，不能因为P0分支缺失而跳过。
4. **部署冒烟：** 读取测试版本/健康状态与受控profile解析；确认扫描/自动派发/全局恢复仍关闭，无运行中批次被更换。不重跑全P0、全生物流程、TTL或group logger canary。

只做上面有限验证不宣称真实CCE故障注入或WES上线验收。若用户希望真实小样本启动，另明确样本/批次与运行范围后执行，不从“验证”推断临床任务授权。

**回滚：** 恢复本次记录的测试服务mount、gate/env/bootstrap、catalog/profile及nipttest旧包。新不可变制品与验证记录保留；不删除DB/结果/FASTQ/pending。生产无切换，不存在本轮生产回滚动作。

## Review Focus / 完成条件

- R1：源文件原地更新但版本名不变时按内容hash处理，VCF与tbi配对；不能套用9/22旧摘要。
- R2：SFS外载不等于base一定兼容；共享nipttest安装不能影响未识别消费者。
- R3：候选profile部署不等于可供旧平台启动；不可变SWR digest和资源READY必须配套。
- R4：按内容而非仅提交祖先识别已纳入修复；781877e已有ae416fa等价代码，合并保留其语义而不是回退或重复合入。
- R4：小范围用例证明所测链路，不冒充全局启用、真实云端恢复或WES验收。

四项均有owner回执、最终测试分支commit和最小验证结果后才标记本计划完成。当前已获执行授权，R1启动核对与发布，R2–R4尚未执行。
