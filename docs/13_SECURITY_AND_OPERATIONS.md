# 13 安全和运维约束

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
