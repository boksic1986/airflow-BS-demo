# Runtime progress and unified96: readonly diagnosis

Task: `W423-323D3F-EVIDENCE-ROUTE-READONLY-20261002`.
Evidence times below are UTC on 2026-10-02; 13:19Z is 21:19 in Asia/Shanghai.

## Latest human decision — overrides the earlier candidates

Final overriding instruction was human message
`01a0fcd4-a575-7e53-bde4-6bef27dd82b0`: leave unchanged code/display in place and
fix only WGS/GATK node switching. Progress rollback and new progress patching
stopped. The common temporary96 configuration was actually applied at14:15Z,
with the same current execution and natural Airflow wait handoff confirmed at
14:17:56Z. See [the actual paired-node release](../releases/2026-10-02-common-control-node-bs96.md).
The earlier rollback discussion below is historical evidence, not a current task.

## Historical instructions and diagnosis — superseded

Earlier human message `01a0fccf-9928-7840-b9c2-97cedcde5e76` requested a rollback
assessment for the progress-clearing regression. The coordinator reviewed the
exact 728f098 diff, and the Airflow owner completed the existing-artifact/node
comparison below. That assessment did not produce a deployment or recovery.
The final instruction above stopped this work; no progress rollback remains
pending.

At 13:30Z the Airflow owner directly read coordinator-thread human message
`01a0fccc-0a41-7151-8ec4-ab78893921ba`: do not make the proposed fixes; return to
the previously accepted mode. The default control node remains200; when200 is
blocked, WGS and GATK use96 together as a temporary alternative. Implementation,
display and accepted versions should remain consistent across nodes.97 is not an
alternative. The current323D3F attempt1 execution on96 stays in place.

The earlier new-patch and public-node-variable redesign candidates below were
withdrawn. The minimum comparison used existing records and is complete. The
progress rollback assessment has stopped; the accepted Step2 repair and identity
fences remain in place.

The existing08:44:40Z switch record identifies only the added96 SSH Host and
worker/scheduler WGS alias change. GATK, other environment values, images,
mounts, backend, observer and frontend were unchanged by that switch. Thus the
switch did not establish a frontend version regression. Returning to200 has not
been shown to cure the shared progress-write behavior. Missing historical
baseline facts are marked unknown instead of requiring more remote reads.

## Existing200 mode versus96: minimum artifact comparison

| Item | Existing200 record | Actual96 record / difference |
| --- | --- | --- |
| Control route | original wgs-node200 → .200 SSH stanza retained | 08:44 only WGS worker/scheduler alias changed to wgs-cce-node96; GATK stayed200 |
| Airflow/other services at switch | original env/mount/image/command/user | image58195672 and every other env/mount/command/user unchanged; backend/observer/frontend not replaced |
| Host configuration | original initial-recover env/policy |96 later added WGS TZ=Asia/Shanghai and initialized the original policy journal directory; current200 equivalents not freshly verified |
| Paired platform source/policy | original accepted pair66f7999a / 033a5819 |12:42 only96 changed to981e7e82 / ec6f3592 for the accepted Step2 repair;200 unchanged by that deployment |
| Native/bootstrap lineage |04:07–04:10 maintained089/c8d07c21/e502 wheel and b928 pair selected/import receipts |Step2 deployment preserved native/guard/dual bootstrap hashes; current200 complete byte inventory not repeated |
| Progress display baseline |no preserved equivalent200 Step3 live status→API observation in this task's known records |13:16 current96 same-tuple counters erased/restored; UI unchanged at node switch |

Original evidence is the08:44:40Z and true paired install/import/select entries in
`HANDOFF.md`, including04:09:43–04:10:07 actual four-consumer imports (raw receipt
SHA211287bf). Those imports prove accepted pairing/admission, not a successful
Step3 progress display baseline. The exact later96 original/new pair is recorded
in [the Step2 release record](../releases/2026-10-02-step2-initial-routing-bs96.md).
The08:44 safe route candidate/activation records are
`new3a001e-a2-node96-route-candidate.jsonl` and
`new3a001e-a2-node96-route-activation.jsonl` in the private ops evidence directory.

The existing two runner-alias configuration choices and preserved200 SSH stanza
are configuration candidates for the original mode. They have not been applied
by this task, and alias restoration does not establish matching current versions.
In particular,200 has no fresh evidence of the accepted Step2 source981e/policyec6f.
Current96 attempt1 must stay on its current execution with its identity fences and
Step2 repair.

### Rollback evidence and feasibility boundary

Local Git identifies reconnect wiring commit
`728f0983acd2a1f4de91a832faa7d308fd6ef62d` and its parent
`400bf77ff9880d0f10d0a267547c642a8ad03760`. The commit changed paired runtime,
query reconnect and WGS gate. The parent is a source comparison candidate; the
known records do not establish it as an installed, accepted normal-progress
production artifact. Likewise66f7999a is an accepted older paired source, not
proof of a progress-safe version: the problematic confirmation path already
exists in the current code lineage before the Step2-specific change.

