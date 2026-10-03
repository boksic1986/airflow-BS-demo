# WGS 4.2.3 / Airflow / cce-pipeline 0.8.9 联合发布协调单

## 2026-10-03 归仓说明

本文件记录 10 月 1 日联合发布及按时间保留的历史检查点；当时的 pending/GO
不是新的执行授权。后续 D-test1 的两项修复、真实部署和 Step1–6 完成状态见
[最终落地核验](../reviews/2026-10-03-wgs-terminal-identification.md)。本次归仓没有部署。

原 Airflow 分支先前的 Group TEST 检查点记录：两 Master 已推送，W423-R1 在保持
prepare 合同的前提下仅向三处版本集合加入 `V4.2.3`，BS10610 focused GREEN26；
UE04/05/06 已验来源复用。详情见
[Group TEST 消费者审计](2026-10-01-w423-group-test-consumer-audit.md)。
当时“安装、最终登记及 TEST 配对待完成”的结论已由下方 23:05 CST 最终状态覆盖，
不得据此重放安装或测试；FQ/async prepare、QC2 和新交付扩展仍为延期范围。

状态：2026-10-01 23:05 CST，本轮共享0.8.9安装、TEST配对及生产新请求入口发布已完成
最小验收。WGS4.2.3/native0.8.9与两Master group参数、平台80abdfc已配套启用。
两端手动WGS/GATK执行入口已恢复，自动提交仍有效关闭；未启动新的临床批次。
FQ合成/async prepare、QC2和审核回传仍延期，不属于本轮发布。

## 最终状态（优先于下方历史检查点）

| 项目 | 已核实结果 |
|---|---|
| 共享环境 | nipttest安装0.8.9/source1f5e1e0/wheelf843；30源匹配、197其他分发未变 |
| 新WGS请求 | wgs-4.2.3-bafd27c，Master e4812533，profile r1/raw436a6608；422只保留历史/回滚 |
| GATK | 7.6.0 Master a4f8d15e，profile r5/raw17d2bb59，共享同一0.8.9 |
| 平台 | AF80abdfc；四节点消费者/受信入口、TEST六服务和PROD六服务完成实际配对 |
| 生产切换 | receipt16f131a4真实注册，14:52:31Z CAS441→423，catalog35c53a2e |
| 最终门禁 | 两端WGS/GATK executiontrue、effectiveautofalse；PROD scantrue/TEST false、原watermark保留 |
| 外部健康 | 最终backend切换后TEST15:04:56Z及PROD15:05:16Z均HTTP200/ok，原始exit0 |
| Heavy | 两端core554f、各精确进程及双新鲜快照通过，25 Lease实读一致，不清Lease |

最终只读回执SHA：PROD18ff3d914f5f2f319f8d9489f05f728050fdb4c225ee27e7295a0e3c31ca9f6f；
TESTd7093fad978a7d93f88c7172eaf10a111f962217d85722c8d0ad7d64be921898。
原PROD Gate4 exit5是env auto与有效策略混同的验收脚本错误，原失败证据保留，以实际
配置/解析器/外部health只读闭合，没有修改策略或重复apply/POST。安装前policy字节
快照未采集，不声明旧新策略字节完全相同；当前路径、SHA、只读挂载及有效autofalse已验。

本轮验收仅含受影响的安装/接线/实际加载/资源与已有API回读。已验UE/Group证据复用；
未提交新marked089、真实group临床canary或完整批次，不能把发布通过称为新批次全流程
验收。旧attempt不迁移，5类Worker不重建。任何新marked089建立后禁止自动全局降包或
回退旧producer/DAG；保留兼容栈按诊断修复。AF公开索引和文档已闭合：docs85cae2c+
d14e567，产品仍80abdfc；最终index6603fdf8a4de03d781aa8fcdfc56327f4325db9890d2e3d8d069e52196414d39，
local-only tar25690074ff2c9def2ee54afb0ecfcef407e9fb0c54d0b485a525bfb707286b96。
108项证据引用未改变，索引两处表述更正和时间变化不涉及生产或原始回执；旧版字节保留。

以下为按时间形成的历史检查点；“待安装/closed/待发布”不代表当前状态，不得重放。

## 2026-10-01 最新执行授权：WGS4.2.3与共享0.8.9

TEST实际联合配对已验收，final index24b901d01590f12dc0c0aac3aa9d916f3ee79051a6487c5e616c475dd6c917e6，
39成员archive1bd2928fbad15bc9b47c697da091863f5be7353c55b8f3594c521d9853b0f2bc。
四consumer实际089/1f5、TEST六服务source/import/dist、完整62挂载、423 catalog和Heavy
双新鲜读数通过；初始验证脚本错误已按原证据收尾，没有重复POST或放宽产品校验。
Rules现有数据0条、未提交marked089或临床attempt，不称真实producer回放或完整临床验收。
现在放行AF按固定packetf9cf2671/80abdfc完成PROD六服务与精确Heavy、正常receipt/CAS
441d5e7→bafd27c。核对通过后paired最后恢复各环境原门禁，不改原有效自动提交策略，
不重复UE/Group测试、不扩大功能或重传/清理。精确操作与回滚边界见最新HANDOFF。
这是生产下一关GO，尚无生产完成回执。

安装完成证据：原始命令13:21:16–13:21:33Z exit0，shared CLI/import0.8.9/source1f5，
30源全部匹配、197其他分发不变、bootstrap9e36、旧bootstrap备份匹配。
log c74eb2e4、after-install4663ccc0已审，AF继续已批准TEST配对。
两端入口closed；四consumer已配对，生产网关/catalog/Heavy仍待，不称整次发布完成。

用户最新直接指令“直接放行安装，和本次发布没有关系”覆盖4个跨UID关键词PID调查：
停止这项排查，不动无关进程。native第二GO已发，AF完成既定v3 admission关闭并把
有效门禁回执直接交native后，即安装固定e9fc19dd脚本/f843 wheel/9e36 bootstrap；
不再等待额外协调审批，不重复全量扫描或已有验收。生产新入口仍需安装后TEST配对
验证再启用；当前授权不是声称已安装完成。

最终packet f9cf2671 /44成员archive cf8fef55已完成静态及独立审核，无阻断；
43项引用SHA/size一致，原始归档回执已核。当前仅放行AF窗口第一关：刷新身份/有效
挂载与任务idle，执行v3旧源码admission freeze并确认。PROD只关WGS/GATK execution
与auto-dispatch，TEST只关两execution，扫描和原watermark字面值保持不变。
native第二GO现已发，收到门禁关闭证据即安装。配对后保持v2.paired-frozen/paired-management；
TEST实际联合验收后再生产catalog CAS，v2.paired恢复原门禁必须最后执行。
任一marked089出现后，包及producer/client兼容栈均不得自动降回旧版；保持入口关闭，
先报告明确修复方向。此为操作顺序明确化，不新增测试或发布范围。

源码补齐验收更新：最终AF80abdfceea0d604e6524375e2b1a2aa32022ee65（parent0afd）；
仅两处保护补齐，原17 focused及2 PostgreSQL GREEN原始证据已审。下面待提交描述为
此前检查点，不重放。node16/bootstrap/phase/frontend原hash仍有效，不重建或复测。
最终packet需列PROD/TEST节点Heavy collector旧entry/core到既有554f3ed的精确接线、
启动身份与回滚；后台bind不代表节点加载更新。当前仅候选，无collector重启/清Lease。

