# 26 WGS T7 自动扫描与 Step4 人工修复

> T145 修正：本文中 scanner/observer 混合服务、`bootstrap_ignored`和
> `waiting_barcode_stat`入库行为已被
> [文档 27](27_WGS_SCANNER_OBSERVER_LIFECYCLE.md)取代。Step4 repair 合同仍有效。

## 1. 当前边界

本功能绑定唯一 WGS 发布 `wgs-4.1.1-1656b5d`，版本 `V4.1.1`，提交
`1656b5d7a6e2f24242c38149f6d1c92ac266cd37`。代码按 cce-pipeline 0.7.1
合同实现，但不安装、升级或校验 cce-pipeline。`bio_wgs`保持 paused，
`WGS_EXECUTION_ENABLED=false`、`WGS_RUNTIME_ADAPTER_ENABLED=false`，自动分析
关闭。

本阶段扫描器只登记发现状态。它不运行 sampleinfo、不建立分析目录、不创建
`AnalysisRun`或 Airflow `DagRun`，也不访问 OBS/CCE。

## 2. T7 扫描合同

`wgs-observer`每 1800 秒扫描只读挂载`/bi/fastq/T7_Fastq`，并使用 PostgreSQL
advisory lock保证单实例。1800秒按扫描开始时间计算，扫描耗时不会额外延长周期；
永久`bootstrap_ignored`目录后续不再枚举FASTQ，只更新时间。芯片目录必须匹配：

```text
^\d+th_(\d{8}[A-Z])_[A-Za-z0-9.-]+$
```

目录名中的捕获组是上机批次。只有目录直属的普通文件`BarcodeStat.txt`存在时才
算下机完成；扫描器不递归、不打开 FASTQ、不计算 MD5。直属文件仅识别
`<sample>-WGS.R1.fq.gz`和匹配的 R2。sample ID 以`-S\d+`结尾时作为加测排除。
非加测配对缺失进入`needs_review`；没有非加测 WGS 对（含仅加测）进入
`no_new_wgs`。

eligible fingerprint只包含芯片号、上机批次、BarcodeStat 的 stat，以及非加测
文件的文件名、大小和 mtime。ready 后 eligible 输入漂移进入`needs_review`；
加测文件变化不作为分析门禁。数据库可保存扫描根路径和不可逆指纹，但公开 API
和前端不得返回源路径、指纹或样本编号。

首次运行是 bootstrap：已完成目录登记为`bootstrap_ignored`且以后不会自动转为
ready；尚未完成的目录登记为`waiting_barcode_stat`，后续出现 BarcodeStat 才
进入正常判定。状态集合为：

```text
waiting_barcode_stat | ready | no_new_wgs | needs_review | bootstrap_ignored
```

`WGS_AUTO_DISPATCH_ENABLED=false`是独立硬门禁。未来自动提交必须另行实现“事务
锁定 discovery、重新核对 fingerprint、调用 WGS prepare、创建 AnalysisRun、
触发 bio_wgs”，不得复用本阶段扫描函数产生运行副作用。

## 3. 数据库和 API

Alembic `20260829_0011`：

- 扩展`wgs_intake_batch`，允许`analysis_id`为空，保存芯片/上机批次、
  BarcodeStat stat、三类计数、eligible/observed fingerprint、状态和扫描时间；
  关联运行删除时使用`SET NULL`保留发现证据。
- 新增单例`wgs_intake_scanner_state`，保存 bootstrap、最近/下次扫描、耗时、
  计数和错误。
- 新增`wgs_maintenance_action`，按`analysis_id + attempt + action_type`唯一，保存
  Step4维护 DagRun、状态、证据和审计字段。

公开接口：

- `GET /api/intake/status?pipeline=wgs`：分页和状态过滤后的芯片级摘要；不含样本
  编号、源路径或 fingerprint。
- `GET /api/intake/scanner-state`：1800 秒调度、bootstrap、扫描错误和
  `auto_dispatch_enabled=false`。
- `GET /api/runs/{id}`：增加`step4_repair`能力和最近维护操作。
- `POST /api/runs/{id}/actions/repair-step4`：仅 operator/admin，固定`cram`；
  请求体不接受 path、group、project、batch、run_id、确认串或 shell 参数。

## 4. Step4 repair 合同

只有同 attempt 的 Master 已成功、运行处于 Step4 异常、冻结 bundle 的
`RESOLVED_PROFILE.yaml`声明`analysis.delivery.repair_groups.cram`时才显示能力。
后端根据冻结 batch binding生成：

```text
REPAIR-LINKAGE:<project>/<batch>/<run_id>:cram
```

`bio_wgs`使用`maintenance_mode=repair_step4`，Step1-Step3变成无副作用跳过；
node200只执行冻结 bundle 中：

```bash
Step4_publish_results.sh \
  --repair-linkage-group cram \
  --confirm 'REPAIR-LINKAGE:<project>/<batch>/<run_id>:cram'
```

原 DagRun仍在等待时，维护 DagRun只修复 Step4，由原 DagRun继续。原 DagRun已
失败时，维护 DagRun从普通 Step4核验继续 Step5、Step6和 finalize。操作异步且
幂等，observer读取`step4_repair_cram.status.json`更新状态。执行开关关闭、
cce-pipeline 0.7.1尚不可用或合同不满足时返回 409，并且不得建立 SSH/CCE操作。

## 5. 前端和安全

Dashboard展示“T7自动扫描”、扫描状态、eligible配对数、排除加测数和配对异常
数，并明确显示“自动分析关闭”。Run Detail在合同满足时为 operator/admin展示
“修复CRAM联动并继续”，点击后必须二次确认；viewer只读。UI不允许编辑
sampleinfo或提交任意维修参数。

T7根目录只读挂载给 observer。observer不持有 kubeconfig或 OBS credential；
维修仍通过既有受限 node200边界。Docker继续使用外部
`nipt_analysis_test_net`（`192.168.199.0/24`，gateway `192.168.199.1`），只发布
前端`172.17.106.10:12959`。

## 6. 禁用态验收

- scanner单元测试覆盖非法目录、BarcodeStat缺失、无 WGS、正常/混合/仅加测、
  非加测缺对、bootstrap、漂移、幂等和 advisory lock。
- Step4测试覆盖 RBAC、固定 cram、服务端确认串、同 attempt、幂等、原 DagRun
  两种继续模式和执行关闭 409。
- 远端通过 backend、observer、DAG、runner、frontend、Alembic、Compose与网络
  测试。
- 首次生产扫描只能 bootstrap；至少观察两个完整 1800 秒周期，且前后
  `AnalysisRun=0`、Airflow `DagRun=0`。
- 本阶段不运行 sampleinfo、Step1-Step6、OBS传输或 CCE workload。
