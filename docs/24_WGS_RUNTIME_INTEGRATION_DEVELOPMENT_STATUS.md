# WGS 4.1.1 Runtime Integration Development Status

更新时间：2026-08-29

当前结论：T143/T144 已按 WGS commit
`1656b5d7a6e2f24242c38149f6d1c92ac266cd37`完成 T7 scan-only和Step4 repair
禁用态接入与发布。两个真实1800秒周期通过。真实sampleinfo、AnalysisRun、
Airflow DagRun、OBS/CCE批次和Step4 repair均未获批准。

## 1. 当前发布合同

| 项目 | 当前目标值 |
|---|---|
| release ID | `wgs-4.1.1-1656b5d` |
| WGS version | `V4.1.1` |
| WGS commit | `1656b5d7a6e2f24242c38149f6d1c92ac266cd37` |
| BS10610 repo | `/mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1` |
| node200 repo | `/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1` |
| runtime request | `wgs-runtime.request.v3` |
| batch binding | `wgs-runtime.batch-binding.v2` |
| Rule event schema | `1` |
| unique DAG | `bio_wgs`, 18 tasks, manual, paused |

两个共享仓库路径已读核对为相同 HEAD。prepare 前 runner 检查 HEAD 和
`git status --porcelain`；仅允许 `docs/` 下未跟踪文档，任何已跟踪漂移或其他未跟踪
运行代码都返回 `release_unavailable`。prepare 成功后 Step1-Step6 只使用批次冻结
bundle，因此仓库后续更新不会改变已开始 attempt。

Airflow 不复制 WGS 源码，也不在 node200 创建 Airflow-owned release。Airflow 不固定
或校验 cce-pipeline 版本、wheel、profile SHA 或 Master digest；WGS prepare 负责兼容性，
生成的 `RESOLVED_PROFILE.yaml`只作为审计信息写入 `resolved_runtime`。

## 2. 已完成代码改造

- observer增加只读 T7扫描、首次bootstrap、eligible/add-on配对分类、fingerprint
  漂移和advisory lock；1800秒扫描与5秒evidence轮询独立。
- migration `20260829_0011`增加scanner状态、芯片发现和Step4维护操作。
- 后端/UI增加无样本标识的intake投影，以及固定cram的Step4 repair能力、RBAC、
  二次确认和执行关闭409。
- 唯一`bio_wgs`增加同attempt的`repair_step4`维护模式，但任务数、paused状态和
  正常Step1-Step6图不变。

- 单一 schema-3 `wgs_releases.yaml`取代 development snapshot catalog。
- `POST /api/runs`不接受客户端版本字段，后端自动绑定当前 release、WGS version 和
  source commit；新增 `GET /api/wgs/release`。
- Run Detail、Rule timing、observer binding、Rule event去重和历史 ETA 均按
  `pipeline_release_id`隔离。
- migration `20260827_0010`将
  `observer_run_state.pipeline_snapshot_id`改名为`pipeline_release_id`，并迁移残留
  WGS run params；用户、角色和平台设置不重置。
- runtime request v3 不再携带 snapshot path、cce-pipeline version 或 wheel hash。
- node200 runner固定 `WGS_REPO_ROOT`，prepare重试复用已有 binding；resume 和
  rerun attempt 继续使用原 release，原 commit不可用时明确阻断，不能静默换版本。
- 前端提交页只读显示 `WGS V4.1.1 / 1656b5d`，没有版本选择器；Run Detail显示
  release、commit和prepare后解析的 runtime审计字段。
- 已删除 Airflow-owned WGS复制脚本、candidate sync脚本及其旧测试。

## 3. 编排和运行边界

唯一 DAG 保持现有 18-task项目编排：

```text
validate
→ prepare
→ Step1 upload
→ Step2 Master
→ Step3 monitor
→ Step4 publish
→ Step5 download
→ Step6 materialize
→ finalize
```

不增加 FASTQ MD5、上传后 FASTQ验证、固定 Master slot、local/SGE DAG、Step0、
Step7或Step8。OBS阶段使用单槽位，长任务使用五秒 reschedule sensor。Rule JSONL和
Master Job/Pod evidence仍由node200写入共享spool，observer不持有kubeconfig或SSH
私钥；API/UI只展示Master，不持续枚举Worker Pod。

