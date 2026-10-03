# Run Detail / Batch Runs 加载诊断与最小修复建议

- 任务：PERF-RUN-PAGES-20261001。
- 授权：排查原因并提出方案；本轮不修改产品代码、部署、重启服务或触发分析。
- 产品基线：AF `80abdfceea0d604e6524375e2b1a2aa32022ee65`；审查 worktree HEAD `d14e567`，其后仅文档变化，前后端源码与产品基线一致。
- 范围：两个页面的首屏请求、对应后端投影及刷新逻辑。不扩展到流程执行、旧批次恢复、QC 阈值、SFS 图表或平台重构。

## 1. 结论与证据边界

存在真实的读路径效率问题，不是简单的 Loading 文案问题，也不能归因为 SSH 握手或 Master 镜像。列表把完整 QC 计算放进每个批次的摘要读取；详情把维护动作的重校验放进首屏。前端缺少请求截止和取消机制，会放大慢接口的影响。

当前生产列表请求实测 HTTP 200 / **2.278 秒**，TTFB 2.278 秒，20 行 / 总计 27 行，86,103 bytes。这次等待主要发生在服务端返回首字节前，不是响应体传输。历史 GATK 基础详情和 workspace 本轮分别为 **0.483 秒 / 0.124 秒**，未复现持续长时间 Loading。

用户补充：任意批次略慢，主要从 Batch Runs 点进详情特别慢，GATK 更明显。因此优先关注 GATK 详情入口与前端请求链，而不是只修 WGS QC。尚未取得用户浏览器的 Network waterfall，不能断言已复现截图里全部等待时长，更不能将列表 2.278 秒全部归于某一个函数。

2026-09-29 的架构报告 §15–19 已指出部分相同问题。本次重新核对当前部署源码后确认它们仍存在；不把旧报告的计时当成本次结果，也不重开已完成的公共执行器和镜像发布验收。

## 2. 生产核验与计时

唯一生产检查者为既定 Airflow owner；协调者及两个前后端 reviewer 只读取本地源码和诊断证据。BS96 实际 hostname `server96`；实际控制目录为 `/data/airflow-WGS/unified089-wgs423-0afd253-20261001-control`。backend `7aadaf93`、frontend `4df1c67c` 的 image、实际挂载以及相关 11 个源码文件、前端三项构建资源均匹配最终发布记录。旧 `current` 链接并非实际选中源码的充分依据。

鉴权开启；WGS/GATK 执行入口开启，扫描开启、有效自动提交关闭，watermark 未动。

| 2026-10-01 UTC | 请求/通道 | HTTP | 首字节 | 完整响应 | 说明 |
|---|---|---:|---:|---:|---|
| 15:45:54 | 正式网关 `/api/health`，host 无内部头 | 200 | 0.007s | 0.007s | 服务存活对照 |
| 15:45:54 | 已鉴权 backend 内部 `/api/health` | 200 | 0.011s | 0.011s | 内部通道对照 |
| 15:45:54 | 已鉴权 backend 内部 `/api/runs?pipeline=deployed&sort=created_desc&limit=20&offset=0` | 200 | 2.278s | 2.278s | 正常默认页，17 success / 2 cancelled / 1 failed |
| 15:47:20 | 已鉴权 backend 内部，历史 GATK base detail | 200 | 0.483s | 0.483s | 2,200 bytes，success / 43 samples |
| 15:47:20 | 同一 GATK `/workspace` | 200 | 0.124s | 0.124s | 6,029 bytes，562 rules |
| 15:47:21 | 同一 GATK `/samples` | 200 | 0.014s | 0.014s | 5,773 bytes，43 rows |
| 15:50:35 | 内部 `/api/runs?pipeline=gatk&sort=created_desc&limit=20&offset=0` | 200 | 0.063s | 0.063s | GATK 过滤页，6 success / 共 6 行，20,475 bytes |
| 15:50:35 | 内部 `/api/platform/capabilities` | 200 | 0.005s | 0.005s | 两个已部署流程 |

详情采样对象为既有终态 `GATK_20260929_024231_F246CD`。先请求基础详情可能使后续 workspace 的文件缓存变暖，不能将二者差值当作函数成本或宣称冷首屏只需 0.124 秒。

这些是少量顺序采样，不是压测、冷缓存基准或 p95。内部 token 通道在 `main.py:185–189` 返回内部身份，**绕过了浏览器 session DB 验证**；不包含用户到网关的网络、cookie 认证及渲染时间。最初从容器带内部头访问外层网关得到 403，已保留原始结果；它不是页面响应计时，也不能据此宣称用户被白名单阻止。未为诊断更改鉴权/白名单。

