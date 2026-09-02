# 11 部署 Runbook

## T168 `.96` production control plane

The production WGS control plane is deployed on `172.17.61.96` under
`/data/airflow-WGS`. Its `current` symlink points to an immutable release; the
server-local `production.env` and SSH identity live outside every release.

PostgreSQL must use the named Docker local volume
`airflow-wgs_postgres-data`. The volume is backed by `.96` local `/data` storage;
do not relocate PGDATA to `/sg2`. WGS business results and runtime spools remain
under the separately approved `/sg2/14.hanjingjing/Cloud_WGS_Clinical` roots.

The deployment must retain all of these disabled-state invariants:

```text
WGS_EXECUTION_ENABLED=false
WGS_RUNTIME_ADAPTER_ENABLED=false
WGS_SUBMISSION_PREVIEW_ENABLED=false
WGS_AUTO_DISPATCH_ENABLED=false
bio_wgs paused
nipt_analysis_test_net = 192.168.199.0/24, gateway 192.168.199.1
only 172.17.61.96:12959 published
frontend client allowlist includes 10.10.30.0/24; deny all remains the default
Docker logging max-size=20m, max-file=3
```

Before any real run, independently validate the `hanjj` node200 kubeconfig,
kubectl and CCE operator config. A working SSH/OBS probe alone is insufficient.
Enabling the two execution gates and unpausing `bio_wgs` require a separate
approved minimal-batch acceptance. Never use `docker compose down -v`, recreate
the external network, or delete `/sg2` data during release switching.

Initial disabled-release evidence and database dumps are stored at
`/data/airflow-WGS/backups/T168-initial-20260902T140812Z` with mode 0600.
Acceptance must request both `/` and `/api/health` from an operator workstation;
an API-only localhost smoke does not validate the Nginx client allowlist.

## T166 WGS展示投影发布

T166不迁移数据库、不运行WGS、不操作OBS/SFS业务数据。发布前备份biodemo与Airflow
metadata，并保存当前`current`目标和容器镜像ID。使用新backend源码和经BS10610 Docker
验证的frontend dist创建不可变release，只重建backend、frontend和读取同一源码的
run-observer；PostgreSQL、Redis、volume和外部网络均不重建。

对历史成功批次的修复仅运行`python -m app.wgs_rule_reconcile_cli --analysis-id <id>
--attempt <n>`。CLI从数据库登记的evidence相对路径解析日志，不接受用户路径；运行前
必须已有数据库备份和同SHA256的只读`analysis.log`镜像。该操作只重建Rule投影，不能
提交DagRun、Master、传输或WGS。完成后验证Step1-Step6均success、Rule phase含Cloud
delivery、sequence非空、样本仅精确匹配，并确认执行开关仍false、DAG仍paused。

本次生产实例：

```text
release: 20260902-wgs-4.1.1-6c98281-t166-workflow-rule-r1
frontend image: airflow-demo/frontend:t166-workflow-rule-r2
backup: backups/T166-workflow-rule-20260902T1655+0800
replay: WGS_20260901_031616_C74E6C / attempt 1
result: rules_projected=208, rules_enriched=147
```

固定网络验收不变：`nipt_analysis_test_net=192.168.199.0/24`、gateway
`192.168.199.1`，唯一发布端口为`172.17.106.10:12959`。

## T165 生产前端禁用态发布

BS10610当前release为
`20260902-wgs-4.1.1-6c98281-t165-production-ui-r1`。切换前必须备份两套数据库、
暂停`bio_wgs`，并将`WGS_EXECUTION_ENABLED`、`WGS_RUNTIME_ADAPTER_ENABLED`和
`WGS_AUTO_DISPATCH_ENABLED`设为false。应用加法迁移`20260901_0013`后，只重建应用、
Airflow、scanner/observer、metrics collector和frontend；不得重建PostgreSQL、Redis、
volume或外部网络。

重建后的生产不变量：

- scanner继续启用，`WGS_INTAKE_SCAN_INTERVAL_SECONDS=600`；
- `nipt_analysis_test_net`保持`192.168.199.0/24`，gateway为`192.168.199.1`；
- 只有frontend/nginx发布`172.17.106.10:12959`；
- node exporter或Cloud Eye不可用时只显示degraded，不阻断WGS，也不回退到BS10610指标；
- 禁用态submit必须返回HTTP 409且不得创建DagRun。

## T163 最小在途热修复

T163从在线T152 release建立新不可变release，不提前部署migration 0013。发布前备份
biodemo、Airflow metadata、runner状态和受保护env；测试使用BS10610 Docker及
`--network none`。仅当Step4状态文件的analysis/attempt/stage完全匹配、status为
success且业务run仍停留在Step4假失败，才可把同attempt投影恢复为downloading；真实
Step5失败不得被普通注册隐藏。Step4/Step5异步重试必须使用runner返回的`retry_no`
等待对应generation状态可见，禁止以跨主机时间戳判定新旧状态。

Step5因可恢复传输故障失败时，只允许在旧worker确认退出、request SHA不变且checkpoint
仍在原位时归档旧status/worker/log并建立新generation。不得删除已校验结果或checkpoint，
不得重跑Step1-Step4；重新放行Airflow sensor前必须确认同一retry generation为running。

scanner精确忽略项通过受保护env的`WGS_INTAKE_IGNORED_CHIP_IDS`配置。删除发现行前
必须确认`analysis_id IS NULL`和关联分析数为0；删除后立即运行一次`--once`并确认
该行未重建、AnalysisRun/DagRun计数未增加。Compose继续复用外部
`nipt_analysis_test_net`，不运行migration、不删除volume。真实batch未终态时不得
关闭会阻止其后续Task调度的运行门禁；终态验收后再切回disabled状态。

## T158禁用态发布门禁

迁移`20260901_0013`前备份biodemo和Airflow metadata。两个WGS执行开关保持false，
`bio_wgs`保持paused，自动提交保持false；scanner周期为600秒。新增metrics collector
不发布端口。保留外部网络`192.168.199.0/24`，只能发布`172.17.106.10:12959`。
共享WGS HEAD与catalog不一致时不得自行改绑或启用。
当前生产候选必须核对共享仓库分支`dev_CJC_4.1.1_cloud`和完整commit
`6c982817614db6a1157b6f287427ddf01ac91827`，catalog必须同时为
`wgs-4.1.1-6c98281`/`V4.1.1`，runner固定路径为node200的
`/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1`。`wgs-4.2.0`仅供测试，
不得被生产Airflow静默改绑。
`WGS_SUBMISSION_PREVIEW_ENABLED`仅作为历史draft API兼容门禁；新的catalog受控Submit不依赖preview worker。部署前必须验证WGS prepare的sampleinfo→analysis语义和最终sampleinfo同步。
迁移`20260901_0013`的downgrade会删除draft、stage projection和资源快照，默认
拒绝执行；只有经批准回滚并确认数据可丢弃时才可临时设置
`ALLOW_WGS_PRODUCTION_UI_DOWNGRADE=true`。

## T152 Step4 Master时序恢复

1. 只读核对Step3成功sidecar、冻结binding、Master名称/UID/namespace和Kubernetes
   Complete终态。任一身份不一致或Master真实失败时停止。
2. 备份biodemo、Airflow metadata、完整attempt runner sidecar/log、binding和Task状态，
   校验SHA256；不要备份私钥、OBS凭据或kubeconfig。
3. 运行runner/backend/DAG import/Compose/network测试后，原子部署runner和不可变
   control-plane release。不要重建PostgreSQL、Redis、volume或网络。
4. 只清除原DagRun的Step4、Step5、Step6、finalize和release_leases。明确核对
   Step1-Step3仍success且try number不变。
5. 同request SHA的failed Step4只有在旧worker退出后才可形成retry generation。
   正常Step4最多等待Master Complete 600秒；不得用该等待掩盖其他错误。
6. 如果重试越过Master检查后出现新的交付合同错误，立即停止继续清Task。不得在未
   审批时热补丁冻结bundle、覆盖OBS marker或改用CRAM repair。

本次真实恢复在第6步停止：WGS 2499749的`cloud_runtime.py`生成带身份的schema-1
JSON `ANALYSIS_COMPLETE`，但同一冻结bundle的`cce_delivery.py`只接受字面量
`status=PASS\n`。完成Step5-Step6前必须先由WGS/runtime侧统一该合同并确定受控的
在途恢复方式。

## T151 YF非临检过滤滚动发布

1. 先验证mixed/YF-only/YF缺对三个RED用例，再验证旧v2 ready指纹兼容升级；运行
   focused和完整backend测试。
2. 备份biodemo并记录AnalysisRun、RunAttempt、DagRun及7条intake状态。确认
   `WGS_AUTO_DISPATCH_ENABLED=false`和600秒周期。
3. 从当前release建立经`realpath`验证的真实目录，禁止使用staging软链接；复制
   scanner代码/测试/文档并先运行`docker compose config --quiet`。
4. 原子切换`current`后只重建`wgs-intake-scanner`，不重建frontend、backend、
   Airflow、observer、PostgreSQL、Redis、volume或Docker网络。
5. 扫描后确认YF被排除、原ready记录没有虚假漂移、业务run计数和当前CCE attempt
   不变；网络仍为`192.168.199.0/24`且仅frontend发布`172.17.106.10:12959`。

回滚只切回前一release并重建scanner。T151无数据库迁移，不删除或恢复intake行。

## T150 T7 scanner滚动修复

1. 在BS10610隔离环境运行scanner focused和完整backend测试；frontend必须在
   BS10610 Docker环境运行测试和生产构建，本机Node结果不得作为验收证据。软链接
   测试必须包含目标不存在的R1/R2，证明scanner不访问目标。
2. 部署前`pg_dump -Fc`备份biodemo并记录AnalysisRun、RunAttempt、Airflow
   DagRun和intake行数。不得清空或修改这些表。
3. 从当前release建立新的不可变release；scanner继续只读挂载
   `/bi/fastq/T7_Fastq`，不要增加`/sg2/T7new`。设置600秒周期并确认
   `WGS_AUTO_DISPATCH_ENABLED=false`。
4. Docker Hub不可用时，以已验收frontend nginx镜像为base，删除继承静态文件后
   离线复制本地tested `dist`；逐项核对index/CSS/JS SHA256，禁止旧hash资产残留。
5. 只重建`wgs-intake-scanner`和`frontend-nginx`。不重建backend、Airflow、
   run observer、PostgreSQL、Redis、volume或网络，不清理或重提活动CCE批次。
6. 触发一次scanner后核对2227为10对ready，历史no-new-WGS按实际名称重新分类，
   且AnalysisRun/RunAttempt/DagRun计数完全不变。通过内部token只读API确认
   `schedule_seconds=600`及前端HTTP 200。
7. 验证scanner只有T7只读挂载；`nipt_analysis_test_net`仍为
   `192.168.199.0/24`/gateway`.1`，仅frontend发布`172.17.106.10:12959`。

回滚只切回前一release、恢复旧frontend tag并重建scanner/frontend。不要恢复
数据库或删除重新分类的intake行；T150没有schema迁移。

## T149 在途 Step3 接管

This procedure is only for a Step3 monitoring/control-plane failure when the
frozen CCE Master still exists. It must not be used to hide or automatically
rerun a real analysis failure.

1. Record the exact `analysis_id`, attempt, DagRun ID, frozen Master Job, and
   namespace. Run the frozen `Step3_status.sh --output json` read-only. Stop if
   it reports `FAILED`; continue only for `RUNNING` or `SUCCEEDED`.
2. Back up biodemo, Airflow metadata, the exact attempt's runner status files,
   and the deployed node200 gate. Store checksums and mode `0600`; do not copy
   private keys, OBS credentials, kubeconfig, or clinical config into Git.
3. Validate backend, runner, DAG import, Compose, and network contracts before
   switching the immutable release. Deploy the node200 gate atomically and
   recreate only the application services that need the new bind mount. Never
   recreate PostgreSQL, Redis, volumes, or `nipt_analysis_test_net`.
4. Clear only `start_step3_monitor` and downstream task instances in the same
   DagRun. Confirm `submit_step2_master` and Step1 remain `success` with their
   original try numbers. Do not create a new DagRun or attempt.
5. Confirm the restarted monitor binds to the identical Master Job and
   namespace, the business run returns from the monitor-generated `failed` to
   `running`, and the observer becomes `active`. Verify no new OBS upload,
   Step2 submission, or CCE Master Job appears.
6. Let the original DagRun continue through Step4-Step6. Final state remains
   governed by the CCE terminal evidence and result verification.

Rollback is limited to restoring the previous release/gate and recreating the
same application services. Do not clear Step1/Step2, delete evidence, or submit
a replacement Master during rollback.

## T146 2499749 / cce-pipeline 0.8.1 手工批次

1. 只读核对BS10610/node200共享WGS HEAD为`2499749ce7fd200d4269d1ee03d7b6a4e8d5bb68`，
   node200实际cce-pipeline为0.8.1，仓库漂移仅允许`docs/`未跟踪文件。
