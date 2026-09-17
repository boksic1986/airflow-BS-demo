# WGS native execution registration — R2-2 candidate

Task: WGS-LOCAL-SGE-20260915. Source-only, default off. This is the execution
identity/input-history slice, **not full R2-2/3 acceptance and not launch permission**.
Depends on [project registration](2026-09-15-wgs-onprem-registration-contract.md).

## Request and identity

`POST /api/wgs/onprem/projects/{project_uuid}/executions`, HTTP200 on registration
or identical retry. Same personal `wgs_session` + `X-CSRF-Token` contract as first
registration. Only original platform owner may register; no internal-service or
disabled-auth actor. Linux actor is reported, not authenticated by the platform.

```json
{
  "schema_version": "wgs.onprem-execution-registration.v1",
  "platform_instance_id": "test-instance",
  "operation_id": "c1315c81-9e11-4010-845f-c2ca6bcf602c",
  "project_dir": "/approved/SYN_PROJECT",
  "execution_mode": "local",
  "execution_target": "node-96",
  "argv": ["--", "--rerun-incomplete"],
  "execution_user": "synthetic-user",
  "execution_uid": 1234
}
```

`argv` is the ordered argument vector appended to original Step1, not a shell
command; this endpoint records but never executes it. Internal `--worker`,
credential-like arguments and credential-containing config are rejected. Mode
and target must match project registration; no implicit node/profile change.

Same project + operation UUID + exact normalized body returns the same receipt,
even after file edits or terminal status; it does not recapture. A new explicit
start/resume uses a new operation UUID and increments generation, preserving
analysis_id/attempt. Changed body with same operation409; unknown project,
changed target/instance or active/unknown execution409; wrong owner403;
unreadable/invalid inputs or private storage400; schema errors422. Authentication
and CSRF reuse existing401/403 behavior. No clinical contents in error responses.

Registration locks only its AnalysisRun database row for the transaction. Reuses
WgsStageExecution (`stage_code=native_analysis`, status accepted), without calling
CCE stage prerequisites/quota, prepare, pending, Airflow or a controller. Does not
mark AnalysisRun running, set started time or create Sample records.

## Location and immutable inputs

New operations verify allowlisted project path and `.wgs-platform/project.json`.
No active execution may exist before changing location. Old path absent or
carrying a different valid same-platform project identity permits updating workdir;
old path still carrying the same UUID is a copy conflict. Unreadable/invalid old
binding is not proof of a move. No disk scan, device identity or file-lock service.
Initial registration stays immutable; audit records old/new locations. Idempotent
retry returns its prior receipt and is **not** a fresh location/launch check.

Backend reads current `config.yaml`, its actual `sample_info` and
`new_sample_info` references, and `Step1_run.sh`. Files must resolve inside the
project; symlink files are rejected. Identical references share capture reads but
retain both field associations. A second read catches edits during collection.
Small-file read limit16MiB protects the endpoint; it is not a biological threshold.
No reference/FASTQ/result data is copied and no source file is rewritten.

R2-3 adds only the selected mode's two profile files to the same files map:
`profile.config.yaml` → absolute PROJECT/pipeline/cfg/profiles/MODE/config.yaml;
`profile.runtime.yaml` → absolute PROJECT/pipeline/cfg/profiles/MODE/runtime.yaml.
Both carry raw-byte sha256. Config is Step1's direct --profile input; runtime is
prepare-overlay provenance, not recomputed when Step1 starts. The confirmed
5485c8a profiles have only these two files and no direct local jobscript dependency.
Other profile layouts require review, not recursive discovery. External images,
tools, references and license content are not frozen or copied. The six logical
refs do not claim complete workflow/environment reproducibility. Owner verified
5485c8a prepare/pipeline.py copies pipeline into staging, with ordinary supported
profile files; standard projects meet this boundary. This is not a claim that
arbitrary user-modified project symlink layouts are supported.

WGS owner verified commit5485c8a: configured analysis scope is **config.sample,
the unique data IDs**, not metadata row count. Join these to current sample_info
by 数据编号 and retain only data_id/sample_id/family_id in the database. Missing
or duplicate matching metadata is rejected; new_sample_info cannot expand or
replace scope. Both original tables remain in private evidence. Configuration
scope is not proof of scheduled/completed work: partial targets/--until and
module-specific subsets must be interpreted using later execution evidence.
Platform does not rebuild trio/pedigree or resolve contradictory user edits.