Replacing the whole current paired file with66f7999a would remove the accepted
Step2 routing repair. Reverting the complete728f098 change would also affect
finite reconnect and false-failure/terminal handling across its three files.
Neither is a proven safe rollback of only progress clearing. The coordinator's
exact hunk review must distinguish a genuine removable regression from a new
behavioral repair; the latter must not be labeled a rollback. No such production
operation, new source edit or test was performed here. The known-normal installed
progress artifact and a safely independent rollback target remain unconfirmed.

## Authority and scope

Coordinator thread `019fa8d1-0d81-7e92-abee-8154dd1cf0a7` directly verified human
message `01a0fcb5-7d30-7b62-ba01-ab2ff5a5d9b2`: diagnose Run Tracker waiting after
refresh and the remaining WGS96/GATK200 control split. The Airflow owner performed
the bounded production reads; two agents reviewed local source only. The
coordinator accepted the progress evidence and instructed that the remaining
precise GATK96 configuration read finish before reporting. That read finished at
13:19:47Z. This record closes that live diagnosis. The final human instruction
above selected only the existing paired node configuration. Its actual release
is complete and linked above; no progress rollback assessment remains active.

## Current monitored execution

| Field | Actual identity |
| --- | --- |
| Batch / analysis | `20260927D-test1` / `WGS_20261002_095408_323D3F` |
| Attempt / action | `1` / `resume_c17cd7cf8b3ab245ae80304d` |
| Stage / generation | `step3_monitor` / `1` |
| Execution | `wse_b7f6bc858e2a3284ed0c01a0` |
| Request hash | `744d85bdf5b47002a834c16022e628ff8b83ea2ba1448d0454f7e007fff4d8b1` |
| Airflow | Current resume DagRun running; start Step3 success; wait Step3 up_for_reschedule |
| Native observation | Master RUNNING, 6/333 rules, 1.8%, retry0 at 13:16:46 and 13:16:59 |

The helper asserted the request tuple and each status execution/generation/hash.
Prepare, Step1 and Step2 remain successful. Step4–6 and final results are not yet
complete. The sole hourly monitor continues to follow this identity.

## Progress loss: live evidence and source chain

The same Step3 status alternated within one bounded read:

| Status updated_at | Status SHA prefix | Business observation |
| --- | --- | --- |
| 13:16:46.010938 | `a967353d` | master present, RUNNING, completed6/total333/percent1.8 |
| 13:16:53.117358 | `799da7c2` | monitor confirmation, reconnect healthy, master and counters absent |
| Still read at 13:16:58.781 | `799da7c2` | same confirmation-only document |
| 13:16:59.489335 | `11bc2baf` | master and 6/333/1.8 observation restored |

Workspace HTTP200 at 13:16:47 and dashboard HTTP200 at 13:16:48 returned the current
running Step3 with `progress_available=false` / `stage_progress.available=false`,
null counters and source `wgs-runtime.stage-status.v1`. Their stored stage timestamp
was 13:16:39.653785. The screenshot's waiting text agrees with those API fields.
This establishes a progress publication defect while the workflow continues.

Local source review identified the matching path:

1. `cce_paired_runtime.py` query completion calls `owner.confirmed()`; reconnect
   saves healthy. `_monitor_query_owner.save` carries only selected top-level
   progress fields into `gate._write_status`.
2. WGS `_write_status` constructs a new document without retaining the nested
   `master` observation. Step3 restores `master` only after `_sync_rule_evidence`.
3. `wgs_observer.py` handles the interim missing master/job by upserting unavailable
   progress, overwriting previously stored counters. Dashboard/workspace read that
   stored projection.
4. `RunProgressBar.tsx` shows Waiting for runtime evidence when an active stage's
   availability is false; `RunTracker.tsx` passes that API availability through.

Relevant reviewed locations: paired 1376–1381/1422–1427, reconnect131–133,
WGS gate548–558/583–585/2280–2294, observer1008–1028/1487–1491,
RunProgressBar6–12 and RunTracker193. Deployed backend observer SHA is
`f0b596f6e543da0f1a4c43b9528ab331b3c0a435eeb498a58312cd2e143bc80b`;
workspace `43ff9053`, dashboard `1d09d0f5`, monitor observation `455d4c2c`.
Observer-container module SHA was not separately read; frontend change history was
not established by this diagnosis.

Withdrawn earlier repair candidate: query-health persistence would retain validated business
observation for the same execution tuple and its actual observed time. A control
confirmation must not manufacture fresh progress or clear a complete same-tuple
observation. Degraded/unconfirmed queries must retain their real freshness and
health semantics, and evidence must never carry across generations. Repair the
shared publication/projection contract; an independent UI placeholder change is
not required by this evidence. This is retained as a historical diagnosis proposal,
not a current task. No source was changed in this task.

## Actual control consumer routes

The read first verified server96, `/data/airflow-WGS`, actual current symlink,
container IDs/mounts, Production/auth/WGS execution/adapter gates and effective
auto-dispatch false. Raw backend AUTO env true is not the effective setting.