差量最新状态：`_controls` 保留已得BS10610 GREEN17/1.16s，file e9b16fe5，尚未提交/
部署。另准许删除main force_new_generation分支重复的锁内sync：同请求锁前同步已在，
锁内再次另session锁同run会自等待。保留锁后身份/contract检查，仅用既有PostgreSQL两例
验证，结果待交接；这是保留生产修复，不新增执行/恢复机制。最终源码SHA待两项提交。

发布前差量：0afd遗漏实际生产Step4 `_controls` 的严格旧queued恢复豁免，公共UE调用链
没有等价退役；AF仅保留该精确hunk并复用现有最小回归。新版摘要helper保留，不整文件
覆盖回旧版、不扩恢复框架。最终AF提交将在验收后追加；0afd仍为本表已审基线而非
包含该补齐项的最终可部署源码。正式切换需此项与完整rollback packet一起通过。

当前唯一任务卡W423-R1-UNIFIED089，承接已验UE04/05和UE06隔离交接，不重开源码验收
或旧Step1事故。用户明确纠正：发布后新WGS任务切换4.2.3；422退出新任务入口，只保留
历史attempt和回滚。取消先发422-native089的中间路线，不再新增422 binding/phase alias/
部署receipt。已有未启用草稿标obsolete/not-selected，静态兼容证据仅供历史参考。
唯一候选为WGS bafd27c/e481/r1、GATK7.6.0 a4f/r5、共享native1f5/f843/0.8.9。
AF需列明生产实际producer/DAG/服务及overlay的最小切换差量与完整回滚；先最终组合
TEST验收，再按审定窗口切换生产新请求。旧release ID/attempt保持冻结，不原地迁移。
严格版本/hash保护不改，不能用旧publisher receipt声称新Operator配对验收已完成。

用户已明确选择统一升级共享nipttest和生产GATK为0.8.9，WGS/GATK及后续流程采用同一
native版本；下文“待安装选择/建议TEST-private”全部作为历史记录，不再阻塞授权。
native owner唯一负责安装冻结1f5e1e0/f843完整wheel，AF owner唯一负责相关真实consumer、
gate/policy/selector配置配对。先双方新鲜预检与活跃批次安全/rollback确认，再依次执行，
避免包先变、配置仍旧的窗口；现未执行安装。版本与实际CLI/import/assets必须一致。
生产GATK/native及WGS目标423已明确，不代表无关BS96服务升级或真实临床提交；不重跑
或修改已冻结attempt，不部署延期FQ/async prepare，不执行真实LIMS/批次清理。

用户随后要求废弃私有环境：当前cce-pipeline/operator统一为共享nipttest0.8.9，WGS、
GATK及后续流程的新请求不再选择流程私有安装。AF负责旧入口退役/迁移，native单写
共享包；旧副本仅为历史attempt/rollback保留，不直接删除。解释已向用户说明：本轮不
强行合并生信工具依赖，也不合并TEST/生产数据凭据。共享bootstrap若存在双policy实际
冲突，按精确合同报告解决，不松绑授权根或改成新的私有版本分叉。

10:21Z前预检回报：生产/TEST非终态分析及传输均0，相关Airflow DAG queued/running0，
node200只保留collector。BS/node005对同一nipttest可写，f843候选及45c9回滚包已确认；
未安装、未关闭门禁。四consumer真实同cluster/PVC a96cb97f/PV80dc8875、/workspace
映射，旧TEST policy中的35e498b9是过期UID（原始读取SHA b9a0e6b0）。不扩native schema。
仍须定稿公共platform/source closure、4个受信wrapper的目录/registered-stage配置和
完整rollback；native单写包及包旁bootstrap，AF单写policy/消费者。就绪后才开启短暂
新派发维护窗口，安装配对验证后恢复原有效门禁。不要把仅pip成功视为发布完成。

## 0. 最新用户范围：W423-R1（优先于下方历史JR-02–05全量顺序）

- 先跳过prepare阶段FQ合成，完成已合并4.2.3与cce-pipeline更新，重点更新WGS/GATK
  两个Master，展示group内正在运行/已完成/等待的rule及各自真实起止信息。
- 新async prepare、merge-progress、QC2、审核回传及未合入CRAM交付布局不进入本轮。
  已合并release原生行为保留，不删除原merge算法；本轮平台不启用--merge。
- WGS owner刚交付的11ddb7a/e950合同/7项synthetic证据与用户消息时间交叉，保留为后续
  prepare候选，不继续消费或补验；以df6bbfc或可证明等价的隔离分支加必要云绑定发布。
  AF以已整合827dc56为起点，新增prepare候选另保留，不能reset或混入本轮。
- native已审1f5e1e0/f843 wheel和canonical runner继续使用。镜像由WGS owner统一入口，
  每镜像一个实际构建人；先核实两镜像准确基线/profile，GATK不改业务版本/算法。
- 测试重点仅最终镜像内容/配对加载和现有事件到API/页面的一次group状态时间联验。
  复用既有8项/CCE/Worker证据；不重跑完整P0、五类Worker smoke或临床批次。
- 先TEST发布验证，再审定BS96最终423新请求切换窗口与精确服务清单；不是立即上线。
  nipttest共享消费者/policy/活跃使用/rollback审核保留。
  测试发布完成后，再和用户讨论local、SGE、CCE的合成职责，不提前确定三者分配。

完整源/制品/hash见下方已核实候选记录。下面prepare/QC/回传开发批准是历史记录，
已被本节暂停，并非本轮继续执行的指令。

### 最终源码与制品收尾（当前状态，优先于下方逐次记录）

| 部分 | 本轮冻结候选/结果 |
| --- | --- |
| WGS源码与资产 | bafd27ce5f38e736aae516d5c00247e449872479；资产20261001.1-wgs423已发布 |
| native | 1f5e1e0d7d7095ab43b14f514aafe623f4f89ca3；0.8.9 wheel f843cfa7，共享安装及四consumer已验 |
| WGS Master | sha256:e48125333a8a4343921eed4a63dd3346d80a981b33ba7e5090136ef3da94f941；已push |
| GATK Master | sha256:a4f8d15e728b9e9c4f56d4b7cea320cef57998b32ae59875d286b9d975f6be1d；已push |
| profile原字节SHA | WGS r1 436a6608；GATK r5 17d2bb59；四node配置/TEST已选择，PROD网关待切换 |
| profile规范化revision SHA | WGS 21558a4c8ff146715ee25f988c0711f2cd39f1f3ce1fad992c4160b69547bdc1；GATK fd652a12443d4db1ce255c77a3e31b95158da85763908c144e23b8f8d84f2b24 |
| Airflow | 80abdfceea0d604e6524375e2b1a2aa32022ee65；parent0afd，保留5415/0048及两处生产保护 |
| WGS owner最终BOM | 3194dd3373026f4ee6e9ea57b317aad3443de1a69955475fa1934a4c70a2fd1b；26项原始证据hash一致 |

BOM本地：`D:/pipeline/task-artifacts/w423-master-release-20261001/provenance/final-release-bom.json`。
它保留签收时的AF5415与phase待补快照；本节明确追加AF0afd，不重写历史BOM或重发制品。
WGS docs-only1129162也不替代实际已发布bafd payload。

