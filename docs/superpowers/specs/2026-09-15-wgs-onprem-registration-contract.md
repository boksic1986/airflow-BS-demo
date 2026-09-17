# WGS 后台项目首次登记合同 v1（R2-1）

2026-09-16 更新：BS10610 已部署并通过受控 synthetic 联调及用户浏览器复测；下方早期候选状态为历史记录。未合并 main 或发布 BS96。

任务：WGS-LOCAL-SGE-20260915 / R2-1；日期2026-09-15。
状态：双方合同已核对；SSH恢复后平台候选8项登记、1项迁移、2项提交兼容测试通过，语法检查通过。未部署/未启用，WGS薄钩子和联合验收尚未完成。
本文件是已定向验证的候选合同，不代表现有部署提供此接口；WGS可按此合同开发薄接入点，仅做隔离synthetic验证，不调用未部署的真实API。
验证源码包wgs-register-green.tar SHA256：8cd8e05b79fdaa4cc0569bf17bbe9164112eaa1573625e0fb3a3340fa48d60a7；源码尚未提交，不是发布版本。

关联：[R2设计](2026-09-15-wgs-local-sge-platform-integration.md)、[计划](../plans/2026-09-15-wgs-local-sge-platform-integration.md)。

## 1. WGS接入边界

- 仅analysis子命令新增可选 --platform-monitor（拟定参数名）；不加到all/sampleinfo共用参数。
- 只接受local/sge；CCE及既有网页handoff-request组合不走后台首次登记，避免重复AnalysisRun。
- 原生筛选、pending更新、目录发布、权限处理、附属sampleinfo发布等全部成功后，退出原生prepare处理分支，再执行HTTP登记；不能在目录rename后立即调用。
- selected为空返回None时不生成待启动项目、不登记；selected_count是selection.kept行数，不是唯一患者数。
- 新项目在其staging内生成随机UUID4及初始绑定，随项目发布持久化；无开关不读平台配置、不创建UUID、不请求平台。
- prepare返回成功但登记失败，保留项目和UUID/初始请求，只补登记；不能再次prepare或读写pending。建议补登记入口 prepare/register_platform_project.py --project-dir，尚未实现。
- 原生project路径写死在Step1/config中，mv后绑定可保留，但原生路径需要用户修正；本步不自动改写脚本。
- R2-1不生成可以绕过execution登记直接启动的监控入口；原Step1保留，实际监控启动等R2-2/3接通。

## 2. 认证与私有配置

复用现有个人平台会话，不新增长期PAT或密码托管，不分发X-Airflow-Demo-Token全能内部密钥。
用户通过现有 POST /api/auth/login 建立会话，服务端 Set-Cookie 名称为 wgs_session，响应包含 csrf_token。
登记请求同时携带 Cookie: wgs_session=<原始cookie值> 及 X-CSRF-Token: <csrf_token>。
仅有效个人operator/admin账号可登记；auth_required=false、内部服务token主体或匿名兼容用户均不能登记。
Operator来自已认证会话，不接受请求中自报username；Linux执行账号在后续实际execution采集，不在首次登记中伪造。

客户端建议私有配置 ~/.config/airflow-wgs/platform.json，目录700、文件600：

- base_url：HTTP或HTTPS同源服务地址；不跟随携带凭据的跨源重定向。
- platform_instance_id：与后端明确配置一致，绑定不跨平台复用。
- execution_target：node-96/node-97/sge-default，明确配置，不能根据prepare所在hostname猜。
- session_cookie：wgs_session的原始值，不是完整Cookie header。
- csrf_token：登录响应原值。

该配置文件客户端尚未实现。会话有效期沿用现有设置（默认8小时），过期需要刷新个人会话；不持久化admin密码、不自动取管理员凭据。配置/响应日志不能输出cookie或CSRF。
2026-09-16 用户明确允许现有HTTP部署，不再限制为HTTPS；HTTP会明文传输会话。WGS候选34b487d仅放宽协议验证，仍拒绝URL内凭据、路径、查询参数、fragment与控制字符，不跟随重定向，私有凭据文件权限和日志脱敏要求不变。

## 3. 请求与返回

POST /api/wgs/onprem/projects，JSON；全部对象拒绝未知字段，不上传完整config或临床样本表。

| 字段 | 约束 |
| --- | --- |
| schema_version | wgs.onprem-project-registration.v1 |
| project_uuid | UUID4，来自已发布项目绑定 |
| platform_instance_id | 1–128位字母/数字/点/下划线/连字符，首位字母或数字 |
| project_dir | 实际已存在的绝对项目目录，禁止..与项目目录软链接，必须位于后台显式注册根下 |
| batch_name | 原生项目批次名称，1–128位安全名称，不以此字段去重 |
| execution_mode | local 或 sge |
| execution_target | local对应node-96/node-97，sge对应sge-default |
| prepare_summary | 下表，仅初次准备摘要，不作为启动时最终样本快照 |

