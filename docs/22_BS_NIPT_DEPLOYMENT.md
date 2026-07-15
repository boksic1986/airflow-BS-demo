# BS NIPT-only Airflow Deployment Contract

> T127 supersession: this document remains the historical T125/T126 NIPT-only
> baseline. BS10610 now upgrades the same Compose project to one shared Airflow
> control plane with `bio_nipt_docker`, `bio_wgs`, and `bio_intake_scan`.
> PGT-A remains absent; no second WGS Airflow stack or database is deployed.

## Scope

This document defines the deployment contract for moving only the Airflow and
NIPT Docker workflow to BS10610, with BS1069 prepared as a cold standby.
PGT-A, WES, WGS, email notification, and fengxian run history are out of scope.

Project root:

```text
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-NIPT
```

Both BS10610 and BS1069 have been verified writable through this `/mnt`
mapping. `/bi/biodevrwbi/33.chenjiucheng` addresses the same NFS data through a
different mapping, but deployment tools must not use it for writes.

The deployment uses the validated NIPT Snakemake 9 derivative image copied from
fengxian. The Snakemake 7 NIPT image already present on BS is not an acceptable
default runtime.

## Docker network hard constraint

These values are immutable for this deployment:

```text
network=nipt_analysis_test_net
subnet=192.168.199.0/24
gateway=192.168.199.1
```

The network already exists on BS10610 and BS1069. Compose must use
`external: true`. Deployment code must not create, remove, recreate, resize, or
otherwise modify this network. `192.168.199.0`, `192.168.199.1`, and
`192.168.199.255` cannot be assigned to services.

Before deployment, verify the live IPAM configuration and current attachments:

```bash
docker network inspect nipt_analysis_test_net \
  --format '{{json .IPAM.Config}}'
docker network inspect nipt_analysis_test_net \
  --format '{{range $id, $c := .Containers}}{{$c.Name}} {{$c.IPv4Address}}{{println}}{{end}}'
```

Expected IPAM values:

```text
Subnet: 192.168.199.0/24
Gateway: 192.168.199.1
```

Any mismatch or address collision blocks deployment. It must not be worked
around by selecting another subnet.

## Nginx ingress allowlist

The nginx client allowlist and Docker IPAM are independent controls and do not
conflict:

- `192.168.199.0/24` controls container addressing.
- `172.17.61.0/24` controls which client source addresses may open the web UI.

Because BS10610 and BS1069 are on `172.17.106.0/24`, an allowlist containing
only `172.17.61.0/24` can block node-local or BS-subnet operations. The initial
nginx policy must therefore account for the actual access path:

```nginx
allow 172.17.61.0/24;
allow 172.17.106.0/24;
allow 172.20.8.0/24;
allow 127.0.0.1;
deny all;
```

Read-only SSH verification from the current operator workstation on 2026-07-14
showed BS10610 receiving source `172.17.61.18`, while the live browser request
on 2026-07-15 reached nginx as `172.20.8.85`. The allowlist therefore includes
the operator workstation subnet `172.20.8.0/24`. Reconfirm the HTTP source in
the nginx access log during deployment acceptance; do not infer it only from
the SSH path.

If Docker port publishing presents a node-local health request to nginx with a
`192.168.199.0/24` source, add that internal subnet only after confirming the
observed source in the access log. Do not replace the allowlist with
`allow all`. Keep PostgreSQL and Redis unpublished.

## Node roles

- BS10610 is the primary node.
- BS1069 is a cold standby.
- Only one node may run the scheduler, worker, and intake scanner against the
  shared NFS paths at a time.
- Failover requires stopping the primary before starting the standby.

## Required services

- Docker nginx gateway
- React frontend
- FastAPI backend
- PostgreSQL
- Redis
- Airflow API server, scheduler, and Celery worker
- `bio_nipt_docker` and `bio_intake_scan` DAGs only

PostgreSQL and Redis remain internal. Only the nginx gateway publishes host
ports. NIPT FASTQ stays on existing BS mounts and is never copied into Git or
the project release directory.

## Runtime requirements

- NIPT runtime: Snakemake 9.23.1 derivative image.
- The logger plugin must be discoverable through the approved NIPT S9
  entrypoint and its `PYTHONPATH` setup.
- Full analysis uses the validated profile and current 32-core default.
- NIPT input mounts are read-only; run workdirs are writable.
- No `docker compose down -v`, volume prune, system prune, or network deletion.

## Acceptance gates

1. Reconfirm the `/mnt` project root is writable with a create/remove probe.
2. Confirm Docker IPAM matches the hard constraint.
3. Confirm planned service IPs are unused.
4. Validate image IDs and SHA256 checksums after transfer from fengxian.
5. Verify Snakemake 9.23.1 and `--logger airflow-demo` through the real S9
   entrypoint.
6. Run `docker compose config --quiet` before startup.
7. Confirm Airflow exposes only `bio_nipt_docker` and `bio_intake_scan`.
8. Complete mount smoke, then one supervised small full run before the known
   72-sample full acceptance run.
9. Confirm all scheduled Snakemake jobs have terminal logger events and NIPT
   QC/CNV/T21/fetal-fraction/summary outputs are present.
10. Keep BS1069 stopped after cold-standby validation.

## T126 deployment result

BS10610 is the active primary. It runs fresh PostgreSQL/Redis databases,
FastAPI, the React/nginx gateway, and Airflow API/scheduler/Celery worker. The
deployed DAG inventory contains only `bio_nipt_docker` and
`bio_intake_scan`; the scanner remains paused.

Validated runs:

| Run | Samples | Runtime | Rule events | QC | Peak memory |
|---|---:|---:|---:|---:|---:|
| `NIPT_20260714_133355_B3081A` | 10 | 277 s | 96/96 success | 10/10 pass | below limit |
| `NIPT_20260714_140419_F999B0` | 72 | 923 s | 592/592 success | 72/72 pass | 42.86 GiB |

The 72-sample input inventory contains 144 FASTQ files; before/after stat and
SHA256 manifests are identical. Mapping QC, T21 classifier, and
dynamic-reference summaries match the fengxian S9 baseline. Fetal-fraction
differences are <= `4e-6`, below the accepted engineering tolerance.

All image archives were downloaded from fengxian to the local Windows staging
directory and uploaded separately to each BS node. Direct remote-to-remote
copy was not used. BS1069 has checksum-verified, loaded images but no running
platform service, database, scheduler, worker, or scanner.

## Rollback

Stop services without deleting volumes, restore the previous image/profile,
and keep the external network unchanged. Preserve databases, workdirs, logs,
results, FASTQ, and image archives.
