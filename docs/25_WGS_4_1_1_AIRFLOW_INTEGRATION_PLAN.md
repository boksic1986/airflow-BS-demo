# WGS 4.1.1 Airflow 生产接入方案

更新时间：2026-08-26

本文是当前唯一有效的 WGS Airflow 接入设计。`22_WGS_ONLY_LOCAL_CCE_PLATFORM_DESIGN.md`、T131-T133 和 WGS 4.0.1/4.1.0 内容仅保留为历史记录。

## 1. 固定基线

| 组件 | 固定身份 |
|---|---|
| WGS source | `/mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1`，commit `3489b3958869e5cfab983aca1eb9c7f158c06dff` |
| Airflow snapshot | `wgs-v4.1.1-candidate-3489b39-64d50022` |
| snapshot manifest | `9b1bfe00ebf7e8ed693f1e9eb17ec05174aa43b04900802d67e54f50dc27f52e` |
| cce-pipeline | `0.5.0`, source commit `70a9a737c62865f232ed0b49f682aa7c9a69e467` |
| cce wheel | SHA256 `43a4ab478e8b8810b1691bb755e54336b0bc8fd86a16d4fed9be3783036e1756` |
| CCE profile | `wgs-4.1.1-r1`, SHA256 `19a7cc76cfc086c032c5e2329310d4ff90cd67e5cb52632bfb98f1b4fea59276` |
| Master RepoDigest | `sha256:815d70a6105b08b8fc6031a425cfed5ced8773e4d66c18ad98502b9a61ffeecc` |

Airflow snapshot 排除 `prepare/config.yaml`、Git/cache/runtime 文件、OBS 配置、kubeconfig、SSH key、token 和患者数据。上游 WGS 仓库保持只读。

## 2. 主机边界

```text
React/FastAPI/Airflow/observer/PostgreSQL/Redis       BS10610
WGS prepare/cce-pipeline/obsutil/kubectl/Step1-Step6 node200 (172.17.61.200)
Master + Snakemake scheduler                         CCE
Rule JSONL/result evidence                           SFS
input/result objects                                 OBS
```

- CCE 不调用 BS10610 API；状态只通过 SFS 和 node200 单向拉取。
- observer 不持有 SSH key、OBS 凭据或 kubeconfig。
- node200 不运行 Airflow，也不保存 biodemo 数据库。
- `wgs-cloud-delivery` 保持独立，不安装 Airflow adapter 或 logger。

共享 runtime 映射必须使用：

```text
BS10610 /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime
node200  /sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime
```

## 3. 输入与唯一 DAG

公开请求：

```json
{
  "pipeline": "wgs",
  "execution_mode": "cce",
  "project_name": "project-name",
  "batch_no": "batch-no",
  "fq_path": "/data/wgs-intake/controlled-link-directory"
}
```

第一版只允许手工提交。自动扫描、local、SGE、Step0、Step7 和 Step8 不在自动 DAG 中。

唯一 `bio_wgs` 共 18 个 task：

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

`bio_wgs` 无 schedule，默认 paused，最大四批项目级并发；OBS 传输租约只允许一个 active transfer。所有长等待均使用 `reschedule` sensor。

## 4. WGS Step 合同

| Airflow 阶段 | WGS 入口 | 完成条件 |
|---|---|---|
| prepare | `prepare_wgs_batch.py all` | bundle、`RESOLVED_PROFILE.yaml`、`BATCH_RUNTIME.yaml` 有效 |
| upload | `Step1_upload_fastq.sh` | WGS/cce-pipeline 上传完成合同成功 |
| Master | `Step2_run.sh` | 批次 Master Job 已提交 |
| analysis | `Step3_status.sh` | 精确 Master 终态与 Rule reconciliation |
| publish | `Step4_publish_results.sh` | payload manifest/READY 成功 |
| download | `Step5_download_verify.sh` | 长度与 MD5 验证、`DOWNLOAD_VERIFIED` 成功 |
| materialize | `Step6_materialize_results.sh` | 原子物化、`MATERIALIZED` 成功 |
| finalize | backend reconciliation | 分析、交付、监控状态一致 |

