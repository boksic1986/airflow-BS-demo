# WGS 4.1.1 Runtime Integration Development Status

更新时间：2026-08-28

当前结论：T142 已按用户确认的 WGS commit
`1778fcabd99b5253aa90cd410112dc2f78e0c51a`完成 Airflow 单一发布版本接入、
BS10610 禁用态发布和 smoke。真实 OBS/CCE 批次仍未获批准。

## 1. 当前发布合同

| 项目 | 当前目标值 |
|---|---|
| release ID | `wgs-4.1.1-1778fca` |
| WGS version | `V4.1.1` |
| WGS commit | `1778fcabd99b5253aa90cd410112dc2f78e0c51a` |
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
- 前端提交页只读显示 `WGS V4.1.1 / 1778fca`，没有版本选择器；Run Detail显示
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