2. 在两个execution gate为false时运行runner/backend/DAG/frontend/Compose测试，创建
   新disabled release并保持`bio_wgs` paused；不得先启动OBS或CCE。
3. node200受保护runtime env中的`CCE_PIPELINE_BIN`必须指向
   `/bi/software/mamba/envs/WGS/bin/cce-pipeline`。BS10610只读挂载受控FASTQ目标根；
   私钥、OBS配置和kubeconfig不得进入release或容器。
4. 旧批次重建时先保存受控FASTQ软链接，再以Step0合同清理SFS和OBS result；如还要
   删除OBS FASTQ，必须使用精确`Project_fastq/<project>/<batch>`前缀并复核0B。
   不删除软链接目标。旧本地分析目录不属于新run输入，也不需要重建。
5. disabled HTTP smoke确认登录、release API、create/detail和submit 409后，才开启两个
   gate；确认自动提交仍关闭后，解除`bio_wgs`的pause，再通过operator API手工create
   和submit一个run。paused DAG会接受DagRun但不会调度task，不能作为手工运行方式。
6. 前端必须显示release、Transfers、Rules和Master-only状态；Step5/Step6与最终业务
   状态一致后才判定成功。任何失败保留attempt evidence并按resume优先处理。

所有Airflow组件必须共享受保护的`AIRFLOW_WEBSERVER_SECRET_KEY`。缺少该值时API
server与Celery worker会生成不同密钥，任务日志代理会返回HTTP 403；密钥只保存在
未跟踪的生产环境文件中，不进入release、镜像或日志。

`runner-requests/<analysis_id>/attempt-N`必须由backend设置为共享组
`WGS_RUNTIME_SHARED_GID`（BS10610/node200当前为520）和mode `2770`。否则backend
虽能登记request，node200却无法原子写入`*.status.json.partial`，prepare会在任何
OBS/CCE操作之前失败。不要用全局`chmod 777`规避该边界。

`release_leases`采用`all_done`只为确保清理总会执行；清理结束后必须检查同一DagRun
的失败和`upstream_failed` task并主动失败。后端同步WGS状态时也必须核对task实例，
不能仅信任Airflow叶节点汇总状态，否则清理task成功会把上游失败误报为run成功。

WGS prepare配置固定使用当前共享WGS release内的`prepare/config.yaml`；不要指向
不存在的`~/.config/wgs/prepare.yaml`。CCE operator配置仍必须显式使用node200上
受保护且可读的绝对`cce.yaml`，其内容不得进入Airflow release或日志。

手工Airflow任务的`fq_path`是受控、重新校验过的软链接目录，代表人工确认上云；
prepare调用必须显式传`--skip-samplelist-ready-check`，避免再次要求线下Samplelist和
FASTQ ready标志。该开关不绕过Airflow输入快照、R1/R2配对、批次字段和目录唯一性。

Airflow的`batch_no`保存完整分析目录名，但WGS CLI的`--analysis-batch`只接受从中
提取的上机批次（例如`20260825A`），由WGS自行生成最终
`WGS_<batch>_<platform>Hg38<version>`。`fq_path`绑定具体受控芯片目录，而CLI的
`--fastq-root`传该目录的父目录；提交前必须验证目录名包含同一个上机批次。

传输sensor每次只同步当前`analysis_id + attempt`的状态文件，同时读取同一attempt的
`runs/.../batch-binding.json`并写入`resolved_runtime`。这不是恢复全局runtime扫描；
不得glob其他run，也不得让空闲observer轮询binding。

`Step3_status.sh --output json`可能先输出kubectl资源提示，再在最后一行输出JSON。
runtime gate必须从后向前选择最后一个合法JSON记录并执行严格schema校验，不能对整个
stdout直接`json.loads`，也不能忽略非零退出码。

T146真实运行发现的兼容性门禁：cce-pipeline 0.8.1 Step2会在Master START前建立
`run_root/evidence/<run_id>/jobs.ndjson`。resolved Master镜像必须接受这一精确stub并
原子写入`config/run-id`；0.7.0系列Master会将其判为无身份的既有run目录并立即失败。
出现该组合时应关闭两个execution gate并暂停DAG，不得通过重试、修改Airflow分析
目录或热补丁冻结bundle绕过。

网络不得重建：`nipt_analysis_test_net=192.168.199.0/24`、gateway
`192.168.199.1`，只有`172.17.106.10:12959`可发布。

## T145 稀疏基线和 observer 拆分发布

发布前停止旧`wgs-observer`，备份 biodemo 并校验 SHA256。重新查询 intake
关联分析数；非 0 立即中止。迁移到`20260830_0012`后运行带精确 confirm
的 cleanup CLI，再启动`wgs-intake-scanner`和`wgs-run-observer`。首次 scanner
只建立基线；验收 batch/run/DagRun 均为 0，run observer 空闲时无日志。
网络和三个门禁保持不变。完整步骤见[doc 27](27_WGS_SCANNER_OBSERVER_LIFECYCLE.md)。

## T143 T7 scan-only 禁用态发布

1. 确认 catalog绑定`wgs-4.1.1-1656b5d`，两个 execution gate为 false，
   `bio_wgs` paused；不得安装或升级 cce-pipeline。
2. 运行远端 backend/observer/DAG/runner/frontend、Alembic往返、Compose和网络
   验收。不得调用 sampleinfo、Step1-Step6、OBS或 CCE。
3. T143历史发布中observer只读挂载宿主`/bi/fastq/T7_Fastq`到同路径，并设置：
   `WGS_INTAKE_SCAN_ENABLED=true`、`WGS_INTAKE_SCAN_INTERVAL_SECONDS=1800`、
   `WGS_AUTO_DISPATCH_ENABLED=false`。
4. 迁移到`20260829_0011`并只重建相关服务；不删除 volume，不重建外部
   `192.168.199.0/24`网络。
   当前T150及以后release必须改用`WGS_INTAKE_SCAN_INTERVAL_SECONDS=600`。
5. 首次扫描仅建立 bootstrap。核对 AnalysisRun和 Airflow DagRun均为零；T143按
   真实1800秒间隔连续观察至少两个周期，确认状态计数幂等且仍无运行副作用。
6. 只在上述验收通过后切换`current`。真实自动 prepare、分析目录创建、Step4
   repair执行和 CCE分析均需单独审批。

回滚仅切回前一个 disabled release并重建应用；不要降级含新 intake/maintenance
数据的数据库，不删除扫描源、WGS仓库、volume或 Docker网络。

## T142 单一 WGS release 禁用态发布（历史）

1. 只读确认 BS10610 和 node200 的共享 WGS 仓库 HEAD 均为
   `1778fcabd99b5253aa90cd410112dc2f78e0c51a`，已跟踪文件无漂移，未跟踪文件
   仅位于`docs/`。
2. 运行 backend/observer/runner/DAG/frontend 测试、Alembic 临时库升级和
   `docker compose config`；不得调用 Step1-Step6。
3. 在任何 Compose recreate 前运行`python3 scripts/check_wgs_docker_network.py`
   和`docker network inspect nipt_analysis_test_net`；不创建、修改或删除网络。
4. 创建一个新的 disabled release；运行`alembic upgrade head`，只重建相关
   application service，不使用`down -v`，不删除数据库/Redis volume。
5. 验证只发布`172.17.106.10:12959`、唯一`bio_wgs`有18 tasks且 paused、两个
   execution gate 均为 false。
6. HTTP smoke覆盖登录、`GET /api/wgs/release`、禁用态 create、Run Detail 和
   submit 409。真实 OBS/CCE 操作与 DAG unpause须另行批准。

node200 的`forced-command.sh`继续执行共享 runtime 下的`wgs_runtime_gate.py`；
不要复制 WGS 仓库或在 node200 创建 WGS release。回滚只切回上一 disabled
control-plane release并重建应用服务，不回滚 migration、不删除 volume/network。

node200 的 SSH command session 即使非交互也会读取`~/.bashrc`。必须先导出固定
runner PATH（包含`/home/chenjc/.local/bin`、WGS环境、`/usr/local/bin`、
`/usr/bin`和`/bin`），随后对非交互 shell直接`return`，再执行交互登录需要的
conda初始化。修改前保留`.bashrc`的owner/mode备份并运行`bash -n`；从Airflow
worker验证`hostname`、Git路径、固定WGS HEAD和非法forced-command快速拒绝。
不得中断或修改node200上与本次发布无关的传输进程。

> **历史说明：** T141 WGS 4.1.1 禁用态 release 已部署；两个 execution gate
> 仍为 false，`bio_wgs` 仍 paused。T141 已接入 Master Rule JSONL bridge，但
> 尚未运行真实 CCE reader；现行发布与 T140 启用门禁见
> [`25_WGS_4_1_1_AIRFLOW_INTEGRATION_PLAN.md`](25_WGS_4_1_1_AIRFLOW_INTEGRATION_PLAN.md)
>；以下 T133 runbook 为历史记录。

## T133 WGS 4.1.0 deployment gate

Do not recreate the current BS10610 Compose or unpause `bio_wgs` yet. The
candidate must first receive (1) a reconciled cce-pipeline FASTQ source
manifest that does not make Airflow calculate FASTQ MD5, (2) structured
transfer progress from cce-pipeline, (3) installation and disabled-mode
acceptance of the restricted `wgs-runtime` command on node 200, (4) a new
immutable profile revision referencing Master logger image digest
`5d1d977f...`, and (5) a successful remote frontend test/build. Keep
`WGS_EXECUTION_ENABLED=false` and
`WGS_RUNTIME_ADAPTER_ENABLED=false` throughout installation.

The Master image prerequisite itself is complete: the approved r2 base
contains Snakemake `9.24.0+biosan1`, Executor `0.6.4+biosan3`, and
cce-pipeline `0.2.0`; the BS10610-built logger overlay passed tag/digest smokes
and is pinned at RepoDigest `sha256:5d1d977fb21e541582230f31540cc8cd4f7a183e417b41e508162060cfcdf211`.

When those gates pass, build a fresh release containing only `dags/bio_wgs.py`,
run `docker compose config`, migrations, focused backend/frontend/DAG tests,
and verify the immutable external network remains `192.168.199.0/24` with only
`172.17.106.10:12959` published. Pause/remove old DAG metadata only after the
new DAG import check; never reset volumes or the network. Step7/Step8 cleanup
requires a separate explicit operator action and is not part of Airflow.

## T119 Intake archive and NIPT small-batch rollout

1. Record and pause `bio_intake_scan`; reject maintenance while a PGT-A/NIPT
   run is active.
2. Back up Airflow and biodemo with `pg_dump -Fc`, API inventories, the PGT-A
   intake inbox, and SHA256 checksums.
3. Apply Alembic `20260713_0005`, deploy backend/frontend/DAG config, then run
   one controlled PGT-A scan. Successful linked requests must move atomically
   to `.archive/YYYY/MM/<request_id>` and disappear from `lifecycle=active`.
4. Stage NIPT data under a hidden `.partial` directory. Validate R1/R2 pairs,
   `gzip -t`, file count, total bytes, and SHA256 against the BS inventory,
   then atomically rename the batch directory.
5. Restore the scanner pause state and wait for two unchanged scans. Confirm
   three NIPT Discovery rows appear and no NIPT run is automatically created.
6. Manually create and submit projects `NIPT-BS-T13-10`,
   `NIPT-BS-T18-15`, and `NIPT-BS-T21-20`, one at a time. Stop immediately on
   failure; preserve the workdir/events/logs and diagnose or resume before any
   later batch.
7. For each success verify terminal rule events, QC/sample counts, classifier,
   fetal-ratio, CNV, summary artifacts, and logical Intake archive.

T119 completed evidence:

- Backup: `/home/jiucheng/project/airflow-demo-backups/T119-20260713T140647`.
- Runs: `NIPT_20260713_080217_DEC52B` (10 samples),
  `NIPT_20260713_090714_C941EA` (15), and
  `NIPT_20260713_095250_374EA9` (20) all reached backend/Airflow success with
  45/45 aggregate sample QC pass and no residual running rule events.
- A 40-core T18 mapping attempt hit the container 60 GiB cgroup limit. The
  recovery preserved the workdir and used 32 cores plus `--rerun-incomplete`.
  Clear only the exact failed `run_nipt_docker` and downstream collect task via
  the official Airflow REST API; never use a broad date-range clear or
  `--forceall`.
- After recovery, call `sync-airflow`. The backend imports JSONL fallback events
  first and then reapplies the terminal Airflow state, so a stale failed event
  cannot overwrite an authoritative successful DAG run.
- Final scanner state is unpaused with 6 archived records and 0 active records;
  NIPT auto-submit remains false.

Rollback: pause the scanner, restore the previous backend/frontend images and
config, and downgrade only if no T119 lifecycle data is needed. Never delete
FASTQ, workdirs, logs, results, Postgres/Redis volumes, or pipeline releases.

## T118 PGT-A manifest publication and scanner retention

Write the manifest first and create READY last:

