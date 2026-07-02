# SERVER_INFO.md

> 服务器信息模板和只读探测记录。Codex 可以补充环境探测结果，但不得写入密码、token、真实患者数据。

## 1. 基础信息

```text
server_name: gts
server_host: fengxian
os_release: Ubuntu 18.04.6 LTS (Bionic Beaver)
kernel: Linux 4.15.0-213-generic x86_64
cpu: 128 logical cores observed by nproc
memory: 1.4T total, read-only preflight on 2026-07-02
disk: /dev/sda2 20T with 14T available; /data NFS 48T with 21T available
timezone: Asia/Shanghai observed from date output
```

## 2. 用户和路径

```text
deploy_user: jiucheng
project_root: /home/jiucheng/project/airflow-demo
data_root: /data/project/CNV/PGT-A
shared_root: /home/jiucheng/project/airflow-demo/shared
reference_root: <TO_BE_FILLED>
wes_pipeline_root: <TO_BE_FILLED>
nipt_pipeline_root: <TO_BE_FILLED>
pgta_pipeline_root: /home/jiucheng/pipelines/PGT_A
biosoftware_root: /biosoftware
```

## 3. Docker

```text
docker_version: Docker version 20.10.21, build 20.10.21-0ubuntu1~18.04.3
docker_api: client/server API 1.41
docker_compose_version: Docker Compose version v2.24.7
docker_compose_path: /home/jiucheng/.docker/cli-plugins/docker-compose
docker_compose_sha256: 19c9deb6f4d3915f5c93441b8d2da751a09af82df62d55eab097c2cbfebd519f
compose_install_source: local Windows GitHub Release download, scp to fengxian, user-level install
compose_fallback_source: TUNA Docker CE focal docker-compose-plugin_2.24.7 deb unpack only
user_in_docker_group: unknown, but deploy user could run read-only docker commands
planned_demo_subnet: 172.30.10.0/24
existing_docker_networks: bridge 172.17.0.0/16; cnv_biosan_local_net 172.18.0.0/16
compose_config_status: passed on fengxian for commit dd1d8a7
minimal_smoke_status: postgres/redis/mailhog/backend up, backend /api/health ok, then docker compose down
```

## 4. Python/Node

```text
system_python: /usr/bin/python3, Python 3.6.9
pgta_python: /biosoftware/miniconda/envs/snakemake_env/bin/python, Python 3.12.2
pgta_snakemake: /biosoftware/miniconda/envs/snakemake_env/bin/snakemake, Snakemake 8.5.4
pip: <TO_BE_FILLED>
conda_or_mamba: miniconda under /biosoftware/miniconda
node: <TO_BE_FILLED>
npm_or_pnpm: <TO_BE_FILLED>
```

## 5. Airflow

```text
airflow_image: <TO_BE_FILLED>
airflow_uid: planned 50000 in .env.example
airflow_base_url: planned http://airflow-api-server:8080 inside Docker network
airflow_admin_user: <TO_BE_FILLED_NO_PASSWORD>
planned_pgta_dag_id: bio_pgta
```

## 6. qsub/SGE/PBS

PGT-A first smoke does not use qsub. qsub information remains to be confirmed for later WES/NIPT work.

```text
scheduler_type: <SGE|PBS|UGE|unknown>
qsub_path: <TO_BE_FILLED>
qstat_path: <TO_BE_FILLED>
qacct_path: <TO_BE_FILLED>
default_queue: <TO_BE_FILLED>
demo_queue: <TO_BE_FILLED>
max_demo_jobs: <TO_BE_FILLED>
```

## 7. SMTP/Mail

```text
smtp_host: <TO_BE_FILLED>
smtp_port: <TO_BE_FILLED>
mail_from: <TO_BE_FILLED>
mailhog_enabled: service defined and HTTP GET probe passed on fengxian 127.0.0.1:8025
```

## 8. 端口规划

| Service | Host port | Container port | Planned container IP | Exposure | Notes |
|---|---:|---:|---|---|---|
| frontend | 3000 | 80 | `172.30.10.30` | internal/demo | |
| backend | 8000 | 8000 | `172.30.10.20` | internal/demo | |
| airflow | 8080 | 8080 | `172.30.10.10` | internal/demo | |
| mailhog | 8025 | 8025 | `172.30.10.60` | internal/demo | |
| postgres | none/prefer internal | 5432 | `172.30.10.40` | internal | |
| redis | none/prefer internal | 6379 | `172.30.10.50` | internal | |

## 9. BS10610 迁移预检快照

```text
server_host: BS10610
hostname: server10610
login_user_seen: chenjc
os_release: Ubuntu 20.04.4 LTS
docker_version: Docker version 28.1.1
docker_compose_version: Docker Compose version v2.35.1
host_ipv4: 172.17.106.10/24
existing_docker_networks: bridge 192.168.192.0/24; nipt_analysis_test_net 192.168.199.0/24
fengxian_paths_present: false for /home/jiucheng, /biosoftware, /data/project/CNV/PGT-A
```

BS10610 迁移前必须将路径参数化到 `.env` 并重新执行 Level 0 preflight。

## 10. 禁止记录的信息

- 数据库密码。
- Airflow admin 密码。
- SMTP 密码。
- API token。
- 真实样本清单。
- 真实患者信息。
