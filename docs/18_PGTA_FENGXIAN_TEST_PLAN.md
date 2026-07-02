# 18 fengxian PGT-A demo 测试计划

## 1. 目标

本计划用于把 airflow-demo 的第一轮部署测试限定为安全、可回滚、可观察的最小闭环。目标是在 `ssh fengxian` 节点上，后续用 Docker 容器启动 React、FastAPI、Airflow、PostgreSQL biodemo DB、Redis 和 MailHog，并把 `/home/jiucheng/pipelines/PGT_A` 作为外部只读 Snakemake 流程接入。

本计划本身只记录测试方案和验收标准，不执行安装、部署、容器启动或服务器变更。

第一轮闭环：

```text
frontend/API submit pgta run
  -> FastAPI records biodemo state
  -> Airflow DAG bio_pgta starts
  -> Airflow worker calls PGT-A Snakemake lightweight target
  -> logs/artifacts are collected under shared runs
  -> frontend can display status and failure summary
```

## 2. 已确认的只读环境事实

### fengxian

```text
ssh alias: fengxian
hostname: gts
deploy user: jiucheng
os: Ubuntu 18.04.6 LTS
kernel: 4.15.0-213-generic
docker: 20.10.21, API 1.41
docker compose: not installed during read-only preflight
host ipv4: 192.168.1.211/24
existing docker networks:
  - bridge: 172.17.0.0/16
  - cnv_biosan_local_net: 172.18.0.0/16
project path: /home/jiucheng/project/airflow-demo
PGT-A path: /home/jiucheng/pipelines/PGT_A
Snakemake: /biosoftware/miniconda/envs/snakemake_env/bin/snakemake 8.5.4
Python: /biosoftware/miniconda/envs/snakemake_env/bin/python 3.12.2
```

### BS10610

```text
ssh alias: BS10610
hostname: server10610
login user seen in read-only preflight: chenjc
os: Ubuntu 20.04.4 LTS
docker: 28.1.1
docker compose: v2.35.1
existing docker networks:
  - bridge: 192.168.192.0/24
  - nipt_analysis_test_net: 192.168.199.0/24
missing fengxian-style paths:
  - /home/jiucheng
  - /home/jiucheng/project/airflow-demo
  - /home/jiucheng/pipelines/PGT_A
  - /biosoftware
  - /data/project/CNV/PGT-A
```

BS10610 只能作为迁移目标预检记录，不能直接复用 fengxian 路径。

## 3. 固定决策

- 对外 pipeline 名称：`pgta`。
- Airflow DAG ID：`bio_pgta`。
- 不使用带旧草案后缀的命名作为 API/UI/DAG 名称。
- 第一阶段不升级 Snakemake 到 9+，不依赖 logger plugin。
- 第一阶段用 Airflow task log、Snakemake stdout/stderr、PGT-A 现有 rule log 和 artifact registry 做可观测性。
- 如果后续要测试 Snakemake 9 logger plugin，必须使用隔离环境或单独容器镜像，不修改 `/biosoftware/miniconda/envs/snakemake_env`。
- Docker Compose 在 fengxian 后续采用用户级 Docker CLI plugin：`$HOME/.docker/cli-plugins/docker-compose`。
- Compose 建议版本：`v2.24.7`，用于兼容 Docker `20.10.21` / API `1.41`。
- 不做系统级 Docker 升级，不使用 legacy `docker-compose` v1。
- 固定 demo Docker 网段：`172.30.10.0/24`，gateway `172.30.10.1`。
- 禁止使用 `docker compose down -v`、`docker system prune -a`、`docker volume prune` 作为默认测试或回滚步骤。

## 4. 运行架构

### 4.1 路径

```text
PROJECT_ROOT=/home/jiucheng/project/airflow-demo
SHARED_ROOT=/home/jiucheng/project/airflow-demo/shared
PGTA_PIPELINE_ROOT=/home/jiucheng/pipelines/PGT_A
PGTA_CONTAINER_ROOT=/opt/pipelines/PGT_A
CONTAINER_SHARED_ROOT=/data/airflow-demo
```

### 4.2 容器服务

```text
frontend
backend
airflow-api-server
airflow-scheduler
airflow-worker
postgres
redis
mailhog
```

### 4.3 固定容器 IP

| Service | Container IP | Notes |
|---|---|---|
| airflow-api-server | `172.30.10.10` | Airflow UI/API |
| backend | `172.30.10.20` | FastAPI |
| frontend | `172.30.10.30` | React |
| postgres | `172.30.10.40` | Airflow metadata + biodemo, separated by DB/schema |
| redis | `172.30.10.50` | Airflow broker |
| mailhog | `172.30.10.60` | demo mail |

### 4.4 Volume contract

```text
/home/jiucheng/pipelines/PGT_A:/opt/pipelines/PGT_A:ro
/biosoftware:/biosoftware:ro
/data/project/CNV/PGT-A:/data/project/CNV/PGT-A:ro
/home/jiucheng/project/airflow-demo/shared:/data/airflow-demo:rw
```

PGT-A 流程目录和数据目录只读挂载。demo 输出只能写入：

```text
/data/airflow-demo/runs/<analysis_id>
/data/airflow-demo/reports/<analysis_id>
/data/airflow-demo/logs
```

## 5. PGT-A 测试层级

### Level 0: preflight

目的：确认节点具备后续测试的最低条件。

验收项：

