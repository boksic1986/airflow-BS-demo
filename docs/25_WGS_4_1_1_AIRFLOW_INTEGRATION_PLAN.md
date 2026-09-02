# WGS 4.1.1 单一发布版本 Airflow 接入方案

更新时间：2026-09-01

> 2026-09-02身份迁移更新：本文中的`chenjc` node200身份、旧共享runtime和
> attempt内分析目录是当前线上/历史合同。已确认的新生产目标以
> [文档29](29_WGS_HANJJ_RUNTIME_IDENTITY_MIGRATION_DESIGN.md)为准：运行账号替换为
> `hanjj`，新控制根和`WGS_Clinical/<batch>`分析根迁到`14.hanjingjing`空间。
> 设计已批准，代码和在线配置尚未切换。

本文定义单一发布和正常Step1-Step6边界；T7 scan-only和Step4 repair的当前增量
设计以[文档 26](26_WGS_T7_INTAKE_STEP4_REPAIR.md)为准。文档 22、T131-T142 中的
Airflow-owned snapshot、固定 cce-pipeline wheel/profile/image 门禁和 WGS
4.0.1/4.1.0 内容均为历史记录。

> T145 更新：scanner 稀疏入库和 event-driven CCE observer 生命周期以
> [文档 27](27_WGS_SCANNER_OBSERVER_LIFECYCLE.md)为准；它取代文档 26 中的混合
> `wgs-observer` 运行方式，不改变 WGS release 或 Step1–Step6 业务合同。

## 1. 固定发布合同

生产同一时间只提供一个 WGS 发布版本：

| 字段 | 当前值 |
|---|---|
| release ID | `wgs-4.1.1-2499749` |
| WGS version | `V4.1.1` |
| source commit | `2499749ce7fd200d4269d1ee03d7b6a4e8d5bb68` |
| BS10610 path | `/mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1` |
| node200 path | `/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1` |
| Rule event schema | `1` |

两个路径是同一共享仓库。Airflow 不复制 WGS 源码，不维护 pipeline snapshot
或 snapshot manifest，也不在 node200 创建额外 WGS 发布目录。前端不允许用户
选择或提交版本；后端创建 run 时自动绑定当前 release ID、version 和 commit。

prepare 前 node200 必须验证：

- 固定仓库、`prepare/prepare_wgs_batch.py` 存在且不是符号链接。
- `git rev-parse HEAD` 等于 run 绑定的 commit。
- 已跟踪文件无变化。
- 未跟踪内容只允许位于 `docs/`；其他未跟踪运行代码触发
  `release_unavailable`。

prepare 成功后，Step1-Step6 只运行批次目录中的冻结 CCE bundle。Airflow task
重试复用同一 binding/bundle；`resume`和`rerun_failed`的新 attempt 继续绑定原
release。原 commit 不可用时返回 `WGS_RELEASE_UNAVAILABLE`，不得静默切换。

## 2. 责任边界

```text
React/FastAPI/Airflow/observer/PostgreSQL/Redis       BS10610
WGS prepare/obsutil/kubectl/Step1-Step6              node200 172.17.61.200
Master + Snakemake scheduler                         CCE
Rule JSONL/result evidence                           SFS
input/result objects                                 OBS
```

- Airflow 只调度外部 CCE，不执行本地/SGE WGS，也不运行 Snakemake。
- cce-pipeline 的版本兼容由 WGS prepare/adapter 负责；Airflow 不安装、升级或
  校验 cce-pipeline 版本、wheel SHA、profile SHA 或 Master digest。
- `RESOLVED_PROFILE.yaml`中的实际 cce-pipeline、profile 和 Master image 信息
  仅在 prepare 后作为审计字段入库，不是 Airflow 部署门禁。
- CCE 不回调 BS10610 API；node200 将状态和证据单向写入共享 spool。
- observer 不持有 SSH key、OBS credential、kubeconfig 或 Docker socket。
- `wgs-cloud-delivery`保持独立，不安装 Airflow adapter 或 logger。

共享 runtime 路径：

```text
BS10610 /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime
node200  /sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime
```

## 3. 请求、DAG 与 WGS Step

公开创建请求固定为：

```json
{
  "pipeline": "wgs",
  "execution_mode": "cce",
  "project_name": "project-name",
  "batch_no": "batch-no",
  "fq_path": "/data/wgs-intake/controlled-link-directory"
}
```

未知字段被拒绝，因此客户端不能伪造 release、commit、snapshot path 或运行时
版本。第一版只支持前端/API 手工创建；自动扫描、local、SGE、Step0、Step7 和
Step8 不进入自动 DAG。

唯一、版本无关的 `bio_wgs` 有 18 个 task：

```text
validate_request
-> prepare_wgs_batch
-> input_transfer.acquire_obs_transfer_slot
-> input_transfer.start_step1_upload
-> input_transfer.wait_step1_upload
-> input_transfer.release_obs_transfer_slot
-> submit_step2_master
-> start_step3_monitor
-> wait_step3_analysis
-> start_step4_publish
-> wait_step4_publish
-> result_transfer.acquire_obs_transfer_slot
-> result_transfer.start_step5_download
-> result_transfer.wait_step5_download
-> result_transfer.release_obs_transfer_slot
-> materialize_step6_results
-> finalize_run
-> release_leases
```

`bio_wgs`无 schedule、默认 paused、`max_active_runs=4`。`wgs_cce_runs`控制
CCE 批次并发，`wgs_obs_transfer`和 PostgreSQL lease 共同保证仅一个输入上传或
结果下载。六个长等待使用五秒 `reschedule` sensor。