Airflow 不计算 FASTQ MD5，不生成 `FASTQ.MD5SUMS`，不增加上传后 FASTQ 验证，也不在 API create 阶段生成 `sampleinfo.tsv` 或 `config.yaml`。这些文件由 node200 的 WGS prepare 生成。

## 5. node200 adapter 与 SSH

按用户最终决定使用现有 RSA 和 SSH config：

```text
ssh -tt -F /opt/airflow/ssh/config wgs-node200 \
  /home/chenjc/.config/airflow-wgs/forced-command.sh \
  wgs-runtime <analysis_id> <attempt> <stage>
```

配置固定 host、user、IdentityFile、known_hosts、`BatchMode yes`、`IdentitiesOnly yes`、`StrictHostKeyChecking yes` 和 `RequestTTY force`。私钥只读挂载给 Airflow UID 50000，不进入 Git、release、镜像、数据库或日志。

adapter 只接受以下 stage：

```text
prepare step1_upload step2_master step3_monitor
step4_publish step5_download step6_materialize
```

异步阶段使用 `nohup + setsid + flock`，记录请求 SHA256、PID、boot ID、启动时间和原子 status。重复调用只能恢复同一请求。

## 6. 状态、数据库、API 与前端

- biodemo 保存 run/attempt/sample/family/snapshot/validation/transfer/Rule/Master/artifact/QC/audit 状态；Airflow metadata DB 只保存调度元数据。
- `/pods` 只返回批次 Master Job/Pod，不持续枚举 Worker Pod。
- transfer 第一版只承诺阶段状态、heartbeat 和错误摘要；`progress_detail_available=false` 时字节、速度和 ETA 为 null，前端不渲染进度条和虚假 0 值。
- Rule JSONL 必须由 Master Snakemake logger 写 SFS；observer 按完整换行、event ID 和 byte offset 幂等消费。
- API 除 health/login 外要求认证；viewer 只读，operator 可创建/提交/恢复/重跑/取消，admin 管理账号。
- 前端活动任务约五秒刷新；Airflow UI、backend、PostgreSQL、Redis、observer 不发布宿主机端口。

## 7. Rule logger 与单向 bridge

固定 Master RepoDigest `sha256:815d70a6...`已包含 Snakemake
`9.24.0+biosan1`及 `snakemake_logger_plugin_rule_status`。正式
`cloud_wgs_all`命令写 SFS
`<run_root>/evidence/<run_id>/rule-status/raw/*.jsonl`，不修改 Rules、Worker
images、stdout/stderr 或 `analysis.log`，也不包含 FastAPI URL、token 或 HTTP
callback。node200 本地 Python/Snakemake 版本不参与云端分析。

node200 没有 `/workspace` SFS 宿主机挂载，因此 Step3 通过 kubectl 每约五秒从
运行中 Master 读取完整 JSONL 行并按 stream byte offset 写入共享
`cce-evidence/<analysis_id>/attempt-N`。Master 退出后，一次性 reader Job仅只读
挂载 workspace PVC，补齐最终增量后删除。reader 与 Worker Pod 均不进入前端。

disabled-mode 代码和合成测试已经完成；真实启用仍需 T140 验证
planned/running/success/failed/retry、offset 续读、Master 中断、reader 清理、四批
隔离和 logger degraded。缺失终态事件不得伪造成功，显示为
`unknown_interrupted`。

## 8. 发布和启用门禁

当前禁用态 release：

```text
20260827-wgs-4.1.1-disabled-t141
WGS_EXECUTION_ENABLED=false
WGS_RUNTIME_ADAPTER_ENABLED=false
bio_wgs paused
```

禁用态已完成 migration、demo-state cleanup、登录/API/HTTP/SSH/network smoke。任何真实 OBS/CCE 操作都需要单独批准，并按顺序：启用两个 gate、保持 DAG paused、手工提交一个最小批次、完成中断/失败/MD5/四批并发验收，最后才允许解除 pause。
