# SERVER_INFO.md

## T146 BS10610 WGS 2499749 active acceptance (2026-09-01)

```text
primary: BS10610
compose_project: airflow-wgs
release: 20260901-wgs-4.1.1-2499749-t146-r3
wgs_release: wgs-4.1.1-2499749
wgs_commit: 2499749ce7fd200d4269d1ee03d7b6a4e8d5bb68
node200_runtime: cce-pipeline 0.8.1
resolved_master_digest: sha256:965473cf89539ec67869cb38265f1416de508aa71ab5f35ad9be6a979548dab0
active_analysis: WGS_20260901_031616_C74E6C attempt 1
active_stage_at_checkpoint: input_transfer.wait_step1_upload
execution_gates: true on BS10610 and node200 for the approved manual run
bio_wgs: unpaused
auto_dispatch: false
external_network: nipt_analysis_test_net, 192.168.199.0/24, gateway 192.168.199.1
published: only 172.17.106.10:12959 frontend/API gateway
```

The old `WGS_20260831_194429_145176` business rows, 11 DagRuns, runtime and
batch evidence, SFS/OBS prefixes and CCE lock/workloads were removed after
separate mode-0600 biodemo and Airflow metadata backups. One cleanup audit row
is retained. The active replacement uses a new analysis ID and is monitored by
Airflow reschedule sensors; the run observer activates only at Step3.

## T146 BS10610 WGS runtime snapshot (2026-09-01)

```text
primary: BS10610
compose_project: airflow-wgs
release: 20260901-wgs-4.1.1-cdee32c-t146
wgs_release: wgs-4.1.1-cdee32c
node200_runtime: cce-pipeline 0.8.1
resolved_master_runtime: cce-pipeline 0.7.0 series (incompatible with 0.8.1 Step2 pre-start manifest)
execution_gates: false on BS10610 and node200 after failed real acceptance
bio_wgs: paused
auto_dispatch: false
external_network: nipt_analysis_test_net, 192.168.199.0/24, gateway 192.168.199.1
published: only 172.17.106.10:12959 frontend/API gateway
accepted_stage: prepare and Step1 input transfer
blocked_stage: Master startup before Snakemake; existing evidence stub lacks run-id contract
```

The failed Master, exact empty SFS evidence stub, diagnostic Jobs and batch lock
were removed after evidence capture. Uploaded OBS FASTQ and the failed Airflow/
biodemo audit records were preserved. Do not reopen the gates until the resolved
Master image implements the same pre-start run-root contract as cce-pipeline 0.8.1.

## T127 BS shared NIPT/WGS deployment snapshot (2026-07-15)

```text
primary: BS10610
cold_standby: BS1069 (images loaded, all platform services stopped)
compose_project: airflow-nipt (shared control plane; do not start airflow-wgs)
project_root: /mnt/biodevrwbi/33.chenjiucheng/project/airflow-NIPT
wgs_host_project: /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS
external_network: nipt_analysis_test_net, 192.168.199.0/24, gateway 192.168.199.1
published_primary: 172.17.106.10:12959 frontend/API, 172.17.106.10:12958 Airflow
executor: CeleryExecutor
worker_concurrency: 2
heavy_pool: bs_heavy_analysis, 1 slot shared by NIPT Docker and WGS
deployed_dags: bio_nipt_docker, bio_wgs, bio_intake_scan
scanner_state: paused
default_nipt_image: 172.17.61.235:2333/niptpro/niptpro:1.1.11
default_nipt_image_id: sha256:71df36b7f8080762f2db771e13e4daa7f4a666b3e1efc19c3bf12add22187254
rollback_nipt_image: 172.17.61.235:2333/niptpro/niptpro:1.0.11
wgs_scheduler: Snakemake 9.23.1, Python 3.12, host-native through restricted SSHOperator
wgs_default_cores: 96
wgs_validation_scope: one family / three new pre-calling samples
frontend_nginx: nginx 1.30.3, Alpine 3.23.5
backend_image: airflow-demo/backend:bs-control-f11ea02, sha256:22195533260900e6abde7f971513511da678caa5d04b5bcfefa87ab6952e640d
backend_archive_sha256: 48d71ebb5b2c0ab1d309b8bad94bcab0bf10e1cef74f9a35cfe683855d2009da
frontend_image: airflow-demo/frontend:bs-control-f11ea02, sha256:93cf3a076c43e4c9d9eacbf8f0b6e0c7edb22a9acf0e01f561f3eeeaa4c29612
frontend_archive_sha256: 52e98121b4d94a6aa30c67781ea17b5c6dc90c726b9dc5b42ae79e49dfaff0bb
release_archive_sha256: 74ee973c55411ab7c6ec2dc7d9d013a2136f90298b26ea692e59490990fd008b
wgs_acceptance: WGS_20260715_062217_351C76 completed Airflow-managed pre-calling dry-run success in 12s; 21 planned jobs are terminal skipped and no WGS rule executed
nipt_acceptance: three serial 27-sample full runs success; 858s, 783s, 884s; 27/27 QC pass and 232/232 success events each
```