- `docker --version` 可运行。
- `docker compose version` 可运行；若不可用，只记录阻塞，不进入服务启动。
- 固定网段 `172.30.10.0/24` 与已有 Docker/host 网段不冲突。
- PGT-A 路径存在且可读。
- Snakemake/Python 可执行文件存在且可执行。
- `/biosoftware` 与 `/data/project/CNV/PGT-A` 存在。
- `df -h`、`free -h` 显示有足够空间和内存。

### Level 1: metadata smoke

目的：真实执行 Snakemake，但只跑轻量 `metadata` target。

约束：

- 不跑 mapping、baseline QC、CNV 或 reference build。
- 不写回 `/home/jiucheng/pipelines/PGT_A`。
- 使用 run workdir 中生成的隔离 config。

验收项：

- API 提交 `pipeline=pgta`、`target=metadata` 后生成 `analysis_id`。
- Airflow DAG `bio_pgta` 进入 success。
- 生成 `shared/runs/<analysis_id>/logs/run_metadata.tsv`。
- backend artifacts API 能登记 metadata/log artifact。
- frontend run detail 能看到 success 状态和日志入口。

### Level 2: dry-run smoke

目的：验证 PGT-A rule DAG 能在容器内解析。

验收项：

- API 提交 `pipeline=pgta`、`target=dryrun_cnv`。
- Airflow worker 执行 Snakemake dry-run。
- Snakemake exit code 为 0。
- stdout/stderr 被写入 shared run log，并可由 backend log API 读取。

### Level 3: failure smoke

目的：验证错误摘要链路。

触发方式：

- 提交非法 target，例如 `target=invalid_target`。
- 或提交故意缺失 config 的测试 run。

验收项：

- Airflow DAG failed。
- `analysis_run.error_summary` 包含命令、退出码、失败 task、stderr 最后 100 行。
- frontend failed run 默认显示 stderr 摘要。

### Level 4: baseline_qc

目的：在 Level 1-3 通过后，单独验证一个更接近真实生信运行的目标。

进入条件：

- Level 1 metadata smoke 通过。
- Level 2 dry-run smoke 通过。
- Level 3 failure smoke 通过。
- 用户明确同意运行较重生信任务。

约束：

- 使用隔离 workdir。
- 限制并发。
- 不默认运行 CNV/predict/reference build。
- 不删除或覆盖 `/data/project/CNV/PGT-A` 既有结果。

## 6. 后续实现拆分

| ID | Owner | Task | Acceptance |
|---|---|---|---|
| PGTA-001 | infra | 用户级 Compose v2 plugin 准入 | `docker compose version` 输出固定版本 |
| PGTA-002 | infra | docker compose 基础服务与固定网络 | `docker compose config` 通过，网络为 `172.30.10.0/24` |
| PGTA-003 | backend | 支持 `pipeline=pgta` 提交与 run 记录 | `/api/runs` 可创建 pgta run |
| PGTA-004 | airflow | 新增 DAG `bio_pgta` | DAG import/check 通过 |
| PGTA-005 | airflow/snakemake | pgta metadata runner | `logs/run_metadata.tsv` 生成 |
| PGTA-006 | backend/frontend | log/artifact/error summary 展示 | 成功和失败 run 都能从页面定位日志 |
| PGTA-007 | qa | Level 0-3 smoke 验收报告 | 验收报告记录命令、结果、风险 |

## 7. Compose 安装计划

后续安装 Compose 前必须先确认：

```bash
docker version
mkdir -p "$HOME/.docker/cli-plugins"
```

推荐安装方式是在本地 Windows 从 GitHub Release 下载官方二进制，然后用 `scp` 同步到 `fengxian` 用户级 plugin 路径。若本地下载需要代理，显式给 `curl.exe` 加 `--proxy socks5h://127.0.0.1:1080`；不要把代理配置写入仓库。

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

备用安装方式是在国内 Docker CE 镜像下载 deb 包，并只解包 CLI plugin 二进制到用户目录，不执行系统级 apt/dpkg 安装。`fengxian` 的 bionic Docker CE 镜像只提供到 Compose 2.18.1；为固定 `v2.24.7`，使用 focal 包中的静态 plugin 二进制。

```bash
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

验收：

```text
Docker Compose version v2.24.7
```

回滚：

```bash
rm "$HOME/.docker/cli-plugins/docker-compose"
```

国内镜像探测结论：

- 清华、交大、阿里云 Docker CE `focal`/`jammy` 镜像包含 `docker-compose-plugin_2.24.7`。
- 清华、交大、阿里云 Docker CE `bionic` 镜像仅探测到 `docker-compose-plugin_2.18.1`。
- 清华/中科大/交大 GitHub-release 路径未探测到可直接下载的 `docker/compose/v2.24.7/docker-compose-linux-x86_64`。

## 8. BS10610 迁移预检

迁移前必须把以下值全部参数化到 `.env`，不得硬编码 fengxian 路径：

```text
PROJECT_ROOT
SHARED_ROOT
PGTA_PIPELINE_ROOT
PGTA_DATA_ROOT
BIOSOFTWARE_ROOT
DOCKER_SUBNET
```

BS10610 第一轮只做 Level 0 preflight。只有路径、Docker、Compose、PGT-A 环境都确认后，才能复制 fengxian 的 Level 1-3 测试。

## 9. 参考链接

- Snakemake monitoring/logger plugin 文档：<https://snakemake.readthedocs.io/en/stable/executing/monitoring.html>
- Snakemake 9 migration 文档：<https://snakemake.readthedocs.io/en/v9.2.0/getting_started/migration.html>
- Docker Compose plugin Linux 安装文档：<https://docs.docker.com/compose/install/linux/>
