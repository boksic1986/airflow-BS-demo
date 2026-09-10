# Test and production release boundary

This document is the stable authority for selecting an airflow-demo runtime
environment. Release names and commits are observations, not permanent
configuration. Before any remote action, inspect the target host and the
containers that are actually running.

## Authority order

Use the first applicable source:

1. the user's explicit instruction for the current task;
2. live, read-only preflight on the target host;
3. this environment boundary;
4. `AGENTS.md`, skills and runbooks;
5. dated entries in `CURRENT_STATE.md`, `HANDOFF.md` and `SERVER_INFO.md`.

If live state and the expected contract disagree, record configuration drift
and stop before deployment or analysis submission. Never resolve ambiguity by
using a test path in production or a production credential in test.

## Environment matrix

| Contract | BS10610 test | server96 production |
| --- | --- | --- |
| SSH alias | `ssh BS10610` | `ssh BS96` |
| Hostname | `server10610` | `server96` |
| Gateway | `http://172.17.106.10:12959` | `http://172.17.61.96:12959` |
| Control root | `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS` | `/data/airflow-WGS` |
| Pipelines | `wgs,gatk` | `wgs` only |
| Runtime identity | `ctapa:bioinfo` via `id_rsa_ctapa` | `ctapa:bioinfo` via `id_rsa_ctapa` |
| Intake scanner | disabled | enabled |
| Auto dispatch | disabled | enabled by production policy |
| Database | disposable test state | retained production state |

Only frontend-nginx publishes port 12959. Backend, Airflow, PostgreSQL, Redis,
observers and collectors stay internal. Both deployments attach to the
existing `nipt_analysis_test_net` network with subnet `192.168.199.0/24` and
gateway `192.168.199.1`; releases must not recreate it.

Production automatic analysis requires all three values:

```text
WGS_INTAKE_SCAN_ENABLED=true
WGS_AUTO_DISPATCH_ENABLED=true
WGS_AUTO_DISPATCH_NOT_BEFORE=<approved ISO-8601 activation time>
```

The 2026-09-09 read-only observation found scanning enabled but auto dispatch
disabled in both backend and scanner. That is recorded drift from the policy
above, not permission for a documentation or cleanup task to enable analysis.

The 2026-09-10 T253 read-only production check supersedes that observation:
both gates are true, with not-before `2026-09-08T08:00:00Z`. Test still has both
gates false. Synchronizing source from production must preserve the test gates,
test runtime identity and test data roots.

## Directory contract

### BS10610 test

```text
control/release root:
  /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS

WGS analysis root:
  /sg2/50.ctapa/project/HWcloud/WGS_test/WGS_Clinical

WGS runtime:
  BS10610 /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-ctapa/wgs-runtime
  node200 /sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-ctapa/wgs-runtime

GATK source/result root:
  /sg2/50.ctapa/project/HWcloud/WES_test/WES_Clinical

GATK runtime and evidence:
  BS10610 /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-ctapa/gatk-runtime
  node200 /sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-ctapa/gatk-runtime
  evidence below the matching gatk-runtime root

Cloud Eye test spool:
  BS10610 /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-ctapa/wgs-runtime/platform-metrics/cloud.json
  node200 /sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-ctapa/wgs-runtime/platform-metrics/cloud.json
  producer /home/ctapa/.config/airflow-wgs-test

SSH runtime identity:
  user ctapa
  key  id_rsa_ctapa
  WGS  /home/ctapa/.config/airflow-wgs-test/forced-command.sh
  GATK /home/ctapa/.config/airflow-gatk-test/forced-command.sh
```

The retired `hanjj` SSH identity, the old `14.hanjingjing` analysis tree and
the earlier mixed `airflow-wgs/runtime` and `airflow-gatk/runtime` roots are
historical only. New test requests, receipts and evidence use the dedicated
`airflow-ctapa` control roots above; new analysis output uses only the approved
`50.ctapa` WGS/WES test roots.

The `50.ctapa` analysis roots are writable by `ctapa` on node200 but are
read-only through the BS10610 NFS export. Therefore they must not be used for
container-side runtime spools. BS10610 writes control state through the
`/mnt/biodevrwsg2` mapping, and node200 sees the same control state through
the `/sg2/biodevrwsg2` mapping.

The test database, runtime, evidence and results are never promoted to
production. Controlled real-data smoke tests may use these approved roots, but
patient fields, FASTQ, results and credentials must not enter Git artifacts.

### server96 production