| Consumer | WGS | GATK | Actual mechanism |
| --- | --- | --- | --- |
| Airflow worker | wgs-cce-node96 →172.17.61.96 | wgs-node200 →172.17.61.200 | pipeline-specific restricted command, common RO SSH config |
| Airflow scheduler | same96 | same200 | same actual aliases/config |
| Backend | shared WGS runtime RW / evidence RO | shared GATK runtime RW / evidence RO | produces requests, no SSH route |
| wgs-run-observer | WGS runtime/evidence RO present | GATK runtime/evidence env/mounts absent in inspect | shared observer module, declared pipelines wgs,gatk, interval5 |
| Maintenance/cleanup DAGs | WGS alias96 | GATK alias200 | reviewed consumer resolves the same pipeline routes; no cleanup invoked |

Actual worker `acb2289e`, scheduler `d206c0bf`, image `58195672`; SSH config
`df94468ad8cb7bbc03e16327d9accdbbe259d6d29c3a2c96a1072f47303e5370`, strict checking
true, ctapa/22. Backend `a70599bd` source is step7-perf-fd85593 merged/backend;
observer `e5c018a5` source is unified089 merged/wgs-run-observer. The missing GATK
observer mounts are an observed read-plane gap, not the cause of current WGS
progress erasure.

## Existing GATK96 prerequisites and limits

At 13:19:47Z existing-key/strict-pin read on server96 as ctapa6801:520 found:

| File/configuration | Actual facts |
| --- | --- |
| GATK forced-command.sh | present, nonsymlink, 0700, SHA40cf7002, references current common release |
| GATK runtime.env | present, nonsymlink, 0600, SHA475c5f78; read as literal selected fields, not sourced |
| gatk_runtime_gate.py | present, 0644, SHAcfee7594 |
| cce.yaml | present, 0600, SHAa5952014 |
| Shared pair | bootstrap b928a9df / policy ec6f3592 / platform pin981e7e82 / original journal root |
| Runtime requests/evidence/transfer-progress | original roots present, 2770, readable/writable by ctapa |
| Repository | original master088-r4-417de59 release present, readable, not writable by ctapa |
| Result root | `/sg2/50.ctapa/Clinical/WES_Clinical` present, readable/writable by ctapa |

The configured Python is an existing symlink; its target was not validated here.
The narrow authorized_keys filter emitted no matching `/airflow-` command entries.
That empty result proves neither missing authorization nor readiness: the actual
Airflow key/restricted dispatcher handshake was not exercised. Workflow/entry
invocations, configuration imports and writes were zero.

Withdrawn earlier route candidate: one public deployment control-node authority supplies
both pipelines' target96, retaining each adapter's restricted command, identity,
input/profile and policy validation. Preserve the existing wgs-node200 alias's
meaning. Include the actual observer GATK runtime/evidence read-plane gap in the
deployment plan. Restricted96 admission still needs bounded confirmation in that
future scope. Updating shared worker/scheduler environments can require container
recreation; active WGS interruption risk cannot be dismissed. No restart or shared
bootstrap/native/policy replacement is included in this diagnosis. The current
direction is the existing default200/common temporary96 mode, without a new
configuration architecture.

## Evidence, execution failures and seven-field status

Private evidence directory: `.codex-artifacts/wgs-runtime-evidence-route-20261002/`.
Original records: `service-api-route.safe.jsonl` (13:16:45–13:17:03Z) and
`gatk96-entry-config.corrected.safe.jsonl` (13:19:47Z). No credentials or patient
values are included in this document.

The first service helper could not read the host SSH config as its SSH user
(PermissionError), before API/sidecar reads. It was narrowed to hash/config
resolution inside the actual consumer containers with their default user. The
first GATK helper treated a policy trust entry dictionary as a path (TypeError);
its local parser was corrected to use the recorded path. Both corrected reads
exited0. These are helper method failures, not new production faults. No ACL or
production data was changed. Tests were not run: scope was diagnosis only.

| Status field | Outcome |
| --- | --- |
| 1 Task / scope | W423-323D3F-EVIDENCE-ROUTE-READONLY-20261002; progress and unified96 diagnosis complete |
| 2 Workspace / version | gatk-prod-compat; jiucheng/ops/WGS-6C78D5-prepare-recovery-20261002; source b861052/981e7e82, docs baseline adc336d |
| 3 Implementation | no implementation in this task; root cause and minimum candidates recorded |
| 4 Acceptance | bounded readonly live chain plus independent local source review; both final helpers RC0; no tests |
| 5 Deployment | none in this task; current WGS continues same attempt/action/execution |
| 6 Evidence | two private safe JSONL files above, exact times and actual mount/route/receipt hashes |
| 7 Blocker / next owner | historical diagnosis complete; successor common-node configuration is now complete per the release linked above; progress code stays unchanged; sole hourly monitor follows the original Step3 execution |

Rollback is not needed for production because this task made no production
changes. Existing inputs, OBS objects, results, runtime evidence and other runs
remain protected. Full Step1–6 completion has not been declared.
