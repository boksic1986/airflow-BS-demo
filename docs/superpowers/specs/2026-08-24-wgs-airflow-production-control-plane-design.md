# WGS Airflow 生产控制面设计

日期：2026-08-24  
范围：Airflow-only 第一阶段

## 1. 目标

把 BS10610 上的 demo 平台重建为唯一的 WGS 4.1.0 CCE 生产控制面。本阶段只完成 React 前端、FastAPI 后端、Airflow、observer、PostgreSQL 和 Redis，不接入 cce-pipeline wheel、node200 runner、WGS 启动命令或真实 CCE/OBS 操作。

生产发布不得包含 NIPT、PGT-A、WES、local/SGE、旧 WGS DAG 或 demo/mock 运行入口。真实提交必须保持禁用并返回可解释的 HTTP 409。

## 2. 组件边界

### React 前端

只保留登录、WGS任务列表、新建 WGS 任务、Run Detail 和账号管理。Run Detail 保留总体阶段、样本/家系、传输、Rule、Master、QC、日志和结果文件区域，为第二阶段真实事件接入保留稳定展示模型。

### FastAPI 后端

只接受 `pipeline=wgs` 和 `execution_mode=cce`。负责身份认证、RBAC、业务状态、审计、Airflow REST 调用和前端查询。viewer 只读，operator 可创建和操作任务，admin 可管理账号。

后端不得执行 kubectl、obsutil、Snakemake 或任意宿主机 shell。真实运行适配器未启用时，submit、resume、rerun_failed 和 cancel 返回 409，不生成伪造运行事件。

### Airflow

只发布一个 paused DAG：`bio_wgs`。DAG 只表达项目级阶段，不把 Snakemake Rule 展开为 Airflow task。第一阶段保留最终阶段名称和 reschedule sensor 边界，但所有需要 cce/WGS 的执行动作经过 disabled adapter 失败关闭。

目标阶段为：

```text
validate_request
→ prepare
→ input_upload
→ submit_master
→ wait_analysis_and_rules
→ publish
→ result_download
→ materialize
→ finalize
→ release_leases
```

任务图可以用 TaskGroup 展开租约和等待节点，但只允许一个 DAG ID。DAG 必须 `is_paused_upon_creation=True`，并同时受 `WGS_EXECUTION_ENABLED=false` 和 `WGS_RUNTIME_ADAPTER_ENABLED=false` 双门禁保护。

### Observer

observer 使用后端相同镜像和 biodemo DB，作为内部后台进程运行。第一阶段只验证空 spool、幂等启动和数据库连接；不持有 SSH key、kubeconfig 或 OBS 凭据。第二阶段再接入真实 transfer、Rule JSONL 和 Master evidence。

### PostgreSQL 与 Redis

PostgreSQL 继续包含两个逻辑数据库：Airflow metadata DB 和 biodemo DB。Redis 仅作为 Airflow Celery broker。三者均不发布宿主机端口。

## 3. 生产数据重置

这是从 demo 到生产的全量控制面重建，不做数据迁移：

- 删除并重建 Airflow metadata DB。
- 删除并重建 biodemo DB，包括用户、角色、会话、审计、分析、样本、家系、Rule、Master、传输、QC、artifact 和日志索引记录。
- 清空 Redis DB。
- 运行全部正式数据库迁移。
- 从未跟踪的生产环境文件重新创建唯一 admin。
- 删除旧 DAG metadata、旧测试 spool、mock运行目录和平台测试记录。

清理必须在新 release 禁用态代码测试通过、服务停止并核对精确目标后执行。不得使用 `docker compose down -v`、Docker prune 或宽泛递归删除。

## 4. 明确保留的数据

以下内容不属于控制面清理范围：

- WGS 4.1.0 源码和 worktree。
- cce-pipeline 源码、wheel、revision 和开发证据。
- 生产 FASTQ 和软链接目录。
- 参考基因组、数据库、许可证和容器镜像。
- CCE、SFS、OBS 中的运行数据和生产结果。
- 已有服务器生产结果目录。
- Docker 外部网络 `nipt_analysis_test_net`，其子网固定为 `192.168.199.0/24`。

## 5. 最小生产 release

新 release 只包含运行所需内容：

```text
backend/
frontend dist 或固定 frontend image
dags/bio_wgs.py
config/（仅 WGS 平台配置）
docker-compose.wgs.yaml
必要 migration、observer 和部署文档
```

开发测试、fixtures 和 mock 数据可以留在 Git 工作树中，但不得复制进生产 release 或生产镜像。旧 NIPT、PGT-A、WES、local/SGE DAG、页面、配置和挂载不得进入新 Compose。

服务仅允许前端发布：

```text
172.17.106.10:12959
```

Airflow Web UI、FastAPI、PostgreSQL、Redis 和 observer 都只在外部 Docker 网络内部可见。

## 6. 发布顺序

1. 从当前 worktree 整理 Airflow-only 源码，移除未完成的 cce/WGS runtime 假设。
2. 运行 backend、frontend、DAG、Compose、迁移和安全边界测试。
3. 创建新的禁用态 release，不切换 `current`。
4. 停止旧应用服务，不删除 volume 或外部网络。
5. 解析并记录 Airflow DB、biodemo DB、Redis 和测试 spool 的精确目标。
6. 重建两个数据库、清空 Redis、运行迁移并创建新 admin。
7. 启动新 release，验证唯一 DAG、RBAC、登录、API、HTTP、端口和双门禁。
8. 原子切换 `current`。
9. 验证新平台无旧 DAG、旧业务记录和 mock 数据后，删除旧平台 release 内容。

任何一步失败都停止后续清理。数据库重建之后不提供 demo 数据回滚；代码回滚只能恢复 release，不能恢复已清空的 demo 数据。

## 7. 第一阶段验收

- Airflow 只加载 `bio_wgs`，且 paused。
- DAG import 无错误，只有 WGS CCE 项目级阶段。
- 两个执行开关均为 false，真实 submit 返回 409。
- API 和前端只展示 WGS；旧 pipeline 创建和访问均被拒绝。
- viewer/operator/admin 权限矩阵通过。
- 新数据库中不存在旧分析、旧用户、旧审计、旧 Rule、旧 Pod、旧 transfer 或旧 DAG run。
- 新 admin 可以登录并创建一个不提交运行的 WGS 草稿。
- observer 空 spool 启动正常且不持有外部凭据。
- Compose 只发布 `172.17.106.10:12959`，外部网络保持 `192.168.199.0/24`。
- release、镜像、日志和数据库中不存在 SSH 私钥、kubeconfig、OBS配置或真实患者信息。
- WGS源码、FASTQ、参考数据、SFS/OBS和生产结果均未修改。

## 8. 第二阶段边界

cce-pipeline、node200 受限入口、WGS Step1–Step6、传输进度、Rule JSONL、Master 状态和真实 CCE/OBS 验收全部属于第二阶段。第一阶段不得提前固化 cce-pipeline 版本、wheel 路径、profile revision、Master image 或结果 marker；只保留可替换的 disabled adapter 接口。
