# Same-execution monitor progress publication

Task: `W423-MONITOR-PROGRESS-PRESERVE-20261002`.
Owner: Airflow thread `01a0e728-4c99-71d0-87e9-987b311022c9`.
Coordinator: `019fa8d1-0d81-7e92-abee-8154dd1cf0a7`.
All times are UTC on 2026-10-02.

## Authorization and outcome

Direct human message `01a0fd02-c837-7e63-9367-04202221fc6f` approved the bounded
shared monitor fix, minimum BS10610 verification and reviewed BS96 deployment.
Message `01a0fd0f-0e11-7901-8f07-2842df964ff8` allowed only monitor reconnection
if the existing mechanism safely reuses the original Master, Workers, attempt,
inputs and completed rules; otherwise stop. Both messages were read directly in
the coordinator thread. This supersedes the previous instruction to leave the
progress code unchanged, while retaining the completed paired-node change.

The source candidate passed minimum synthetic acceptance. Production activation
and current-run reconnection are stopped at the existing API/reader boundary.
The current progress flicker has not been declared fixed in production.

## Minimal implementation

Only `scripts/cce_paired_runtime.py` changes product behavior: 35 lines of diff,
lines, candidate raw SHA256
`34606ce7428557f8ac05bd811a8acf6b0078e9e83dd29a7e89e30639240ce2c4`.

`monitor_registered` hands its returned, fully validated observation to the
query owner's healthy save through a local callback. That one atomic status
write publishes the new WGS nested Master and frozen locators, or derives the
normal GATK counters from the same observation. It cannot expose a healthy
confirmation with old or missing counters before the ordinary collector writes.
Unknown counts remain `None`; they do not become a measured zero. Existing
rule-evidence errors remain degraded until the evidence collector recovers.

Non-healthy saves retain safe progress and evidence-error fields, and keep the
new control timestamp. Existing backend `query_unconfirmed` consumers freeze
the previous business progress/time while consuming the new retry marker. No
old `updated_at` is copied back. No previous receipt/binding is passed as trusted
writer details; the verified gate emits those fields through the existing path.

The typed analysis/attempt/stage/generation/execution/request-hash check, original
deadline, save-before-request, GATK fsync, bounded retries and terminal fences
are retained. QueryReconnect, native runtime, gates, frontend, backend behavior,
services, node configuration and the accepted Step2 fix were not changed.
WGS healthy publication keeps the existing `_binding_run_label` validation,
also used by the normal outer monitor. No unvalidated-label fallback is present.

## Actual test environment and evidence

14:44:18 preflight matched `server10610`, UID 6708, control root
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`, current
`releases/20260912-opt-4d3d24e6`, actual backend/worker source mounts and gates.
Existing backend image `8491604e…` supplied its installed dependencies; the test
container used network `none`, a private evidence directory and read-only source
mounts. No dependencies were installed and no running service was modified.
Maintained native source remained raw SHA `bfa1e15f…` throughout.

Private remote evidence root:
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/wgs-monitor-progress-preserve-20261002T1444Z`.
Private local evidence root: `.codex-artifacts/wgs-monitor-progress-preserve-20261002/`.

| Phase | Actual result | Raw output SHA256 |
| --- | --- | --- |
| RED2 against old paired `981e7e82` | pytest RC1, 8 expected failures, 2.05s | 3c2dc37188de9009653886167844216ea0833990d59385e1bb0f15fd8b2cc6fb |
| GREEN against paired `34606ce7` | pytest RC0, 24 pass, 4.14s | 55ab65a547a1e8c7a6965839b2849b0d55cc6580cb0f27f2fc0208bc7e6340bb |
| Existing selected reconnect cases, same paired `34606ce7` | pytest RC0, 6 pass, 52 deselected, 13.63s | 368cb061fc61ce04afefbce142100cacad4678b7bf16d8f3a7259635b5a9ad59 |

Selections: `scripts/tests/test_cce_monitor_reconnect.py` and
`backend/tests/test_cce_monitor_reconnect_ingestion.py`. The new tests cover
atomic fresh business publication, retained bridge failure, absent counts and
actual WGS/GATK ingestion: non-healthy control advances while business time/counts
stay fixed; a complete new observation then advances to the new 7/333 result.
Existing scope, retry, exhausted and callback/DagRun fences remain covered.
No whole P0 suite, clinical task or production canary was run.

The final selection was `scripts/tests/test_p02_selected_monitor.py -k reconnect`.
Its XML contains the required initial-submission reconnect pair and four existing
fresh selected-monitor reconnect/downstream cases. Actual collection was six,
not the expected two; no additional rerun followed. At15:14:53 the TEST host,
current release, actual mounts/gates and maintained native hash matched again.
The existing plugin image `8ba8858e…` supplied the selected fixtures. Its native
source and service containers were unchanged; the task container had no network.

Only the affected WGS/reconnect synthetic copy was corrected before freezing:
new `master-job.yaml` run label, any template/selector references and the new
control binding use `cce-run-0123456789abcdef`. Original bundle/native files were
not edited. `files_sha256` does not include the Master manifest; the later native
handoff/CREATE intent freezes its new `manifest_sha256` and native request hash
normally. The retry wrapper forwards the new internal `observation` keyword.
This restores the existing normal gate contract without patching its validator.

The runner records the child pytest exit code; its own SSH command may return0
after recording an expected RED. Original failed methods are preserved:

1. The initial isolated image lacked `httpx`: collection RC4, not a product RED.
   It was replaced by the existing TEST backend image, without installing a package.