15:47:23Z 的单次 stats 为 backend CPU 0.16% / 565.4 MiB，nginx CPU 0% / 108.8 MiB；有限 5 分钟日志中没有 5xx/已识别异常类。它们没有提供 CPU/内存饱和的当时证据，但不能排除间歇阻塞。认证中间件的同步 session 查询可能受连接等待影响，尚无生产证据，不据此盲改池大小、worker 数或 DB 配置。

只读核对现有 nginx access format 不包含 `request_time` / `upstream_response_time`，无法从旧访问日志还原用户那次耗时；本轮没有改日志配置。GATK 过滤页、capabilities 这次较快，说明不能把 GATK 较慢笼统解释为“样本多/计算重”；混合列表与 GATK 详情应分开定位。

原始证据位于 AF owner worktree `.codex-artifacts/perf-run-pages-20261001/`；仅记录端点、状态、耗时、字节数及非临床摘要，不保存凭据或完整患者响应。

## 3. 首屏实际依赖

| 页面 | 正常请求链 | 主体何时出现 |
|---|---|---|
| Batch Runs | 冷启动先 `/auth/me`，随后 capabilities 和单个 `/runs?limit=20` 并行 | 列表 GET 完成 |
| Run Detail | 冷启动 `/auth/me` → capabilities → `/workspace` → 当前标签页数据 | **workspace 200 后立即写入 detail；不必等 samples** |

已登录页面内跳转通常复用两个 provider。正常详情并不等待所有标签页；只有 workspace 返回 404 时，兼容分支才通过六个 GET 的 `Promise.all` 等待完整结果。生产是否命中 404 必须看实际状态，不能将此兼容分支当作正常路径。

源码锚点以 AF 产品 worktree 为准：`frontend/src/pages/RunsPage.tsx:42`、`RunDetailPage.tsx:107,123,144,197,242,294`、`App.tsx:24`。

## 4. 已确认的问题

### P1：列表摘要调用完整 QC，重复查询和文件 I/O

`run_service.py:62–97` 已先 SQL 分页并批量读样本，不是全表读取后分页，也没有前端逐行 GET。但 `pipeline_registry_service.py:220` 对每个 WGS run 调 `wgs_sample_projection.get_wgs_batch_qc_status:99`，再次查询 selected samples，并调用完整 `_read_qc:207`。

完整路径读取 QCstat、manifest/config、每样本 multiQC，补 SNV/CNV 计数、计算 SHA 和逐项 judgments；列表最终却只使用 QCstat 的“是否通过质控”状态。成功历史批次同样执行。variant 计数已有 path/size/mtime LRU，不能声称每轮必扫全部 variant；其他重复读取和完整投影仍存在。

另有 `qc_highlights.py:11–29`：指标配置为空时仍读取页内全部 QcMetric，最终没有展示收益。单批 QC 文件异常也应在投影边界隔离，避免整页失败；不得将缺失或异常伪装成 pass。

### P1：详情摘要与动作前检查混在一个请求中

`main.py:1951–1952` 的 workspace 先完整调用 `run_detail()`，再新开 session 读取同一 run 的 workspace；不是单一事务快照。WGS workspace 再完整计算 QC。

GATK 成功终态的 `gatk_step7_service.capability:145` 仍执行 `_check` 和 `_snapshot_files:109`，遍历 bundle 并读取/哈希冻结文件与 `.py/.sh`，只是为了首屏清理能力展示。真正 POST 的严格校验有必要，但不应每次普通详情/轮询都承担相同成本。

### P1：GET 不完全只读

`wgs_execution_dispatch_service.py:159–180` 在 dispatch 不存在时创建记录并 commit，没有终态 guard。这是确定的 GET 副作用；可能造成首次并发读竞争，但本次没有 DB 等待证据，不能宣称它已导致慢请求。为避免诊断本身改变业务数据，本轮不调用不能证明已有 dispatch 的 WGS detail/workspace。

native-view 另有 `wgs_onprem_views.py:247–330` 持 run 行锁进行文件读取并可能更新 QC 摘要。这只适用于 native monitor 分支，不泛化到普通 CCE 页面；保留为相关只读接口收敛项，不列为截图已证实根因。

### P1：前端慢请求没有截止/取消

`api.ts:1194` 等待 fetch 和完整 body，没有应用层 deadline/signal。`useSilentRefresh.ts:36` 在 key 改变后仍等待旧 pending；卸载只取消 timer，不取消请求。因此旧请求长期不结束时，新筛选/路由也被拖住。

已有 single-flight、路由响应隔离和失败退避应保留。已返回的 HTTP/解析错误会结束 Loading；不能泛称错误被吞。GET 的网络重试现为一次，不是无限重试。

### P2：详情刷新粒度过大

