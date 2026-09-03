# WGS three-stage submission and SFS monitoring design

Status: approved implementation contract for T173.

## Scope

This change implements four approved items only:

1. Submit Run becomes a real three-stage workflow with a pipeline selector.
2. New WGS runs use one canonical run ID in WGS, Airflow and runtime evidence.
3. The production resource card exposes SFS Cloud Eye only; OBS is removed.
4. SFS Turbo metrics are collected through node200 with an existing protected
   `hwybioinfo1` access key and regional `CES ReadOnlyAccess`.

Heavy-rule slots, job/core limits, WES execution, automatic dispatch and Step7
execution are outside this change.

## Submission lifecycle

The browser never runs WGS directly. One `bio_wgs` DagRun is created during
stage 1 and pauses through reschedule sensors at the two human gates:

```text
Stage 1: choose WGS + project/platform/batch/FASTQ root
         -> validate -> prepare sampleinfo -> import candidate samples
         -> wait_config_approval
Stage 2: inspect sample/family preview and choose catalog-controlled settings
         -> approve config -> prepare analysis -> import final eligible/pending samples
         -> wait_execution_approval
Stage 3: inspect the final sample/config summary
         -> approve execution -> Step1 upload through Step6 materialize
```

The two approval sensors use `mode=reschedule`, so they do not occupy a Celery
worker. The API stores approval state server-side and records the acting user.
The client may submit only catalog IDs and whitelisted values. It cannot submit
paths, YAML, image/profile names, shell text, CCE identities or OBS/SFS URIs.

WGS `prepare_wgs_batch.py sampleinfo` is used for stage 1 and
`prepare_wgs_batch.py analysis` for stage 2. Both execute through the restricted
node200 runner. Step1-Step6 continue to use the frozen analysis bundle.

Existing in-flight and historical runs keep their original DagRun IDs and are
not rewritten. The new topology treats a legacy request without approval fields
as already approved so a scheduler refresh cannot stall an in-flight run.

## Canonical ID

For a new attempt, the canonical runtime ID is:

```text
<analysis_id>-a<attempt>
```

It is used unchanged as Airflow `dag_run_id`, WGS `run_id`, runtime request
identity and evidence identity. `analysis_id` remains the database/public run
key. Maintenance DagRuns retain their explicit maintenance IDs.

## SFS Cloud Eye

The monitored file system is `sfs-turbo-clinical` in `cn-east-3`, resource ID
`37cacd44-60ad-41ef-9df2-f93b3dca7095`. Metrics use namespace `SYS.EFS` and
dimension `efs_instance_id`.

IAM uses existing user `hwybioinfo1` and its existing mode-0600 credential file
`/home/hanjj/sfs_api.credentials`. A dedicated group
`airflow-wgs-sfs-metrics` grants only `CES ReadOnlyAccess` for `cn-east-3` and
contains only that user. No new access key is created and the existing
`bioinfo` group is not changed.

node200 writes an atomic `platform-cloud-metrics.v1` spool containing SFS only.
The production collector consumes it and never stores credentials. The API and
frontend filter resource type `sfs`; legacy OBS rows may remain in the database
for compatibility but are not returned or rendered.

Metrics shown are capacity used/percent, read/write bandwidth, IOPS, client
connections and source timestamp. Missing or stale data is reported as
degraded and never blocks WGS execution.

## Safety and deployment

- Preserve the active production batch and all OBS/SFS/runtime evidence.
- Do not deploy the new DAG topology while a legacy DagRun is active unless the
  compatibility path has passed server-Docker tests.
- PostgreSQL, Redis, volumes and the external Docker network are not rebuilt.
- The network remains `192.168.199.0/24`, gateway `192.168.199.1`; only
  `172.17.61.96:12959` is published.
- Source remains uncommitted until the user reviews and commits it.