2. The new helper set a fake clock but initially kept real sleep. The exact
   network-none candidate test container was stopped (RC137); no service changed.
   Its fake sleep now advances the same clock; product retry/timeouts were untouched.
3. An intermediate run had four WGS fixture root-contract failures and four real
   GATK failures. The fixture now uses its separate approved synthetic runtime
   root and attempt directory; no production guard was weakened. RED2 above is
   the valid eight-case reproduction.
4. Tar reported source mtimes about17s ahead of the remote clock. Original warning
   output was kept; archive/source hashes matched. No clock or timezone changed.
5. A selected-fixture run used the backend image without its Kubernetes plugin:
   collection RC4. The existing plugin image was used for selected cases instead.
6. The intermediate selected run had one WGS invalid-label fixture failure and
   one GATK pass. The WGS fixture called the shared monitor directly, skipping the
   normal outer monitor's existing label validation. A temporary product fallback
   was rejected by independent review and removed: product SHA remains34606ce7.
7. An attempted compound `-k` CSV split its words into separate pytest arguments:
   RC4, no tests. The simple selection above is the actual final acceptance.

## Current-run activation boundary

Current run: `WGS_20261002_095408_323D3F`, attempt1,
action `resume_c17cd7cf8b3ab245ae80304d`, Step3 generation1,
execution `wse_b7f6bc858e2a3284ed0c01a0`, request hash
`744d85bdf5b47002a834c16022e628ff8b83ea2ba1448d0454f7e007fff4d8b1`.
One authorized narrow read at15:12:45.265325 reconfirmed actual production
container identities, normalized mounts and gates, the same full Step3 tuple,
public/Airflow/native running and the original five samples. The wait task's
15:12:40–42 poke returned to `up_for_reschedule`; the original start task remains
successful. Native PID/PGID/SID944075, bootef1fa37a and start4483218750 are unchanged.
Query control is healthy; status SHA
`9a8b63190bedc950d41922dacbd9d42c2b2eb841b7a372b38cce52c355769c9c`
has `master=null`, still the old overwrite behavior. The13:16 six-rule count is
not a fresh measurement. Evidence: task-private
`current-run-readonly.final.safe.jsonl`. No further production read was made.

Two earlier helper preflights stopped before API access: one treated Compose
input as Docker inspect data, the next compared complete Mounts dictionaries.
Using the original actual-container snapshot and sorted Type/Source/Destination/RW
mount tuples corrected those local helper errors; the effective read above passed.
They are not production failures or evidence of service drift.

Both WGS and GATK import `monitor_registered` outside their monitor loops.
Replacing disk source does not replace current PID944075's loaded function.
Normal native observe reads receipts/process state and does not run this save.
Each existing monitor call does reload and verify the disk source/policy pair;
two separate atomic replacements could therefore expose an intermediate pin
mismatch to an active reader. An empty-reader deployment window is not proven.

The existing `interrupted_monitor_action` exception requires a failed monitor,
scoped blocked/exhausted marker and a Step3-origin action. Current c17 originated
at Step2 and remains queued while the run is running. `request_resume_stage`
rejects another stage at that active-action gate before its generic branch.
The generic branch is not universally failed-only, but cannot be used here.
Legacy reattach waits for the original worker lock; it does not replace a healthy
native monitor. A general Master Resume can also recover compute and is not a
monitor-only guarantee.

No POST was sent to test rejection, and no PID, DB/status/marker, receipt, lock,
generation or action was changed to satisfy a gate. No new interface, hot injection
or recovery framework was introduced. The authorized conditional activation is
stopped because the existing mechanism cannot satisfy this current state.

## Seven-field handoff

| Field | Result |
| --- | --- |
| Task/scope | bounded shared monitor source fix ready for independent review |
| Workspace/version | gatk-prod-compat; paired candidate34606ce7, old accepted production981e/ec6f retained |
| Implementation | one shared product file, three synthetic test files, runtime contract and this record |
| Acceptance | valid 8-case RED, 24-case GREEN and 6 existing selected reconnect passes; raw logs and XML retained |
| Deployment | none; current running monitor is unchanged and still uses old code |
| Evidence | task-private local/remote paths above; no patient or credential content |
| Remaining | no viable existing monitor-only activation path in the current state; production held, unique hourly continues original Step3–6 |

Coordinator independently reviewed the strict-label source and the final fixture,
read the original24-case GREEN plus final log/XML, and accepted the source
checkpoint:30 cases passed. No more tests or production reads are required.

## Future activation and rollback conditions

There is no current production GO. A later proposal must first prove an empty
window for every affected WGS/GATK consumer that checks the source/policy pair,
read back the exact installed source/policy, and show an existing normal mechanism
can reuse the original Master/Workers/attempt/inputs/results without changing
compute. Current running/healthy Step3 under a Step2-origin action fails that
condition. No new production package or interface was prepared for this task.

The rollback candidate remains the actually installed Step2-compatible pair:
paired source `981e7e82a0054a38d233a64c4120219094c34879b5820661d08907230806f588`
and local policy `ec6f35920a10e2879f34602c112325d31be1aaedee68717d3027caa8b2ba5210`.
Use exact private original bytes and the same empty-consumer requirements if a
future release is approved; never downgrade the accepted Step2 fix or replay an
old deployment guard. No rollback is needed or executed now.

The paired temporary96 configuration and all existing successful stages remain
unchanged. No completed rule is recomputed. Original FASTQ/OBS/sampleinfo/pending,
references, analysis/results and all new/old evidence and other batches remain
protected. Full Step1–6/final-result completion is still outstanding. No Step7
or cleanup was performed.