## 4. 禁用态预验收

T143/T144当前结果：BS10610 backend `216 passed, 1 skipped`，runtime/scripts
`17 passed`，唯一 paused `bio_wgs`有18 tasks且无import error；frontend 9个测试
文件、30 tests、TypeScript和Vite build通过。临时PostgreSQL已完成
`0010 → 0011 → 0010 → 0011`往返，并核对nullable分析关联和`ON DELETE SET NULL`。
生产已迁移0011并启动新服务，`current`已切换到T143。
首次bootstrap记录1817个`bootstrap_ignored`和11个`waiting_barcode_stat`，且
AnalysisRun、RunAttempt、maintenance action和Airflow DagRun均为0。

部署时发现旧evidence遍历可延后原先同循环中的首次扫描，因此scanner已改为
observer进程内的独立线程和独立1800秒时钟；evidence的5秒循环不再阻塞T7扫描。
扫描调度按每轮开始时间计算，不把扫描耗时叠加到1800秒间隔。首次全量扫描约
325秒；永久`bootstrap_ignored`随后跳过FASTQ枚举，稳定扫描约1.4秒。bootstrap后
新完成但无eligible WGS的芯片只登记为`no_new_wgs`，未创建运行。
稳定基线为`10:20:30.971949 UTC`；两个自然周期分别推进到
`10:50:30.972362`和`11:20:30.972623 UTC`，耗时516ms和1216ms。两轮分类计数
保持1817/11/1，业务run/attempt/maintenance及Airflow DagRun均为0。T143验收完成。

以下为T142历史预验收结果：

- BS10610 isolated backend：`202 passed`。
- BS10610 runtime/scripts：`16 passed`。
- Airflow：5个DAG unittest、py_compile和运行镜像DagBag均通过；`bio_wgs`为18
  tasks且`is_paused_upon_creation=true`。
- frontend：8个test files、27 tests通过；TypeScript和Vite production build通过。
- PostgreSQL临时库验证`20260826_0009 → 20260827_0010`通过：release字段、observer
  列和管理员sentinel均保留，随后精确删除临时数据库。
- `git diff --check`和迁移smoke脚本`bash -n`通过。

正式 `current` 已切到：

```text
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/
20260828-wgs-4.1.1-single-release-disabled-t142
```

biodemo正式迁移到`20260827_0010`，保留1个管理员且运行数据为零。HTTP验证覆盖
匿名401、登录200、禁用任务创建201、Run Detail 200和submit 409；synthetic数据库
记录、session、audit和workdir随后精确清理。网络仍为`192.168.199.0/24`，只有
`172.17.106.10:12959`发布。

node200的非交互SSH曾被`~/.bashrc`无条件执行共享盘conda hook阻塞。保留备份后在
固定WGS PATH导出之后增加非交互early-return，并加入`/usr/local/bin`供Git commit
校验。Airflow worker现可返回`t640`、读取WGS HEAD和拒绝非法forced-command。

最终清理后`releases/`只保留T142；`backups/`只保留成功切换前的T142 biodemo dump。
被删除的T141 release和第一次回滚生成的冗余dump不可恢复；生产WGS源码、输入、结果、
PostgreSQL/Redis volume及Docker network均未删除。

## 5. 生产启用门禁

在另行批准真实批次前必须继续满足：

```text
WGS_EXECUTION_ENABLED=false
WGS_RUNTIME_ADAPTER_ENABLED=false
bio_wgs paused
```

本轮不运行Step1-Step6，不访问OBS对象，不创建CCE Master/Worker，不修改WGS仓库，
不安装或升级cce-pipeline，不重建PostgreSQL/Redis volume，也不重建外部
`nipt_analysis_test_net`网络。T140最小真实批次和故障/并发验收仍是独立任务。

## 6. 历史状态说明

T139的candidate snapshot、cce-pipeline 0.5.0 Airflow门禁和T141旧release均为历史
实现证据，不再是新任务绑定合同。旧`bio_wgs_cce`、`bio_wgs_intake_scan`和
`bio_wgs_onprem`已在早期清理；当前目标和后续新任务只使用`bio_wgs`。