`WGS_ONPREM_SNAPSHOT_ROOT` is required only for execution registration: an existing
private0700 directory outside the project, default empty. Each server-generated
execution ID gets an exclusive0700 directory; files0600, fsync, manifest last and
directory fsync. DB stores immutable references, hashes, configured scope and
registered_by, not clinical/config contents or credentials. Manifest includes
platform owner, reported Linux uid/user, argv, original project location and
file hashes. Initial release label is explicitly **reported, not observed runtime**;
actual config bytes are captured independently and may differ from prepare.

New additive migration0026 (after0025) creates wgs_onprem_execution_snapshot,
keyed by execution ID, unique(analysis_id, operation_id). Existing Sample and
historical rows are not replaced. A DB/write failure must not authorize launch;
partial/unreferenced files are retained, not replayed or automatically deleted.

## Receipt and remaining launch gate

### Controller terminal and monitor attachment (2026-09-16)

The independent WGS supervisor owns a direct child running the **unchanged**
foreground Step1 and waits for that actual process. It does not load personal
authentication or call the platform. Only after wait returns does it atomically
publish PROJECT/.wgs-platform/executions/EXECUTION/gGENERATION/controller-exit.json.
The private one-shot launch context is not replayable permission; an exclusive
started marker refuses repeat supervisor startup, never authorizes recovery.
Supervisor loss, missing/incomplete final or unknown spawn result cannot produce
a terminal success or cause an automatic new launch.

Receipt schema_version=wgs.onprem-controller-exit.v1 has exactly:
platform_instance_id, project_uuid, analysis_id, attempt, execution_id, generation,
operation_id, native_execution_id, manifest_sha256, execution_mode,
execution_target, execution_user, execution_uid, hostname, started_at, finished_at,
wait_returncode, controller_exit_confirmed=true, evidence_method=direct_child_wait.
Times include timezone and describe the supervisor's child wait interval; rc uses
Python Popen convention (negative for signal). No argv/config/token in the receipt.
Writer fsyncs a same-directory temporary then publishes once without overwriting
an existing final; no symlink directory or world-write permission workaround.

Backend consumes only that fixed path under the current registered project. It
validates all execution identities and hash against the private immutable manifest.
Valid final updates WgsStageExecution/AnalysisRun to success(rc0) or failed(other),
preserving receipt hash, relative evidence key and safe controller_exit summary.
Completion scope is **requested_command**, never a claim that full analysis or
all Sample QC passed (dry-run/partial targets remain distinct). No Sample mutation.
Existing monitor_binding is preserved in terminal_payload_json.

Normal Local nonnegative completion permits a later execution; a signal or SGE
nonzero exit does not prove descendant/queued jobs ended. Such receipts display
failed but store relaunch_eligible=false and reject a new execution until remaining
jobs are verified. No automatic qdel, timeout reset, override or new review API.
Old-generation observation rejects409 before reading or modifying current state.
Missing/invalid final keeps last reliable state; raw native.exitcode remains
non-authoritative for controller termination.

After independent controller spawn, the personal-session helper calls
POST /api/wgs/onprem/executions/EXECUTION/monitor with the same four claim identity
fields. This endpoint grants no launch authority and starts no native process.
It creates only bio_wgs_native_monitor, fixed DagRun native__EXECUTION and exact
conf {pipeline:wgs, monitor_only:true, analysis_id, execution_id, attempt,generation}.
HTTP409 from Airflow is reconciled by reading and comparing that same DagRun conf;
a different conf is a conflict, not a match by name. Lost response/transport503
requires retrying **monitor only**, not registration/claim/spawn. Helper's explicit
monitor-only repair must use saved registration identity, not replay a grant.

Response schema_version=wgs.onprem-monitor-attachment.v1: analysis_id,attempt,
execution_id,generation,dag_id,dag_run_id,monitor_attached=true. Same owner/current
identity is checked on retry. Binding is retained per stage in terminal_payload_json
and current run.dag_id/dag_run_id; audit links it to the execution. Monitor feature
gate remains independent and default off; attachment does not unpause the DAG.

### Native observation boundary (2026-09-15 candidate)

Only registered current analysis/attempt/execution/generation can poll the internal
observe route. Safe summary is stored under params.native_monitor. New observed
start resets current progress/error summary, not historical execution snapshots.
No mutable config recapture during execution; exact project binding still required.
Missing/invalid files retain the last reliable state and a collection-error code.
Polling does not assert native heartbeat or process liveness. Raw command is never
stored/replayed. Native exitcode/finished_at are result evidence, not proof the
controller's post-workflow cleanup exited; the active execution is not released.
Final terminal adapter and automatic monitor-DagRun attachment remain pending.
Default-off WGS_ONPREM_MONITOR_ENABLED is separate from launch/registration gates.