| prepare_summary字段 | 约束 |
| --- | --- |
| selected_count | 严格整数>0，selection.kept行数 |
| pending_count | 严格整数>=0，selection.pending行数 |
| version | 非空字符串，最长32；只作来源声明，不作为已验证release证明 |
| source_commit | 40位小写十六进制或null；取实际config.project_root源码/快照来源，不拿prepare脚本所在仓库HEAD冒充；无法证明则null |
| prepared_at | 带时区的ISO8601时间 |
| files | 必须且仅有config、sampleinfo、step1三个键；分别为relative_path和sha256对象 |
| files.*.relative_path | 相对项目根的规范路径，禁止..、绝对路径、反斜线 |
| files.*.sha256 | 64位小写十六进制SHA256 |

prepared摘要来源标为reported_by_authenticated_prepare；后端不会将这些声明伪装成运行时版本探测。
摘要首次持久化后不随人工编辑config/样本更新，补登记重发初始请求；最终输入在execution启动快照另行采集。

首次与同UUID同请求重试均HTTP200，返回相同登记回执：

```json
{
  "schema_version": "wgs.onprem-project-registration-result.v1",
  "project_uuid": "来自请求的UUID",
  "platform_instance_id": "已配置的平台实例",
  "analysis_id": "平台生成的WGS运行ID",
  "attempt": 1,
  "status": "created",
  "registration_status": "registered",
  "execution_status": "not_started"
}
```

这是首次登记回执，不是实时状态查询。将来任务执行后补取登记回执仍不能将当前状态回退created。
不同UUID在同路径可创建新analysis_id；相同UUID的路径/摘要/目标变化返回409，本步不实现迁移API。
UUID不是授权凭据；相同UUID由另一平台账号登记/查询返回403，不泄露对应run详情。

## 4. 绑定、持久化与副作用

项目 .wgs-platform/project.json 必须可由后台只读访问，至少包含：
schema_version=wgs.platform-project.v1、project_uuid、platform_instance_id。
客户端还可保存registration状态、初始请求和成功回执；不存secret。
服务器只校验绑定身份和注册路径，不因准备后人工修改文件而改写初始摘要。
绑定缺失、损坏、越界、超大或软链接不能触发猜测性新登记。

数据库新增可空字段analysis_run.onprem_project_uuid与唯一索引，迁移20260915_0025，父版本20260914_0024。
旧行保持null且保留；新UUID创建AnalysisRun、RunAttempt及审计，使用独立UUID去重，不插入WgsInputSnapshot或按项目批次唯一的dispatch记录。
不创建Sample，不创建stage execution，不调用Airflow、prepare、pending或文件写入。
普通平台submit/resume/rerun_failed/cancel对native_monitor_only记录拒绝，不能误启动或改变原生分析。

## 5. 错误与部署门禁

| HTTP | 含义/处理 |
| --- | --- |
| 401 AUTH_REQUIRED | 会话缺失/过期，刷新个人会话，不能重跑prepare |
| 403 CSRF_REQUIRED | 缺失或不匹配CSRF |
| 403 PERSONAL_SESSION_REQUIRED/FORBIDDEN | 非个人主体、权限不足或UUID不属本人 |
| 409 ONPREM_REGISTRATION_CONFLICT | 注册关闭、WGS未部署、平台实例不符、绑定不符或同UUID请求变化 |
| 400 ONPREM_PROJECT_INVALID | 路径/绑定无效或不可读；不公开底层文件错误详情 |
| 422 | 请求schema错误，包括mode/target不符、数量/引用格式不符；保持FastAPI validation detail格式 |
| 5xx/连接断开 | 未确认登记结果；原UUID原请求重试，不重新prepare，不自动新建UUID |

除422的既有validation格式外，错误为 {"detail":{"code":"...","message":"..."}}。
连接失败客户端退出应与原生prepare失败区分，WGS客户端实现时定义独立错误码；本文件不宣称已有CLI退出码。

后端设置：WGS_ONPREM_REGISTRATION_ENABLED=false（默认）、WGS_PLATFORM_INSTANCE_ID空（默认）、WGS_ONPREM_PROJECT_ROOTS为空（默认，逗号分隔）。没有显式实例和目录不会接入。
这与WGS_NATIVE_PREPARE_ENABLED不同：前者只登记后台项目，后者是旧网页原生准备接线。
候选代码含新ORM列，即使开关关闭，部署前也必须先应用新增迁移；禁止只热换models而不迁移。
此次只在隔离候选完成定向测试，不修改现有数据库、开关或服务；完整联合验收及发布授权尚未完成，禁止直接启用。