```bash
inbox=/data/project/CNV/PGT-A/rawdata/lib_test/pgta_crontab
request_id=project-YYYYMMDD
tmp="$inbox/$request_id.samples.tsv.partial"
printf 'project_id\tsource_batch\tsample_id\toperator\n' > "$tmp"
printf 'PROJECT-ID\t2026-06-08/BATCH-DIR\tSAMPLE-ID\tjiucheng\n' >> "$tmp"
mv "$tmp" "$inbox/$request_id.samples.tsv"
touch "$inbox/$request_id.READY.partial"
mv "$inbox/$request_id.READY.partial" "$inbox/$request_id.READY"
```

- `source_batch` is relative to the configured PGT-A rawdata root.
- Every non-empty line has four real Tab-separated columns.
- Two unchanged scans are required; never publish READY before the manifest.
- Never modify a submitted manifest. Use a new request ID.

T118 measured 212 ten-minute scanner runs, 211 worker task-log files totaling
about 2.5 MB, and a 13 MB Airflow database. The cadence creates 144 runs/day
and 52,560 runs/year. A separate maintenance rollout should rotate Docker
`json-file` logs at 50 MB x 3 and retain scanner-only task logs and DAG-run
metadata for 30 days. Do not apply broad deletion to PGT-A/NIPT analysis DAGs.

## T117 operator correction and manifest recovery

1. Record and pause `bio_intake_scan`; back up biodemo, the request
   manifest/READY files, and API inventories.
2. Preview `app.operator_maintenance_cli` with exact IDs and expected labels.
   Apply only with `CORRECT_RETAINED_PGTA_OPERATOR`; each change writes an
   audited `RunAction(action=metadata_correction)`.
3. A manifest validation error may be corrected in place only before it has an
   `analysis_id`. Valid observed or submitted manifests remain immutable.
4. Rewrite TSV data atomically and preserve READY. Run two PGT-A-only scanner
   cycles for the stability gate and a third to prove idempotency.

Evidence: `/home/jiucheng/project/airflow-demo-t117/backups/T117-20260713-012000`.
This operation does not alter Airflow users, FASTQ, results, workdirs, Docker
volumes, or completed-run source manifests.

## T116 strict Intake and Airflow history cleanup

This is a destructive CLI-only maintenance operation. It must never be exposed
as an unauthenticated frontend action.

1. Record and pause `bio_intake_scan`; reject cleanup while any target DAG run
   is non-terminal.
2. Back up both `airflow` and `biodemo` with `pg_dump -Fc`, plus complete DAG,
   DAG-run, business-run, and discovery JSON inventories. Generate SHA256 for
   every backup and preview/apply artifact.
3. Preview `app.intake_maintenance_cli` with the exact three business IDs, the
   single manifest-linked keep ID, and expected discovery count.
4. Preview `app.airflow_maintenance_cli` with exact per-DAG counts and keep run
   IDs. Apply only with `DELETE_NON_RETAINED_AIRFLOW_HISTORY`; Intake apply
   separately requires `DELETE_NON_RETAINED_INTAKE_DISCOVERY`.
5. Deploy `.airflowignore` before deleting legacy DAG metadata. The deployed
   DagBag must contain only `bio_pgta`, `bio_nipt_docker`, and
   `bio_intake_scan` with no import errors.
6. Restore the original scanner pause state and observe one full scheduled
   cycle. Discovery must remain limited to valid PGT-A manifest records; the
   scheduled request must not include NIPT.

T116 evidence is stored at:

```text
/home/jiucheng/project/airflow-demo-t116/backups/T116-20260712-014626
```

The cleanup uses Airflow REST DELETE and the biodemo SQLAlchemy maintenance
CLI. It does not directly mutate Airflow tables and does not delete workdirs,
FASTQ, logs, reports, Docker volumes, or pipeline releases.

## T114 biodemo cleanup and NIPT QC repair

This is a CLI-only maintenance operation. Do not expose an unauthenticated
frontend delete button.

1. Record the current `bio_intake_scan` pause state and pause it temporarily.
2. Confirm there is no real active PGT-A/NIPT run.
3. Create a dated backup directory and save both `pg_dump -Fc` and the complete
   `/api/runs` JSON inventory. Record SHA256 values.
4. Back up the NIPT `reports/qc_summary.tsv`, regenerate it from mappingQC and
   fetal-ratio outputs, then call `sync-airflow` to re-import metrics/events.
5. Preview an exact snapshot cleanup. The command aborts if the expected run
   count or keep IDs do not match, an unapproved active record exists, or the
   database changes before apply.

```bash
python -m app.maintenance_cli \
  --keep PGTA_20260711_062522_4C4FC2 \
  --keep PGTA_20260711_071416_C8C7BA \
  --keep NIPT_20260711_111140_63C5A6 \
  --expected-total 49 \
  --allow-active-delete WES_20260704_180650_MOCK
```

`--allow-active-delete` is an exact-ID override for a known stale record; it is
never a wildcard. Apply only after reviewing the preview, by adding:

```bash
--apply --confirmation DELETE_NON_RETAINED_BIODEMO_RUNS
```

6. Verify 3 runs, 75 samples, NIPT 504 metrics, 72 pass samples, and the NIPT
   submit/finish timestamps. Restore the original intake pause state.

The cleanup affects biodemo rows only. It must not delete Airflow metadata,
run workdirs, logs, results, FASTQ, Docker volumes, or pipeline releases.

## T113 NIPT Snakemake 9 rollout and rollback

1. Verify the local base image ID equals
   `sha256:1cd289afbd0c48564a530b1a56dd608dc2803b63ed6a4a4c0ca313ef84380b26`.
2. Run `bash scripts/build_nipt_s9_image.sh`. The script builds the derivative,
   verifies both S9 and original S7 versions, and writes image provenance.
3. Optionally set `NIPT_S9_ARCHIVE=true` to write the gzip OCI archive and
   SHA256 under `/home/jiucheng/pipelines/NIPT/images/niptpro-1.0.11-s9-v1`.
   Every build also records `software-versions.txt`, the S9 micromamba package
   inventory, the original analysis Python package inventory, and checksums.
   `NIPT_S9_SKIP_BUILD=true` may refresh provenance only for an already loaded,
   explicitly verified image; it must not be used to approve an unvalidated tag.
4. Keep `NIPT_ALLOW_HEAVY_RUN=false` through lint, dry-run, logger, mount-smoke,
   and baseline comparison preparation.
5. Run one approved full batch with source and bundle before/after manifests,
   resource sampling, all-job terminal-event audit, QC import, and S7 output
   comparison.
6. Only after all acceptance gates pass, set the deployment `.env`
   `NIPT_ALLOW_HEAVY_RUN=true` and recreate backend and Airflow worker. Keep
   NIPT `auto_submit.enabled=false`.

Rollback: set the heavy gate false, choose hidden approved profile
`niptpro-1.0.11`, and recreate backend/worker/frontend. Do not remove the S9
validation run, Docker volumes, source FASTQ, or NIPT bundle. The OCI archive
and checksum restore the validated derivative without a registry pull.

## T111 pipeline profile deployment

`config/pipeline_profiles.yaml` is mounted read-only at
`/app/config/pipeline_profiles.yaml` for backend and
`/opt/airflow/config/pipeline_profiles.yaml` for Airflow services. Both use
`PIPELINE_PROFILE_CONFIG_PATH` to locate it.

Profile release checklist:

1. Add a new immutable profile ID; do not change an ID already referenced by a run.
2. Confirm PGT-A executables/reference paths are readable or NIPT images already exist.
3. Call the template and validation endpoints and confirm runtime details are absent.
4. Run backend, runner, frontend, and Compose tests.
5. Validate with PGT-A metadata and NIPT mount-smoke only unless a heavy run is explicitly approved.

Adding a compatible software profile does not require a new DAG. Changes to
Airflow project stages or the Snakemake config contract require a separate
versioned integration task.

## 1. 前置检查

```bash
whoami
pwd
uname -a
df -h
free -h
docker --version
docker compose version
python --version
node --version || true
which qsub || true
which qstat || true
```

把非敏感结果写入 `SERVER_INFO.md`。

## 2. fengxian 代码镜像

服务器目录只作为 GitHub 镜像，不直接开发或提交。

首次同步：

```bash
test -d /home/jiucheng/project/airflow-demo
find /home/jiucheng/project/airflow-demo -mindepth 1 -maxdepth 1 | head
git clone git@github.com:boksic1986/airflow-BS-demo.git /home/jiucheng/project/airflow-demo
```

如果目录非空且不是 Git 仓库，先停止并确认/备份，不覆盖。

后续更新：

```bash
cd /home/jiucheng/project/airflow-demo
git pull --ff-only
```

## 3. Docker Compose v2 用户级准入

在 `fengxian` 只安装用户级 Docker CLI plugin，不升级系统 Docker，不安装 legacy `docker-compose` v1。

优先路线：在本地 Windows 通过 GitHub Release 下载官方 `docker-compose-linux-x86_64`，再用 `scp` 同步到 `fengxian`。如果本地 GitHub 下载需要代理，显式给 `curl.exe` 加 `--proxy socks5h://127.0.0.1:1080`；不要把代理配置写入仓库。

本地 PowerShell：

```powershell
$url = "https://github.com/docker/compose/releases/download/v2.24.7/docker-compose-linux-x86_64"
$local = "$env:TEMP\docker-compose-v2.24.7-linux-x86_64"
curl.exe -L --fail --retry 3 --proxy socks5h://127.0.0.1:1080 -o $local $url
scp $local fengxian:/tmp/docker-compose-v2.24.7-linux-x86_64
Remove-Item -LiteralPath $local -Force
```

远端 `fengxian`：

```bash
mkdir -p "$HOME/.docker/cli-plugins"
install -m 0755 \
  /tmp/docker-compose-v2.24.7-linux-x86_64 \
  "$HOME/.docker/cli-plugins/docker-compose"
rm -f /tmp/docker-compose-v2.24.7-linux-x86_64
docker compose version
```

备用路线：若本地无法访问 GitHub release asset，可使用国内 Docker CE 镜像下载 `docker-compose-plugin` deb 包，并只解包其中的 CLI plugin 二进制到用户目录。`fengxian` 是 Ubuntu 18.04，但 bionic 镜像只到 Compose 2.18.1；为了固定 `v2.24.7`，使用 focal 包解包二进制，不做系统级 dpkg/apt 安装。

```bash
mkdir -p "$HOME/.docker/cli-plugins"
tmpdir="$(mktemp -d)"
curl -fL \
  "https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/ubuntu/dists/focal/pool/stable/amd64/docker-compose-plugin_2.24.7-1~ubuntu.20.04~focal_amd64.deb" \
  -o "$tmpdir/docker-compose-plugin.deb"
dpkg-deb -x "$tmpdir/docker-compose-plugin.deb" "$tmpdir/extract"
install -m 0755 \
  "$tmpdir/extract/usr/libexec/docker/cli-plugins/docker-compose" \
  "$HOME/.docker/cli-plugins/docker-compose"
rm -rf "$tmpdir"
docker compose version
```

验收输出应为：

```text
Docker Compose version v2.24.7
```

已探测但不作为优先路线：

- `fengxian` 直连 GitHub Release 容易受网络限制。
- 清华/中科大/交大 GitHub-release 路径对 `docker/compose/v2.24.7/docker-compose-linux-x86_64` 返回 404 或错误重定向。
- 清华、交大、阿里云 Docker CE `focal`/`jammy` 镜像可提供 `docker-compose-plugin_2.24.7`。

## 4. 初始化目录

```bash
mkdir -p <PROJECT_ROOT>
mkdir -p <SHARED_ROOT>/runs
mkdir -p <SHARED_ROOT>/reports
mkdir -p <SHARED_ROOT>/logs
```

## 5. 配置环境变量

从 `.env.example` 创建 `.env`：

```bash
cp .env.example .env
```

不得提交 `.env`。

`fengxian` 当前端口约定：

```text
AIRFLOW_PORT=12958
FRONTEND_PORT=12959
BACKEND_PORT=8000
MAILHOG_WEB_PORT=8025
MAILHOG_SMTP_PORT=1025
```

Current frontend/backend browser access:

```text
AIRFLOW_IMAGE=airflow-demo/airflow:0.1.0
FRONTEND_IMAGE=airflow-demo/frontend:0.1.0
SNAKEMAKE_RUNNER_IMAGE=airflow-demo/snakemake-runner:0.1.0
BACKEND_CORS_ORIGINS=*
```

Timezone defaults:

```text
AIRFLOW_DEMO_TZ=Asia/Shanghai
AIRFLOW_DEFAULT_TIMEZONE=Asia/Shanghai
AIRFLOW_DEFAULT_UI_TIMEZONE=Asia/Shanghai
FRONTEND_DISPLAY_TIME_ZONE=Asia/Shanghai
```

`fengxian` host time is `Asia/Shanghai`. Airflow containers and the React frontend must use the same display timezone so Airflow UI logs, task logs, run list timestamps, and run detail timestamps do not appear 8 hours behind the server clock. Backend and biodemo DB timestamps remain timezone-aware values; do not rewrite historical DB timestamps for a display-only timezone fix.

