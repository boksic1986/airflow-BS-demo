# WGS 4.1.1 Runtime Integration Development Status

更新时间：2026-08-26

当前结论：T135-T139 的 Airflow 控制面开发、禁用态部署和 demo 状态清理已经完成；T140 真实 OBS/CCE 批次仍未获批准，也不具备 Rule logger 启用条件。

## 1. 已部署状态

| 项目 | 当前值 |
|---|---|
| BS10610 release | `20260826-wgs-4.1.1-disabled-t139` |
| 唯一 DAG | `bio_wgs`，18 tasks，manual schedule，paused |
| execution gates | `WGS_EXECUTION_ENABLED=false`、`WGS_RUNTIME_ADAPTER_ENABLED=false` |
| WGS snapshot | `wgs-v4.1.1-candidate-3489b39-64d50022` |
| snapshot manifest SHA256 | `9b1bfe00ebf7e8ed693f1e9eb17ec05174aa43b04900802d67e54f50dc27f52e` |
| WGS source | clean commit `3489b3958869e5cfab983aca1eb9c7f158c06dff` |
| cce-pipeline | `0.5.0`; formal wheel SHA256 `43a4ab478e8b8810b1691bb755e54336b0bc8fd86a16d4fed9be3783036e1756` |
| profile | `wgs-4.1.1-r1`, SHA256 `19a7cc76cfc086c032c5e2329310d4ff90cd67e5cb52632bfb98f1b4fea59276` |
| biodemo | revision `20260826_0009`; 1 admin; 0 sessions/runs/samples/events/transfers/workloads |
| Docker network | external `nipt_analysis_test_net`, `192.168.199.0/24` |
| published port | only `172.17.106.10:12959` |

旧 `bio_wgs_cce`、`bio_wgs_intake_scan`、`bio_wgs_onprem` 的 source mount 和 Airflow metadata 已删除。PostgreSQL/Redis volume 与外部 Docker network 未重建或删除。
旧 Airflow WGS release 与 demo-state 清理备份已精确删除；`releases/` 只保留上述当前 release，`backups/` 为空。该清理不可恢复，但未触及生产 WGS 仓库、输入或结果。

## 2. 已完成开发

- 安全生成不含 `prepare/config.yaml` 的 WGS 4.1.1 allowlist snapshot，并固定 WGS、profile、wheel 与 Master RepoDigest 身份。
- `bio_wgs` 只编排 WGS prepare 和 Step1-Step6；不生成 FASTQ MD5，不增加上传后 FASTQ 验证，不自动执行 Step0/Step7/Step8。
- node200 adapter 使用 WGS 生成的 Step 脚本、原子 stage status、`nohup + setsid + flock` 异步 worker和五秒 reschedule sensor。
- backend/observer 支持 4.1.1 snapshot、运行 attempt、阶段型 transfer、Master-only workload、Rule cursor、结果门禁和审计。
- transfer 没有精确合同时返回 `progress_detail_available=false`；前端不显示虚假的 0%、0 B/s 或 ETA 0。
- 前端只提供 WGS 手工提交、Run Detail、Families、Rules、Master、Transfers、QC、Logs、Files 与 RBAC 页面。
- demo run、样本、session、事件、传输、workload、audit 与 Redis 状态已清理；管理员账号保留。

## 3. node200 SSH 与共享路径

按用户最终决定，Airflow 使用专用 SSH 配置和现有 RSA：

```text
ssh -tt -F /opt/airflow/ssh/config wgs-node200 <registered-wrapper-command>
```

Celery 没有本地终端，因此使用 `-tt` 强制分配 TTY。配置同时固定 `BatchMode yes`、`IdentitiesOnly yes`、`StrictHostKeyChecking yes`、known_hosts 和私钥路径。实际 host key 指纹为 `SHA256:KKSrhbpZdPlBe7ej63ZaYhvYwWhQpdEnGejD59NGMv4`。

实测共享路径不是早期文档中的 `/sg2/33.chenjiucheng/...`。正确映射为：

```text
BS10610: /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime
node200:  /sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime
```

两端 marker 探针已通过。旧路径属于不同的 NFS export 位置，不能用于共享 spool。

## 4. 禁用态验收证据

- backend：`193 passed`。
- node/runtime scripts：`14 passed`。
- deployment contract：`5 passed`；实际 Airflow worker 中 DAG 动态合同通过，
  `bio_wgs` 为 18 tasks、paused，Airflow import errors 为 `[]`。
- 前端：27 tests、TypeScript build、Vite production build 通过；部署产物 SHA256 与本地构建一致。
- frontend release image 会先删除基底中的旧 demo 静态文件，再复制固定 dist；运行容器只剩当前 JS/CSS 两个资源。
- Compose config、HTTP 200、backend health、匿名 API 401、管理员登录均通过。
- 禁用态 synthetic run：create 201，submit 409，真实 CCE 未启动；只生成 `input-manifest.json`，没有生成 `sampleinfo.tsv` 或 `config.yaml`。测试记录和文件随后全部删除。
- Airflow worker 内 `ssh -tt -F ... wgs-node200 hostname` 返回 `t640`。

BS10610 无可用 Node 基础镜像且外部 mirror DNS 失败，因此 Vitest 不能在 BS10610 重新构建测试镜像；前端使用本机 bundled Node 完整测试/构建，并在 BS10610 完成固定 SHA256 离线 packaging 与 HTTP smoke。

## 5. T140 启用阻塞点

以下问题未解决前不得把两个 gate 改为 true，也不得解除 DAG pause：

1. node200 正式 WGS 环境的 Snakemake 当前为 `9.23.1`，不是预期的 `9.24.0+biosan4`。
2. clean WGS commit `3489b395...` 中没有 `rule-status`/`biosan-jsonl` 启动参数、Rule JSONL 路径或 `LOGGER_DEGRADED` 合同；当前 Rule 页面只能保持无事件状态。
3. 必须用最终 Master image完成一个最小批次 dry-run 一致性与 logger 不影响 `analysis.log`/退出码的验证。
4. 必须完成真实上传中断恢复、Master 中断、Rule failure/logger degraded、错误结果 MD5 和四批并发验收。

cce-pipeline 0.5.0 已安装在正式 WGS Python 环境，`PYTHONNOUSERSITE=1` 下版本检查通过；“正式环境缺少 cce-pipeline”不再是当前阻塞点。

## 6. 任务状态

| Task | 状态 |
|---|---|
| T135 snapshot/provenance | done |
| T136 node200 adapter/single DAG | done in disabled mode |
| T137 backend/observer | done in disabled mode |
| T138 frontend | done in disabled mode |
| T139 disabled production release | done |
| T140 real batch acceptance | blocked pending upstream logger/runtime and explicit approval |