最终profile规范化摘要由BS10610固定f843 wheel zipimport的1f5 schema生成，无安装或
云端执行。协调已读原始final-profile-digests.sh/log；log SHA
9fe8445355d70adf04f7ad5a67f5dcbc5ad868507203ce5241b0f52e57e0cd71，script SHA
ac74c49d418d809974ce76d82b4cfc8d624097a2289897ebb915de8446ec7fc9。
原profile字节未变，Master与WGS资产摘要一致；这只补候选输入证据，安装后实际consumer
验证仍为pending。不得改写历史BOM中当时null值，不重复计算或将raw SHA代入canonical。

AF0afd的实际diff/唯一parent7ad、GREEN7/1.64s、8项manifest哈希和archive1d242cad均经
协调核对。18 additions包含422原12+新6，7个base source overrides包括原SMA；GATK
精确r5，未审identity/rule仍Unknown。此前版本GREEN26和group API2/UI9/build不重跑。
以上是源码与制品验收，不等于最终TEST已加载或临床批次通过。

QC原始ab29证明必经规则只生成表/交付脚本；native owner检查固定1f5正常Step6只落地，
不执行独立delivery/LIMS/host Step2脚本。因此本轮不扩回传配置/新开发，不因历史BOM的
外发提示把正常group测试再挂起；实际执行独立交付始终不在授权范围，空密码不作安全开关。
这不是对未来AF额外handler或人工脚本执行的保证，不运行真实HTTP、不改已发布QC配置。

用户随后已选择共享nipttest及生产GATK统一089，取代TEST-private建议；执行授权和
安全顺序见本文顶部。由native/AF完成新鲜活跃任务预检及实际CLI/import/runtime、
canonical摘要、私有配置、TEST入口/回滚配对和最小接口验收；不扩大到全部BS96平台
升级或临床运行。WGS制品owner收尾待命，不新增测试/开发。

### 前序补齐项记录（以下待审字样为历史状态）

1. WGS `bafd27ce5f38e736aae516d5c00247e449872479` 安全原始提交已审，6文件/9行
   必要绑定、df6父提交、旧dirty文档保留；不含延期11ddb。候选资产ID
   `20261001.1-wgs423` 与 AF catalog ID `wgs-4.2.3-bafd27c` 是不同合同字段；
   后者需匹配最终source前7位，gateway批准repo与SFS pipeline也必须分列。
2. AF `b3f0174` 的group消费验收不重跑。但源码两处精确版本集合
   `validate_release_repository`/`_uses_prepare_handoff` 仅到V4.2.2，原测试仍拒绝
   V4.2.3；backend/main.py必需handoff receipt集合也有相同缺口，现已直接核实并纳入。
   原AF owner唯一当前卡AF-V423-BINDING：三处一起保留现有合同及缺回执not-ready保护。
   UE04/05/06已验且祖先在b3，不重开或恢复旧Step1。新版本继续已有prepare合同，不改异步/
   合成，不放宽root/allowlist/身份/摘要校验，未支持版本负例保留。新HEAD及focused
   GREEN待交接，b3暂为消费基线而非最终发布HEAD。
3. 新9对象snapshot SHA749b8b1651e5fc97fb2381f8bf5fc98e289d1a786553a3734723557e47d0fd71、
   16个OBS精确新目标无冲突preflight SHA408141979541566123e88f0da9f2fc987f3d838e427bb2ce4748bc638ddd3056
   已读回。9对象原始upload回执SHAca632f6cd93e3552fec9422ebf6a8597eae38750bd0b75c5cda6031158bdce93
   与日志已审，size/SHA/MD5 metadata逐条匹配snapshot，总4,900,000,732 bytes；不是
   新一次服务器端全量hash。SOURCE_READY/SFS READY未验收。既有088/417de59 publisher
   runtime-info已读回，按owner能力核验可用，
   新路径apply/export不是TEST operator089启用，也不能覆盖旧资源。
   **后续源码核实更正**：088正式release publish的update模式本就支持不存在的新目标；
   已有目标必须有matching baseline。采用该正式update链，撤销必须replace的旧推断，
   不调用replace，不新增发布逻辑；原始模式语义依据与最终发布回执随BOM保留。
4. 候选包脱敏追加且仅追加 `cfg/auto_qc_config.yaml:lims.password`，与既有三个
   DingTalk字段同一可复现变换、保类型、保全部其他业务字段；不输出秘密、不改source。
   真实外发与新增QC2/审核回传不启用；原生QC计算/汇总仍保留，不能以缺凭据跳过。
   若原生QC强制依赖LIMS鉴权，报告准确耦合/候选限制，不在本轮擅改业务逻辑。
5. 用户的shared/private089安装选择仍未答复。两种安装和入口切换都未执行；
   独立资源发布/版本接线可继续，不以此绕过安装选择，BS96不切换。

### WGS 正式资产发布回执（后于上述待 READY 检查点）

现成0.8.8/417de59发布器执行原正式release publish/update；原始log与cce-release.v1
回执已读回，assets `PASS`、`state_verified=true`，不是TEST执行包0.8.9已安装。

| 项目 | 已发布候选摘要 |
| --- | --- |
| 内部 receipt digest | `16f131a4ed501bd3c2f7747e3532f34bd84b18d024d39f90525b55693282893f` |
| receipt 文件 SHA256 | `006b405fcee225baeb5d7150e3d9a74199b95f6abe69dede694d01fd0676eef3` |
| pipeline build（140文件） | `cf2b6bdfac113215f94ca4f782d2234bcdcfcc1c23662bf514aba8d4038724f5` |
| resource manifest（9增量+map/READY） | `7cd067fb5ad854a387355bed27b59f3039d2343f1f8790af1d78f534096d5252` |
| asset manifest | `339e565d8e14f7b470fe1914dc4cf1ad33a6b8717ee3a11179353483725a537e` |
| WGS profile | `436a6608ed0b5d76739b8191589b4de435db15d7be720cc537c7e59f94566abc` |

source固定bafd27c，资产ID20261001.1-wgs423/catalog ID wgs-4.2.3-bafd27c及两gateway
repo路径均正确分列；资产/发布节的共同字段机械核对一致。新SFS pipeline/resource和
新WGS profile仅写此前批准新路径，未覆盖旧release。owner事后Pod日志NotFound如实
保留，安全Job绑定/Complete与ctapa新source/profile可读性待最终交接，不重跑发布。

GATK profile唯一writer仍为WGS制品owner：actualTEST62265原字节SHA核对后，仅新Master
a4f与必要独立revision/外部新路径；旧profile、源码、业务版本、资源、Worker/配额不改。
AF只消费最终同一profile并配对TEST selector/runtime；raw SHA和canonical revision SHA
不能混用。额外合同字段若必须改变先报，不扩大GATK业务发布。本节资产发布成功不授权
089安装、TEST入口启用或BS96切换；安装选择待人类回复。

### 两 profile 最终候选与发布运行身份补齐

- GATK外部候选：`/bi/biodevrwbi/33.chenjiucheng/project/cce-pipeline-profiles/gatk/releases/20261001.1-group-status/gatk-scmc-v7.6.0-r5.yaml`，
  BS10610对应`/mnt/biodevrwbi/...`。rawSHA
  `17d2bb5911abf7ac15fdca63c0da7b8617411b159f62cf6cf7e2c541799d7e78`；原62265未漂移。
  receipt SHA3c05056f16f1a50393ec726c2676bc20501dafba8d5ed0d15409ffd1c0d32af0已读，
  语义差量只有revision r3→r5与Master ee93→a4f；r4另属已验088/P0候选。