`frontend` now builds this repository's React app and serves it through Docker nginx. The browser API base defaults to `http://<current-host>:8000/api`; override with `window.__AIRFLOW_DEMO_CONFIG__.apiBaseUrl` or `VITE_API_BASE_URL` only when a reverse proxy is added.

Airflow bind-mounts `./shared` and must run with the deploy user's host uid so Airflow-only DAGs can create new workdirs under `shared/runs`. On `fengxian`, `jiucheng` is uid `1005`, so the tracked default and remote `.env` use `AIRFLOW_UID=1005`. On a new server, set:

```bash
AIRFLOW_UID=$(id -u)
```

If this is left at Airflow's container-default uid `50000`, Airflow worker tasks may fail with `PermissionError` when creating `/data/airflow-demo/runs/<analysis_id>`.

Airflow admin 密码只写入未跟踪的 `.env`：

```text
AIRFLOW_ADMIN_USERNAME=admin
AIRFLOW_ADMIN_PASSWORD=<SECRET_FROM_ENV>
AIRFLOW_ADMIN_EMAIL=airflow-demo@example.com
```

Postgres 和 Redis 只在 Docker 网络内使用 `5432` / `6379`，不发布宿主机端口。

PGT-A v1 样本发现只允许扫描白名单路径。`fengxian` 默认：

```text
PGTA_DATA_ROOT=/data/project/CNV/PGT-A
PGTA_CONTAINER_DATA_ROOT=/data/project/CNV/PGT-A
INPUT_SCAN_ROOTS=/data/project/CNV/PGT-A/rawdata
PGTA_SNAKEMAKE9_BIN=/biosoftware/miniconda/envs/snakemake9_env/bin/snakemake
PGTA_SNAKEMAKE_CORES=64
PGTA_PYTHON_BIN=/biosoftware/miniconda/envs/snakemake_env/bin/python
PGTA_CONDA_LIB=/biosoftware/miniconda/envs/snakemake_env/lib
PGTA_LIBSTDCXX=/biosoftware/miniconda/envs/snakemake_env/lib/libstdc++.so.6
AIRFLOW_DAGS_ROOT=/opt/airflow/dags
AIRFLOW_DEMO_QSUB_MODE=mock
AIRFLOW_DEMO_QSUB_PYTHON=python
```

backend 只读挂载 PGT-A 数据根目录，不上传或复制 5-6G FASTQ。

## 6. 检查 compose

```bash
docker compose config
docker compose config --images
```

项目自有镜像必须显式带 tag，不能依赖隐式 `latest`。当前项目镜像名应为：

```text
airflow-demo/backend:0.1.0
airflow-demo/frontend:0.1.0
airflow-demo/airflow:0.1.0
airflow-demo/snakemake-runner:0.1.0
```

当前对外端口应渲染为：

```text
airflow-api-server: 12958 -> 8080
frontend: 12959 -> 80
backend: 8000 -> 8000
mailhog: 1025 -> 1025, 8025 -> 8025
```

backend 镜像构建时先使用仓库内 `backend/pip.conf` 的国内 PyPI 源配置，并在镜像内 `/opt/venv` 安装依赖。不要在 `fengxian` 宿主机系统 Python 上裸跑 `pip install`；若将来确实需要宿主机 Python 辅助脚本，必须先创建虚拟环境：

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

`snakemake-runner` 镜像构建时使用 `snakemake_runner/pip.conf` 的国内 PyPI 源，固定安装 `snakemake==9.23.1` 和 `snakemake-executor-plugin-cluster-generic==1.0.9`。该镜像只用于 WES/NIPT mock qsub profile runtime，不修改 `/biosoftware/miniconda/envs/*`。

Airflow services use the project image `airflow-demo/airflow:0.1.0`, built from `airflow_image/`. It keeps Airflow dependencies on the base image and installs Snakemake 9.23.1 plus `snakemake-executor-plugin-cluster-generic==1.0.9` into `/opt/airflow/snakemake-venv`. Because that venv is first on `PATH`, run Airflow unit tests with `/usr/local/bin/python` when they need the base Airflow Python:

```bash
docker compose -f docker-compose.yaml build airflow-worker airflow-scheduler airflow-api-server
docker run --rm airflow-demo/airflow:0.1.0 airflow version
docker run --rm --entrypoint snakemake airflow-demo/airflow:0.1.0 --version
docker run --rm --entrypoint /usr/local/bin/python \
  -v /home/jiucheng/project/airflow-demo:/repo:ro \
  -w /repo airflow-demo/airflow:0.1.0 \
  -m unittest dags.tests.test_bio_wes_qsub_dag dags.tests.test_wes_qsub_runner -v
```

## 7. 最小启动验收

第一轮只启动基础容器和 backend health，不启动 Airflow、frontend 功能页或 PGT-A。

```bash
docker compose up -d postgres redis mailhog backend
curl http://127.0.0.1:8000/api/health
docker compose down
```

期望 health：

```json
{"status":"ok"}
```

禁止使用 `docker compose down -v` 作为默认停止方式。

## 8. 启动完整服务

先初始化 Airflow metadata DB 和 admin 用户：

```bash
docker compose -f docker-compose.yaml up airflow-init
```

再启动基础服务：

```bash
docker compose -f docker-compose.yaml up -d postgres redis mailhog backend frontend airflow-api-server airflow-scheduler airflow-worker
```

检查：

```bash
docker compose ps
docker compose logs --tail=100 airflow-scheduler
docker compose logs --tail=100 backend
```

## 9. 初始化数据库

`biodemo` 业务库和 Airflow metadata DB 共用同一个 Postgres 容器，但使用不同 database/user。先启动 Postgres，再运行可重复的 one-shot 初始化服务：

```bash
docker compose -f docker-compose.yaml up -d postgres
docker compose -f docker-compose.yaml run --rm biodemo-db-init
```

然后用 backend 容器执行 Alembic migration：

```bash
docker compose -f docker-compose.yaml run --rm backend alembic upgrade head
```

如果 backend 服务已经在运行，使用 `exec`，避免 `run` 创建新 backend 容器时和宿主机 `8000` 端口映射冲突：

```bash
docker compose -f docker-compose.yaml exec -T backend alembic upgrade head
```

验证核心表：

```bash
docker compose -f docker-compose.yaml exec -T postgres \
  psql -U "$POSTGRES_USER" -d biodemo \
  -c '\dt'
```

`.env` 必须包含 `BIODEMO_DB`、`BIODEMO_USER`、`BIODEMO_PASSWORD`、`DATABASE_URL`。不要在命令输出或文档中打印真实密码。

## 10. Airflow 初始化

推荐使用 one-shot 初始化服务：

```bash
docker compose -f docker-compose.yaml up airflow-init
```

验证用户列表：

```bash
docker compose -f docker-compose.yaml exec airflow-api-server airflow users list
```

如需创建用户，必须使用 `.env` 中变量，不在文档写密码。

## 11. 健康检查

```bash
curl http://<SERVER_HOST>:8000/api/health
curl http://<SERVER_HOST>:8000/api/health/db
curl http://<SERVER_HOST>:8000/api/health/airflow
curl http://<SERVER_HOST>:12958/health
curl http://<SERVER_HOST>:12959/
curl http://<SERVER_HOST>:8025/
```

`fengxian` 宿主机已探测到系统 nginx，可作为后续反向代理候选，但当前 airflow-demo 未配置宿主机 nginx，也不应在没有单独计划时修改或 reload nginx。

```bash
/usr/sbin/nginx -v
```

已探测版本：

```text
nginx version: nginx/1.14.0 (Ubuntu)
```

### 11.1 PGT-A frontend run detail smoke

T050/T057 验收启动 `postgres redis backend frontend airflow-api-server airflow-scheduler airflow-worker`，不运行新的 PGT-A DAG。前端访问 `12959`，Airflow UI 仍访问 `12958`。

```bash
docker compose -f docker-compose.yaml config --quiet
docker compose -f docker-compose.yaml build backend frontend
docker build --target test -f frontend/Dockerfile frontend
docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q
docker compose -f docker-compose.yaml up -d postgres redis backend frontend airflow-api-server airflow-scheduler airflow-worker
curl -fsS http://127.0.0.1:12959/
curl -fsS 'http://127.0.0.1:8000/api/runs?pipeline=pgta&limit=5&offset=0'
curl -fsS http://127.0.0.1:8000/api/runs/PGTA_20260703_054712_501D8B/rules
curl -fsS 'http://127.0.0.1:8000/api/runs/PGTA_20260703_054712_501D8B/logs?stream=metadata&tail=2'
curl -fsS http://127.0.0.1:8000/api/runs/PGTA_20260703_054712_501D8B/artifacts
docker compose -f docker-compose.yaml down
```

已验证的 T050/T057 frontend smoke：

```text
frontend: http://127.0.0.1:12959/ returned React HTML
backend tests: 31 passed
frontend tests: 2 passed
PGTA_20260703_054712_501D8B rules: all=success, collect_run_metadata=success
Airflow health: metadatabase healthy, scheduler healthy
```

## 12. PGT-A server-path project smoke

T022/T024 验收只创建项目，不触发 Airflow DAG，不运行 Snakemake。先启动 Postgres/backend 并完成 biodemo 初始化和 Alembic migration。

扫描候选样本：

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/input/scan \
  -H 'Content-Type: application/json' \
  -d '{"pipeline":"pgta","rawdata_root":"/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28","max_samples":5}'
```

用扫描结果中的 1-2 个样本创建 run：

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/runs \
  -H 'Content-Type: application/json' \
  -d @/tmp/pgta-create-run.json
```

验收：

```text
analysis_run.status = created
analysis_run.dag_run_id is null
sample rows contain fq1/fq2 server paths
shared/runs/<analysis_id>/config/samples.selected.tsv exists
shared/runs/<analysis_id>/config/request.json exists
```

后续使用 submit action 触发 Airflow `bio_pgta`。

## 13. PGT-A submit smoke

T027/T035/T045 验收把已存在的 `created` PGT-A run 提交到 Airflow。当前 `bio_pgta` 支持 `metadata`、`dryrun_cnv`、`invalid_target` 和受控 `baseline_qc`。默认 smoke 仍使用 metadata/dry-run/failure；`baseline_qc` 是 Level 4 staged real smoke，会真实执行 mapping + baseline QC，必须至少 2 个 selected samples 并经用户确认后再跑。

先确认配置、测试和 DAG import：

```bash
docker compose -f docker-compose.yaml config --quiet
docker compose -f docker-compose.yaml build backend
docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q
docker compose -f docker-compose.yaml run --rm --no-deps --entrypoint env \
  airflow-scheduler PYTHONPYCACHEPREFIX=/tmp/pycache \
  python -m py_compile /opt/airflow/dags/bio_pgta.py /opt/airflow/dags/pgta_metadata_runner.py
docker compose -f docker-compose.yaml run --rm --no-deps --entrypoint python \
  airflow-scheduler -m unittest discover -s /opt/airflow/dags/tests -v
```

启动所需服务：

```bash
docker compose -f docker-compose.yaml up -d postgres redis
docker compose -f docker-compose.yaml run --rm biodemo-db-init
docker compose -f docker-compose.yaml up airflow-init
docker compose -f docker-compose.yaml run --rm backend alembic upgrade head
docker compose -f docker-compose.yaml up -d backend airflow-api-server airflow-scheduler airflow-worker
```

提交已有 `created` run：

```bash
analysis_id=<PGTA_CREATED_ANALYSIS_ID>
curl -fsS -X POST \
  "http://127.0.0.1:8000/api/runs/${analysis_id}/actions/submit"
```

验收 Airflow 和产物：

```bash
docker compose -f docker-compose.yaml exec -T airflow-scheduler \
  airflow dags list | grep bio_pgta
docker compose -f docker-compose.yaml exec -T airflow-scheduler \
  airflow dags list-runs -d bio_pgta --output json
find "shared/runs/${analysis_id}" -maxdepth 4 -type f | sort
cat "shared/runs/${analysis_id}/logs/snakemake.command.txt"
head -5 "shared/runs/${analysis_id}/logs/run_metadata.tsv"
```

biodemo DB 中该 run 应更新为 `submitted` 且 `dag_run_id` 非空。Airflow success/failed 状态回写需要显式调用 `sync-airflow`。

已验证的 fengxian smoke：

```text
analysis_id: PGTA_20260702_171533_9A85B1
dag_run_id: manual__PGTA_20260702_171533_9A85B1
Airflow state: success
metadata artifact: shared/runs/PGTA_20260702_171533_9A85B1/logs/run_metadata.tsv
```

已知边界：`run_metadata.tsv` 中 `git_branch` / `git_commit` 字段在当前 Airflow 容器内显示 git permission error，但 metadata target 和 DAG run 已成功；后续如需干净 provenance，可单独修正 PGT-A metadata rule 的 git 调用环境。

T088 故障排查记录：如果提交后 Airflow DAG run 约数秒内失败，先查看：