| Airflow 阶段 | 冻结 bundle 入口 | 完成条件 |
|---|---|---|
| prepare | `prepare_wgs_batch.py all --batch <YYYYMMDDA> --analysis-batch <batch_no> --run-mode cce` | `BATCH_RUNTIME.yaml`、`RESOLVED_PROFILE.yaml`和 Step1-Step6 有效 |
| input | `Step1_upload_fastq.sh` | WGS/cce-pipeline 上传合同成功 |
| Master | `Step2_run.sh` | 批次 Master Job 已提交 |
| analysis | `Step3_status.sh --output json` | Master 终态与 Rule reconciliation |
| publish | `Step4_publish_results.sh` | SFS/OBS 结果发布合同成功 |
| download | `Step5_download_verify.sh` | 结果长度/MD5 和下载 marker 成功 |
| materialize | `Step6_materialize_results.sh` | 本地原子物化 marker 成功 |
| finalize | backend reconciliation | Step6 和业务终态一致 |

Airflow从完整分析批次名中提取上机批次字段传给`--batch`，但分析根仍为Airflow
attempt workdir下的`<project_name>/<batch_no>`；不重建或复用旧
`/sg2/.../wgs_test/WGS_Clinical`目录。这样OBS前缀继续由固定的
`WGS_Clinical/<batch_no>`决定。

Airflow 不计算 FASTQ MD5、不生成 `FASTQ.MD5SUMS`、不增加上传后 FASTQ 验证
task，也不在 create API 阶段生成 sampleinfo/config；这些均由 WGS prepare 和
Step 合同负责。

## 4. node200 request 与冻结 binding

内部请求使用 `wgs-runtime.request.v3`：

```text
schema_version, analysis_id, attempt, stage,
pipeline_release_id, wgs_version, wgs_source_commit,
bs10610_workdir, node200_workdir, project_name, batch_no, fq_path
```

请求不包含 pipeline snapshot path、WGS repo path、cce-pipeline version、wheel
hash、profile hash 或 Master digest。node200 runner 从固定 `WGS_REPO_ROOT`调用
prepare；请求不能覆盖该路径。

prepare 写 `wgs-runtime.batch-binding.v2`，至少保存：release/version/commit、
batch root、CCE bundle、run ID、namespace、Master Job、Rule evidence path 和
从 `RESOLVED_PROFILE.yaml`解析的 `resolved_runtime`。后续 Step 只读取 binding
内路径，不再读取 WGS 仓库。

Airflow 使用现有受保护 RSA 配置：

```text
ssh -tt -F /opt/airflow/ssh/config wgs-node200 \
  /home/chenjc/.config/airflow-wgs/forced-command.sh \
  wgs-runtime <analysis_id> <attempt> <stage>
```

SSH config 固定 host key、BatchMode、IdentitiesOnly 和 IdentityFile；私钥只读
挂载给 UID 50000，不进入 Git、release、镜像、日志或数据库。异步阶段使用
`nohup + setsid + flock`，记录 request SHA256、PID、boot ID、启动时间和原子
status；重复调用只能恢复相同请求。

## 5. Rule、Master、数据库和 API

Master 内 Snakemake logger 写：

```text
<run_root>/evidence/<run_id>/rule-status/raw/*.jsonl
```

node200 Step3 每约五秒通过 kubectl 复制完整 JSONL 行并保存逐 stream byte
offset。Master 退出后使用一次性只读 reader Job补齐末尾事件。Worker Pod 不持续
枚举、不入库、不展示；`/pods`只返回 Master Job/Pod。证据同步失败标记
monitoring degraded，未终结 Rule 转为 `unknown_interrupted`，但批次业务终态仍由
WGS/结果交付合同决定。

Alembic `20260827_0010`：

- `observer_run_state.pipeline_snapshot_id`重命名为
  `pipeline_release_id`。
- WGS `analysis_run.params_json`中的残留 snapshot/source 字段迁移为
  release/source 字段。
- 不删除用户账号、角色或平台配置。

公开接口：

- `GET /api/wgs/release`：当前 release/version/commit 和两个执行门禁。
- `POST /api/runs`：服务端绑定当前 release，不接受客户端版本。
- `GET /api/runs/{id}`：返回 `pipeline_release_id`、`wgs_version`、
  `wgs_source_commit`和 prepare 后的 `resolved_runtime`。
- Rule 去重、observer binding 和 ETA 历史均按 `pipeline_release_id`隔离；ETA
  选择同 release 最近 20 个成功 CCE run。

前端 Submit 页只读显示 `WGS V4.1.1 / 2499749`和 release ID，不提供版本选择
器。Run Detail、Rules、Transfers 和 Master 页面显示本次 run 的 release；
resolved runtime 在 prepare 前明确显示为未解析。

## 6. 禁用态发布与启用门禁

T142 发布必须保持：

```text
WGS_EXECUTION_ENABLED=false
WGS_RUNTIME_ADAPTER_ENABLED=false
bio_wgs paused
```

BS10610 只做测试、migration、Compose/service rebuild 和 HTTP smoke，不启动 OBS
传输或 CCE Job。不删除数据库/Redis volume，不重建外部 Docker network；
`nipt_analysis_test_net`必须保持 `192.168.199.0/24`、gateway
`192.168.199.1`，且只有 frontend 发布 `172.17.106.10:12959`。

禁用态验收包括：backend/observer/migration、runner/DAG import、frontend
test/build、Compose/network、登录、release API、禁用态 create、Run Detail、真实
submit 409、SSH/repo commit 和 secret boundary。真实批次、启用两个 gate 和 DAG
unpause均需要单独批准。