- WGS436a与GATK17d2均为原字节profile摘要。AF后续按实际native消费者合同计算
  canonical revision digest并分列，不能用raw替代；目前两个profile均未激活TEST入口。
- WGS资产Job `cce-assets-wgs-4.2.3-r1-20261001.1-wgs423`，UID
  `0fa72489-ad50-4acf-bb00-201fb9decf4d`，succeeded1；08:35:18–08:37:31Z，e481镜像，
  非root10001:10001/fsGroup10001/supplemental520，安全原始绑定已读。
- node200 t640/ctapa6801:520读取新SOURCE_MANIFEST/adapter/Snakefile/WGSprofile成功；
  source manifest SHA23e8cbdab8f4387821130609185433c6d8ab9b59d17e32f39c225a57a940abe0，
  WGSprofile raw436a相符。无需新增reader/重复hash。已回收Pod原日志不可用照实保留。

WGS owner仅收尾统一BOM及文档，AF继续精确423版本接线；0.8.9安装选择与TEST真实加载
配对仍是待完成项。本节不代表临床运行、生产或整体TEST发布验收。

### Airflow 4.2.3 必要版本接线完成

最终AF HEAD `5415b13f6d699deb5809d925f99fd4706520bc47`，parent b3f0174；group产品0048
和此前UE修复不变。产品差量仅gate两个版本集合及backend必需handoff receipt集合精确
接受V4.2.3；未知V4.2.999仍拒绝，身份/摘要/root/代次/两stage合同未变。
协调已读源码diff、原始BS10610 RED5fail/2pass→GREEN26pass/8.33s、隔离运行脚本，
manifest10项源码/测试/日志SHA一致、tracked clean/diffcheck0，无重复测试或部署。
GREEN SHA77090ca52dcfe63867530c2365390ce70fd04a5db13eb3e36f83f602a5d18609。

该源码卡通过并交WGS更新BOM；两Master及WGS资产无需重建。余项为最终423清单对应的
phase/catalog静态绑定，以及安装选择后实际089 canonical/runtime/private配置/TEST加载。
旧421消费fixture不能替代423制品绑定；也不为此重跑已接受group/UE/Worker测试。

### 最终 phase 配对缺口（未完成，必要展示差量）

AF本地13个catalog字段与已发布receipt一致。源码实际phase consumer按精确release
身份选择，当前WGS policy仅登记cc9/34bf/ebf/441d，GATK仅至r4；新bafd与r5会Unknown。
协调直接核对后，分工为WGS提供冻结源14模块/include/use-rule别名的实际差量，以及
最终GATK SCMC_GATK.smk与已验1cf9 blob/17rule的对应；AF仅按现有policy结构登记
新身份/准确additions/source overrides，保留旧release。无来源证明不复制旧映射，
不引入prefixfallback或第二套rule状态系统。最小验收为原phase fixture的新身份、
实际变化rule和未登记Unknown，不重复group事件/时间/Worker/full P0。

未审submission_options继续不可用，不把cc9的DNAscope defaults移植给bafd。
仅静态核对现有关闭options路径是否尊重原生Haplotyper/all、不启merge且普通提交可走；
真实阻挡或算法覆盖才报告具体差量后处理，不能借此重开prepare或新配置功能。

后续AF一次静态链核对确认：普通catalog省略未启用options，后端/gate不注入algo，
reference=all，本轮选用该no-merge入口；Haplotyper仍由固定WGS源的原生默认提供。
独立test-projects源码导入preview要求审定options/effective-config，目前bafd未登记会
HTTP400；该入口不用于本轮，限制明确延期，不复制cc9 attestation或扩展配置开发。
这是入口范围决定和静态结论，不是实际测试派发/生产/临床批准。

固定源证据现已到齐并审：phase-source-audit SHA53f86f3429b7ea21a846e2b08e064169132d11ae9099fa40030ec948fddcc281，
5原始证据hash与14模块的441d基线/bafd冻结blob匹配。6模块变动但无rule删除/新增include，
只有QC的limsQC/auto_qc、SNV的varid_txt2vcf及其3别名新增。GATK最终冻结host模块仍
1cf9/17rule；不冒充新SFS读取。AF注册需继承422的12additions再加6，共18；相对cc9
base的overrides应7处（包括此前SMA），而不是只收相对441d的6处。旧release不变。

原生新增QC两rule的空凭据运行依赖尚待WGS静态说明：是否cloud必经、既有开关、输出/
失败语义；不得真实外发、注入凭据、跳过QC或扩QC2。如mandatory鉴权阻断候选运行，
先报告具体限制由人类决定。phase名称来源验证不能代替该运行限制核对。

WGS后续静态结论：两QC rule是cloud必经，却只生成表/脚本，无实际HTTP/执行回调；
空password不是它们的直接失败条件，原生QC数据要求和hold不变。但生成配置仍clinical，
执行lims_callback.sh或host Step2_upload.sh/uploadAll链会HTTP，且失败记录不必然非零。
因此本轮不执行真实交付脚本，不能声称整个TEST交付链已禁用LIMS。现有mode=test/
--test仅作为未启用提案，不修改已发布不可变制品或提供凭据。native owner仅静态确认
正常089Step6是否触发这些脚本还是仅复制落地；该调用关系尚待证据，不运行真实回传。

### 范围隔离回执

- AF已切到 `jiucheng/airflow/W423-test-group-release-20261001` /
  `827dc56004ddf7857644499c85835ded8ae93a85`，协调者只读Git核对tracked clean；原
  `.codex-artifacts/` 保留。新增prepare内容仅107行synthetic测试，已独立保存
  `jiucheng/airflow/W423-prepare-deferred-20261001` /
  `08e4cbc10350f3f7976117fb1f175897b368fa8f`，未运行，没有prepare产品/DAG/API变更。
- WGS已确认停止新增开发，保留11ddb7a及4dirty/5untracked docs；获准同正式仓库从
  df6bbfc建立隔离发布分支，保留原dev指针与延期ref。不新增worktree，不强制checkout，
  不批量stash/reset/revert；若普通切换覆盖dirty则停报。Owner随后回报隔离完成：
  `jiucheng/wgs/W423-group-release-20261001@df6bbfcdf7493aa63413bb321dae86317138300f`；
  原dev/deferred仍11ddb7a，9项dirty/untracked前后清单一致。原始隔离回执已读回，见下节构建记录。
  构建从固定提交导出，不把脏工作目录或私有配置打入制品。WGS唯一构建两个Master。
- native确认不重开prepare/core，也不另行构建Master；依据既有原始报告，executor继续
  `0.6.4+bs8.dev2`，既有wheel SHA
  `4adf2595794b3f08cc22b506173c33e99dcad795102417079f8a2d042a828b1a`。
  这是复用已批准版本，不是本轮升级或新增后缀；最终builder仍须核对实际输入摘要。
  既有Worker无需重建；旧报告不替代新组合GATK API/页面的实际差量验收。

WGS owner已核实两份executor wheel实物摘要一致。其报告的历史WGS r3 profile/digest和
GATK profile/accepted候选不是当前TEST active证据；正等待AF实际selector/profileSHA/digest。
若某流程测试端未启用，应如实写未启用并提供候选基线依据，不扩大访问BS96来寻找active。
导出必须使用新的干净任务子目录：旧native-contract任务candidate保留延后merge_progress.py，
不能覆盖解包后携带残留。协调者已提醒原builder，旧导出/证据不删除。