```bash
curl -fsS "http://127.0.0.1:8000/api/runs/${analysis_id}/logs?stream=stderr&tail=100"
```

若 stderr 出现：

```text
PermissionError: [Errno 13] Permission denied: '/home/airflow/.cache/snakemake'
```

说明 Snakemake cache 没有指到 run-local 目录。当前修复要求 `bio_pgta` / `bio_pgta_airflow` 在执行 Snakemake 时设置：

```text
XDG_CACHE_HOME=<workdir>/tmp/xdg-cache
```

不要通过 chmod `/home/airflow` 修复该问题。

### T045/T084 dry-run 与 failure smoke

`dryrun_cnv` run 通过前端 target 下拉或 API 创建，submit 后 `bio_pgta` 会生成 CNV 配置方向的 run-local `config.yaml`，并执行：

```bash
snakemake --snakefile /opt/pipelines/PGT_A/Snakefile \
  --cores ${PGTA_SNAKEMAKE_CORES:-64} --printshellcmds --configfile <workdir>/config.yaml \
  --dry-run --ignore-incomplete --rerun-triggers mtime
```

`dryrun_cnv` 的 run-local config 使用 `/data/project/CNV/PGT-A/refactor_validation_20260419/results_build_ref_v2_mask_only/reference` 下已有只读 WisecondorX XX/XY/gender reference。该 smoke 只验证 Snakemake DAG 可解析，不产生真实 CNV 结果。

验收：

```bash
analysis_id=<PGTA_DRYRUN_ANALYSIS_ID>
curl -fsS -X POST "http://127.0.0.1:8000/api/runs/${analysis_id}/actions/sync-airflow"
curl -fsS "http://127.0.0.1:8000/api/runs/${analysis_id}/logs?stream=stdout&tail=50"
curl -fsS "http://127.0.0.1:8000/api/runs/${analysis_id}/artifacts"
```

期望 `status=success`，stdout/stderr 存在，`config/pgta_run_config.json` 可见，且没有真实 CNV 结果写回 PGT-A 流程目录。2026-07-04 验收样例：`PGTA_20260703_170917_20E8F2`，Airflow `success`，stdout 记录 7 个 dry-run jobs。

`invalid_target` run 只用于 failure smoke。submit 后 Snakemake 会收到 `__airflow_demo_invalid_target__` 并自然失败。验收：

```bash
analysis_id=<PGTA_INVALID_ANALYSIS_ID>
curl -fsS -X POST "http://127.0.0.1:8000/api/runs/${analysis_id}/actions/sync-airflow"
curl -fsS "http://127.0.0.1:8000/api/runs/${analysis_id}/logs?stream=stderr&tail=100"
curl -fsS "http://127.0.0.1:8000/api/runs/${analysis_id}"
```

期望 `status=failed`，`error_summary` 非空，并包含 stderr 路径和最后 100 行错误内容。

### Level 4 PGT-A baseline_qc staged smoke

只读审计确认 `/home/jiucheng/pipelines/PGT_A/Snakefile` 支持 `baseline_qc`，但它要求至少 2 个 baseline/reference samples，并会运行 `mapping`、`metadata`、`baseline_bam_uniformity_qc` 和 `aggregate_baseline_qc`。不要把它当作单样本轻量 smoke。

前端/API 创建要求：

```text
pipeline=pgta
target=baseline_qc
selected_samples >= 2
```

submit 后 `bio_pgta` 生成 run-local config：

```yaml
pipeline:
  mode: build_ref
  targets: [mapping, metadata, baseline_qc]
build_reference:
  mode: selected_samples
  groups:
    demo: [<selected sample ids>]
```

验收命令：

```bash
analysis_id=<PGTA_BASELINE_QC_ANALYSIS_ID>
curl -fsS -X POST "http://127.0.0.1:8000/api/runs/${analysis_id}/actions/sync-airflow"
curl -fsS "http://127.0.0.1:8000/api/runs/${analysis_id}/qc"
curl -fsS "http://127.0.0.1:8000/api/runs/${analysis_id}/artifacts"
test -s "shared/runs/${analysis_id}/qc/baseline/baseline_qc_summary.tsv"
test -s "shared/runs/${analysis_id}/qc/baseline/baseline_qc_report.md"
```

期望：

```text
status=success
QC summary 有 pass/warn/fail/unknown 计数
artifacts 包含 pgta_baseline_qc_summary、pgta_baseline_qc_pass_samples、pgta_baseline_qc_report
PGT-A 流程目录和 rawdata 目录没有被写入
```

### T093 PGT-A controlled interrupt and resume

Use this only for an already active `baseline_qc` run that the user explicitly chooses to interrupt and resume. Do not interrupt unrelated host processes.

1. Re-check Airflow and exact matching processes:

```bash
analysis_id=PGTA_20260706_162150_00C4FD
docker compose -f docker-compose.yaml exec -T airflow-scheduler \
  airflow dags list-runs -d bio_pgta --output table
docker top airflow-demo-airflow-worker-1 -eo pid,ppid,etime,pcpu,pmem,args \
  | grep -F "$analysis_id" | grep -v grep
```

2. If still running and the user has approved interruption, terminate only the matching Snakemake process first. If needed, terminate only child shell/BWA/Samtools processes whose command contains the same `analysis_id`.

3. After the old DAG run reaches `failed`, sync backend state:

```bash
curl -fsS -X POST \
  "http://127.0.0.1:8000/api/runs/${analysis_id}/actions/sync-airflow"
```

4. Resume through FastAPI:

```bash
curl -fsS -X POST \
  "http://127.0.0.1:8000/api/runs/${analysis_id}/actions/reanalyze" \
  -H 'Content-Type: application/json' \
  -d '{"mode":"resume","reason":"controlled resume after interrupting pre-T091 cores=1 run"}'
```

5. Verify the new run writes unlock and resume command artifacts:

```bash
cat "shared/runs/${analysis_id}/logs/snakemake.unlock.command.txt"
cat "shared/runs/${analysis_id}/logs/snakemake.command.txt"
grep -F -- '--cores 64' "shared/runs/${analysis_id}/logs/snakemake.command.txt"
grep -F -- '--rerun-incomplete' "shared/runs/${analysis_id}/logs/snakemake.command.txt"
! grep -F -- '--forceall' "shared/runs/${analysis_id}/logs/snakemake.command.txt"
```