The BS10610 databases are fresh and are not a migration of fengxian history.
The current workstation could not route directly to `172.17.106.10`; health
acceptance was performed from the BS node. Use an SSH tunnel or an approved BS
network route for workstation browser access.

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
container_timezone_target: AIRFLOW_DEMO_TZ=Asia/Shanghai; Airflow core/UI timezone target Asia/Shanghai; backend API timestamps remain timezone-aware
container_timezone_status_2026_07_06: after T089 redeploy, backend/frontend/Airflow containers show `TZ=Asia/Shanghai` and `date` reports `+0800 CST`; Airflow `core.default_timezone` and `webserver.default_ui_timezone` report `Asia/Shanghai`
host_nginx_path: /usr/sbin/nginx
host_nginx_version: nginx/1.14.0 (Ubuntu)
host_nginx_probe: verified executable on fengxian 2026-07-02; not configured for airflow-demo
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
fengxian_planned_demo_subnet: 172.30.10.0/24
existing_docker_networks: bridge 172.17.0.0/16; cnv_biosan_local_net 172.18.0.0/16
compose_config_status: passed on fengxian for commit 5e9065d; Airflow 12958 and frontend 12959 rendered correctly
minimal_smoke_status: postgres/redis/mailhog/backend/frontend/airflow web/scheduler/worker up, health probes ok, then docker compose down
airflow_init_status: metadata DB migrated and admin user created by airflow-init on 2026-07-02; password only in remote .env
biodemo_db_status: initialized by biodemo-db-init, migrated by Alembic revision 20260702_0001 on 2026-07-02
backend_test_status_2026_07_02: Dockerized pytest in backend image passed 9 tests on fengxian
backend_pip_config: backend/pip.conf uses TUNA PyPI mirror; backend image installs dependencies in /opt/venv
host_port_probe_2026_07_02: 12958,12959,8000,8025,1025,5432,6379 free before smoke; 3000 busy on 127.0.0.1 by non-project next-server
image_cleanup_2026_07_02: removed 37 dangling <none>:<none> images with docker image rm, no volumes removed
image_pull_status_2026_07_02: compose external images pulled successfully; backend built as airflow-demo/backend:0.1.0
project_latest_images: none after retagging backend; non-project latest images were left untouched
t119_runtime_2026_07_13: /home/jiucheng/project/airflow-demo-t119 healthy; Alembic 20260713_0005 applied; backend 168 tests, frontend 40 tests, Intake DAG 3 tests, production build and Compose config passed
t119_nipt_small_batches: 10/15/20-sample Snakemake 9 full runs all reached success with 45/45 sample QC pass; 40-core T18 mapping hit the 60 GiB cgroup and controlled 32-core same-workdir recovery passed
t119_intake_state: bio_intake_scan unpaused; 6 completed records archived, active=0; scheduled PGT-A/NIPT discovery enabled but NIPT auto-submit remains disabled
```

Verified compose images:

```text
apache/airflow:2.9.3-python3.11
postgres:15-alpine
redis:7-alpine
mailhog/mailhog:v1.0.1
nginx:1.27-alpine
airflow-demo/backend:0.1.0
airflow-demo/airflow:0.1.0
```

## 4. Python/Node

```text
system_python: /usr/bin/python3, Python 3.6.9
pgta_python: /biosoftware/miniconda/envs/snakemake_env/bin/python, Python 3.12.2
pgta_python_conda_lib: /biosoftware/miniconda/envs/snakemake_env/lib, used by T095 as first `LD_LIBRARY_PATH` entry for baseline QC Python imports
pgta_snakemake: /biosoftware/miniconda/envs/snakemake_env/bin/snakemake, Snakemake 8.5.4
pgta_snakemake9: /biosoftware/miniconda/envs/snakemake9_env/bin/snakemake, Snakemake 9.23.1
pgta_snakemake9_python: /biosoftware/miniconda/envs/snakemake9_env/bin/python
pgta_snakemake9_logger_interface: snakemake_interface_logger_plugins importable; `--logger` and airflow-demo plugin args verified on 2026-07-03
pgta_level4_audit_2026_07_06: Snakefile supports baseline_qc; requires at least 2 baseline/reference samples; staged airflow-demo integration added but real run not executed in audit
pip: <TO_BE_FILLED>
conda_or_mamba: miniconda under /biosoftware/miniconda
node: <TO_BE_FILLED>
npm_or_pnpm: <TO_BE_FILLED>
```

## 5. Airflow

```text
airflow_image: airflow-demo/airflow:0.1.0, based on apache/airflow:2.9.3-python3.11
airflow_uid: 1005 on fengxian so Airflow can write ./shared as deploy user; set to `id -u` on new servers
airflow_snakemake: /opt/airflow/snakemake-venv/bin/snakemake, Snakemake 9.23.1 in project Airflow image
airflow_cluster_generic_executor_plugin: available in project Airflow image, plugin version 1.0.9
airflow_base_url: planned http://airflow-api-server:8080 inside Docker network
airflow_host_port: 12958
airflow_admin_user: admin
planned_wes_dag_id: bio_wes_qsub
planned_pgta_dag_id: bio_pgta
planned_pgta_airflow_only_dag_id: bio_pgta_airflow
```

## 6. qsub/SGE/PBS

PGT-A first smoke does not use qsub. WES/NIPT qsub work currently uses mock mode because `qsub/qstat` are not available on `fengxian`.

```text
scheduler_type: none detected on fengxian
qsub_path: not found by `command -v qsub` on 2026-07-04
qstat_path: not found by `command -v qstat` on 2026-07-04
qacct_path: <TO_BE_FILLED>
default_queue: <TO_BE_FILLED>
demo_queue: <TO_BE_FILLED>
max_demo_jobs: <TO_BE_FILLED>
snakemake_cluster_generic_executor_plugin: available inside Docker images `airflow-demo/snakemake-runner:0.1.0` and `airflow-demo/airflow:0.1.0`; not installed in host snakemake_env 8.5.4 or snakemake9_env 9.23.1 on 2026-07-04
mock_qsub_wrapper_status: direct wrapper smoke passed on official mirror with backend event POST and `/api/runs/WES_20260704_180650_MOCK/rules`; full `--profile profiles/qsub` runtime passed in `snakemake-runner` with `WES_PROFILE_20260704_230713`; Airflow DAG `bio_wes_qsub` passed with `WES_AIRFLOW_20260705_004506`
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
| frontend | 12959 | 80 | `172.30.10.30` | internal/demo | Docker nginx placeholder; host 3000 is occupied by a non-project next-server |
| backend | 8000 | 8000 | `172.30.10.20` | internal/demo | |
| airflow | 12958 | 8080 | `172.30.10.10` | internal/demo | host 12958 verified free on 2026-07-02 |
| mailhog | 8025 | 8025 | `172.30.10.60` | internal/demo | |
| postgres | none/prefer internal | 5432 | `172.30.10.40` | internal | host 5432 not published |
| redis | none/prefer internal | 6379 | `172.30.10.50` | internal | host 6379 not published |

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
bs_nipt_network_name: nipt_analysis_test_net
bs_nipt_network_subnet: 192.168.199.0/24
bs_nipt_network_gateway: 192.168.199.1
bs_nipt_network_policy: hard constraint; external network only; do not create/recreate/delete/change IPAM
bs_nipt_project_root: /mnt/biodevrwbi/33.chenjiucheng/project/airflow-NIPT
bs_nipt_alternate_mapping: /bi/biodevrwbi/33.chenjiucheng maps the same NFS data but is not used for deployment writes
bs_nipt_write_probe_2026_07_14: BS10610 and BS1069 confirmed writable through /mnt/biodevrwbi/33.chenjiucheng
bs10610_observed_ssh_client_2026_07_14: 172.17.61.18; covered by proposed nginx allowlist 172.17.61.0/24
operator_local_address_note: workstation/VPN addresses may differ from the source observed by BS; use nginx access logs for final HTTP allowlist validation
fengxian_paths_present: false for /home/jiucheng, /biosoftware, /data/project/CNV/PGT-A
```

BS10610 迁移前必须将路径参数化到 `.env` 并重新执行 Level 0 preflight。
BS1069 作为 cold standby 使用相同项目根目录和相同 Docker 网络硬约束；
两台机器不得同时运行 active intake worker。部署前必须重新执行
`docker network inspect nipt_analysis_test_net`，确认 subnet/gateway 和计划静态 IP
没有冲突。

## 10. 禁止记录的信息

- 数据库密码。
- Airflow admin 密码。
- SMTP 密码。
- API token。
- 真实样本清单。
- 真实患者信息。