### 本轮必要云绑定/资源差量（不是重开prepare合成）

已读 `D:/pipeline/task-artifacts/wgs423-merge-paths-20261001/REVIEW.md`：release已合入，
但df6的pipeline/resource-set/profile仍4.2.2、正式WGS环境operator为0.8.8。允许WGS
owner在本轮候选仅更新4.2.3云绑定和adapter0.8.9要求，显式选择批准nipttest operator；
不安装/改变正式 `/bi` WGS环境，不改旧profile/bundle，不实现async prepare/FQ合成。

release数据库10变化字段对应9唯一data+6indices，3HC复用、6data为新引用，两个ROH
字段共享一文件。owner须先冻结精确source→destination、size/可信digest、索引/复用项、
目标现状和同步计划；仅新4.2.3资源前缀，不整目录搬迁或覆盖/删除4.2.2资源。
校验仅传输完整性、准确映射及READY，不扩大生物内容回归/QC2。现有检查是chenjc源
可读，不等于ctapa可用；最终测试配对按实际运行身份核对必要路径一次。
权限/缺资源/目标冲突/凭据暴露风险先报，不换库、不放宽保护。新改动需新commit/BOM。

源元数据清单已审核：`provenance/resource-source-inventory.json` SHA256
`c6974c0aac225b529d77d1057834c38dcbd84b5676e3e69f6ea8a3eba60b94c4`，
身份t640/chenjc6708:520，不是ctapa核验。10变化键对应9data+6index；HC3data/3index
拟继承4.2.2，新增6data+3index共9唯一目标、4,900,000,732bytes，ROH双键只存一份。
所有拟新增目标位于上述独立4.2.3前缀；BKW whitelist及index另列保留，不替换普通V1。
协调者仅校验清单摘要、去重计数、大小之和和目标前缀，未复制或读取资源内容。
所有digest尚null，现有SFS map继承条目、新目标现状/真实写入映射、运行身份可读性
及一次完整性校验方案仍待owner补齐整份传输计划；目前sync=NOT_RUN，不可标READY。
adapter0.8.9定向RED→GREEN由owner报告，最终源码提交/原始证据待联合BOM审核。

### TEST 实际基线漂移（AF fresh 回报，尚未切换）

AF核实node200实际 `t640/ctapa6801:520`。BS10610当前catalog
`/data/wgs-release-catalog/wgs_releases.yaml` SHA
`6801b8a8365ace077c88ee5e6608c8cc3196948c7b6c8dc8ac074ffe9354b910`，active为
`wgs-4.2.2-3b1dae5`，指向 `cce-pipeline-profiles/wgs/wgs-4.2.2-r2.yaml`，不是历史r3。
catalog登记pin c98b13c6...与实测profile SHA
`cccb04c5b8412d7e7a53e1cb667615ed7c46a597321a94e90a29820008176606` 不符。
停止共享pip/切换；不篡改旧pin/覆盖旧profile来通过检查，本轮独立新profile/catalog成套。
实际Master/workloads与GATK selector原始回执由AF继续提供，旧active和可选择的已验收
base镜像分开登记，说明选择理由；不把缓存candidate标为active或因此丢弃必要既有修复。

AF报告production WGS selector已选private assets，但operator解释器仍nipttest。
解释器共享不等同于包导入依赖，也不证明完全隔离；仅只读追踪本次共享替换所需入口/
import/selector链，若有未覆盖影响继续不pip，不能替生产做迁移/服务切换。
TEST policy原pin与shared当前包版本分别列实测值，不能单凭版本名宣称兼容。

### 双Master底图裁定（以fresh实装证据补充历史报告）

WGS builder复核actual r2 profile SHAcccb04c5，其Master仍为
`3d180a9f074cf38ffaf18446f2910a316e2b784b8f7f859bea5dc4a74d10f1af`；容器实装
Snakemake9.24+biosan1/executor bs8dev2/UID10001。允许以该digest为WGS direct base，
从新建 `w423-master-release-20261001` 干净任务根构建固定native1f5/approved4adf。

GATK源码profile SHA62265f84...指ee93eaf2，本机实装executor是 **0.6.4+biosan3**，
不是bs8dev2；AF actualTEST selector仍待完整确认。经协调裁定，新GATK可采用先前已验收
P0候选 `1a923e3213736bfb330797e69478ee9304821d96afa35962501e17c25e320754` 为direct base，
该候选已有bs8dev2及START/身份验收，再替换canonical1f5 runner/assets。
active（若确认ee93）、direct base1a、最终candidate三者必须分列；这是复用已批准P0插件，
不是新plugin开发，但相对旧active确有版本差异，不能再写“所有依赖不变”。

原始fresh实装/隔离回执现已导出至
`D:/pipeline/task-artifacts/w423-master-release-20261001`；此前本地ENOENT只是导出尚未到达，
不据此否认远端证据，也不重复构建。
两镜像仍由WGS唯一构建，native不重复build；新GATK运行身份/catalog/profile/native需成套，
不能只换image留不匹配pin。旧P0/Worker套件不重复，最终group受影响联验仍未完成。

native已据此修订 `GROUP_RELEASE_EVIDENCE.md`，协调者读回并核对SHA256
`31b3ca0031bffed3998c3c957c0021b13a3112cb386d7659a7613ddf44732a38`。
明确区分源码profile、待确认active与已验收direct base，原历史验收未改；仅证据记录更正，
1f5/f843候选不变，没有新增构建、测试或安装。

### 双Master构建与TEST selector新回执（未发布验收）

AF原始 `w423-integration-20261001/node200-runtime-bindings-v2.log` 已读回：
TEST GATK实际runtime.env SHA8d3e327b12304549afc35dea7c64db92f6e0ed8062bde65f2fa02fe4f45f1e46，
repo为 `/bi/biodevrwbi/33.chenjiucheng/project/gatk-cloud-airflow/releases/20260917-test-prepare-retry`；
其 `profiles/cce-pipeline/gatk.yaml` SHA62265f844b9119ea70d5088b99117c10df307b0c086b96c7f428de103aa86d51，
Master确为ee93eaf2。上节待确认条件已满足，1a923仍只是新候选direct base而不是旧active。

WGS构建输入 `provenance/master-build-inputs.json` SHA256
`0760a5c39504e79698fa6547d7c6bcd1d065d92210ae3b79851d2f326fe70d3b` 已核对。
该文件为构建前冻结快照，状态INPUTS_FROZEN不代表后续未构建；以独立build/smoke记录判定。
协调者已读 `logs/wgs-build.log`、`logs/wgs-image-smoke.json`、空stderr和ImageID，机械核对
10个COPY运行文件SHA全部匹配native1f5源码；Snakemake9.24.0+biosan1、executorbs8dev2、
UID/GID10001且operator package absent。节点operator wheel不是Master安装内容。

| 候选 | 本机Image ID | 当前证据边界 |
| --- | --- | --- |
| WGS `group-status-native1f5e1e0-wgs4.2.3` | `sha256:8ba8858e3bf3b86caaf1821bdcebd18b4f5f6d1238067b223cd287a4a6663a67` | build与10资产smoke原始记录已审核 |
| GATK `group-status-native1f5e1e0-gatk7.6.0` | `sha256:82f5bc7502beaa09697df8365599a846f4e0a85f86fa1f67ee89df0cd50b30af` | build与10资产smoke原始记录已审核 |