首次 detail.attempt 从 undefined 变为值会改变刷新 key，可能再触发 workspace + samples；通常发生在主体已经显示后，不是必然首屏阻塞。Overview 默认获取全部 samples，实际主要需要数量及 manifest 摘要；切换标签、规则筛选等又带着 workspace 重读。需要用受控 promise 验证次数，不能直接宣称无限循环。

## 5. 建议按三个小改动落地

按用户补充，PERF-02 的 GATK 首屏与 PERF-03 优先，并与独立的 PERF-01 轻摘要改动并行；以下编号是改动边界，不要求先做完 WGS 才处理 GATK。

| 顺序/责任 | 最小改动 | 不做什么 |
|---|---|---|
| PERF-01 / Backend | 共享 QC status-only 投影；页内 selected samples 批量读取/复用；空 highlights 配置提前返回。列表/workspace 仅需 source overall 状态时不调用全指标解析。 | 不新建 QC 系统、DB 表、缓存服务或第二套 observer；不改变 QC2 阈值/来源语义。 |
| PERF-02 / Backend + Frontend | workspace 直接共用 session 的基础详情与摘要，不前置完整重投影；清理等重 capability 改按需加载，真正 POST 仍严格重验。移除 GET 初始化 dispatch，放回既有创建/prepare/显式确认路径，历史缺失只读返回 unavailable。 | 不移除动作安全检查，不为了性能声称可执行，不直接修写历史生产 DB。native-view 仅在对应路径纳入时单独最小处理。 |
| PERF-03 / Frontend | 公共 GET 支持 deadline/AbortSignal，key 变化或卸载取消旧 GET；summary 与当前 tab 独立刷新；修正 attempt 自触发、Overview 重样本加载。后台错误保留已显示数据和更新时间。 | 不增加轮询频率，不对 mutation 自动重试，不把所有页面合并为巨型接口，不仅靠延长超时。 |

PERF-01 的轻投影仅需精确 QCstat 的 `Sample_ID`、`Name`、`是否通过质控`，共享原状态解析及样本匹配顺序（sample_id → metadata.data_id → 去 `-WGS` → 既有存储状态/unknown）。保持 selected scope、绑定根路径、安全路径选择、缺失语义和重复标识处理。完整 Samples/QC 继续使用原判定器，不能把来源汇总通过等同于逐项判断通过。

第一步不必引入跨请求缓存：从每批多文件、多指标计算缩为一个精确小 QCstat + 页内一次样本查询后先测量。若剩余文件 I/O 仍是瓶颈，再复用现有 observer 的摘要或引入有界版本缓存；键必须覆盖 binding/attempt/path/file identity，不能把终态永久缓存成 success。

客户端截止只保证 UI 可恢复，不能取消已进入服务端的阻塞文件 I/O；后端轻量化必须一起处理。重 capability 暂未加载/不可达时按钮保持不可执行，不能默认 available。

## 6. 最小验证与验收边界

在 BS10610 使用现有 synthetic fixture，复用已有通过的测试，仅补改动边界：

1. 原 QC status 与轻投影差分一致，覆盖状态、别名、selected subset、缺失/fallback；spy 断言摘要不调用 full metrics/multiQC/variant，样本查询一次。
2. workspace/普通列表 GET 不创建 dispatch 或提交业务写；保留现有动作 POST 身份、锁、终态拒绝用例。无需重跑全部 P0。
3. workspace 已返回而 samples 仍 pending 时主体出现；首次 attempt 不重复读取 workspace；旧请求挂起后切换能取消并立即查询当前 scope，晚响应不污染。
4. deadline 后 Loading 结束并可重试；后台失败不抹掉旧结果，非当前标签不请求，mutation/abort 不自动重试。
5. 相同固定 20 条混合列表及 WGS/GATK 终态详情少量前后对比，分别记录首字节、总时间和首屏请求数。不要从一个采样计算 p95，不启动临床批次或完整流程。

建议性能目标（不是已经达到的指标）：测试固定数据下首屏摘要 API <1s；用户网络与首次登录耗时另列。补一次实际浏览器从列表进入 GATK 的瀑布图，记录请求排队、TTFB、capabilities/auth 依赖和 workspace 200/404；只保留去标识化计时，不导出带 cookie/token/患者响应的 HAR。若浏览器 workspace 长等待而同一时刻内部路径快，先定位鉴权/网关/客户端链，不继续扩大 QC 修复来猜根因。

生产部署需要后续明确批准，仅更新批准的前后端，不重启 Airflow/云分析，不改新发布的 native 包/镜像组合。

本轮不运行 Python/React runtime 测试：没有实现改动，本地只做源码、路径及文档检查。当前任务交付是诊断与方案，不是性能修复已完成。