2026-07-07 T093 evidence: the old run `manual__PGTA_20260706_162150_00C4FD` was controlled-interrupted and synced to `failed`; resume run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T095201Z` started successfully. At 18:09 CST it was still running `run_pgta_target`; Snakemake command contained `--cores 64 --rerun-incomplete`, unlock command contained `--unlock`, and active rule processes showed `bwa mem -t 16` plus `samtools sort -@ 16`. No `qc/baseline` terminal artifacts existed yet.

### T094 PGT-A resume cleanup for interrupted samtools sort

Use this only after a `baseline_qc` resume failed because interrupted `samtools sort` temporary BAMs already exist, for example:

```text
samtools sort: failed to create temporary file ".../mapping/G11.sorted.bam.tmp.0000.bam": File exists
```

The T094 runner cleans only the current run workdir:

```text
shared/runs/<analysis_id>/mapping/*.sorted.bam.tmp.*.bam
```

It does not delete `*.sorted.bam`, `*.sorted.bam.bai`, FASTQ, QC, logs, config, PGT-A source files, or rawdata. The cleanup log is:

```bash
cat "shared/runs/${analysis_id}/logs/pgta.resume.cleanup.tsv"
```

Before triggering another resume, confirm no matching process is still active:

```bash
docker top airflow-demo-airflow-worker-1 -eo pid,ppid,etime,pcpu,pmem,args \
  | grep -F "$analysis_id" | grep -v grep || true
```

Then call the same resume endpoint:

```bash
curl -fsS -X POST \
  "http://127.0.0.1:8000/api/runs/${analysis_id}/actions/reanalyze" \
  -H 'Content-Type: application/json' \
  -d '{"mode":"resume","reason":"resume after cleaning interrupted samtools sort temp BAMs"}'
```

### T095 PGT-A baseline QC Python library preflight

Use this after a `baseline_qc` run reaches `baseline_bam_uniformity_qc` and fails while importing compiled Python dependencies, for example:

```text
ImportError: /usr/lib/x86_64-linux-gnu/libstdc++.so.6: version `CXXABI_1.3.15' not found
```

The T095 runner keeps the same run-local cache behavior and additionally sets:

```text
XDG_CACHE_HOME=<workdir>/tmp/xdg-cache
MPLCONFIGDIR=<workdir>/tmp/matplotlib
LD_LIBRARY_PATH=${PGTA_CONDA_LIB:-/biosoftware/miniconda/envs/snakemake_env/lib}
LD_PRELOAD=${PGTA_LIBSTDCXX:-/biosoftware/miniconda/envs/snakemake_env/lib/libstdc++.so.6}
```

Before the long Snakemake command, `baseline_qc` runs a short import preflight with `PGTA_PYTHON_BIN`:

```text
matplotlib
numpy
pandas
pysam
scipy
```

The preflight writes:

```bash
cat "shared/runs/${analysis_id}/logs/pgta.python_preflight.log"
```

If the preflight fails, do not resume blindly. Inspect the log and fix the library path/environment first. After deploying T095, confirm there is no matching active process, then call the same `reanalyze` resume endpoint. The new run should still use `--cores 64 --rerun-incomplete` and must not use `--forceall`.

## 14. PGT-A diagnostics smoke

T025/T062 验收不重新运行 PGT-A；复用已有 Airflow DAG run，同步状态并读取日志/产物。

同步成功 run：

```bash
analysis_id=PGTA_20260702_171533_9A85B1
curl -fsS -X POST \
  "http://127.0.0.1:8000/api/runs/${analysis_id}/actions/sync-airflow"
```

验收：

```text
status = success
error_summary = null
```

读取日志和 artifact：

```bash
curl -fsS \
  "http://127.0.0.1:8000/api/runs/${analysis_id}/logs?stream=metadata&tail=3"
curl -fsS \
  "http://127.0.0.1:8000/api/runs/${analysis_id}/logs?stream=stderr&tail=5"
curl -fsS \
  "http://127.0.0.1:8000/api/runs/${analysis_id}/artifacts"
```

同步历史失败 run：

```bash
analysis_id=PGTA_20260702_171200_A68C19
curl -fsS -X POST \
  "http://127.0.0.1:8000/api/runs/${analysis_id}/actions/sync-airflow"
```

验收：

```text
status = failed
error_summary is not null
```

缺失日志验收可以使用未提交 run：

```bash
curl -sS -o /tmp/missing-log.json -w '%{http_code}\n' \
  "http://127.0.0.1:8000/api/runs/PGTA_20260702_162531_74CE91/logs?stream=stdout"
cat /tmp/missing-log.json
```

期望 HTTP 404，错误码为 `LOG_NOT_FOUND`。

## 15. PGT-A Airflow-only Snakemake 9 logger/event smoke

该 smoke 验证 Airflow UI/CLI 直接触发 PGT-A metadata，并通过 Snakemake 9 logger plugin 在 Airflow task log/XCom 中展示状态。默认只写 JSONL；若 DAG conf 传入 `backend_event_url=http://backend:8000/api/events/snakemake`，rule/job 事件会同步 POST 到 FastAPI 并 upsert 到 biodemo `snakemake_rule_event`。

前置检查：

```bash
docker compose -f docker-compose.yaml config --quiet
docker compose -f docker-compose.yaml run --rm --no-deps --entrypoint /biosoftware/miniconda/envs/snakemake9_env/bin/python \
  airflow-scheduler /opt/airflow/dags/tests/test_snakemake_logger_plugin.py -v
PYTHONPATH=/home/jiucheng/project/airflow-demo/dags \
  /biosoftware/miniconda/envs/snakemake9_env/bin/snakemake --help | grep -- --logger-airflow-demo-analysis-id
```

Airflow import 检查：

```bash
docker compose -f docker-compose.yaml run --rm airflow-scheduler airflow dags list-import-errors
docker compose -f docker-compose.yaml run --rm airflow-scheduler airflow dags list | grep bio_pgta_airflow
```

手工创建 manifest 后触发：

```bash
analysis_id=PGTA_AIRFLOW_<YYYYMMDD_HHMMSS>
mkdir -p "shared/runs/${analysis_id}/config"
# 写入 shared/runs/${analysis_id}/config/samples.selected.tsv
chmod -R a+rwX "shared/runs/${analysis_id}"
docker compose -f docker-compose.yaml exec -T airflow-scheduler \
  airflow dags trigger \
  --run-id "manual__${analysis_id}" \
  --conf "$(cat /tmp/${analysis_id}.json)" \
  bio_pgta_airflow
```

在 stdin bash 脚本中连续执行 `docker compose exec` 时，给 exec 命令追加 `</dev/null`，避免 compose/容器进程吞掉后续脚本内容。

可选 backend event smoke：

```bash
analysis_id=<PGTA_CREATED_ANALYSIS_ID>
run_id="manual__${analysis_id}_events"
conf="$(ANALYSIS_ID="$analysis_id" python3 - <<'PY'
import json
import os

aid = os.environ["ANALYSIS_ID"]
print(json.dumps({
    "analysis_id": aid,
    "workdir": f"/data/airflow-demo/runs/{aid}",
    "sample_sheet_path": f"/data/airflow-demo/runs/{aid}/config/samples.selected.tsv",
    "target": "metadata",
    "email_to": None,
    "backend_event_url": "http://backend:8000/api/events/snakemake",
}, separators=(",", ":")))
PY
)"
docker compose -f docker-compose.yaml exec -T airflow-scheduler \
  airflow dags trigger bio_pgta_airflow --run-id "$run_id" --conf "$conf" </dev/null
```

验收：

```text
Airflow dag_run state = success
shared/runs/<analysis_id>/logs/run_metadata.tsv exists
shared/runs/<analysis_id>/logs/events/snakemake_events.jsonl exists and is non-empty
shared/runs/<analysis_id>/logs/events/snakemake_rule_summary.tsv exists and is non-empty
collect_snakemake_events task log includes event count and status counts
collect_snakemake_events XCom includes snakemake_event_summary
if backend_event_url configured: GET /api/runs/<analysis_id>/rules returns rule rows
```

已验证的 fengxian smoke：

```text
analysis_id: PGTA_AIRFLOW_20260703_074844
dag_run_id: manual__PGTA_AIRFLOW_20260703_074844
Airflow state: success
run_metadata.tsv: 11 lines
snakemake_events.jsonl: 22 lines
XCom status_counts: {'info': 15, 'progress': 2, 'running': 2, 'started': 1, 'success': 2}
```

已验证的 T026/T043 backend event smoke：

```text
analysis_id: PGTA_20260703_054712_501D8B
dag_run_id: manual__PGTA_20260703_054712_501D8B_events
Airflow state: success
run_metadata.tsv: 11 lines
snakemake_events.jsonl: 22 lines
snakemake_rule_summary.tsv: 29 lines
GET /api/runs/<analysis_id>/rules: all=success, collect_run_metadata=success
```

## 16. WES mock qsub profile runtime smoke

T042 验收使用 Dockerized `snakemake-runner`，不调用真实 qsub，不修改宿主机 Python 或 `/biosoftware` 环境。

```bash
docker compose -f docker-compose.yaml config --quiet
docker compose -f docker-compose.yaml build snakemake-runner
docker compose -f docker-compose.yaml run --rm snakemake-runner snakemake --version
docker compose -f docker-compose.yaml run --rm snakemake-runner snakemake --help | grep -F cluster-generic
```

运行唯一 WES mock profile run：

```bash
analysis_id="WES_PROFILE_$(date +%Y%m%d_%H%M%S)"
docker compose -f docker-compose.yaml run --rm snakemake-runner \
  snakemake \
  --snakefile pipelines/wes/workflow/Snakefile \
  --configfile pipelines/wes/config/mock_config.yaml \
  --config "analysis_id=${analysis_id}" "workdir=/data/airflow-demo/runs/${analysis_id}" "backend_event_url=null" \
  --profile profiles/qsub
```

验收：

```bash
find "shared/runs/${analysis_id}" -maxdepth 4 -type f | sort
test -s "shared/runs/${analysis_id}/reports/final_summary.tsv"
test -s "shared/runs/${analysis_id}/logs/events/snakemake_events.jsonl"
grep -F qsub_submitted "shared/runs/${analysis_id}/logs/events/snakemake_events.jsonl"
grep -F qsub_success "shared/runs/${analysis_id}/logs/events/snakemake_events.jsonl"
```

2026-07-04 `fengxian` 验收记录：

- official mirror `/home/jiucheng/project/airflow-demo` fast-forward 到 `cd22c90`。
- `docker compose -f docker-compose.yaml config --quiet` 成功。
- `docker compose -f docker-compose.yaml build snakemake-runner` 成功，镜像为 `airflow-demo/snakemake-runner:0.1.0`。
- `docker compose -f docker-compose.yaml run --rm snakemake-runner snakemake --version` 返回 `9.23.1`。
- `snakemake --help` 显示 `cluster-generic` executor 和 `--cluster-generic-submit-cmd`。
- `WES_PROFILE_20260704_230713` 通过 `--profile profiles/qsub` 完成 8 个 WES mock jobs。
- 验收输出：`reports/final_summary.tsv`、`logs/qsub/*.o/e`、`logs/events/snakemake_events.jsonl`。
- JSONL 事件共 14 行，包含 `qsub_submitted` 和 `qsub_success`；真实 `qsub/qstat` 未调用。

## 17. WES Airflow mock qsub smoke

T031 验收使用 Airflow worker 直接运行 WES mock Snakemake + `profiles/qsub` + mock qsub wrapper。它不使用 Docker socket，不调用 standalone `snakemake-runner` 服务，不触发真实 qsub。

前置检查：

```bash
docker compose -f docker-compose.yaml config --quiet
docker compose -f docker-compose.yaml build airflow-worker airflow-scheduler airflow-api-server
docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list-import-errors
docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list | grep bio_wes_qsub
```

触发示例：

```bash
analysis_id="WES_AIRFLOW_$(date +%Y%m%d_%H%M%S)"
cat >"/tmp/${analysis_id}.json" <<JSON
{
  "analysis_id": "${analysis_id}",
  "pipeline": "wes_qsub",
  "mode": "new",
  "workdir": "/data/airflow-demo/runs/${analysis_id}",
  "backend_event_url": null,
  "params": {"target": "final_summary", "max_jobs": 2}
}
JSON
conf="$(cat "/tmp/${analysis_id}.json")"
docker compose -f docker-compose.yaml exec -T airflow-scheduler \
  airflow dags trigger bio_wes_qsub --run-id "manual__${analysis_id}" --conf "$conf"
```

验收：

```bash
docker compose -f docker-compose.yaml exec -T airflow-scheduler \
  airflow dags list-runs -d bio_wes_qsub --output json
find "shared/runs/${analysis_id}" -maxdepth 4 -type f | sort
test -s "shared/runs/${analysis_id}/reports/final_summary.tsv"
test -s "shared/runs/${analysis_id}/logs/events/snakemake_events.jsonl"
grep -F qsub_submitted "shared/runs/${analysis_id}/logs/events/snakemake_events.jsonl"
grep -F qsub_success "shared/runs/${analysis_id}/logs/events/snakemake_events.jsonl"
```

2026-07-05 `fengxian` 验收记录：

- `bio_wes_qsub` run `manual__WES_AIRFLOW_20260705_004506` ended `success`.
- `shared/runs/WES_AIRFLOW_20260705_004506/reports/final_summary.tsv` contains `S001` and `S002` `mock_success`.
- `logs/events/snakemake_events.jsonl` has 14 lines and contains `qsub_submitted` / `qsub_success`.
- `collect_wes_artifacts` XCom returned `event_count=14` and `qsub_log_count=14`.
- Real `qsub/qstat` was not called.

## 18. WES resume/rerun smoke

T044/T056 验收在 `fengxian` 的官方镜像目录执行，服务保持运行，未使用 `down -v` 或 prune。

最小流程：

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"pipeline":"wes_qsub","project_name":"WES mock rerun smoke","target":"final_summary"}'

curl -fsS -X POST http://127.0.0.1:8000/api/runs/<analysis_id>/actions/submit
curl -fsS -X POST http://127.0.0.1:8000/api/runs/<analysis_id>/actions/sync-airflow

curl -fsS -X POST http://127.0.0.1:8000/api/runs/<analysis_id>/actions/reanalyze \
  -H 'Content-Type: application/json' \
  -d '{"mode":"resume"}'

curl -fsS -X POST http://127.0.0.1:8000/api/runs/<analysis_id>/actions/reanalyze \
  -H 'Content-Type: application/json' \
  -d '{"mode":"rerun_rule","rule":"fastp","sample_id":"S001"}'
```

2026-07-05 smoke evidence:

- `analysis_id=WES_20260705_162041_2507AF`
- new DAG run: `manual__WES_20260705_162041_2507AF`, success
- resume DAG run: `manual__WES_20260705_162041_2507AF__resume__20260705T162142Z`, success
- rerun DAG run: `manual__WES_20260705_162041_2507AF__rerun_rule__20260705T162151Z`, success
- `/api/runs/WES_20260705_162041_2507AF/rules` returned 7 rule rows
- `shared/runs/WES_20260705_162041_2507AF/logs/events/snakemake_events.jsonl` has 28 lines
- `shared/runs/WES_20260705_162041_2507AF/logs/snakemake.command.txt` contains `--forcerun fastp` and no `--forceall`

## 19. WES QC smoke

T060/T054 验收在 `fengxian` 的官方镜像目录执行，服务保持运行，未使用 `down -v` 或 prune。

最小流程：

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"pipeline":"wes_qsub","project_name":"WES mock QC smoke","target":"final_summary"}'

curl -fsS -X POST http://127.0.0.1:8000/api/runs/<analysis_id>/actions/submit
curl -fsS -X POST http://127.0.0.1:8000/api/runs/<analysis_id>/actions/sync-airflow
curl -fsS http://127.0.0.1:8000/api/runs/<analysis_id>/qc
curl -fsS http://127.0.0.1:8000/api/runs/<analysis_id>/artifacts
```

2026-07-05 smoke evidence:

- `analysis_id=WES_20260705_164813_C5561C`
- `manual__WES_20260705_164813_C5561C` reached Airflow/backend `success`
- `/api/runs/WES_20260705_164813_C5561C/qc` returned `pass=6`, `warn=0`, `fail=0`, `unknown=0`
- artifacts included `wes_qc_summary` and `wes_final_summary`
- `shared/runs/WES_20260705_164813_C5561C/reports/qc_summary.tsv` exists

## 20. 查看日志

```bash
docker compose logs --tail=200 backend
docker compose logs --tail=200 airflow-scheduler
docker compose logs --tail=200 airflow-worker
```

Run 日志：

```bash
find <SHARED_ROOT>/runs/<analysis_id>/logs -type f | sort
```

## 21. 停止服务

安全停止：

```bash
docker compose down
```

禁止默认使用：

```bash
docker compose down -v
```

除非明确需要删除 volume 且已备份。

## 22. 回滚

```bash
git status
git log --oneline -5
# 使用 git revert 优先于 reset --hard
```

服务回滚：

```bash
docker compose down
git checkout <known-good-commit>
docker compose up -d --build
```

DB migration 回滚必须先确认不会丢数据。

## 21. 常见故障

### Airflow scheduler 起不来

检查：

- Postgres 是否 healthy。
- AIRFLOW_UID 是否正确。
- dags 是否 import error。

### DAG 不出现

检查：

```bash
docker compose exec airflow-scheduler airflow dags list-import-errors
```

### Backend 无法触发 Airflow

检查：

- `AIRFLOW_BASE_URL` 是否是容器内可访问地址。
- Airflow API auth 配置。
- backend logs。

### qsub 提交失败

检查：

- `which qsub`。
- queue 名称。
- qsub 参数是否符合服务器调度系统。
- demo 用户是否有提交权限。

### 前端无法访问 backend

检查：

- 前端构建时 API base URL。

## 22. NIPT Docker template-run smoke

T101 deploys `nipt_docker` as a template-run workflow beside PGT-A. It does not deploy NIPT qsub, WES qsub frontend entry, WGS, or mail notification.

Required `.env` values:

```text
NIPT_PIPELINE_ROOT=/home/jiucheng/pipelines/NIPT
NIPT_CONTAINER_ROOT=/opt/pipelines/NIPT
HOST_SHARED_ROOT=/home/jiucheng/project/airflow-demo/shared
NIPT_DOCKER_IMAGE=172.17.61.235:2333/niptpro/niptpro:1.0.11
NIPT_FETAL_IMAGE=172.17.61.235:2333/niptpro/pytorch:biosan
NIPT_DOCKER_NETWORK=nipt_analysis_test_net
NIPT_DOCKER_CORES=40
NIPT_DOCKER_OWNER=6708:520
NIPT_ALLOW_HEAVY_RUN=false
DOCKER_SOCKET_GID=114
```

## 32. BS10610/BS1069 NIPT-only network gate

The BS NIPT-only deployment root is fixed at:

```text
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-NIPT
```

The Docker network is also a hard constraint:

```text
network=nipt_analysis_test_net
subnet=192.168.199.0/24
gateway=192.168.199.1
```

Do not substitute the general fengxian demo subnet (`172.30.10.0/24`) and do
not let Compose create the network. The BS Compose file must reference it as an
external network:

```yaml
networks:
  nipt_analysis_test_net:
    external: true
    name: nipt_analysis_test_net
```

Run this read-only gate on the selected BS node before rendering or starting
Compose:

```bash
docker network inspect nipt_analysis_test_net \
  --format '{{json .IPAM.Config}}'
```

Acceptance requires an entry containing both:

```text
Subnet=192.168.199.0/24
Gateway=192.168.199.1
```

Also list current attachments and allocated addresses before assigning static
service IPs:

```bash
docker network inspect nipt_analysis_test_net \
  --format '{{range $id, $c := .Containers}}{{$c.Name}} {{$c.IPv4Address}}{{println}}{{end}}'
```

Stop immediately if the network is absent, the IPAM values differ, or a planned
address is already allocated. Do not run `docker network rm`, do not recreate
the network, and do not start with an alternate subnet. BS10610 is the planned
primary and BS1069 is a cold standby; they must not run active intake workers
against the same shared storage at the same time.

The NIPT analysis image must be the validated Snakemake 9 derivative image.
The Snakemake 7 image already present on BS is rollback-only and must not be the
default runtime. See `docs/22_BS_NIPT_DEPLOYMENT.md` for the complete scope and
preflight contract.

The default nginx client allowlist `172.17.61.0/24` does not conflict with the
Docker subnet, but it also does not include the BS host subnet. Include
`172.17.106.0/24` for BS node operations and `127.0.0.1` for local checks. Add
`192.168.199.0/24` only if a live access-log check proves Docker NAT presents
local health requests with that source. Keep a final `deny all` rule.

Only `airflow-worker` should mount `/var/run/docker.sock`. On `fengxian`, the socket is `root:docker` with group id `114`, so the worker must have supplemental group `114`:

```bash
stat -c '%a %u %g %U %G %n' /var/run/docker.sock
docker compose -f docker-compose.yaml exec -T airflow-worker id
```

Expected:

```text
660 0 114 root docker /var/run/docker.sock
uid=1005(default) gid=0(root) groups=0(root),114
```

Build and deploy affected services:

```bash
docker compose -f docker-compose.yaml config --quiet
docker build --target test -f frontend/Dockerfile frontend
docker build -t airflow-demo/backend:t101-test -f backend/Dockerfile backend
docker run --rm airflow-demo/backend:t101-test \
  pytest -q tests/test_nipt_docker_lifecycle.py tests/test_run_creation.py tests/test_run_submit.py tests/test_run_diagnostics.py
docker run --rm --entrypoint /usr/local/bin/python \
  -v /home/jiucheng/project/airflow-demo/dags:/opt/airflow/dags:ro \
  -w /opt/airflow airflow-demo/airflow:0.1.0 \
  -m unittest /opt/airflow/dags/tests/test_bio_nipt_docker_dag.py /opt/airflow/dags/tests/test_nipt_docker_runner.py -v
docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler airflow-api-server frontend
docker compose -f docker-compose.yaml up -d --no-deps --force-recreate \
  backend airflow-api-server airflow-scheduler airflow-worker frontend
```

Create and submit a mount smoke run:

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"pipeline":"nipt_docker","project_name":"T101 NIPT Docker smoke","template_id":"run1","run_mode":"mount_smoke","cores":40,"note":"mount smoke"}'

curl -fsS -X POST "http://127.0.0.1:8000/api/runs/${analysis_id}/actions/submit"
curl -fsS -X POST "http://127.0.0.1:8000/api/runs/${analysis_id}/actions/sync-airflow"
```

Acceptance checks:

```bash
docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list-import-errors
docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list | grep bio_nipt_docker
docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list-runs -d bio_nipt_docker --output table
curl -fsS "http://127.0.0.1:8000/api/runs/${analysis_id}/qc"
curl -fsS "http://127.0.0.1:8000/api/runs/${analysis_id}/logs?stream=stdout&tail=5"
curl -fsS "http://127.0.0.1:8000/api/runs/${analysis_id}/artifacts"
```

Verified T101 run on `fengxian`:

```text
analysis_id: NIPT_20260708_033450_8362A0
dag_run_id: manual__NIPT_20260708_033450_8362A0
Airflow/backend status: success
QC summary: pass=96,warn=0,fail=0,unknown=0
Run list qc_status: pass
stdout: mount_smoke_ok NIPT_20260708_033450_8362A0 260414_TPNB500380AR_1065_AH32CCBGY2
artifacts: nipt_qc_summary, nipt_docker_compose, nipt_run_config, nipt_airflow_request, nipt_docker_command
```

Do not run `full_run` unless the user explicitly approves a heavy NIPT batch and `NIPT_ALLOW_HEAVY_RUN=true` has been intentionally set.

## 23. Airflow + pipeline progress observability smoke

T102 validates the `/api/runs/{analysis_id}/progress` endpoint and frontend progress UI. This smoke does not require a heavy PGT-A `baseline_qc` run or NIPT `full_run`.

Build and deploy:

```bash
docker compose -f docker-compose.yaml config --quiet
docker build --target test -f frontend/Dockerfile frontend
docker build -t airflow-demo/backend:t102-test -f backend/Dockerfile backend
docker run --rm airflow-demo/backend:t102-test \
  pytest -q tests/test_airflow_client.py tests/test_run_progress.py tests/test_snakemake_events_api.py tests/test_nipt_docker_lifecycle.py tests/test_run_diagnostics.py
docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler airflow-api-server frontend
docker compose -f docker-compose.yaml up -d --no-deps --force-recreate \
  backend airflow-api-server airflow-scheduler airflow-worker frontend
```

Runtime checks:

```bash
curl -fsSI http://127.0.0.1:12959/
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS http://127.0.0.1:8000/api/health/airflow
docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list-import-errors
curl -fsS http://127.0.0.1:8000/api/runs/PGTA_20260706_162150_00C4FD/progress
```

Light progress smokes:

- Create and submit one PGT-A `metadata` run from server-path scan, then poll `sync-airflow` and `/progress`.
- Create and submit one NIPT Docker `mount_smoke` run, then poll `sync-airflow` and `/progress`.
- Do not run PGT-A `baseline_qc` or NIPT `full_run` unless explicitly requested.

Verified T102 runs on `fengxian`:

```text
PGTA_20260708_050811_A24E36: success, progress_source=snakemake_events, Airflow tasks present, rule event metadata=success.
NIPT_20260708_050843_B3B05E: success, progress_source=snakemake_events, Airflow tasks present, rule event nipt_mount_smoke=success.
```

## 24. T103 PGT-A/NIPT batch scan and auto intake smoke

T103 supersedes the T101 `run1/run2` NIPT submit path for new demos. Historical
template runs remain readable, but the frontend and acceptance flow use scanned
NIPT chip batches.

Required env additions:

```bash
PGTA_INPUT_SCAN_ROOTS=/data/project/CNV/PGT-A/rawdata
NIPT_INPUT_SCAN_ROOTS=/opt/pipelines/NIPT/fastq
BACKEND_BASE_URL=http://backend:8000
INTAKE_SCAN_PAUSED_ON_CREATION=true
```

Build and deploy:

```bash
docker compose -f docker-compose.yaml config --quiet
docker build --target test -f frontend/Dockerfile frontend
docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler airflow-api-server frontend
docker compose -f docker-compose.yaml up -d --no-deps --force-recreate \
  backend airflow-api-server airflow-scheduler airflow-worker frontend
```

Scan roots and NIPT batch discovery:

```bash
curl -fsS 'http://127.0.0.1:8000/api/input/roots?pipeline=nipt_docker'
curl -fsS -X POST http://127.0.0.1:8000/api/input/scan \
  -H 'Content-Type: application/json' \
  -d '{"pipeline":"nipt_docker","rawdata_root":"/opt/pipelines/NIPT/fastq","max_samples":20}'
```

Create and submit one scanned NIPT mount smoke run using one returned chip
folder. Do not send `template_id`:

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/runs \
  -H 'Content-Type: application/json' \
  -d @/tmp/nipt-scanned-create.json
curl -fsS -X POST "http://127.0.0.1:8000/api/runs/${analysis_id}/actions/submit"
curl -fsS "http://127.0.0.1:8000/api/runs/${analysis_id}/progress"
```

Bootstrap auto intake before unpausing `bio_intake_scan`:

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/intake/scan-and-submit \
  -H 'Content-Type: application/json' \
  -d '{"pipelines":["pgta","nipt_docker"],"bootstrap":true,"max_samples":200}'
curl -fsS 'http://127.0.0.1:8000/api/intake/status?limit=50'
docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list | grep bio_intake_scan
```

Only after bootstrap has recorded historical batches, unpause the scanner if
automatic intake is desired:

```bash
docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags unpause bio_intake_scan
```

Do not run NIPT `full_run` unless the user explicitly approves the heavy batch
and `NIPT_ALLOW_HEAVY_RUN=true` has been intentionally set.

## 25. T104 Dashboard Performance And Intake Config Smoke

T104 makes the Dashboard use backend aggregate APIs and moves intake scanner
configuration into `config/intake.yaml`.

Required config:

```bash
INTAKE_CONFIG_PATH=/app/config/intake.yaml
```

The backend service mounts `./config:/app/config:ro`. Environment scan roots are
fallback only.

Build and deploy:

```bash
docker compose -f docker-compose.yaml config --quiet
docker build --target test -f frontend/Dockerfile frontend
docker build -t airflow-demo/backend:t104-test -f backend/Dockerfile backend
docker run --rm airflow-demo/backend:t104-test \
  pytest -q tests/test_dashboard_service.py tests/test_intake_config.py tests/test_system_resources.py
docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list-import-errors
docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler frontend
docker compose -f docker-compose.yaml up -d --no-deps --force-recreate \
  backend airflow-worker airflow-scheduler frontend
```

Runtime checks:

```bash
curl -fsSI http://127.0.0.1:12959/
curl -fsS 'http://127.0.0.1:8000/api/dashboard/overview?pipeline=all'
curl -fsS 'http://127.0.0.1:8000/api/dashboard/runs?pipeline=all&limit=10&offset=0'
curl -fsS 'http://127.0.0.1:8000/api/system/resources'
curl -fsS 'http://127.0.0.1:8000/api/intake/config'
```

Dashboard acceptance:

- First screen uses `/api/dashboard/overview`, `/api/dashboard/runs`,
  `/api/intake/status`, and `/api/system/resources`.
- Run Tracker default page size is 10.
- Intake observed/bootstrap rows do not display as queued execution.
- Do not unpause `bio_intake_scan` during T104 acceptance.
- Do not run NIPT `full_run` during T104 acceptance.
- CORS 配置。
- host port 映射。

## 26. T105 Intake Scanner Settings Console Smoke

T105 adds a read-only Settings surface for automatic intake readiness. It does
not unpause `bio_intake_scan`, does not call `/api/intake/scan-and-submit` from
the frontend, and does not run NIPT `full_run`.

Build and deploy:

```bash
docker compose -f docker-compose.yaml config --quiet
docker build -t airflow-demo/backend:t105-test -f backend/Dockerfile backend
docker run --rm airflow-demo/backend:t105-test \
  pytest -q tests/test_airflow_client.py tests/test_intake_config.py
docker build --target test -f frontend/Dockerfile frontend
docker compose -f docker-compose.yaml build backend frontend
docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend frontend
```

Runtime checks:

```bash
curl -fsSI http://127.0.0.1:12959/
curl -fsS http://127.0.0.1:8000/api/intake/config
curl -fsS 'http://127.0.0.1:8000/api/intake/status?limit=20'
curl -fsS http://127.0.0.1:8000/api/intake/scanner-state
docker compose -f docker-compose.yaml exec -T airflow-scheduler \
  airflow dags list | grep bio_intake_scan
```

Acceptance:

- `/api/intake/scanner-state` returns `airflow_reachable`, `is_paused`, latest
  scanner DAG run fields, and a degraded payload instead of failing the page if
  Airflow is temporarily unavailable.
- `/settings` shows intake config source, PGT-A/NIPT roots, bootstrap observed
  discovery rows, and the `bio_intake_scan` paused state.
- The Settings page only offers refresh/navigation actions; no unpause,
  scan-now, or full-run action is present.
- Confirm `bio_intake_scan` remains paused unless the user separately approves
  enabling automatic intake.

## 27. T106 Intake Dry-run Preview And Auto-submit Gate Smoke

T106 adds a read-only preview endpoint and makes automatic intake submit obey
`config/intake.yaml` gates. The default deployed config keeps automatic
create+submit disabled.

Build and test:

```bash
docker compose -f docker-compose.yaml config --quiet
docker build -t airflow-demo/backend:t106-test -f backend/Dockerfile backend
docker run --rm airflow-demo/backend:t106-test \
  pytest -q tests/test_intake_service.py tests/test_intake_config.py
docker build --target test -f frontend/Dockerfile frontend
docker compose -f docker-compose.yaml build backend frontend
docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend frontend
```

Runtime checks:

```bash
curl -fsSI http://127.0.0.1:12959/
curl -fsS http://127.0.0.1:8000/api/intake/config
curl -fsS -X POST http://127.0.0.1:8000/api/intake/scan-preview \
  -H 'Content-Type: application/json' \
  -d '{"pipelines":["pgta","nipt_docker"],"max_samples":20}'
curl -fsS 'http://127.0.0.1:8000/api/intake/status?limit=20'
curl -fsS 'http://127.0.0.1:8000/api/runs?pipeline=nipt_docker&limit=5&offset=0'
docker compose -f docker-compose.yaml exec -T airflow-scheduler \
  airflow dags list | grep bio_intake_scan
```

Acceptance:

- `/api/intake/scan-preview` returns `summary` and per-batch dry-run rows.
- Preview does not create discovery rows, analysis runs, or Airflow DAG runs.
- `/api/intake/config` shows `defaults.auto_submit=false` and pipeline
  `auto_submit.enabled=false` for PGT-A and NIPT Docker by default.
- `/settings` shows the dry-run preview and blocked-by-config reasons.
- `bio_intake_scan` remains paused unless the user separately approves T107.

Before any future unpause:

1. Review `/settings` Intake Scanner and preview results.
2. Confirm historical records are `Bootstrap observed` or otherwise protected.
3. Confirm `NIPT_ALLOW_HEAVY_RUN=false` unless a supervised heavy run window is
   explicitly approved.
4. Change `config/intake.yaml` auto-submit gates only in a separate reviewed
   task.
5. Unpause `bio_intake_scan` only in a separate T107 rollout with before/after
  run-count checks.

## 30. T112 PGT-A Snakemake 9 release and validation

Deploy the sample-free release without modifying the original PGT-A directory:

```bash
scripts/deploy_pgta_s9_release.sh pipelines/pgta_s9 \
  /home/jiucheng/pipelines/PGT_A_S9 pgta-s9-v1.4
cd /home/jiucheng/pipelines/PGT_A_S9/releases/pgta-s9-v1.4
sha256sum -c SHA256SUMS
```

Apply both schema layers before creating a run:

```bash
docker compose run --rm --user 50000:0 airflow-init
docker exec airflow-demo-backend-1 alembic upgrade head
```

Acceptance order: Snakemake 9 dry-run/logger tests; two-sample 1M-pair hidden
validation profile; one full-sample manual Submit; one two-sample manifest plus
READY automatic Submit; rule terminal-event, QC, logs, timing, and idempotency
checks. Only after all gates pass may PGT-A auto-submit and `bio_intake_scan` be
enabled. Keep NIPT auto-submit and `NIPT_ALLOW_HEAVY_RUN` disabled.

Runtime checks for the approved profile must include:

```bash
/biosoftware/miniconda/envs/snakemake9_env/bin/snakemake --version
/biosoftware/miniconda/envs/wise_env/bin/Rscript --version
/biosoftware/miniconda/envs/wise_env/bin/WisecondorX predict -h
```

The resolved run config must contain the locked CBS seed. The worker subprocess
environment must resolve `Rscript` from the approved WisecondorX environment,
and each QC-passing sample must produce a non-empty prediction statistics file.

Rollback pauses intake, disables PGT-A auto-submit, selects the previous
release/Profile, and recreates services. Never delete historical runs, the
original PGT-A source, or Docker volumes.

## 31. T120 NIPT YAML request intake

Create the host directories without placing a final request in the inbox:

```bash
mkdir -p /home/jiucheng/project/airflow-intake-requests/nipt/.archive
mkdir -p /home/jiucheng/project/airflow-intack-configs/nipt
```

Edit a request under the config workspace. Publish it atomically only after
review:

```bash
src=/home/jiucheng/project/airflow-intack-configs/nipt/project-20260713.nipt.yaml
inbox=/home/jiucheng/project/airflow-intake-requests/nipt
cp "$src" "$inbox/project-20260713.nipt.yaml.partial"
mv "$inbox/project-20260713.nipt.yaml.partial" "$inbox/project-20260713.nipt.yaml"
```

The YAML uses `batch_id`; do not write an absolute FASTQ path. `samples` may be
`all` or a list. `submit: true` is an explicit full-analysis authorization.
Backend policy and `NIPT_ALLOW_HEAVY_RUN` are checked again before creation.

Safe rollout checks:

```bash
find /home/jiucheng/project/airflow-intake-requests/nipt -maxdepth 1 -type f -printf '%f\n'
docker compose -f docker-compose.yaml config --quiet
docker compose -f docker-compose.yaml build backend
docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend
curl -fsS http://127.0.0.1:8000/api/intake/config
curl -fsS 'http://127.0.0.1:8000/api/intake/status?pipeline=nipt_docker&lifecycle=all&limit=20'
```

An empty first command is required during deployment acceptance. Do not publish
a `submit: true` request merely to smoke-test the parser. Parser and gate tests
run inside the backend test image. Rollback removes the request-inbox mount and
restores the prior intake config; it does not delete Discovery rows, runs,
FASTQ, results, logs, or Docker volumes.

Before enabling or recreating automatic intake, generate a random
`INTERNAL_SERVICE_TOKEN` in the untracked `.env`. Compose requires it and passes
the value only to backend and Airflow services. Verify an unauthenticated event
POST returns HTTP 401 and that a worker-authenticated missing-run probe reaches
HTTP 404 without writing an event.

The PGT-A profile must pin `release_manifest` and
`release_manifest_sha256`. Run profile availability validation inside the
worker after deployment; it checks the manifest hash and every listed release
file. Never repair a mismatch in place. Deploy a new immutable revision and
update the profile instead.
# T123 rollout and rollback

1. Confirm `/api/dashboard/runs?status=active` is empty before recreating an
   Airflow worker.
2. Back up the `bio_intake_scan` DAG-run inventory and record its pause state.
3. Run backend pytest, Intake DAG tests, frontend test/build, and
   `docker compose config --quiet` on `fengxian`.
4. Rebuild backend, Airflow API/scheduler/worker, and frontend without deleting
   volumes. Restore the scanner pause state.
5. Sync failed runs so stale running rules become canceled while true failed
   sample/rules remain failed and selectable.
6. Run a supervised 32-core NIPT clone only when no analysis is active.
7. Confirm the scanner task tree ends with `propagate_scanner_result`; a failed
   `scan_and_submit` must leave the DAG run failed even if retention succeeds.

T123 acceptance baseline: `NIPT_20260713_162606_5B5B11` completed the
20-sample Full workflow with 20/20 sample QC pass and 176/176 rule events
success. The failed 40-core audit run remains retained and must not be used as
an ETA baseline.

Rollback: restore prior images and profile defaults. Preserve DB rows, FASTQ,
workdirs, logs, results, and Docker volumes. Retention must reject analysis DAGs.

## 33. T126 BS10610 NIPT-only rollout

Use `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-NIPT` for all deployment
writes. Validate the external network with `scripts/bs_nipt_preflight.sh`; do
not create or modify `nipt_analysis_test_net`.

Image transfer is always two independent hops:

```text
fengxian -> D:\pipeline\t126-image-stage -> BS10610 or BS1069
```

Verify SHA256 after each hop. Load `niptpro:1.1.11` without removing or
retagging `1.0.11`. Render the standalone stack before startup:

```bash
docker compose --env-file env/bs10610.env \
  -f current/docker-compose.bs-nipt.yaml config --quiet
```

Initialize fresh databases only on BS10610, create `nipt_s9_full` with one
slot, and keep `bio_intake_scan` paused. Never initialize or start the BS1069
cold standby during ordinary deployment.

T126 acceptance evidence is under `backups/T126-20260714`. The 10-sample run
`NIPT_20260714_133355_B3081A` and 72-sample run
`NIPT_20260714_140419_F999B0` are successful. The latter completed in 923
seconds with 72/72 QC pass, 592/592 terminal-success events, 42.86 GiB peak
memory, complete mapping/CNV/T21/fetal-fraction/summary outputs, and identical
before/after SHA256 for 144 input FASTQ files.

Rollback: pause intake, set `NIPT_ALLOW_HEAVY_RUN=false`, stop Compose without
`-v`, and select the retained `1.0.11` profile. Do not delete the external
network, Docker volumes, workdirs, logs, results, FASTQ, or image archives.

## 34. T127 BS10610 shared NIPT/WGS control plane

T127 upgrades the existing Compose project `airflow-nipt` in place. Do not
start a second `airflow-wgs` Compose project. Preserve the existing PostgreSQL
and Redis volumes and expose only `12959` (frontend/API gateway) and `12958`
(Airflow through nginx).

1. Confirm no running/submitted/queued analysis and record the paused scanner.
2. Back up Airflow and biodemo with `pg_dump -Fc`, API inventories, network
   inspect output, the untracked env, and SHA256.
3. Verify `nipt_analysis_test_net` remains `192.168.199.0/24`, gateway
   `192.168.199.1`.
4. Build images on fengxian, download them to local Windows, then upload them
   to the shared BS archive path. Never copy images server-to-server.
5. Install WGS Snakemake 9 and immutable releases below
   `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`.
6. Install a forced SSH key using `authorized_keys2` when the administrator
   has intentionally marked `authorized_keys` immutable. The command must be
   exactly `wgs-run <analysis_id> <stage>`.
7. Run Compose config, migrations, and Airflow init; create
   `bs_heavy_analysis` with one slot.
8. Recreate backend, Airflow API/scheduler/worker, and frontend only. Never use
   `down -v` and never recreate PostgreSQL/Redis volumes.
9. Verify capabilities contain only `nipt_docker,wgs`, DAG inventory contains
   only `bio_nipt_docker,bio_wgs,bio_intake_scan`, and the scanner stays paused.
10. Run the one-family WGS Snakemake 9 dry-run at a 96-core ceiling with
    `WGS_ALLOW_EXECUTION=false` in backend, scheduler, worker, and host env.
    Require the Airflow DAG to finish success and every graph-only job to be a
    terminal skipped dry-run event. Then run the selected NIPT full batches
    serially, stopping at the first failure.

WGS results are stored under
`/mnt/biodevrwbi/33.chenjiucheng/airflow-result/wgs/runs`; NIPT results remain
under `/mnt/biodevrwbi/33.chenjiucheng/airflow-result/nipt/runs`.

T127 acceptance used three 27-sample NIPT batches. Each completed with all
sample QC decisions passing and all 232 persisted rule events in success.
`WGS_20260715_062217_351C76` completed an Airflow-managed pre-calling dry-run
in 12 seconds; its 21 graph jobs are planned/skipped and no WGS rule executed.
The older deliberately stopped `WGS_20260714_180953_9D7981` remains a failed
historical handoff record and must not be used as current acceptance evidence.

## 35. T128 BS NIPT manual scan latency repair

The BS FASTQ mount remains read-only and unchanged:

```text
/sugon01/fq_backup/NIPT_fq_backup -> /data/nipt-fastq:ro
```

Only the approved discovery root is narrowed:

```text
NIPT_INPUT_SCAN_ROOTS=/data/nipt-fastq/FQ2026
```

Do not pass the host path `/sugon01/...` to the API. Verify the backend root
and run a read-only bounded scan before opening Submit Run:

```bash
curl -fsS http://127.0.0.1:12959/api/input/roots?pipeline=nipt_docker
curl -fsS -X POST http://127.0.0.1:12959/api/input/scan \
  -H 'Content-Type: application/json' \
  -d '{"pipeline":"nipt_docker","rawdata_root":"/data/nipt-fastq/FQ2026","max_samples":20}'
```

The scan must return candidate samples before the 60-second nginx timeout.
This is a discovery-only acceptance: do not click Create/Submit, do not
unpause `bio_intake_scan`, and do not move or delete FASTQ. Roll back by
restoring the T127 backend/frontend images and release pointer without touching
PostgreSQL, Redis, results, volumes, or `nipt_analysis_test_net`.
## WGS-only Phase 1 release

Use `docker-compose.wgs.yaml` with an untracked `.env.wgs` and keep `WGS_EXECUTION_ENABLED=false`. Publish only nginx; do not mount Docker socket, kubeconfig, SSH keys, or OBS credentials. Verify migration, login/RBAC, WGS-only capabilities, paused DAGs, and explicit submit denial before switching `current`.

On BS10610 the daemon default address pool is exhausted, so this profile reuses the approved existing `nipt_analysis_test_net` as an external application network without recreating or altering it. The deployed Airflow image requires `AIRFLOW_UID=50000`.

Before every WGS Compose `up` or service recreate, run:

```bash
python3 scripts/check_wgs_docker_network.py
docker network inspect nipt_analysis_test_net
```

The preflight must report exactly subnet `192.168.199.0/24`, gateway
`192.168.199.1`, unique in-range attachments, and network name
`nipt_analysis_test_net`. A mismatch is a hard stop; do not recreate, delete,
or repair the shared network automatically. Only `frontend-nginx` may publish a
port, bound exactly to `172.17.106.10:12959`. PostgreSQL, Redis, backend,
observer, and Airflow remain internal-only. Record attachments before and after
recreate; Docker-assigned service IPs may change within the fixed subnet, so
service communication must use Compose DNS names rather than hard-coded
container IPs.
# T131: Apply biodemo migration non-destructively; recreate application
# services without volumes. Keep both gates false, all WGS DAGs paused, fixed
# network `192.168.199.0/24`, and only frontend `172.17.106.10:12959` published.