SWR push曾返回Authenticate Error；随后用户在WGS owner线程明确回复已登录可继续，
owner未读取/复制/修改凭据，只重试一次两push并分别远端imagetools inspect，均成功。
协调者已读回 `logs/wgs-push-after-login.log`、`logs/gatk-push.log` 和
`provenance/{wgs,gatk}-remote-image.txt`，push与远端manifest摘要一致：

- WGS registry digest `sha256:e48125333a8a4343921eed4a63dd3346d80a981b33ba7e5090136ef3da94f941`。
- GATK registry digest `sha256:a4f8d15e728b9e9c4f56d4b7cea320cef57998b32ae59875d286b9d975f6be1d`。

GATK build/smoke/ImageID原始导出也已读回并机械核对10资产匹配、空stderr、UID/GID10001、
executorbs8dev2且无operator。原auth失败log保留，不重建、不把ImageID当registry digest。
此为候选制品已上传，不等于profile/SFS/TEST已启用或group联验完成。最新失败工具标记
是候选adapter仍要求0.8.8时的定向RED，不是push失败；仅允许本轮必要0.8.9版本绑定。

AF Rules API已有group关联，UI必要补充进行中。producer历史accepted证据与synthetic
协议消费回放必须分开：历史canary-worker/master-events.json是Kubernetes EventList，
不是Snakemake规则原始JSONL。当前没有已核本地完整规则raw，不声称本轮真实raw→API
验收；不因此新建CCE reader/重复真实canary。最终API/页面差量及发布组合仍未验收。
共享nipttest安装继续等冻结bundle/import消费者影响结论与配套回滚，不直接pip。

### 共享包升级差量：不能混淆两个比较基线

已读回native `inspection/package-upgrade-impact.json`，SHA256
`08d9394d86177c5f2ad76821ac784a5d59bf874166dac284b6f6ab7a07d0ff80`。
批准rollback0.8.8/source417de59/wheel45c99到最终0.8.9/source1f5/wheelf843：

- 修改4文件：`__init__.py`、`_build_commit.py`、`assets/cce_batch_runtime.py`、
  `assets/cce_writer_guard.py`；新增 `stage_execution.py`，25文件不变、0删除。
- console入口名字仍为 `cce-pipeline = cce_pipeline.cli:main`；入口文本未变不证明
  运行时module/import解析或版本门禁不受影响，也不证明生产隔离。
- 此前“其他29文件相同”只指已验收0.8.9候选717→最终1f5，不适用于0.8.8→0.8.9。

AF仅针对上述变化核对现有冻结bundle/console/import消费者链，分别给出WGS/GATK与TEST
影响，不扩大成完整UE或生产审计。若生产实际使用shared changedassets/package版本，
应先报告精确影响和最小选项，不能把已批准测试安装解释为生产迁移授权。此差量报告
不含安装/测试/兼容通过结论；native尚未pip，配套回滚门禁不变。

### 已查明共享依赖与待用户选择的安装方式

AF的 `node200-transitive-resolution.log`、`node200-gatk-console-final-v2.log`、
`node200-native-chain-final.log` 原始记录已读回：

- 生产WGS所查gate/paired入口有效PYTHONPATH指private0.8.8，实际同环境module解析亦在
  private路径；不据此推广所有NFS消费者隔离。
- 生产GATK冻结bundle的runtime/guard文件不会被pip替换，但其cce_delivery优先导入
  `cce_pipeline.shared_permissions`。实际加载shared nipttest的 `__init__.py` 0.8.8和
  shared_permissions；后者字节不变，但升级后下一次进程会加载新包metadata。因此不是
  纯TEST隔离，尚无证据必然业务失败，也无证据走新stage_execution/shared runtime。
- 已查的生产GATK prepare请求实际上选择正式WGS环境CLI，不是sharedCLI；不能和
  下游脚本的nipttest Python混为一谈。TEST入口则确需新console/runtime/guard/policy/
  catalog/profile成套；旧policy漂移不可因pip自动忽略。

协调者已询问用户：建议沿用nipttest Python但将完整0.8.9包安装至TEST专用prefix并显式
选择，保留shared0.8.8/production不动；或坚持shared升级，先交生产兼容/影响方案。
这涉及此前明确安装位置的变更，未获回复前两种安装/入口切换均不执行。原owner可继续
group消费验证和新配对静态清单，不扩大生产审计/迁移、不重新测试已验UE。

### 允许的单次SFS只读资源预检

既有4.2.2发布map SHA654bce060b31c209d14a990515382dbcbffa60df667b9031a28806d338e4abfe、
files.tsv SHA67713468626acbcaecf62a1ac23181b487c1074cffc833a10a6889ac8db122e7由WGS
owner回报；原始清单将在完整传输计划审阅。BKW继承4.2.1独立对象，不按文件名替换。
SFS只有biosan-clinical PVC而无host直接挂载，fresh无可复用asset-status-reader。
允许WGS owner按既有reader模板创建一次有界只读metadata Job：先登记namespace/Job/
image digest/UID/GID/deadline并核环境；PVC readOnly:true，无SFS写入/初始化改权限。
只查小mapSHA、HC3+3index/BKW2关键路径和9新目标/root冲突及PVC映射，不跑样本、
不全库hash/递归扫描，不改RBAC/凭据/TTL保护。失败停报，结束仅回收本次精确Job/Pod。
这是发布预检，不是同步/覆盖批准；无需重复Worker canary。实际运行回执仍待owner。

### 资源预检完成与限定同步批准（后于以上待审状态）

协调者读回 `resource-transfer-plan.json` SHA46c4998423e606de5ace8d1b6c492a1b3a5f4306a987ae757826ff386232af89、
candidate map30dd72553d5ec44c65b5f490efa4800d25c1cb7c08b7f70b639e89cb2a649151、旧map654bce/files677134，
以及source9SHA稳定回执和ctapa6801:520逐路径一字节可读回执。机械核对9新对象唯一、
4,900,000,732bytes、完整SHA/索引映射、不覆盖标记、OBS/SFS目标拼接一致。
owner声明新map131keys覆盖128required；此为新候选，不替代发布后READY。

只读Job `snakemake-ns/wgs423-resource-preflight-20261001`，UID
`a5e2543e-8c90-4091-9122-8b1af7e5f5d0`，succeeded1；原镜像2b807、deadline120/TTL60、
readOnly PVC挂载及非root10001:10001/groups520已读回。旧mapSHA一致，继承HC6/BKW2
均regular/readable，新roots/9targets不存在。owner报告本次CM显式回收、Job原TTL回收；
不重复reader或影响旧Job/PVC。Pod可读与node200 ctapa源可读证据分开保留。

最终新增SFS目标修正为既有publisher标准
`/workspace/wgs/resources/wgs-4.2.3-r1/objects/...`，不是早期draft中的resource-sets/423，
不创建symlink。继承的4.2.0/4.2.1对象继续原路径；原4.2.2 map不改。
允许原WGS owner推进这9对象的独立候选同步/既有完整性校验，不等operator安装选择。
执行清单须补明已核profile的bucket `obs-biosan-bioinfo`、namespace `snakemake-ns`、
非秘密配置摘要；仅经node005既有专线入口。写前精确检查新OBS9对象及本次manifest/READY，
SFS不存在不能证明OBS不存在；未知/不同既有内容停报，本次可证明相同内容只幂等复用。
禁止旧prefix覆盖/清理、全库重hash、真实批次、权限重整或借此pip/切TEST/BS96。
正式manifest固定独立commit，不能把dirty目录/延期prepare打入包。若既有publisher
依赖未批准089安装，先报精确依赖，不绕过安装门禁。同步完成/READY仍待原始回执。

