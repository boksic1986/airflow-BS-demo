# WGS Scanner 稀疏入库与 CCE Observer 生命周期

更新日期：2026-09-01

本文以 T145 的服务拆分为基础，并由 T150 更新 FASTQ 识别合同。T145 修正文档
26 中将 T7 scanner 和 CCE
observer 放在同一常驻进程、并为 1830 个历史目录保存明细的实现。
WGS release、Step1–Step6 和 Step4 repair 合同仍分别以文档 25/26 为准。

当前 release 为
`20260901-wgs-4.1.1-2499749-t150-t7-scanner-r5`。scanner 每次统计约1837个
目录，但只保留基线后已完成的7条芯片发现；它不自动创建分析。

## 1. 服务边界

- `wgs-intake-scanner`每 600 秒只读扫描`/bi/fastq/T7_Fastq`，只负责
  芯片目录发现和分类。
- `wgs-run-observer`只处理已被 Step3 激活的`analysis_id + attempt`。无活动
  任务时阻塞在 PostgreSQL `LISTEN wgs_observer_activation`，不扫描 binding、
  evidence、runtime 或传输目录，不输出空心跳。
- Step1/Step5 传输进度由对应 Airflow `reschedule` sensor 每次只读本任务
  的精确 status/progress 文件，不再由 observer 全局 glob。
- 两个 Compose 服务均使用`json-file` `max-size=20m` / `max-file=3`。

Step3 runner 被 node200 接受后，Airflow 通过内部 token API 将 attempt 设为
`active`并发送 PostgreSQL notification。终态或`release_leases`清理将它设为
`draining`；observer 完成最后一次增量同步后设为`stopped`。连接断开时
指数退避重连；重启只恢复`active/draining`。

## 2. Scanner 稀疏数据合同

`wgs_intake_scanner_state` id=1 只保存：

```text
first_scan_at
last_scan_at
last_scanned_directory_count
last_error
```

扫描开关、间隔和 auto-dispatch 状态来自运行配置，不入库。重建基线的第一
次扫描只记录时间和目录数，不创建`wgs_intake_batch`。后续扫描忽略：

- 未出现`BarcodeStat.txt`的目录；
- 基线时间之前已经完成的历史目录。

只对基线后新生成`BarcodeStat.txt`的目录进行 FASTQ 分类，并且只持久化
`ready`、`needs_review`、`no_new_wgs`。规范化芯片路径唯一，重复扫描更新
原记录。每轮最多一条汇总日志，不打印逐目录日志。

T150以后，FASTQ分类只看目录直属项的basename：普通文件、硬链接、有效或失效
软链接都使用同一`<sample>-WGS.R1/R2.fq.gz`配对规则。scanner不对FASTQ目录项
调用`resolve()`，不读取链接目标，也不检查目标是否在容器中可见；目标与内容完整性
留给后续prepare/上传。`-S\d+`结尾的加测样本仍排除，普通样本缺R1或R2进入
`needs_review`。

`wgs-t7-entry-fingerprint.v2`只包含芯片、上机批次、BarcodeStat的stat和排序后的
eligible FASTQ名称，不包含FASTQ大小、mtime、目标路径或MD5。已ready记录的名称
新增、删除或重命名仍触发漂移保护；内容或目标变化不触发scanner漂移。旧v1普通
文件ready记录可在名称未变化时一次性升级；历史`no_new_wgs`不再冻结fingerprint，
可重新分类为`ready`或`needs_review`。

## 3. 数据清理和迁移

Alembic `20260830_0012`精简 scanner singleton，并为`observer_run_state`增加：

- `lifecycle_status=active|draining|stopped`；
- `monitoring_health=healthy|degraded|error`；
- `activated_at` / `deactivated_at`；
- 活动生命周期查询索引。

1830 条 demo scanner 明细的删除不放在结构迁移中。部署时必须依次：

1. 停止旧混合 observer。
2. `pg_dump -Fc` 备份 biodemo 并生成 SHA256。
3. 重新查询`wgs_intake_batch.analysis_id IS NOT NULL`的记录数。
4. 只在结果为 0 时，用`python -m app.wgs_intake_cleanup_cli --confirm
   RESET-WGS-INTAKE-BASELINE`在单个事务中清空 batch 和 scanner state。
5. 若发现任何关联分析，整个事务失败，不删除任何行。

## 4. API 和前端

- `GET /api/intake/scanner-state`返回四个基线字段，并动态补充
  `root/enabled/schedule_seconds/auto_dispatch_enabled`。
- `GET /api/intake/status?pipeline=wgs`只返回三种持久化状态。
- 内部 observer activate/deactivate 按 attempt 幂等；未进入 Step3 的 cleanup 不会
  制造 observer 记录。
- Run Detail 分开显示 lifecycle 和 monitoring health。无 observer 时显示
  “CCE监控尚未启动”，不标记为错误。
- Dashboard 显示“本轮扫描 N 个目录”，发现列表不展示历史/等待目录。
- Dashboard使用API的`schedule_seconds`动态显示扫描周期；生产600秒显示“每10分钟”。

## 5. 安全与启用门禁

T150不改变分析门禁或当前手工运行状态；scanner唯一固定门禁是
`WGS_AUTO_DISPATCH_ENABLED=false`，因此扫描不会创建AnalysisRun或DagRun。
发布不得删除 volume、重建`nipt_analysis_test_net` (`192.168.199.0/24`)或
干预活动CCE attempt；仅 nginx 发布`172.17.106.10:12959`。
