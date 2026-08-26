# 13 安全和运维约束

> **当前 WGS 4.1.1 边界：** 按用户最终决定，Airflow 使用现有 RSA 与
> `/opt/airflow/ssh/config`，通过 `ssh -tt -F ... wgs-node200` 登录；config
> 固定 host key、BatchMode、IdentityFile 和 TTY。私钥只读挂载给 UID 50000，
> 不进入 release、镜像、数据库或日志。当前两个 execution gate 均为 false。
> 以下 T133 forced-key 描述为历史候选。

## T133 node 200 boundary

Node 200 (`172.17.61.200`) is the only host allowed to hold the private OBS configuration and
CCE kubeconfig for this release. Airflow reaches only the forced
`wgs-runtime <analysis_id> <attempt> <stage>` command. Compose services,
biodemo, logs, Rule JSONL and release artifacts must not contain OBS secrets,
kubeconfig, FastAPI callback tokens or patient names. CCE writes SFS evidence
only and never calls BS10610. The observer is read-only, unprivileged and has
neither cloud credential.

## 1. Demo 安全边界

该项目是 demo，不默认达到生产安全级别。服务器部署时至少保证：

- 只在内网或 VPN/Tailscale 内访问。
- 不暴露 Postgres/Redis 到公网。
- 不使用真实患者数据。
- 不提交 `.env` 或密钥。

## 2. Secrets 管理

禁止入库：

```text
.env
*.pem
*.key
password files
SMTP password
DB password
Airflow admin password
API tokens
```

如果需要示例，使用：

```text
<TO_BE_FILLED>
<SECRET_FROM_ENV>
```

## 3. 路径安全

Backend log/artifact API 必须限制在 `SHARED_ROOT` 内：

```text
resolve(path).is_relative_to(resolve(SHARED_ROOT))
```

禁止读取任意服务器文件。

## 4. qsub 限流

必须有：

```text
MAX_DEMO_JOBS
QSUB_QUEUE
ALLOW_REAL_QSUB=true/false
```

默认建议：

```text
ALLOW_REAL_QSUB=false
```

先用 mock qsub 验证 UI 和事件流，再启用真实 qsub。

## 5. Docker 风险

- Docker socket 权限等同宿主机高权限。
- 只有在受控 demo 服务器使用。
- 不要把 backend/frontend 直接暴露到公网。
- Docker 容器不要挂载过宽宿主机目录。

### BS NIPT-only network guard

For BS10610/BS1069, `nipt_analysis_test_net` is shared infrastructure and has a
fixed IPAM contract: subnet `192.168.199.0/24`, gateway `192.168.199.1`.
Deployment automation may inspect and attach to this network, but must never
create, delete, recreate, or change it. A subnet/gateway mismatch or static-IP
collision is a hard stop, not a condition to repair automatically.

T126 image movement must use a local relay: download signed/checksummed
archives from fengxian to the Windows staging directory, verify them locally,
then upload separately to BS10610 or BS1069 and verify again. Direct
remote-to-remote copy is not an accepted deployment path. BS1069 is a cold
standby: images and release files may be loaded, but scheduler, worker,
frontend, backend, PostgreSQL, and Redis must remain stopped until a controlled
failover explicitly stops BS10610 first.

T127 WGS execution uses a restricted SSH key. The authorized-key entry uses a
forced command plus `restrict`; forwarding and PTY access are not allowed. The
gate validates a generated WGS analysis ID and a fixed stage allowlist, reads
only the run-local signed request, checks approved roots and SHA256, and uses
`flock` to prevent duplicate execution. Airflow receives no general host shell
credential. Historical batch-context symlink targets must resolve below exact
`WGS_PRECALLING_SOURCE_ROOTS` and the sibling fastp QC directories through
`WGS_QC_SOURCE_ROOTS`; a broad `/sg2` allowlist is prohibited.

## 6. 审计

建议记录：

- 谁提交了 run。
- 哪个 pipeline。
- 参数摘要。
- 重分析 action。
- 失败摘要。
- artifact 路径。

## 7. 备份

Demo 最低备份：

```text
biodemo DB dump
shared/reports
shared/runs metadata/logs
```

不建议备份大 FASTQ/BAM，除非 demo 需要。

## 8. 清理策略

建议提供清理脚本，但默认 dry-run：

```bash
python scripts/cleanup_runs.py --older-than-days 30 --dry-run
```

不得默认删除最近 run 或 reports。

T116 history cleanup is CLI-only and requires all of the following: scanner
paused, no non-terminal target runs, dual database dumps, JSON inventories,
SHA256 verification, exact expected counts, explicit keep IDs, a read-only
preview, and a fixed confirmation token. Airflow history must be removed via
the stable REST API rather than direct metadata-table SQL. Never add these
maintenance actions to the unauthenticated frontend.

## 9. 生产化后续清单

- HTTPS/reverse proxy。
- 统一登录/LDAP/OIDC。
- 权限模型。
- 操作审计。
- secrets manager。
- object storage。
- 监控告警。
- 多环境部署。
- CI/CD。
## WGS-only trust boundary

Only nginx is host-published. The observer has read-only evidence access and no CCE, Docker, SSH, or OBS credential. Passwords are scrypt-hashed; HttpOnly sessions, CSRF, roles, and audit logs protect mutations. Private OBS transfer stays on node005 and CCE administration stays outside Compose.