### 候选包通知字段脱敏

owner仅检查字段名发现源模板非空dingtalk.webhook/secret/members，未导出值。
允许仅新pipeline打包副本清空这三字段，保持字段类型/业务算法/数据库路径及callback
脚本路径不变；源码、Git历史与凭据不改。原config.mail.ini/prepare/config.yaml等私有
排除继续有效。只记录脱敏字段名、可复现transform、输出文件/包manifest摘要，绝不把值
写入证据/diff/临时提交。沿现有打包检查一次确认仅许可字段变动，TEST通知关闭，不真实
发送；空通知若导致强制失败则报限制，不扩改核心。未执行凭据轮换或历史制品泄露审计。

### Airflow group消费候选审核

commit `0048c3694164f087b686ad69303538b166244262` parent827dc56，tracked clean。
协调者读diff、synthetic97行测试、原始API2passed/UI9passed/Vite成功输出、6帧DOM与两截图；
保留旧harness构建失败后修正记录，未重复跑测试。产品只改现有Group列和无成员start时
等待显示，不变API/projection、不制造inventory行；等待/独立运行/成功失败时间和消息
的synthetic消费证据可接受。现测试使用既有release注册，不声称最终423版本绑定已验收。
真实producer已验收报告复用，新配对/423精确ruleinventory/phase及TEST启用仍待后续；
安装方式未获用户答复前不切换。仅源码/consumer证据阶段通过，不是整体验收。

AF最终交接HEAD固定 `b3f017477ba4f1814f14291cc36e8c17d5b816e8`，产品仍0048c369；
协调者核对新增4文件仅文档（25+/2-）、提交祖先、tracked clean与diffcheck通过。
读回owner一次whole-branch review记录及其范围限制；不把owner无finding结论推广为
已验生产/新部署。`final-evidence-manifest.json` 八个原始文件摘要再次逐项一致。
AF候选源码交接完成，后续仅等待用户安装选择与WGS最终BOM/READY进入TEST配对，
不为等待而继续重复审阅/测试或恢复旧批次任务。

### WGS 独立绑定提交回报

owner回报 `bafd27ce5f38e736aae516d5c00247e449872479`（parentdf6bbfc，未push），
仍在W423-group-release-20261001；4必要binding文件、README精确选择片段和一份窄范围
说明共6文件，原9项dirty/untracked保留、延期11ddb非祖先。原始Git提交回执待导出审核。
协调者已读定向operator-binding-green.log：1test通过，精确接受089/拒绝088；这是版本
门禁单例，不是发布/运行兼容性验收。静态检查脚本仅允许runtime4字段、scheduler镜像、
prepare的profile_file改变，默认Haplotyper和rules/Worker/localSGE保持基线，实际提交
diff仍须对照。新profile路径为
`/bi/biodevrwbi/33.chenjiucheng/project/cce-pipeline-profiles/wgs/releases/20261001.1-wgs423/wgs-4.2.3-r1.yaml`。

owner发现BS10610同名 `/bi/software/.../cce-pipeline` 不支持runtime-info；不凭路径相同
认定与node200包一致。核现成publisher实际Python/module/version/既有发布能力，若需未
批准安装则停该发布环节；不新增CLI、换装或绕过用户待决安装方式。独立源快照/暂存可继续。

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
| native | `019f9d79-be3f-7701-af33-3595d72bbfac` | 0.8.9 operator wheel/runtime、canonical Master runner 参数整合、共享包安装与包回滚；prepare handler 接入由 Airflow owner 实现，native core 复用 |
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

## 8. JR-01 / W423-03 审核决定（2026-10-01 后续）

三位 owner 已返回起点。Airflow 刷新确认远端 main 与
`refs/heads/jiucheng/release/production` 均为 `ce497d6`；在原 tracked-clean
worktree 保留 UE06 分支并新开 `jiucheng/airflow/W423-integration-20261001`。
先从 ce497 合入 UE06 谱系，再各一次整合实际缺失的 a85cfb6、6d11712、e634ca4。
owner 报告预览7文件冲突；协调者只读检查确认该分支正在合并、冲突尚待 owner 解决，
未将这一步记为完成或验收。原 GATK TTL helper 分支须保留，合并后核对实际调用。

### native 核心复用，平台受信 prepare 接入

协调者直接读取 native 导出的 `stage_execution.py`，SHA256
`21b505da319cc752c5694f2b42e4082dd02dc47e3c7ddad895fdb87b08581bd2` 与已验收源一致。
`ExecutionRef.from_trusted_registration` 对任意受信 JSON binding 绑定摘要；
StageExecutor 的 registry/resolver、后台提交、同 ref 观察、终态与进程互斥不要求 batch。
因此**不为 prepare 修改 native 核心/公开 ExecutionRef 协议**，不复制 WGS 合成逻辑。
当前缺口在 Airflow 受信接入的 `_STAGES`、`_trusted_ref` 和 `_freeze_registered_request`。

Airflow owner 实现时必须保持：

1. 只登记 WGS `prepare_analysis` 能力，不因公共 stage 列表扩展而顺带启用 GATK prepare。
   WGS 特定来源/路径/完整性由 WGS gate 的受信 resolver/handler 提供，共享 adapter 保持通用职责。
2. prepare prebinding 冻结后永久保持该执行的 ref；成功产出的最终 batch binding 另行验证绑定，
   不能替换 prebinding，导致 worker finally/重连/历史观察的 ref 变化。
3. 已冻结业务 deadline 与 SSH 预算独立。当前 `bio_wgs.py` 的 prepare runner 和 wait 都是2h；
   merge 新请求的24h期限须端到端接入，而非只把提交改成后台。普通 prepare 期限保留。
   期限到/观察失败仅需核实，不自动取消活跃后台、不伪造失败、不重置期限；仍可观察原 ref。
4. 原生 receipt、最终 selection/bundle/binding 未完整验证，不放行 Step1。保留原生合法
   `selected=[]` 的 all-pending/零选样语义：prepare 可完成但不造 bundle、不启动分析。

以上属于原 W423-03 差量，合并到现有 synthetic 验证；不另建恢复框架或重跑 UE 全套。
这次为源码/方案审核，不是新增实现 GREEN。

### Master 参数最小归并

协调者核对当前717 runner 确实只有 Master logger 参数，缺 executor 的
`--kubernetes-rule-status-dir/attempt`，并重读原定向验收报告。
native owner 溯源确认实际两行修复/测试在 `910bb782d6de9750d909345e2340db12b3bee690`；
`ad7bd2d` 是历史验收 HEAD，其自身仅修改镜像 LABEL。只归并精确 runner 两行与既有测试，
不 cherry-pick 旧 overlay/整分支。批准在最终整合候选上跑一次原8项参数/run-mode测试；
不再演示已知 RED 或重复 CCE/group smoke。最终仍0.8.9，旧wheel不覆盖，待 paired 审核后安装。
WGS 最终 Master 必须消费新 canonical runner/assets 与已批准的 executor 插件 wheel；
0.8.9 **operator wheel 用于节点 nipttest，不要求安装进 Master**。两类 wheel/镜像来源分别
登记；仅安装节点 operator wheel 不能证明镜像 runner 已更新。

