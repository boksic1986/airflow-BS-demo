# WGS `hanjj`运行身份与目录迁移设计

更新时间：2026-09-02

## 2026-09-03 implementation status

T171 implemented the request-v4 and runtime identity design on the `.96`
production control plane. The active node200 identity is `hanjj`; the restricted
runner, WGS 4.1.1 repository mapping, kubeconfig/kubectl, CCE config, evidence
root and transparent obsutil progress wrapper passed read-only preflight.
`bio_wgs` is unpaused and the two manual execution gates are enabled, while
scanner auto-dispatch and the historical draft-preview gate remain disabled.
No batch was submitted during activation; AnalysisRun, RunAttempt and DagRun
counts remained zero. Sections describing the earlier design-only or disabled
state are retained as history.

## 1. 目标和现状

本设计将 BS10610 Airflow 到 node200 的生产运行身份从`chenjc`整体替换为
`hanjj`，同时把新任务的控制面和 WGS 分析写入迁到`14.hanjingjing`共享空间。
迁移不改变 WGS 4.1.1 源码、唯一`bio_wgs` DAG、Step1-Step6业务顺序、公开提交
参数、数据库业务模型或固定 Docker 网络。

只读审计确认：

- 新 RSA key 的指纹为
  `SHA256:CQsyQXQUr+WqooGabSzek0BtlxQIA6DtJYkrzQ/3EHE`，远端实际账号名是
  `hanjj`，不是`hanjingjing`。
- 该身份可登录`172.17.61.96`、`172.17.61.97`和`172.17.61.200`，三台
  主机的`/proc`均可读。
- node200上的`/home/hanjj/.obsutilconfig`已存在且可读，
  `/bi/software/mamba/envs/WGS/bin/cce-pipeline`可执行。
- `hanjj`尚无可用的`~/.kube/config`和`~/.local/bin/kubectl`。
- 旧 runtime 对`hanjj`只读；`/sg2/14.hanjingjing/Cloud_WGS_Clinical`由
  `hanjj:bioinfo`所有并可写。
- 目标`WGS_Clinical`和`airflow-wgs/runtime`子目录尚未创建。

当前线上仍使用`chenjc`身份和旧 runtime。本轮设计固化不复制私钥、不创建目录、
不修改node200配置、不切换Compose，也不启动WGS、OBS或CCE操作。

## 2. 选择的架构

### 2.1 方案比较

1. **直接替换SSH用户名但继续使用旧runtime：不采用。** `hanjj`无法写旧目录，
   强行放宽旧目录还会继续混用两个用户的运行证据。
2. **把控制文件和分析结果全部放入`WGS_Clinical`：不采用。** request、PID、状态、
   checkpoint和证据会污染业务交付目录，Step5/Step7边界也更难审核。
3. **控制面与分析面分离：采用。** 两者都位于`14.hanjingjing`空间，但使用互不
   重叠的白名单根；浏览器和DAG均不能传入任意路径。

### 2.2 固定目录

```text
分析项目根（也是WGS的`--outpath`）:
/sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical

批次结果:
/sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical/<batch>

Airflow控制根:
/sg2/14.hanjingjing/Cloud_WGS_Clinical/airflow-wgs/runtime

控制根下:
runner-requests/
runs/<analysis_id>/attempt-<n>/
bindings/
transfer-progress/
platform-metrics/
maintenance/
```

BS10610和node200均已观察到`/sg2`共享视图，因此新配置优先在两端使用同一绝对
路径，不再维护`/mnt/...33.chenjiucheng`与`/sg2/...33.chenjiucheng`双重映射。
部署前仍必须从backend容器和`hanjj@node200`各写入一个无临床信息的随机marker，
互相读取并核对inode/内容，随后删除marker；探测失败即停止迁移。

目录由`hanjj`创建，group固定为`bioinfo`（GID 520），控制根为`2770`目录。
Compose中真正写控制根的服务必须显式获得GID 520；其他服务只读或不挂载。

### 2.3 请求和冻结binding

公开`POST /api/wgs/runs`保持不接受路径。内部请求升级为
`wgs-runtime.request.v4`，将现有含混的`node200_workdir`拆为：

```text
control_workdir
analysis_project_root
expected_batch_root
```

- `control_workdir`只能由控制根、analysis ID和attempt服务端派生。
- `analysis_project_root`固定为
  `/sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical`。
- `expected_batch_root`固定为`<analysis_project_root>/<batch>`。
- prepare继续调用固定WGS仓库，但`--outpath`直接使用分析项目根。
- prepare成功后，冻结binding记录三个路径、WGS release、run ID、CCE identity、
  OBS prefix和evidence位置。Step1-Step7以后只消费binding，不重新解析仓库或请求路径。
- 同一batch只允许一个活动attempt。resume复用原batch和binding；创建新分析或参数
  改变时若目标batch已存在，进入`needs_review`，不得覆盖。

## 3. 身份和配置边界

### 3.1 BS10610 SSH身份

新私钥安装到release之外的受保护目录，例如：

```text
/home/chenjc/.config/airflow-wgs/ssh-hanjj/id_rsa
/home/chenjc/.config/airflow-wgs/ssh-hanjj/config
/home/chenjc/.config/airflow-wgs/ssh-hanjj/known_hosts
```

- 私钥owner固定为Airflow UID 50000、mode `0400`。
- SSH config固定`BatchMode=yes`、`IdentitiesOnly=yes`、
  `StrictHostKeyChecking=yes`和独立`UserKnownHostsFile`。