The user requires deployed WGS baseline34bfcbf rather than unfinished newer4.2.1.
WGS candidateb07bbc4 carries only thin hooks onto that source; native Step1/profile
semantics are unchanged. Runtime version labels alone must not select test code.

### R2-3 one-shot claim candidate (2026-09-15)

Registration still returns launch_allowed=false. A separate, default-off
`WGS_ONPREM_LAUNCH_ENABLED` gate controls
`POST /api/wgs/onprem/executions/{execution_id}/claim`, using the same personal
session/CSRF and original owner. Request fields only: platform_instance_id,
operation_id(UUID4), generation(positive int), manifest_sha256(lowercase64hex).
No caller-supplied executable or changed arguments are accepted by this endpoint.

The backend checks current run/execution/operation/generation, private manifest
hash and identity, current binding/location and all captured source-file hashes.
It rejects evidence already present under the newly assigned native ID. A
conditional database update accepted→launching grants permission exactly once;
repeat claim409 and **never another grant**, including after a lost response.
This is at-most-one automatic launch attempt, not a guarantee of launch. Claim
does not set started_at, mark AnalysisRun running or contact Airflow/SSH/subprocess.
New operation registration continues to reject launching as a nonterminal state.
No new table/migration/lease timeout/lock service is added. No automatic path may
reset launching to accepted on elapsed time, unknown process state or API failure.

HTTP200 grant has schema_version=wgs.onprem-launch-claim-result.v1,
claim_granted=true, analysis_id,attempt,execution_id,generation,operation_id,
manifest_sha256,files,project_dir,execution_mode,execution_target,argv,
execution_user,execution_uid and native_execution_id:
`<analysis_id>-a<attempt>-g<generation>-<execution_id>`.
Other identity/state/input-hash conflicts409, unauthorized403/401, malformed or
unavailable input400, schema422. The grant is not an idempotent registration receipt.
Client must **never** treat registration replay or a saved grant as permission
to start another process. Before any native call, recheck grant/current bytes,
identity, effective Linux uid and original entry's absolute project path locally.
Lost/ambiguous claim response, post-grant validation failure or spawn uncertainty
stops automatic launch and requires review; don't request another operation.

The monitored claim rejects config/entry/directory/profile/executor overrides,
including --config, --configfile(s), --directory, --snakefile, --profile,
--workflow-profile, --executor, --cluster/--cluster-sync, --drmaa, --jobscript,
external --background/--worker, short -C/-s/-d and long abbreviations. These can
invalidate the fixed-file snapshot. Users may edit actual project config before
registration; original native commands remain unrestricted. This contract does
not yet support arbitrary composed CLI config overlays. Partial targets/--until
and dry-run are not proof of full analysis/QC completion, even on process exit0.

The WGS owner confirmed native started_at is written before Snakemake begins;
native exitcode appears before finished_at, and both precede final wrapper
cleanup. A future observer must tolerate partial evidence, distinguish controller
start from rule start, and not claim entire wrapper success solely from those
markers. Metadata command uses Bash quoting: never eval/replay it. Early errors
may produce no markers. Background parent exit0 is only a spawn acknowledgement.
Caller implementation, terminal observation and monitor-only DAG are still pending;
keep both native feature gates off. The claim candidate alone is not a deployment.

Response: schema_version=wgs.onprem-execution-registration-result.v1,
analysis_id, attempt, execution_id, generation, operation_id,
registration_status=registered, manifest_sha256, files(name→source/sha256),
**launch_allowed=false**. No private snapshot contents or absolute snapshot root
are returned. Receipt remains stable across retries; it is not live execution state.

R2-3 must connect caller-side current-file/hash/location validation, native argv
forwarding, once-only launch claim, terminal evidence and monitor-only DAG before
enabling monitored starts. In particular moved Step1 may still contain its old
absolute PROJECT_DIR: recording its bytes does not validate a repaired launcher.
The platform must not silently rewrite original WGS scripts. An accepted candidate
registration remains blocked until terminal evidence exists; no timeout-based
assumption that a controller is absent, no automatic restart or cancel endpoint.

Current/history Sample, QC, rules/log readers and fallback-path protection are
still R2-2/R2-4 work. Existing web-native runner snapshots are an older internal
contract, not the new CLI consumer; do not enable them as a substitute. No live
migration, real Local/SGE analysis, service deployment or production changes.