### WGS 原生合同新增待审点

WGS owner 报告 auto-QC 的10X/30X来源覆盖与单样本/批次罕见病 applicability 不同。
需用精确脚本/配置及条件对照区分有意语义与消费映射问题，不直接改原生阈值/判断。
保留来源汇总，受影响逐项保留来源/参考或待审，其余可靠策略不一概禁用；LIMS维持关闭。
merge 当前具有 pair manifest/源stat/输出大小mtime及原子完成依据，但结构化当前文件/
计数/更新时间尚未实现；由 WGS 在既有准备证据中最小补齐，AF仅消费，禁止猜百分比。

native 新鲜预检回执位于
`D:/pipeline/WGS-noncoding-model/.codex-artifacts/w423-03-native-20261001/source-preflight.log`，
记录 server10610/chenjc6708:520、source7172573、tracked clean、旧backup保留及候选wheel匹配。
共享包仍0.8.8，尚未完成最终构建/安装/联合测试或生产发布。

## 9. JR-02 源码检查点与 merge 进度合同确认

Airflow owner 已完成源码整合：UE merge `3bf2871`、WGS phase `1a6170d`、GATK phase
`ac64347`、Step4 晚到回执保护 `827dc56`。协调者 Git 只读核对确认当前提交与
tracked-clean（保留原 `.codex-artifacts/`），`main.py` 冲突保留 UE generation/runtime-sync
保护。上述是源码检查点，不是新差量 GREEN、配套安装或发布验收。

WGS 原生合同受控文件：
`D:/pipeline/task-artifacts/wgs423-native-contract-20261001/native-contract-df6bbfc.json`；
远端对应 `WGS_test/cce-evidence/wgs423-native-contract-20261001/`。
完整 SHA256 `ac0a0d2a59fb7e29376bfe16c830a0f81018ceb66d2a00f5d8d6a89a72df0486`，
冻结 release `5fa72a9` / cloud `df6bbfc`，状态 `SOURCE_FROZEN_GAPS_NOT_ACCEPTED`。
实现后需重出新源/合同摘要，不能把此合同中的缺口当成已有能力。

协调者与 Airflow owner 已确认 WGS 提出的最小合成观测可消费，由 WGS 唯一实现：

- 路径为当前已校验 handoff 的 `artifact_root/prepare_analysis.merge-progress.json`；
  schema `wgs.prepare-merge.progress.v1`，scope `fastq_merge`。沿用受控代次目录、权限
  与原子写入；只启用受信 WGS CCE prepare 合成路径，不改变 local/SGE。
- 复制 handoff 的 `analysis_id/attempt/execution_id/generation/request_hash/release_id`
  和 `source_sampleinfo.sha256`；AF 对比当前冻结身份，不能按 mtime 选择旧代次。
  prepare prebinding 同时冻结既有 pending revision/hash，不能漏掉原生允许的 pending 来源。
- `state=waiting|merging|complete|failed|not_required`；`total_files` 必须来自真实计划，
  未确定时可无快照，不能伪造0/0完成。`completed_files` 只计已完整验证/原子发布或
  依原生完整性成功复用的 pair（每对2个）；`current_file` 仅安全序号 `merge-0001:R1/R2`。
- `updated_at` 使用实际观察时间，约30s跟随复制循环，不额外建守护进程；真实I/O阻塞可
  陈旧，终态不反复刷新时间。不提供不可靠字节百分比。
- 进度写失败仅降级观察并作有界提示，不能吞生物业务复制/验证错误；`complete` 只代表
  merge 子过程完成，仍需最终 sample selection/bundle/prepare receipt/batch binding。

双方共用一次 synthetic producer→consumer 差量，复用原生完整性测试，不真实等20分钟。
QC 源配置20列/46规则不等同于旧页面指标列数，不缩减已有 UI；来源 override、罕见病
适用条件差异如实登记，不能直接改阈值或默认为pass。受控源合同不整份进入 Git fixture。

### native 已接受的最小源差量

已读原始 `D:/pipeline/WGS-noncoding-model/.codex-artifacts/w423-03-native-20261001/`
下 `integration-green.log` 与 `commit-integration.log`：BS10610 定向8项测试全部通过，
提交 `1f5e1e0d7d7095ab43b14f514aafe623f4f89ca3` 只含 runner 两行、原63行测试及交接。
runner SHA `762c3acd1692fb42c8ecb2fe2b578b433b3271a16997103ea474830401a4d583`，
native core SHA `21b505da319cc752c5694f2b42e4082dd02dc47e3c7ddad895fdb87b08581bd2`
及 delivery SHA `da3dbbfff9c9382a92e4c78abf17679bb960920b55a3fa15ae7d2a326337c72c` 未变。
接受该源差量，不重复测试；新 wheel/最终 Master/测试配对验收仍待交付。

AF 合并的原 GATK TTL helper 与 ce497 基线 Git blob 同为
`b4ef441f6d50a4780f8f341ce852cf8c01150dc9`；UE06 是当前827dc56祖先。
这证明保留源码，不替代新 prepare/QC 接线的差量验证。

### 最终 operator wheel 候选（已审打包，未安装）

已读 owner 原始 `build-final-wheel.log`、`inspection/wheel-verification.json` 及精确
`inspection/source-delta.patch`，本轮源 `1f5e1e0` 的候选为：

- 路径 `/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/w423-03-native-20261001/wheel/cce_pipeline-0.8.9-py3-none-any.whl`。
- SHA256 `f843cfa7766169bb7e5485b2af99ffbe933aac9ae7e667056aa3223da62c098d`，153323B。
- 30个包文件中29个与已验收717包逐字节相同；仅 `_build_commit.py` 来源元数据改变。
  RECORD、source/version/entrypoint 检查通过，旧 bda21dd2 wheel 保留，包内无 Master runner。
- runtime SHA `c2988621e4552f4240f3f8c2254d99be315ad1633ed51b8f712bf310acced7c7`；
  guard SHA `e99378dcb1a0f71d3561c6705f4b5fe2f9886bc9e0307b5dc7c1b822de6e6d0f`。

协调者接受候选来源/打包证据；不重新验收相同包逻辑。原三位 owner 已收到准确产物及
Master/operator 职责更正。共享 nipttest 安装仍要先完成消费者/policy/活跃使用/回滚审核，
不能把构建成功写成已安装/配对/生产发布；Airflow 与 WGS 的新增接口实现仍在进行。

另已直接核对 owner 导出的当前 Master Dockerfile，SHA256
`6aacc15cf082cd142ec338bef3f3b81c8ace64f7c49f645933dfbf9fb87042f3`：
明确卸载 operator 包、复制 canonical runner/assets、只安装 `EXECUTOR_WHEEL`，并检查
不能 import `cce_pipeline`。上述分工更正有源码依据，不是新增镜像依赖变更。

native 完整候选证据另存本地同任务根 `inspection/native-candidate-evidence.json`，
协调者已读并核对 SHA256
`54fe4e5abc46dd0f9c5a83f3b0efbf46bd47ae403596f832bd5b3b79bfdafac2`。
远端为同 evidence root 的 `provenance/native-candidate-evidence.json`，作为本单 native
来源清单引用，不新增第二套登记系统。