```text
control/release root:
  /data/airflow-WGS

WGS analysis/result root:
  /sg2/50.ctapa/project/HWcloud/WGS_Clinical

WGS runtime and intake:
  /sg2/50.ctapa/project/HWcloud/airflow-wgs/runtime
  /sg2/50.ctapa/project/HWcloud/airflow-wgs/runtime/intake

WGS FASTQ input:
  /bi/fastq/T7_Fastq
```

Production deploys WGS only. GATK code present in the repository does not
authorize a production GATK mount, DAG, pipeline capability or execution gate.

## Permission contract

- The test and production workflow identity is `ctapa:bioinfo`. Each environment
  has its own restricted runtime configuration and data roots. The control root may be
  administered by a separate approved owner; do not infer workflow authority
  from the owner of `/data/airflow-WGS`.
- Immutable release directories use 0755 directories, 0644 data files and
  0755 executable scripts.
- `env/` and `secrets/` use 0700 directories and 0600 secret files.
- Mutable runtime, evidence, results and shared roots use group `bioinfo`,
  setgid 2770 where isolation is required, and explicit default ACLs for the
  named runtime users.
- FASTQ, workflow source, references and input projects are mounted read-only.
  Only approved runtime, result, log, binding and spool roots are writable.
- Never use `chmod 777`, recursively widen `/sg2` or `/bi`, or follow symlinks
  outside an approved root while changing permissions.

Before deployment, run `id`, `namei -l`, `stat` and `getfacl` on every host
root and inspect container mounts. Prove required write access with a random,
non-clinical marker created, read and removed through the same runtime identity.
An absent path, truncated ACL mask, unexpected owner/group or writable input
fails closed.

The 2026-09-09 observation that test execution used `hanjj` and mode 0775 is
historical. T254 requires every new ctapa test runtime, evidence and result
directory to use group `bioinfo` and setgid mode 2770 before activation.

## Release preflight

Record this fingerprint before any mutation:

```text
target_environment
ssh_alias and hostname
current symlink and SOURCE_COMMIT
Compose project and Compose file
container image IDs and actual bind-mount sources
published ports and external network
pipeline capabilities and execution gates
scanner/dispatch/watermark state
active AnalysisRuns, transfers and external workloads
directory owner/group/mode/ACL checks
```

Inspect service mounts individually. A `current` symlink does not prove that a
long-running service consumes that release. On 2026-09-09 production backend
used T241 while the scanner remained intentionally pinned to the T238 source;
such service-level pins must be explicit in every release record.

## Promotion and rollback

- Build and validate a clean, pinned commit in BS10610 test first.
- Test acceptance never authorizes production deployment automatically.
- A production rollout needs explicit approval, an exact target commit,
  current and rollback release paths, an active-run check, and a service-level
  restart list.
- Recreate only affected services. Preserve container IDs for unrelated
  services and never restart an active workflow merely to align source mounts.
- Do not copy test databases, runtime evidence, keys, OBS configuration or
  results into production.
- Rollback restores the recorded release and environment contract; it does not
  delete databases, volumes, networks, CCE workloads or analysis output.

## Docker image and container governance

Target hosts build source releases from preloaded images with `--pull=false`
and, where supported, `--network none`. Source-specific Airflow test images are
not built or staged on fengxian.

Each release records an environment-specific keep set containing:

- every image ID referenced by a running container;
- the current release and one verified rollback release;
- the approved Airflow, backend and frontend build/runtime bases;
- the lock-bound Node 22 builder and nginx 1.30.3 runtime base;
- `postgres:15-alpine` and `redis:7-alpine`;
- GATK release images on BS10610 only.

Base-image archives travel through the approved local relay with image ID,
SHA-256 and provenance verification. BS10610 builds test releases locally and
BS96 builds production releases locally. A generic Node or Python image is not
deleted merely because Airflow once used it.

After every release, inventory first and remove only:

- Exited, Created or Dead containers whose Compose project is an approved
  Airflow project;
- unreferenced `airflow-demo/*` tags outside the keep set;
- dangling images proven to be Airflow build products and unreferenced by any
  container.

Never use `docker system prune -a`, unfiltered `docker image prune -a`, volume
prune, network deletion or build-cache deletion as part of this policy. A
cleanup record contains before/after inventories, exact deleted IDs and disk
usage without secrets.

On fengxian, preserve the currently running legacy `airflow-demo` stack and
its exact images until a separate shutdown is approved. Remove only stopped
Airflow containers and unreferenced `airflow-demo/*` test images. Do not touch
other projects, their stopped containers, or shared generic base images.