- `wgs-node200`固定`HostName 172.17.61.200`、`User hanjj`，不接受请求覆盖。
- `.96/.97`仅作为资源采集别名；`.200`不展示为Analysis Node。
- 原`chenjc`目录在禁用态验收前保留为未挂载回滚材料；生产Compose同一时间只挂载
  一套身份，不允许按任务在两个账号间自动回退。

### 3.2 node200运行配置

由`chenjc`协助在node200安装，但最终文件归`hanjj`所有：

```text
/home/hanjj/.obsutilconfig
/home/hanjj/.kube/config
/home/hanjj/.local/bin/kubectl
/home/hanjj/.config/wgs/cce.yaml
```

目录mode为`0700`，credential/config为`0600`，kubectl为`0755`。迁移工具不得打印、
复制到仓库或记录这些文件内容，只记录路径、owner、mode和脱敏校验结果。
`cce.yaml`中的路径全部改为`hanjj`目录；不得继续间接读取`/home/chenjc`。

最低验收为：

- `obsutil`仅列举批准的WGS前缀并丢弃对象名输出，退出码成功。
- `kubectl config current-context`与批准CCE集群一致。
- 按实际cce-pipeline合同验证Master Job所需的最小RBAC，不扩大为集群管理员。
- `cce-pipeline`prepare/preflight可读固定WGS仓库并写入新控制/分析根。
- 禁用态不得上传、创建Master Job或删除SFS/OBS内容。

## 4. 资源监控

`.96/.97`使用`hanjj`新key采集CPU、内存、load、磁盘吞吐/IOPS和网络吞吐；
`.200`只承担WGS云端操作，不放进前端“Analysis Node Health”。节点采集与WGS
runner使用同一受保护身份，但分为不同进程和固定alias，不能接受HTTP传入host、user、
命令或路径。

资源采集推荐使用独立`platform-node-probe`，它只持有SSH目录和一个可写metrics
spool，不持有数据库密码、OBS配置、kubeconfig或WGS runtime写权限。现有
`platform-metrics-collector`只读spool并写biodemo，不直接持有SSH key。前端地址和
节点名称完全来自API，不能再硬编码`.96/.97`。

OBS/SFS继续由node200单向生成Cloud Eye快照。OBS已有的obsutil credential不自动
等同于Cloud Eye权限；只有具备批准的CES只读权限、OBS bucket维度和SFS instance ID后
才启用。缺少Cloud Eye时显示degraded/stale，不通过`obsutil du`高频遍历对象来伪造
实时容量。

## 5. 历史兼容、切换与回滚

- 旧控制根
  `/sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime`保持只读，
  不删除、不迁移、不接受新request。
- 历史AnalysisRun、DagRun、Rule、日志索引和审计记录不改绑。需要读取旧证据时只允许
  通过已有数据库绑定和旧只读根，禁止路径fallback。
- 新release先保持`WGS_EXECUTION_ENABLED=false`、
  `WGS_RUNTIME_ADAPTER_ENABLED=false`、`WGS_AUTO_DISPATCH_ENABLED=false`，并保持
  `bio_wgs` paused。
- 禁用态通过后原子切换`current`，但仍不执行真实流程。获得单独批准后才手工提交一个
  最小真实batch。
- 最小batch必须验证prepare、Step1传输、Master、Rule JSONL、Step4、Step5、Step6及
  最终目录均绑定`hanjj`身份和新根，且旧根mtime不变化。
- 回滚只恢复上一release和旧SSH mount；不得复制新batch回旧根，不删除新目录、OBS、
  SFS、数据库、volume或Docker网络。

## 6. 实施阶段和验收

### 阶段A：禁用态准备

1. 备份biodemo、Airflow metadata、当前env、current链接和旧runner状态。
2. 创建新目录并完成BS10610/node200交叉写入探测。
3. 安装`hanjj` kubeconfig、kubectl和CCE operator config，验证owner/mode及只读能力。
4. 安装BS10610新SSH目录并固定`.96/.97/.200` host key。
5. 对新key、配置和runtime根运行敏感信息扫描，确保不进入release。

### 阶段B：代码和禁用态release

1. 先增加request v4、双根白名单、batch冲突、历史binding和新身份配置的失败测试。
2. 修改backend、DAG、runner、Compose和资源采集，不改变公开提交表单。
3. 在BS10610 Docker中运行backend、scripts、DAG、frontend、Compose和网络测试。
4. 只重建应用、Airflow、node probe、metrics collector和frontend；不重建PostgreSQL、
   Redis、volume或外部网络。
5. 验证唯一发布仍为`172.17.106.10:12959`，外部网络仍为
   `nipt_analysis_test_net=192.168.199.0/24`、gateway `192.168.199.1`。

### 阶段C：单独批准的真实验收

1. 启用两个执行开关但保持DAG paused，通过API手工提交一个最小batch。
2. 验证所有写入和OBS/CCE身份均为`hanjj`，旧runtime无新文件。
3. 验证一次checkpoint恢复、Master/Rule状态和结果MD5门禁。
4. 成功后再决定是否解除pause；Step7仍需admin单独双确认。

## 7. 明确不做

- 不修改WGS 4.1.1业务Rules、Master/Worker镜像或Snakemake logger合同。
- 不把4.2.0测试分支接入生产。
- 不迁移或删除历史runtime、OBS/SFS对象、结果或数据库记录。
- 不给浏览器任意服务器路径、SSH host、OBS prefix、kubectl参数或shell参数。
- 不因Cloud Eye尚未就绪阻断WGS分析。
