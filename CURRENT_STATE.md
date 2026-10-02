# Current state

## 2026-10-02 W423-A468E9-HOURLY-20261002 — ACTIVE only follow-up

### W423-A468E9-INITIAL-RECOVER — authorized implementation, not deployed

Direct human message 01a0fa57-9513-7c20-a09b-b100f8d2066a in coordinator
thread019fa8d1-0d81-7e92-abee-8154dd1cf0a7 says "修复后 rerun" after the
bounded initial-submission reconciliation proposal. Verified by read_thread
on2026-10-02 Asia/Shanghai. This supersedes the authorization hold below only
for A468E9/a1: retain original five samples, ten FASTQ, successful Step1 and
all old Step2/gen1 evidence. Native owner implements the existing recovery
branch; Airflow owner supplies the thin consumer and remains sole production
writer; coordinator reviews exact candidates and pre-deployment fingerprint.
No selector/package switch or recovery POST has occurred. Normal API recovery
must prove START was never sent, complete absence of active writers/Jobs/Pods/
Workers, unchanged input and exact pending-owner CAS before same-attempt new
Step2 generation. Unknown evidence blocks. Existing hourly automation remains
unique and read-only while this owned implementation is in progress; it must
not dispatch duplicate development. Source GREEN is not current-run recovery.

Platform prelaunch snapshot hook is implemented and minimally validated only:
BS10610 real StageExecutor21b505da RED5, final GREEN5, adapter SHA91e05347.
Old dispatch/business receipt/stderr are frozen before overwrite/spawn using
nonblocking worker lock. Native initial-abort/capability integration is pending;
no package/selector/API recovery action occurred. No backend/DAG/API/DB change.

Human-authorized status-summary owner is thread01a0b254-07b5-7352-99aa-871b117459ad.
The12-item existing-source snapshot was delivered to that owner and coordinator;
hourly monitor now reports substantive changes/completion/blockers to both.
This changes reporting only; original scope, cadence and runtime remain unchanged.

Only active follow-up: WGS_20261001_210659_A468E9, current attempt 1,
20260927D-test1. Hourly live read 2026-10-02 07:20 Asia/Shanghai found Step1
SUCCESS: 10/10 files, 522,508,028,738/522,508,028,738 bytes, native receipt
ed0959d7 matching wse_ec58be/gen1/hash f0486b75. Upload ended06:48:47.
Step2 wse_1fd307e0dd889fecc284a93a/gen1/hash c0bc4e60 failed06:52:32:
`Master original handoff deadline changed`. Platform/DagRun failed; Step3–6
have not started. Exact Job/Pod and frozen run-label Job/Pod inventories are empty;
initial journal remains created, handoff JOB_CREATED, directory lock OWNED with
initial action/gen1 and empty Master UID. No START intent/confirmation or native
RUN_COMPLETE/RUN_FAILED final proof exists in the selected local evidence view.

Confirmed platform wrapper root cause: native CREATE intent froze1790895698.794229,
wrapper journal/handoff independently froze1790895698.8144848,20.2558ms later.
Minimum platform fix inherits the validated native intent deadline; BS10610
real-native RED reproduced both WGS/GATK, GREEN19passed/1intentional skip plus
4negative guard cases passed. Source candidate only, NOT merged/deployed; native
core/old evidence/locks are unchanged. Ordinary same-attempt Step2 resume refuses
the absent unconfirmed Master. A separate bounded initial-submission reconciliation
design is ready for coordinator/human decision; do not POST or invent final proof.
See docs/reviews/2026-10-02-wgs-a468e9-step2-deadline.md. The full batch is not
complete; retain the monitor and follow this current a1, avoiding repeated probes
or implementation while the required new native scope remains undecided.

Coordinator has accepted the retained RED/GREEN evidence and final independent
read-only source review for candidate 1c6b274: source ready, no blocking findings.
This does not approve deployment or current-run recovery. It has already asked the
human about the separate native reconciliation scope; reply is pending.
Keep candidate unmerged/undeployed. Hourly checks remain read-only: if current
a1/gen1 failure is unchanged, stay quiet and do not repeat native diagnosis,
tests or retries. New human authorization or material evidence is required
before advancing the recovery design.

Directly verified human message 01a0f953-fa91-7ef0-9e4a-4b956784104c requests
hourly monitoring, communication on issues, minimum scoped repair and recovery
until the full workflow ends. Unique heartbeat automation wgs-test1 is ACTIVE,
once per hour, targeting thread 01a0e728-4c99-71d0-87e9-987b311022c9; saved TOML
readback matched and no matching monitor already existed. Unchanged state stays
quiet; report issues, meaningful progress and completion. Complete and remove
the monitor only after Step1–6 final receipts, delivered results and consistent
Airflow/platform success. Scope remains this current attempt: no Step7 or repeat
of the completed deletion, creation, prepare/profile or earlier recovery scopes.

## 2026-10-02 W423-PREPARE-6C78D5-20261002 — scoped recovery COMPLETE

User explicitly confirmed 2775/0664/0775 and then authorized deleting only the
online records for 20260927D-test1 (WGS_20261001_200308_6C78D5, failed) and
20260927D-test (WGS_20261001_180321_BE4F5F, cancelled), followed by one normal
resubmission of test1 under its original label. The earlier new-label approval
wait is superseded.

Exact deletion is complete: two Airflow DagRuns and two parent business records,
27 owned rows total including 5+5 sample rows. The three old audit rows remain;
two deletion audit rows were added. Both old IDs return 404 from business API
and Airflow. Related global slot/lease/reference/intake/draft/observer counts
were zero; original 5035B0 success and all its fields are unchanged. File
deletions: zero. The private snapshot uses 0600 files/0700 directory, SHA256
660bef282eb17d9ba7713229d3a55da85b8df14d92492c1f86f33865b8d2e5de.

One normal POST returned 201 and created WGS_20261001_210659_A468E9, attempt 1,
for 20260927D-test1 on wgs-4.2.3-3f98682-perm2775. The original five-row source
SHA starts 48f5c4fc; normal all/default configuration approval returned 200.
Sampleinfo and prepare-analysis acceptance passed: prepare_analysis success,
ready=true, artifact_pending=false, failed=false, generation 1,
execution_id wse_a4e1a8881a3a550bc77baa29, request SHA256
a0129d092d247b4173c4ddd062121104a688d6963a6c00297407b227261ad7aa.
Registered receipt SHA256
743a2d45556ea1a4edca36ce652a0c857925673dcedd0a9deab797e2ae1055d9
matches the node status file; prepare_handoff_receipt is present. The new request
freezes corrected profile raw SHA 26b6fb15; WGS source 3f98682 and native 0.8.9
remain selected. API sample_count=5, sample_scope_status=ready.
Exact deletion, one normal resubmission and prepare acceptance are complete.

Direct read_thread verification of the human instruction in airflow-cloud-demo,
message 01a0f918-6569-7df3-ac4a-ac0c28f1c433, confirmed "修复后 rerun".
The latest deletion/resubmission request has no restriction to stop before
execution. Under this original authorization, one normal
POST actions/start-wgs-execution for A468E9 returned 200, preserving the same
five-row/all/default selection and normal dispatch/lease gates. Current
submission_phase=approved, config_approved=true, execution_approved=true.
Actual Step1 dispatch/execution acceptance passed: Airflow execution approval,
execution commit, upload-slot acquisition and upload start are success;
the Step1 upload waiter is up_for_reschedule.
Dispatch is running/CCE/committed, attempt 1 revision 2. Step1 execution is
wse_ec58be0b95c3e84d357d60e5, generation 1, request SHA256
f0486b753e23f7a523e728a4d5df989589b6d84e9ed6c1aaae62ba573e0ef8be.
The normal slot wgs-obs-upload-01 holds A468E9-a1-input. Full batch execution
is not complete and batch success is not claimed; continuation belongs only to
W423-A468E9-HOURLY-20261002 above.

PROD catalog receipt 10951f7a and phase source 49531b9 remain selected;
backend a70599bd/observer e5c018a5 retain original code, ten other IDs unchanged.
UE04/05/06, old Step1 and WGS-PANEL deployment are complete; do not reopen them.

## 2026-10-02 WGS-PANEL configuration COMPLETE

TEST and PROD now select `wgs-4.2.3-3f98682`, source commit
`3f986821172e5fbd5f5abd1213baea64c6b976f9`, original wgs-4.2.3/r1 profile
raw SHA `f0150c60…`, pipeline build `051371a9…`. Native changed only the
profile build field; AF added exact roots/private prepare mappings and the
verified unchanged rule inventory. AF source `fd0a01b` changes only phase JSON.
Both catalog registration/CAS and authenticated panel GETs passed; formal
health/index200 and unauthenticated401. Original options/gates/watermark and
historical entries/requests/bundles remain unchanged. PROD backend0c9914ab and
observer2dac00a9 load the exact policy file; ten other service IDs and fd855934
product code mounts are preserved. No full tests, analysis or cleanup ran.
Only normal branch synchronization and concise docs close this task. See
[release record](docs/releases/2026-10-02-wgs-dnascope-panel.md).

## 2026-10-02 STEP7-PERF fix and BS96 release COMPLETE

User-authorized Step7 function and webpage loading fixes are released from
source `fd8559347dc71ddd015e8c3c757d1805d33260f7`. Normal atomic fast-forward
synchronized main and `jiucheng/release/production`, retaining accepted
UE01–UE06/native089/WGS423/GATKr5 history. Both coordinator review gates passed.
Focused tests ran only on BS10610: Step7 GREEN37, backend read GREEN26,
frontend24 selected GREEN plus final7 affected GREEN, tsc and production build.
Original RED failures and fixture corrections remain in the evidence record.

TEST and BS96 check/apply/accept passed. BS96 applied at
`2026-10-01T17:36:40Z` (2026-10-02 01:36:40 Asia/Shanghai), replacing only
backend `ef698b65…` and frontend-nginx `04811cf1…`; ten other service IDs are
unchanged. PROD packet SHA256 `26ba1e4d…` binds the actual 110-file backend
overlay, nine reviewed increments and three-file dist. Inherited Heavy
`dd4fb66…`, observer/Airflow/node layers and the original current symlink remain
preserved. Formal gateway health/index returned200, served index matches the
build, and unauthenticated API returned401. WGS/GATK execution stays true,
PROD scan=true/effective auto=false, original watermark unchanged; catalog
remains `wgs-4.2.3-bafd27c`. All27 business runs remain terminal (23/2/2).

Single internal GET samples: default20 list 2.278426s before → 0.166185s after;
historical GATK detail 0.483357s → 0.067499s. Warm cache is possible; these are
not browser timings. No original Step7 action was retried, stopped or deleted,
and no clinical/SFS/OBS data action was performed. Docs closure only follows
this accepted deployment. Exact mounts, rollback pins, tests and limits are in
the [release record](docs/releases/2026-10-02-step7-run-pages-fix.md).

## 2026-10-02 STEP7-20260927C read-only diagnosis complete

WGS_20260928_130059_3B40E3 attempt1 remains biological success/11 samples.
Its Step7 action step7-sfs-2e667d84a31c/generation1 failed before actual cleanup:
the request carried stage_execution protocol cce.stage-execution.v1, while
the installed node gate admits only Step1-6 for this marker. The exact worker
traceback is ValueError: unsupported WGS stage execution protocol or stage,
at wgs_runtime_gate.py2990, before the normal worker/cleanup shell. This is
not a captured0.8.8/0.8.9 version-check exception. PID5143 was absent on the
matching node boot; the stage receipt remains accepted without terminal success.
The original Airflow TI reported 清理进程已退出，尚无成功回执; a later callback
replaced the UI message with the generic monitor-stopped fallback. No retry,
POST/probe/clear, deletion, DB direct access, fix/deploy or test occurred.
Actual cloud retention/removal by other actors is not established. See
[Step7 diagnosis](docs/diagnostics/2026-10-02-step7-20260927C-readonly.md).

## 2026-10-01 PERF-RUN-PAGES read-only diagnosis complete

BS96 restored backend7aadaf93/frontend4df1, actual mounts and eleven relevant
source hashes matched final80; original gates were preserved. Existing internal
auth GET timing: deployed20 runs200/2.278426s, GATK6 runs200/0.062800s;
historical GATK F246CD detail200/0.483357s, workspace200/0.124118s,
samples200/0.013732s, capabilities200/0.004968s. Gateway health200/0.006982s.
No browser session/navigation timing or user's slow-detail reproduction is
claimed. Internal token measurements bypass browser authentication/nginx;
initial token-bearing gateway403 responses are preserved. One stats snapshot
and bounded logs showed no sampled saturation or5xx; existing access logs lack
request_time. No fix, deploy/restart, DB direct access, new run, policy change
or implementation test occurred. Evidence/limits and coordinator follow-up are
in [diagnostic report](docs/diagnostics/2026-10-01-run-pages-readonly.md).

## 2026-10-01 UNIFIED089 actual release and gate restoration COMPLETE

Coordinator-authorized PROD selection and bounded acceptance completed. The
genuine WGS423 receipt was registered and PROD current release CAS changed from
`wgs-4.2.2-441d5e7` to `wgs-4.2.3-bafd27c` at 14:52:31Z; catalog SHA256 changed
from `cb33a15f...` to `35c53a2e...` (transaction receipt `gate3-prod-catalog-result.json`,
SHA256 `0856802d...`). The six selected services passed exact installed checks:
60 service mounts, 18 Airflow imports with zero errors, loaded gates and four
external HTTP 200 readbacks. Apply/accept/mount/HTTP receipt SHA256 prefixes are
`cf052e66`, `bef51b0c`, `c9d26e88`, `7b80cb64`. Historical Rules GETs returned
WGS total400/page20 with 12 execution group association rows and GATK
total562/page20 with zero association rows; these were read-model checks, not
a new089 producer replay.

Gate4 restored original backend admission at 14:56:34Z on TEST and 14:57:18Z
on PROD. Final read-only closure at 15:04:56Z/15:05:16Z accepted both hosts
(`gate4-BS10610-final-readback-result.json` SHA256 `d7093fad...`;
`gate4-BS96-final-readback-result.json` SHA256 `18ff3d91...`). WGS/GATK execution
is true on both. TEST scan/auto remain false; PROD scan is effectively true
with original watermark literal `2026-09-17T09:34:19.655673+00:00`.
PROD's restored env has `WGS_AUTO_DISPATCH_ENABLED=true`, while its inherited
read-only intake policy has `auto_dispatch_enabled=false`, so **effective auto
dispatch remains false** as before. The first PROD restore checker exited5
because it incorrectly equated effective auto with the env value; the final
read-only policy check resolved this without replaying apply/POST or modifying
policy. Both external `/api/health` checks returned 200; auth and current423
were confirmed. The original env/image/mounts and unrelated service IDs were
preserved. No new analysis, canary, UE04/05/06, 17+2 or full-suite rerun is
claimed. Historical WGS422 is frozen for rollback only. Coordinator accepted
the minimum release closure. Final public index `gate3-prod-evidence-final-index.json`
SHA256 `6603fdf8...` and local archive SHA256 `25690074...` retain109 members
(108 evidence files plus index), verified by size/SHA. The final archive is
local only; no further remote runtime sampling/copy was required. HANDOFF records
the accepted state, original failures and read-only closures. Only the six state
documents are staged; untracked evidence and product source are excluded.
The final index now explicitly records `ORIGINAL_GATES_RESTORED`. Its Heavy
startup explanation is marked as an inference because failure-moment rows were
not captured. Only these two metadata fields and generation time changed;
all108 evidence entries and original receipts remain unchanged.

## 2026-10-01 UNIFIED089 PROD Heavy accepted and six services selected; gates closed (prior Gate3 checkpoint)

Coordinator's PROD GO is active. The bounded small-page activity refresh
completed after the initial page-size-200 timeout: six pages covered 27 runs,
50 transfers and related DAG/TI state, with no nonterminal work; receipt
`gate3-prod-activity-v2-result.json` SHA256 `674720db...` records complete
coverage, exit0 and no mutation. This is the preselection activity gate, not
whole-release acceptance.

PROD Heavy selected the reviewed entry `dc5c1d...`, core `554f3edc...` and
original launcher `5f2a8190...` (each mode0644). The new flock/Python pair is
190070/190480, starttime fields 3077813668/3077813775. Two complete payloads
at 14:42:24.369308Z and 14:43:30.797281Z each used one actual Lease GET
returning25 names, held/used/waiting0, limit25, idle. Read-only acceptance
receipt SHA256 `51b87164...` and 21-file actual index SHA256 `2c3e826c...`
preserve the evidence. The old Python alone received one TERM; flock exited
naturally. The finish invoker exited1 during its final new-process check after
entry/core installation and one original-launcher call. The newly starting
flock window is a possible explanation, but no fail-moment rows were captured;
the cause remains unproven. A later read-only check found the correct pair and
accepted it, with no further signal, launcher or finish replay.

PROD then selected six reviewed gateway services during 14:46:19–14:46:52Z:
backend `dfca6fe5...`, WGS observer `c21e8c41...`, Airflow API `5339e3f9...`,
scheduler `a66f8604...`, worker `e483a853...`, frontend `4df1c67c...`.
Infra's installed minimum checks continue. **PROD catalog has not been POSTed,
execution/auto admission remains closed, and `v2.paired` final gate restoration
has not occurred.** This is not final production release. No new analysis,
UE04/05/06 or 17+2 repeat, or full-suite rerun is claimed. The historical
Gate2 checkpoint below predates these PROD source/Heavy selections.

## 2026-10-01 UNIFIED089 TEST accepted; PROD GO granted (prior Gate2 checkpoint)

The native owner installed shared nipttest0.8.9/source1f5/wheelf843 and its
bootstrap under the separate GO (receipt SHA256 `1727e1f4...`). AF then selected
common16/policy, all four private runtime.env and five fixed wrappers, including
the PROD private node selectors. The node-pair receipt SHA256 is
`2d5164f94b8e0860276858860362294e048a9736c640bf142825f4b00fec62a2`;
rootselect recorded four imports, four CLI selections and installed profiles
passing. Four effective selectors matched the actual PVC/PV, 4/4 PASS. Admission
was not opened. This **did change PROD node env/wrapper selection and the shared
native package**; PROD gateway source, catalog and Heavy remain on their prior
selection, with the v3 execution/auto gates closed.

TEST selected its six actual gateway services using the reviewed paired variants;
backend remained paired-frozen. The installed modules/imports, six-service
mounts, loaded gates and API health passed the minimum acceptance. The exact
mount-contract comparison passed; WGS/GATK Rules GET both returned 200 with
zero historical rows, so this is no real Group event replay. TEST execution,
scan and auto remain closed. The genuine WGS423 receipt was registered and
current selection CAS changed from `wgs-4.2.2-3b1dae5` to
`wgs-4.2.3-bafd27c`; closed readback confirmed catalog SHA256
`342d4e073d2ac3d201ad4028016449daf550a7d88e4da5a2dcd9439754b16069`.
The first transaction POST succeeded, but its final local assertion confused
publisher raw profile SHA `436a6608...` with installed canonical `21558a4c...`
and exited 1. Read-only closure succeeded with no duplicate POST, while gates
remained closed. This was a checker error, not a product change.

TEST Heavy alone now uses core `554f3edc...`, retained entry `dc5c1d...` and
original launcher `65991c5...`, with new flock/Python PIDs 113056/113067.
Two fresh complete snapshots at 13:55:05.298335Z and 13:56:24.895783Z each
matched one Lease GET returning25 objects, held/used/waiting0, limit25 and idle. The
first read-only acceptance timed out because it compared SFS mtime with node
launch wall time; the corrected payload timestamp/hash check passed, retaining
the 599/604-second mtime offset as a clock-source observation, not stale data.
Earlier Heavy apply invoker failures and exact rollback evidence remain in the
Gate2 audit; they caused no ad hoc product patch or clinical analysis.

TEST minimum acceptance is complete and the coordinator granted the complete
PROD gate GO. Production preflight is still in progress: the first read-only
runs request at page size 200 timed out; health and page 1 succeeded, and Infra
is refreshing the full set with smaller pages. Page 1 does not prove global
idleness. No PROD gateway source/catalog/Heavy selection has occurred in this
phase, and **v2.paired LAST** admission restoration remains pending. Production
is not finally released. Keep gates closed; do not submit a new analysis or
repeat full/UE/17+2 tests. Exact Gate2 receipts and limits are in the
[candidate record](docs/releases/2026-10-01-unified-native089-candidate.md).

## 2026-10-01 UNIFIED089 first-gate admission closure COMPLETE

Direct human excluded four cross-UID keyword PIDs as unrelated and authorized
installation. Coordinator released v3 old-code closure and native's independent
installation GO. Two exact backends only were recreated with --no-deps --pull never.
PROD closure at13:17:25Z (21:17:25 Asia/Shanghai): WGS/GATK execution and WGS auto
false; scan true and watermark literal2026-09-17T09:34:19.655673+00:00 unchanged.
TEST closure at13:18:07Z (21:18:07): both execution false, scan/auto false unchanged.
Both API health and loaded gates pass. Original109 source files/image/complete
mount fields/other env stay unchanged; other service IDs/configurations stay intact.

New backend IDs: PROD2d117abbc899714c428251a469cda26f2c3c666cb887fdbad62aac74869c0486;
TEST4a0a528cc9b0b5a1369ada69e68e36fafd34f27bc745886af40dba14f5108b2f.
Exact closure receipts and original rollback are recorded in HANDOFF. Mechanical
gate/time/target evidence sent to native and coordinator; native may install under
its already granted GO. AF did not pip/select source/env/wrappers/collector/catalog.
Native installed result and subsequent TEST pairing/acceptance remain pending.

Next order: native install/pair -> v2.paired-frozen/management -> TEST acceptance
-> PROD catalog CAS -> v2.paired LAST. Once any marked089 attempt exists, both
global package downgrade and automatic old backend/DAG rollback are invalid.
Retain089-compatible stack/gates closed for repair. Frozen packet remains the
approved historical candidate; gate1 actual evidence is a separate append-only index.

## 2026-10-01 W423-R1-UNIFIED089 candidate preparation

Final candidate source is `80abdfceea0d604e6524375e2b1a2aa32022ee65`, sole
parent accepted0afd. Two reviewed deployed safeguards are preserved: controls
GREEN17 and real PostgreSQL GREEN2. Gateway v2 candidates are staged privately
on BS96/BS10610: actual effective `/app/app` and DAG `common` copies merge only
selected files, preserving all other source. PROD app differences13/8, TEST19/10;
each Airflow service has six paired DAG files. All Compose configs passed syntax
checks; actual runtime imports remain pending. No whole `/app` replacement.

Common16 files, four envs/five wrappers, two423 prepares, policy/bootstrap and
two Heavy entry/core candidates are staged with exact original backups. Heavy
launchers/Python/config/evidence/flock/log roots remain; active processes untouched.
Final TEST producer/client/backend/Group pairing precedes production new-request
selection. Native rollback compares29 package source files;197 other distributions
are fingerprints. Full old/new/rollback details are in the final candidate record
and ignored `final-packet.json`. Window CLOSED; no installation/selection/restart.

LATEST USER OVERRIDE: new requests must use WGS4.2.3/bafd27c, not a422
transition. The422-native089 ID/config/phase/receipt drafts below are obsolete
and unselected. They were not registered or activated. Final candidate is
WGS Mastere481/profile436a plus GATK7.6.0 Mastera4f/r5/profile17d2, shared
native1f5/f843. Verify TEST's fixed final combination first, then switch new
production requests; explicitly audit required producer/DAG/backend overlays.
Old441d remains only historical attempt/rollback provenance. No tracked
product or phase policy was modified by the obsolete transition proposal.

Coordinator reconfirmed the sole active card after the user's resend request.
UE04/05 source is accepted; UE06's isolated installation is not shared
production activation. AF source is80abdfc(parent0afd253), native1f5e1e0/full wheelf843.
The user's current decision is one shared nipttest0.8.9 for new WGS/GATK calls,
with separate TEST/PROD private credentials, requests, results and control roots.
AF owns common source/configuration; native alone owns pip and its bootstrap.

Read-only BS96/BS10610 API and seven known DAG probes found nonterminal0;
the initial narrow node matcher found six SFS/BSS collector/flock processes;
later exact Heavy matching found two more pairs. This is bounded
preflight, not proof of every cloud workload being idle. All four operator
configs resolve the same actual PVC/PV identity; TEST's old PVC pin is stale.
Production scanner/auto/execution=true and original watermark remain intact.

Production current441d WGS422 is frozen to native088. Obsolete draft ID was
`wgs-4.2.2-441d5e7-native089-r1`, retaining the old source/profile/Master/assets.
Its native089 compatibility/static canonical evidence is historical only.
Old publisher receipt is not an089 attestation. Production and
TEST lack the deployed UE marker/client files; environment pairing alone does
not activate the shared UE protocol. No package/config selector/service changed.
See [candidate record](docs/releases/2026-10-01-unified-native089-candidate.md).

## 2026-10-01 W423 exact phase identities verified as source

Owner provenance was checked:14 fixed modules, unchanged entrypoints/aliases,
no declaration removal and three new rules. Existing policy now registers
only `wgs-4.2.3-bafd27c` with18 additions (12 inherited422 plus six new names/
aliases) and seven overrides against cc9 base. GATK r5 uses the same audited
1cf9 workflow blob/17 rules. Older maps remain unchanged; unregistered rules
and identities still return Unknown. BS10610 isolated RED4/controls3 then
focused GREEN7 in1.64s; R1 GREEN26 and Group/UE evidence were not repeated.

Actual installation/canonical/private-config/platform pairing and TEST
acceptance remain pending. The fixed native Step6 only materializes outputs;
this TEST card excludes independent delivery/LIMS script execution. Empty
passwords are not a callback switch; no callback development remains on this card.

## 2026-10-01 W423-R1 exact 4.2.3 compatibility source verified

After the user's resend request, coordinator `airflow-cloud-demo` reconfirmed
`W423-R1-GROUP-FIRST-20261001 / AF-V423-BINDING` as the current task. UE04/05/06
are accepted source history already integrated into baseline `b3f0174`; this
task does not reopen those workstreams or the old Step1 incident.

Three exact version sets now include `V4.2.3`: repository validation, the two
existing prepare handoff stages, and the backend's required-receipt check.
Existing allowlist/root, hash, identity, generation and artifact-pending
semantics remain unchanged. The unsupported negative now uses `V4.2.999`.
Fresh BS10610 isolated RED reproduced five 423 failures (two valid-receipt
controls passed); focused GREEN passed 26 cases. Raw evidence and commands:
`.codex-artifacts/w423-r1-20261001` and the latest HANDOFF entry.

This closes the version compatibility source delta only. Exact final catalog,
profile/resource/phase/runtime pairing and deployed TEST acceptance remain
pending with the Group task below; no package installation or environment
selector/service switch occurred. The WGS publication receipt has since been
supplied and read (assets PASS/state_verified, canonical SHA16f131a4); actual
AF release registration and consumer pairing have not been performed.
The external GATK r5 profile receipt is now also supplied and read: file
SHA3c05056f, profile raw SHA17d2bb59, only revision/Master differ from old62265.
Both raw profile digests are recorded; canonical revision/runtime digests,
rule inventory and deployed consumer pairing remain pending.
Static registry review confirms both new phase identities are absent:
`wgs-4.2.3-bafd27c` and `gatk-scmc-v7.6.0@r5`. These concrete gaps were reported
to the coordinator; no mapping is inferred from old421 fixtures or profiles.
Coordinator selected ordinary catalog/no-merge for later TEST acceptance.
With options disabled, AF passes no algo override and reference=all, leaving
the owner's declared Haplotyper default intact. Independent source-import
test-project preview remains deferred for the unaudited423 option inventory.

## 2026-10-01 W423 Group TEST candidate; no activation

Latest human scope defers prepare/FQ synthesis and QC2. The isolated release
branch `jiucheng/airflow/W423-test-group-release-20261001` starts at integrated
`827dc56`; the only earlier prepare test is retained separately at `08e4cbc`.
Group UI now displays existing group association and independent rule states/
actual times. BS10610: synthetic WGS/GATK ingest/API2 passed, affected UI9
passed, TypeScript/build passed; browser6 synthetic states checked. Accepted
CCE producer reports are reused, not claimed as real event replay.

Actual node200 production GATK frozen delivery imports shared package metadata
through unchanged `shared_permissions`; therefore shared088 overwrite is not
proven isolated. Production WGS traced paths select private088; TEST consumers
need complete new pairing and existing TEST pins/profile bindings have drift.
Coordinator is obtaining the user's choice of shared installation versus TEST
private prefix. Native1f5/f843 and both pushed Master digests are frozen; no pip,
TEST selector/service switch, old profile edit or BS96 action has occurred.
See [candidate, audit and stop gates](docs/releases/2026-10-01-w423-group-test-consumer-audit.md).

Product commit `0048c3694164f087b686ad69303538b166244262` passed one fresh
whole-branch read-only review against ce497d61: no Critical/Important findings.
Coordinator also accepted the bounded consumer evidence. Installation/TEST
activation and final423 release/phase binding remain separate pending gates.

## 2026-10-01 W423 joint release source integration in progress

## 2026-09-29 WGS C Step5 Tracker stage candidate

After the coordinator's Step4 hash release and original-DagRun continuation,
WGS C entered Step5 download, while Tracker still showed Step4 success. The
existing observer replay of Step4 status can regress `AnalysisRun.current_stage`
and status; the progress API then trusts that old stage. A two-module backend
candidate guards run-level Step4 writes when the same attempt has a later
registered Step5/6 execution, and selects that later stage read-only for
already-regressed records. Execution row IDs establish causal order, so a new
Step4 recovery generation is not hidden by historical Step5 evidence. Actual
BS96 overlays were used as the release baseline; the unreleased local GATK
observer edits are excluded. Isolated BS10610 regression passed 45 tests.
The coordinator owns any BS96 release of the backend and WGS observer mounts;
this candidate made no production change.

## 2026-09-29 WGS Step4 dispatch digest candidate

## 2026-09-29 GATK r4 Rules phase source candidate

The production Rules page for the new GATK r4 analysis displayed `Unknown`
phases because the loaded exact-release catalog stopped at r3. A read-only
audit found that r4 `workflow/SCMC_GATK.smk` is byte-identical to r3
(SHA-256 `ebee79067e17544774ff9607fc714d197189abb49cc5b82af297abbee8b03701`,
Git blob `1cf9fe6f1672e919517bd1392bb2fd4496eab702`) and its 17 rules
match the pinned phase inventory exactly. This source candidate registers only
`gatk-scmc-v7.6.0@r4`; unknown releases/rules remain `Unknown`. It also syncs
the tracked WGS phase module and policy to the byte-identical BS96 production
overlay baseline, preserving the existing `441d5e7` verified rule additions.
On BS10610 an isolated, network-disabled regression first failed only the two
r4 cases, then passed all six focused cases after the mapping. No production
module, service, run, database or workflow state was changed. Coordinator
review and any later deployment remain separate.

## 2026-09-29 WGS C Step5 Tracker stage candidate

Fresh remote main and jiucheng/release/production both resolve to
`ce497d61efaa725a4a45266e76dd996d7767fe74`. This owner's existing clean linked
worktree now uses `jiucheng/airflow/W423-integration-20261001`; accepted UE06
branch3c094fc and all earlier evidence are retained. User authorized coordinated
WGS4.2.3/native0.8.9/Airflow source, candidates and test pairing. Production
scope confirmation is pending, so BS96 is not switched.

UE3c094fc is being merged with main's TTL fixes intact. Seven predicted conflicts
were resolved by keeping both distinct contracts/history and the UE runtime-sync
fence. Necessary exact candidates a85cfb6,6d11712,e634ca4 follow once each;
coordinator dirty product files are excluded. This is a source checkpoint, not
tested integration or deployment. Latest W423 plan/spec/joint-release documents
are copied as approved inputs; entries below preserve earlier checkpoints.

WGS/native contracts precede new prepare/group/QC2 work. Native generic executor
already supports trusted prebinding; platform explicitly enables only WGS prepare.
Its original ref must survive final batch-binding publication. Merge remains
unpublishable before asynchronous prepare is implemented; LIMS stays disabled.

## 2026-09-29 WES/GATK 20260927B Step4 restored; Step5/6 pending

`GATK_20260929_024231_F246CD` attempt 1 completed Step3, then Step4 failed
because its frozen runtime required a live successful Master Job. The exact
Master manifest has `ttlSecondsAfterFinished: 100`; original Master UID
`faecf4ae-562d-42f9-a449-18bf50b90c9c` and its Job/Pod were absent at
inspection. The deletion event itself was not observed. BS10610 evidence is
45 passed against the old gate, 21 TTL-specific passed after current-main
integration, and focused 2 RED then 5 GREEN for complete kubectl JSON bytes.

Only node200 `t640` received the private GATK gate/helper correction. BS96's
actual control remained `/data/airflow-WGS/downstream-stage-20260929-control/compose.json`
with the backend/observer services and mounts left as inspected. The
installed gate is the old private-gate patch from `4870e2b` + `eb1b8aa`;
its helper matches current-main candidate `5945f26` + `22e5535`. BS96
backend/worker containers and mounts were
unchanged, with no service restart. The exact original Airflow 2.9.3 DagRun
had 10 Step4-and-downstream task instances selected by dry-run and cleared
(HTTP 200), excluding Step1–3. Step4 generation 2 succeeded with receipt hash
`c72a693c827bc66a51eb01998acd2cb3e69148b65d71dca08c712482fd4ea5a3`
at 2026-09-29T14:39:35Z; `wait_step4_publish` then succeeded. The native
terminal check bound `RUN_COMPLETE`/`START_CONFIRMED` to the original UID,
found all three exit codes 0 and workflow completion, and found no `RUN_FAILED`.
The temporary reader left no Job/Pod. Step5 was waiting for the result transfer
slot, and Step6 had not started at this checkpoint; neither delivery nor whole-batch completion is
claimed. This historical run has no `publish_deadline`; general GATK resume
capability remains disabled in production. See the
[scoped release record](docs/releases/2026-09-29-gatk-ttl-downstream-bs96.md).

## 2026-09-28 BS96 WGS Tracker and GATK wait display release

The coordinator reports a limited BS96 deployment from source `a8ae5fe`.
`backend` and `wgs-run-observer` now read the four reviewed backend display
overlays from `/data/airflow-WGS/releases/20260928-tracker-wait-a8ae5fe`;
the existing Step3 lock fix and all other mounts, containers and runtime gates
were preserved. Gateway `/api/health` returned 200 after the two-service
switch. Existing C attempt-1 PREPARE generation-2 success was re-ingested
through normal stage-status; C and A now show the upload waiting projection.
The observed WES GATK run also shows `running` / `Uploading FASTQ` / `waiting`
with no percentage. Scanner remains enabled, auto-dispatch disabled; no new
batch, upload, cloud or lease operation was performed for this release.

Known limit: C retains historical `pipeline_finished_at=13:10:00.716975Z`
because it was already running before this projection release. No direct DB
change was made. D shows 100% progress but remains running; terminal completion
is not asserted. See [release record](docs/releases/2026-09-28-tracker-wait-bs96.md).

## 2026-09-28 main/production source integration for WGS and GATK UI fixes

The Git-only integration starts from main/production `744cd22`, retaining all
23 target-only commits, and incorporates the five reviewed Step3 lock, WGS
Tracker recovery and GATK transfer-wait commits. Code checkpoint `9f98617`
matches the tested source candidate for the five changed backend product files
and three focused test files. Target release catalog, runtime adapter, WGS DAG,
paired runtime and gate files are unchanged. The three state files and two
contracts had additive documentation conflict resolutions; target content was
retained. Both remote branches were atomically pushed to the code checkpoint,
and local branches fast-forwarded. This closing entry changes documentation
only. BS96 deployment and health validation are owned by the coordinator and
are not claimed here. See HANDOFF.

## 2026-09-28 GATK transfer wait UI projection candidate

GATK Step1 upload and Step5 download acquire-slot markers remain persisted as
`queued` with source `gatk-transfer-slot`. The Run Tracker and Run Detail read
projections now show `waiting`, `Uploading FASTQ` or `Downloading GATK results`,
an English current item and unavailable progress. Registered execution/transfer,
truly running stages without telemetry and terminal runs retain their existing
presentation. An isolated BS10610 backend-image run of the focused synthetic
suite passed 4 cases. This was the source candidate checkpoint; its reviewed
projection is now deployed on BS96 as recorded above. See HANDOFF.

## 2026-09-28 WGS A/C Tracker recovery projection candidate

On the existing production-source baseline, a narrow backend/observer patch
lets a validated newer PREPARE generation replace an old failed stage display
row and clears a failed run's historical `pipeline_finished_at` when its bound
DagRun returns to an active state through `sync-airflow`. Two synthetic tests
failed for the reported symptoms before the patch and passed on isolated
BS10610 source afterward. This was the source candidate checkpoint. The
reviewed projection is now deployed and C's existing PREPARE receipt was
re-ingested through the normal stage-status path. The historical finished time
limitation remains as recorded above. See HANDOFF.

## 2026-09-28 WGS B Step3 registration lock fix

Backend commit `a2d0eef` moves contract-v2 runtime evidence synchronization for
Step3 and `force_new_generation` ahead of the AnalysisRun row lock. The
preflight session checks the current WGS attempt and closes before sync; the
existing locked read and all stage/recovery/command gates remain in place. A
two-case PostgreSQL regression passed on BS10610. `backend/app/main.py`
SHA-256 is `975e1504441784162420691528ca3afbaa3fb6d0980f8b5b217b1d2e2d582ba5`.

The coordinator reports that this exact backend file was activated on BS96
with only the backend rebuilt; other container IDs were preserved and the
gateway/API health check passed from the LAN. The production source before the
hotfix was based on `84510df`; its backend mount was
`/data/airflow-WGS/releases/20260927-p0-local-84510df/backend`, with the prior
`main.py` SHA-256 `ff0f3be345680893893e5d52875f4a7be96a286c4e3a37427694a5595df27bf9`.
The coordinator owns the new release path and rollback record.

For WGS batch `20260927B`, the coordinator reports one same-DagRun Airflow
clear of 14 `failed`/`upstream_failed` task instances. Step1/Step2 were excluded,
and the active Master UID was unchanged. The DagRun returned to `queued`
immediately after the clear. By 12:57:48Z, the coordinator had confirmed
`start_step3_monitor` succeeded, `wait_step3_analysis` was
`up_for_reschedule`, and Tracker reported `stage3running`. The existing Master
was `RUNNING` with `normal=true`; monitoring was `healthy` with no error, and
the first rule snapshot showed 3/223 rules (1.3%), including
`pre_process_Dedup` and `pre_process_mapping`. A read-only node200 `/bin/true`
probe returned 0 in 0.27s. The first bridge observation arrived about four
minutes after dispatch but returned successfully. Step3 monitoring is recorded
as recovered; the analysis itself remains running. The Master was not replaced.
This task performed no production mutation and did not restart Airflow, the
Master, or node200.

## 2026-09-30 UE-06 isolated platform/native loading accepted

The coordinator reconfirmed current task `UE-06-TEST-PAIR-20260930` after the
user requested another message. This owner alone handles AF/platform; native
owner handles wheel0.8.9/source7172573. UE05 final pairing is complete.
AF product source remains `03bab6c768a2c84537ee4e4a6189072256841b63`; branch is
`jiucheng/airflow/UE06-paired-installation`, starting at state commit `a0666e5`.
This closeout changes only CURRENT_STATE/TASKS/HANDOFF/SERVER_INFO.

On BS10610/server10610, the isolated platform candidate is
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/ue06-platform-03bab6c-20260930`.
Native0.8.9 is installed separately under its UE06 evidence root, with exact
wheel/runtime/guard/module pins. Both code-adjacent bootstraps have identical
bytes and select the same installation-only policy (`bindings=[]`). Real paired
and native trust loaders, ordinary WGS/GATK command builders, P0 loading/refusal
of an unregistered synthetic request and four callers' shared SSH imports passed.
The coordinator accepted these installation/loading results and the native
final handoff. No stage, cloud Job, real batch or active service used the candidate.

Raw failed and passing logs, scripts and SHA256 manifests remain in
`.codex-artifacts/ue06-platform/` and the matching remote evidence directory.
The first Step4 origin assertion confused its guard wrapper with the underlying
runtime function; only the inspection artifact was corrected to verify both
existing pinned origins. Product code and trust checks were not changed.

Existing AF preflight and native post-install evidence retain all ten service
IDs, current link, source mounts and disabled scan/auto-dispatch. Shared0.8.8
package/dependency/bootstrap inventories and runtime identity are byte-identical
before/after installation. Exact rollback assets are readable and retained.
The old shared bootstrap points to `/home/ctapa/.config/airflow-wgs-test/`, but
`/home/ctapa` is absent on BS10610 (ENOENT): old paired configuration loading
and actual activation rollback are unverified. An actual switch needs the
original environment owner's confirmation; this task preserves existing pins.
Existing UE01-05 behavior evidence is reused. No additional test, push, merge,
deployment, production action or old Step1/batch cleanup is part of this closeout.

## 2026-09-30 UE-05 AF source delivery and final pairing accepted

Both Important findings from the single review of `8617dfa` are corrected.
Correction source commit: `03bab6c768a2c84537ee4e4a6189072256841b63`.
Manual Step1/2 metadata retains the recovery entry, while compute settlement
binds the action-authorized actual Step3 execution and frozen/native terminal.
The initial source-monitor permit persists on its exact reservation/caller;
the independent nonce Worker follow-up can cross the obsolete UI observation
fence without changing quiet proof, budget or original deadline.

BS10610 fresh boundary checks found `server10610`, Compose project `airflow-wgs`,
the existing pinned images, and intake/automatic dispatch disabled. The existing
Airflow Worker identity `50000:0` loads Airflow 2.9.3; no dependency or permission
change was needed. In isolated network-none/read-only containers, R2's two
parameterized cases passed, R4's existing node passed after correcting its audit
record counting, SSH's nine methods and both thin callback methods passed, and
only `bio_wgs.py`/`bio_gatk.py` imported with no DagBag errors. Fourteen unique
behavior cases and two file imports passed; R2 was not rerun after fixture-only
R4 repair. Raw inputs/logs/JUnit and matching SHA256 are retained in
`.codex-artifacts/ue05-review/`; details are in the latest HANDOFF.

This is source plus isolated synthetic evidence, not installed or production
behavior. The coordinator accepted the AF source delivery and closed both
Important findings after checking fourteen unique passing cases, two DAG file
imports, eighteen evidence-manifest entries and eleven tested inputs against
`03bab6c`. No additional AF review, test or source work is requested.
The coordinator subsequently confirmed native7172573/AF03bab6c final pairing
and authorized UE06 as recorded above. Accepted UE01-04/F7/final-release
evidence was reused. Merge and deployment remain closed. Entries below are
historical checkpoints, including earlier SSH failures and pending states.

## 2026-09-30 UE-05 source checkpoint ready; acceptance pending

The user asked airflow-agent to reconfirm its task with `airflow-cloud-demo`.
The coordinator checked the actual message timeline and confirmed that the
current task remains UE-05. The UE-04 instruction was historical context
misread after compaction. UE-04 `a6c31d1`/`7976f25` remains the accepted source
prerequisite. Continue the existing R2/R4 drafts on
`jiucheng/airflow/UE05-native-recovery-consumers`, worktree `gatk-prod-compat`,
starting HEAD `06bf30a`; no source was reverted during the read-only task check.
The source-only review checkpoint is now committed as `8617dfa`.

Current deliverable is the exact action/DagRun/frozen-Step3/native-terminal
binding, shared six-stage failure/cleanup fences, existing authenticated
snapshot producers, and a source checkpoint for review. BS10610 hostname and
environment preflight briefly succeeded and the backend RED nodes ran, but
the later session was reset by gateway `172.17.61.18:22` before opening.
Stop further SSH attempts until external recovery evidence is supplied.
No GREEN, final DAG import, UE-05 acceptance or runtime activation is claimed.
The retained source integration and static checks are complete for review;
the old pause and
continuation entries below are historical checkpoints. UE-06 remains gated.

R2 now binds the queued action's action ID, DagRun, exact frozen Step3 and native
terminal, and cannot settle a newer monitor with an older proof. Initial marked
monitors also require native terminal before reservation; fresh genuine failure
can resolve an obsolete UI reconnect diagnostic. R4 chooses the protected stage
from current run/route state and preserves the independent transfer/Worker quiet
guards. Both DAGs produce the snapshot on existing authenticated calls; the
Worker challenge follow-up retains its separate nonce contract. The changed
source has 19 files plus the three state documents. `git diff --check` passed;
source input hashes and captured raw command outputs are preserved under
`.codex-artifacts/ue05-continue/`. All final-source delta tests remain unverified.

## 2026-09-30 UE-05 paused pending SSH recovery

The user requested a pause after the airflow agent's current checkpoint.
Current branch HEAD is `06bf30a`, an isolated shared-SSH source commit without
remote GREEN. R2/R4 source and a synthetic R2 test draft remain uncommitted.
They are incomplete: optional native snapshots are partly plumbed, while R4
failure/cleanup fences and DAG callback snapshot producers are not finished.
The dirty worktree must not be treated as integrated or released. `git diff
--check` passed; no tests or remote commands followed the single failed
BS10610 SSH preflight. No further SSH retries or development are scheduled
until the user confirms connectivity has recovered. Deployed state and data
were not changed.

## 2026-09-30 UE-05 authorized continuation (source only)

The source baseline for this continuation was `1e84714` on the isolated UE-05
branch; the shared-SSH source is now committed at `06bf30a`. UE-04 is the
accepted source checkpoint (`a6c31d1`/`7976f25`); the old Step1 discussion is
historical. The user approved one shared SSH connection implementation for
current WGS/GATK Step1-6 and P0 dispatch/observe, followed by optional exact
native snapshots on the existing authenticated R2/R4 poll, callback and cleanup
requests. Keep the Worker nonce probe separate. First commit SSH independently,
then complete R2/R4; retain the three uncommitted R2 draft files and existing
`.codex-artifacts/`. Scope remains isolated source and BS10610 synthetic delta;
no production, node200, real-batch, wheel, service, database or release action.
The coordinator reported a BS10610 gateway timeout. This turn's one necessary
read-only SSH hostname preflight also failed before a session opened (exit 1,
banner exchange timeout to UNKNOWN port 65535). BS10610 hostname, release,
mount and gate identity could not be revalidated, so remote synthetic tests
remain unverified. Do not blindly retry or use local runtime substitution.

The shared SSH source and one synthetic delta fixture were committed and
statically reviewed. Current Step1-6 WGS/GATK and P0 dispatch/probe sites use
one `dags/common/ssh_transport.py`; a cumulative budget cannot spawn after
three known pre-session failures. Native dispatch timeout remains an uncertain
outcome reconciled by exact observe. The source has no BS10610 GREEN because
of the gateway failure; no installed or production behavior is claimed.

## 2026-09-30 UE-05 recovery consumers (source in progress; not deployed)

UE-04 source is committed. The current isolated branch is
`jiucheng/airflow/UE05-native-recovery-consumers`. Scope is the R2 bound
manual/automatic compute-terminal permit, R4 six-stage unknown/failure and
cleanup fences, and final writer read-only transient query reconnection.
Only the affected public WGS sync path and frozen-request digest consumer may
change as required. This is source development and BS10610 isolated synthetic
validation, not a node200, BS96, production, real-batch, wheel, database,
service, cleanup or release action. Existing `.codex-artifacts/` is preserved.

R4 inspection identified a current interface gap: failure callbacks and
cleanup requests do not carry the UE-04 exact native stage snapshot, while the
existing Step3 reconnect observation is UI-only. The six-stage fence must not
infer terminal or quiet from it. The platform final-release query source now
passes the narrow monotonic deadline interface; paired native validation is
owned separately.

The platform final-release read window and WGS Step4 version-correct frozen
digest are committed as `4cb6e0d` with narrow BS10610 synthetic GREEN evidence.
Final-release evidence
uses a stub for the native lock release; paired native lock verification is a
separate owner task. An R2 draft passed its first target node, but review found
it did not bind the action to the frozen request or require the exact native
compute terminal. That GREEN is not R2 acceptance. R2 and R4 need one minimal
authenticated snapshot handoff decision before their source can be completed.
The final-release read retry was refined in `be0adb8`: typed transient reads
continue with 2-second then 5-second capped backoff until the same shared
deadline, rather than stopping after three attempts. Its single added CAS-read
parameter passed with a fake clock. The native owner committed the paired
internal lock deadline source separately as `7172573`; neither commit installs
a wheel or activates a test/production service.

## 2026-09-30 UE-04 unified stage execution (source checkpoint committed; not deployed)

The current task is UE-04 source integration for registered WGS/GATK Step1–Step6.
Step1 transfer work and the old `20260927B` screenshot are historical context,
not active UE-04 work. This task has no production, node200, real-batch, wheel,
service, database, cleanup or release authorization.

The platform gate bridge is committed through `0feec86` and `5fd01a9`; the
shared native DAG client is `7ee7d7c`. Source commit `a6c31d1` completes the
WGS Step3 latest-Step2 receipt and identity barrier (R1), WGS/GATK Step6
business-receipt plus fresh native-terminal finalization (F4), GATK authorized
current recovery DagRun and frozen-conf reconciliation (F3), and exact marked
stage status/sensor handling when submit XCom is absent. Administrative DagRun
success alone cannot project a full CCE analysis to business success. WGS
validation canaries and local runs retain their existing projection. This is
source only on the isolated branch; no production activation follows.

BS10610 synthetic evidence is cumulative, not one final end-to-end run: the
WGS backend files passed 50 tests before the last status-reader refinement,
which passed its focused 1-test delta; WGS DAG passed 18 before the no-XCom
change, then its focused 1-test delta. GATK backend passed 28 before its final
marker/conf refinements, then 7 focused tests; GATK DAG passed 20 before the
no-XCom change, then its focused 1-test delta. Earlier client tests passed
16 and targeted two-DAG import. Full-folder import/CLI list did not provide
acceptance because the isolated image lacked an unrelated plugin and an
initialized metadata DB. See the latest `HANDOFF.md` for exact evidence paths.

The paired native Master TTL source is separately committed as `4fa85874`.
Platform registered Step4/5 passes a selected bundle and exact UID; the native
ordinary v2 fallback uses the persisted handoff after a valid terminal. Existing
tests cover these paths separately with stated mocks, not a complete paired TTL
run. No deployed policy pin to `4fa85874`, node200 installation, production
validation or release has been verified or authorized. The pre-existing
untracked `.codex-artifacts/` directory remains untouched.

## 2026-09-29 UE-03 shared inventory platform source (query slice; not deployed)

The isolated `jiucheng/airflow/UE03-inventory-probe` branch now uses one
bounded native-query inventory for failed recovery evidence, manual recovery
inspection, active Worker observation, exact bound diagnostics and final
writer release. The paired native namespace-list query is committed as
`6f5c120`; the platform test pins its actual source SHA-256
`d4f09a557f2edc93c7010b7a2d1a41a0ed7bc392a004a16bf8451d52ba1eae4f`.
The Heavy global collector now excludes only the explicit native
`evidence-reader` helper role, retaining fail-closed handling of unmarked
WGS Masters with missing Heavy configuration.

BS10610 isolated synthetic candidate `ue03-inventory-probe-20260929`:
initial 275-Worker fixture showed 554 old queries against the required five;
after the change the scoped set passed **35/35, zero skipped** against the
real pinned native `_recovery_query` with only its transport mocked. Raw
log SHA-256 `ff6b43805e71905fa2e83010e53c6cc9cadc1215eac2296bb68df530844a0c3f`;
JUnit SHA-256 `9cd207ecb92d2b1f8f45dd3073ef5fca672505292ca51b798bc2d10309e20e5b`.
Exact inputs and the separate Heavy RED/GREEN are recorded in `HANDOFF.md`.
No wheel install, push, node200, production, real batch, service or database
change occurred.

UE-03 is **not fully closed**: native directory-probe retry needs a trusted
original deadline where one already governs the probe. The platform now
passes the authenticated Step2/3 `cce_recovery_deadline` to the native writer
only in `resume_registered`; its isolated BS10610 test passed 10/10. Step4
`publish_deadline` limits fresh dispatch, not the background worker, and
ordinary Step1/4/6 requests have no applicable frozen absolute deadline.
The native owner has not yet committed the bounded directory-probe retry.
The platform query/Heavy slice can be reviewed independently; native retry
and its targeted evidence remain outstanding. Neither the 120-second local
probe budget nor helper TTL is a new business-stage deadline.

## 2026-09-29 UE-02 native platform gate source complete (not deployed)

The isolated `jiucheng/airflow/UE02-stage-executor-gates` branch now connects
marked WGS/GATK Step1–Step6 gates, Step4 publish observation and paired writer
fences to native `StageExecutor` source `6c0aee2`. Exact old-generation request
and terminal evidence are stored privately per generation; the shared business
status remains in its existing location. Ordinary Step4 and opted-in publish
deadline paths remain distinct. Invalid/null markers, legacy sidecars and
unknown worker evidence fail closed. The previous selected-gate 4/4 synthetic
check remains recorded below in `HANDOFF.md`.

BS10610 isolated candidate `ue02-stage-executor-gates-20260929` ran four
focused files against the native source: 30 passed, 0 skipped. Raw log SHA-256
`f02db17e9e2f808ae7be4375beeb6dbbb29cce1d12dfe4de3b949ab0a1b3b6ed`;
JUnit SHA-256 `a6521601dc3e88206ee69fbdf4b42c27671e3b05e47631a393d4144e824508b4`.
The initial collection/import failure and one assertion/dependency round were
fixed before this final run. Independent review found four direct wiring issues;
their corrections and focused assertions are included. Its final delta review
reported Ready with no remaining Critical or Important finding. DAG/backend
asynchronous consumption is UE-04. No wheel install,
node200, production, analysis submission, service restart or push occurred.

## 2026-09-29 UE-01 stage-execution contract (source complete; not deployed)

Platform changes freeze `stage_execution: {"protocol":"cce.stage-execution.v1"}`
before hashes for newly registered WGS/GATK stages and add a pathless native
identity/snapshot adapter. Existing WGS v2 registrations with matching legacy
hashes remain reusable; immutable GATK prepare remains outside the marker. The
contract and sole synthetic fixture are recorded in `docs/08_WORKFLOW_RUNTIME_INTEGRATION.md`.

The earlier native token and SHA-256 regex blockers are resolved in the current
BS10610 source module (SHA-256
`d9f69cdc8eb998b0dc1257f00fb1a21fffcdb1fb086ece415e2c75127c603b40`).
The single approved synthetic fixture first passed against the corrected native
source. Static UE-01 review then found that the platform mapping accepted a
registered but disabled handler, unlike the native resolver. The same fixture
failed on that new assertion and passed after the narrow platform correction:
final `1 passed in 0.07s`. Raw red/green output and the exact command are in
the latest `HANDOFF.md` entry. No local pytest, full suite,
service/container test, node200 access or production action was performed.
This was the UE-01 closeout gate; the later UE-02 outcome is recorded above.

## 2026-09-28 GATK-PROD-COMPAT gate

Compared the integration commit delta and targeted uncommitted P0 source diffs
against the seven WGS items. Production t640's GATK gate is the recorded deployed SHA256
`b3230de8fcdba8806a91e247679c38d40ae57cd8b02280276e64f33e6f88ec0f`; its
private GATK directory has no `cce_paired_runtime.py` or paired deployment
manifest, and the gate does not reference that module. Current GATK does not
enter the paired-runtime paths changed by the WGS P0 work. No GATK code patch
is indicated. The private gate hash differs from the source worktree's
`gatk_runtime_gate.py` SHA256 `9d2585d74aa40d2172d4098c716e14fc349aabcea2b62b294ebefcbf7c68cac7`;
the configured forced-command wrapper executes the private gate path. The latest
recorded GATK success completed Step3-Step6/finalize on 2026-09-24; no fresh run
or whole-chain validation was performed.

## 2026-09-27 Airflow repair branch synchronization

User requests main and jiucheng/release/production synchronization. Both fetched
targets are0b35278 and are ancestors of tested source03dc8d7, so integration is
fast-forward only. Scope includes the four already-deployed fixes e307328,
a1c5387,953ff94,03dc8d7 plus their tests and operational records. No new runtime
change, deployment, service restart, database operation or analysis retry.


## 2026-09-27 upload blocked before native Step1

User approved new146B51 configuration/execution after the preceding handoff.
Preparation passed; attempt1 Step1 failed at paired request validation before
transfer launch. User approved the bounded platform-only correction. Initial and
recovery request hashes now follow their existing producers; control paths validate
against the exact approved runtime attempt, not the request directory. BS10610
focused synthetic regression:8 passed. Node200 module/policy pin deployed with
backup, no service recreation or workflow changes. Same-attempt resume-stage
queued as resume_aa5a2aca4e8ad16435f6752b, Step1 generation2 running at14:53Z.
At14:54:50Z actual bytes1688899418/482168174652 (8 files), speed335061972 B/s;
API status running/error null on the recovery DagRun. Upload recovery confirmed,
not whole analysis completion. Prepared project/config/attempt unchanged.

## 2026-09-27 original failed submit replaced, awaiting user configuration

User authorized removing old56DC81 submit and resubmitting its original sampleinfo.
Old analysis/owned records plus4 terminal Airflow runs removed after private backup;
pending digests unchanged, audit/raw files retained. New WGS_20260927_141652_146B51,
batch20260919A-test, current release441d5e7, attempt1. Sampleinfo preparation passed
with4 source rows; now config_review awaiting manual step2. No config/final execution
approval given. Do not duplicate submission. See latest HANDOFF for exact deletion
inventory, backup and verification; no unrelated cleanup or code changes.

## 2026-09-27 WGS441d5e7 / native0.8.8 activated on BS96

Designated WGS owner published dev_CJC_4.2.2_cloud source441d5e7, independent r3
profile and asset20260927.4-wgs422-088; genuine43d88c receipt PASS/state_verified.
Node200 ctapa now uses private native0.8.8/source417de59 with nipttest interpreter;
prepare/profile/paired pins verified through the actual deployed gate. Normal APIs
registered and activated wgs-4.2.2-441d5e7. At14:02:18Z original backend/scanner
environments, images and mounts verified restored;10 other container IDs unchanged.
Production gateway/API/DB health ok. No batch retry, pending edit, image rebuild or
redundant runtime test. Old release/package retained. Deployment complete; previous
failed run remains failed, not claimed recovered. Exact pins, commands/evidence and
coordinated rollback: docs/releases/2026-09-27-wgs441d5e7-088-bs96.md.

## 2026-09-27 nipttest0.8.8 installed; consumer integration pending

User-specified wheel33cb78f/source095f1e9 installed first; native owner then supplied
the required runtime-info interface in417de59/wheel45c99c0c, installed same0.8.8
offline/no-deps on node005 nipttest. Actual CLI JSON readback passed; old0.8.7 package/metadata/CLI
archive retained. No production runtime/catalog/service switch. Exact evidence:
docs/releases/2026-09-27-nipttest-088.md. User designates WGS-pipeline as sole
externalCLI compatibility implementer. Native readonly runtime-info is delivered;
installation alone does not resolve WGS prepare or activate the production release.

## 2026-09-27 designated0.8.8 owner corrected

User names WGS-cloud-plugins thread019f9d79-be3f-7701-af33-3595d72bbfac as actual
0.8.8 developer and hands externalCLI compatibility to it. Full context delivered;
other agents instructed not to duplicate implementation. Existingproductionstate
unchanged; no0.8.8 installation/publication ornewbatchretry in this handoff.

## 2026-09-27 external-runtime fix assigned to0.8.8 development

Latestuser directs externalcce support to native0.8.8 currentlyunderdevelopment.
Native/WGSowners coordinating actualCLI runtime/provenance interface andWGS
0.8.8 version compatibility. Do not change installed0.8.7 orretrybatch yet.
Platformregistration fix953ff94 is deployed; remaining blocker is WGS's external
CLI/Python layout assumption, not profilepermissions. Productionupgrade is separate.

## 2026-09-27 registration repaired; external CLI installation assumption remains

953ff94 deployed backend2 modules/scanner+observercatalogparser. Genuinefe530b
receiptregistered/activated; ctapaprepareSHA c9cc826a...; oldbindingsretained.
Originalrunattempt4passed sampleinfo/configuration andpermissioncheck, thennative
preparefailed because WGS assumes bin/python next to configuredexternalCLI.
Finalprojectabsent, noanalysisstarted. Productionflagsrestored,health200.
User explicitly wants WGS to support external/test cce deployments withoutwrite
access to WGS environment. No reinstall/venvfix or furtherretry; WGS/nativeowners
auditing minimum explicitCLI/interpreter/provenance fix. See latestHANDOFF.

## 2026-09-27 r3 permissions published; platform activation blocked

User authorized the exact139 pipeline/resource files. Original publisher completed
official asset20260927.3-wgs422-permissions, PASS/state_verified=true; r3 profile
SHAdaad51fcbaaa35352e7504a1943890ab75f5285f9677db17f7cbc5ec034e282a.
Postcheck:138 files0664, monitor0775, allUID10001/GID520 unchanged;14 existing
parents unchanged. Payload hashes unchanged. All exact temporary Jobs/ConfigMaps
removed. No native reinstall, image build or workflow source change.

Live production validation corrected an earlier audit mistake: catalog accepts
only wgs-X.Y.Z-<7hex>, not proposed wgs-4.2.2-d38322e-permissions. Genuine receipt
fe530b2022a536e0a106d90f1d49b233051016ad5e8d066e46a9162c4614f31d retained,
not registered. Same-ID replacement is also forbidden. Asked user for minimum
release-identity compatibility scope; do not silently overwrite history.
BS96 window restored, gateway200; current remainswgs-4.2.2-d38322e.
ctapa mapping and failed attempt3 unchanged, no retry. Thus permission publication
is complete but original preparation issue is NOT yet fully resolved.

## 2026-09-27 metadata approval received; publication held on broader file effects

User approved publisher metadata permissions. Productionpreflight11:15:55Z idle
(business/Airflow/tasks/leases0); no freeze or writes performed. Owner audit found
standard update replaces130 pipeline+9resource files with new modes/group/stage
owner, not only .cce-assets metadata. Existing business parent dirs are skipped.
Exact scope in task-artifacts/wgs-422-release-20260927/PERMISSION_SCOPE.md;
current SFS modes not yet measured, standard successful staging cleanup removes
temporary backups. Need exact-file scope approval or a supported profile-only
route before publishing. Native owner is checking existing capability read-only.

## 2026-09-27 latest user correction: retain profile r3

User explicitly rejected r4. Keep revisionr3 and only correct permissions to
2775/0664/0775. Prior r4 candidate is superseded, not a publication target.
Publisher notified to prepare r3 and verify genuine same-revision receipt/catalog
handling; no shared publication yet. Metadata-normalization scope and old-run
rebinding decision remain unresolved; user revision choice is not those approvals.

## 2026-09-27 user selected WGS prepare permission standard

Latest user instruction chooses2775/0664/0775 withbioinfo/520; the proposed WGS
prepare code relaxation is withdrawn. Scope is a matching profile release,
not a recursive permission migration. Original WGS publisher asked to prepare
only the necessary profile/receipt change and hold shared writes until the
platform maintenance window. Existing failed attempt remains pinned to r3;
requested user choice on retained-history rebinding versus a new submission.
Publisher prepared local r4 candidate, SHA4eea1a03b1aded68e5843d70e9cc2cd016af949ce60e24558f28cd4ab38e8d67;
only revision and three permission fields differ. Publication held: standard
publisher normalizes its entire .cce-assets metadata tree; explicit scope
confirmation requested. No production freeze, profile switch or retry this turn.

## 2026-09-27 Operator fix deployed; retry exposed WGS permission-contract conflict

Sourcea1c5387 deployed only node200 gate, SHA08c236984cc64d1bd209468e92d88828abb11998ded8a66d641c64218422eefd.
Original run attempt3 passed schema3 materialization but WGS prepare exited2 at
17:45:58 CST: release prepare/cce_pipeline_adapter.py:348 requires2775/0664/0775,
while genuine r3 profile pins0755/0644/0755. Profile hash matches registered value.
Project directory absent; execution approval unset, no cloud analysis started.
Do not alter permissions or immutable source in place. WGS source-owner correction
and coordinated matching release are the next scope; see dated release note.

## 2026-09-27 Operator schema3 fix verified; production deployment authorized

Shared prepare/Step7 transformation accepts native schema3 without legacy paths;
legacy handling and frozen-config refusal preserved. BS10610 isolated synthetic
regression:6 passed,77 deselected. User explicitly requested fix, commit and retry.
Deploy only node200 gate, preserve credentials/policies/services; retry original
run through API with the same previously approved configuration, stopping at
execution review. No cloud execution approval or workflow/image change.

## 2026-09-27 second-step preparation blocked by Operator schema mismatch

After user confirmed configuration, original run attempt2 reached remote
prepare_wgs_analysis, then failed because platform gate requires legacy paths.
Installed native0.8.7 schema3 Operator is valid and intentionally lacks paths.
SSH retries demonstrably worked. Same legacy assumption in Step7 comparison
must be accounted for in a narrow compatibility fix. Diagnosis only; not retried.

## 2026-09-27 SSH fix deployed; original run back at configuration review

Sourcee307328 accepts exact pre-auth timeout trailer; BS10610 regression6/6.
BS96 only3 Airflow services' bio_wgs.py bind updated; DAG import errors empty,
other9 service IDs preserved. Existing runWGS_20260927_090701_56DC81 resumed via
API into attempt2; prepare_sampleinfo succeeded17:26:59 CST. Phaseconfig_review;
user must review configuration and approve execution normally. No new batch,
direct DB edit, cloud test or automatic approvals. Deployment/rollback details:
docs/releases/2026-09-27-ssh-banner-bs96.md.

## 2026-09-27 production prepare SSH failure diagnosed (not fixed)

Run WGS_20260927_090701_56DC81 failed preparing sampleinfo: node200 SSH banner
timeout, exit255. Current banner reachable in3.89s from actual Airflow worker.
Follow-up: actual worker ctapa publickey authentication succeeds; exact attempt
has only request JSON, with no status sidecars/control workdir/project directory.
Deployed pre-execution retry classifier omits the second OpenSSH timeout line,
so this known handshake failure bypassed5s/10s reconnect. No restart or code
change performed; narrow classifier/fixture correction awaits implementation.

## 2026-09-27 WES cloud cleanup completed

User included20260921B. Removed8 exact SFS batch directories and8 OBS prefixes
(134 objects); both WES SFS parents empty, OBS parents0 files/0B. Details in
docs/releases/2026-09-27-wes-cloud-cleanup.md. WES DB/offline/pending preserved,
shared assets and personal/test trees untouched; maintenance Job removed.
Old WGS multipart403 issue deferred by user. No backup/recovery guarantee.

## 2026-09-27 authorized BS96 WGS cleanup completed; multipart/WES outstanding

User authorized four failed WGS20260921B/C/D/E histories and cloud data,
plus cloud batches strictly before20260921. Exact plan in
docs/releases/2026-09-27-authorized-cloud-cleanup.md. Four runs/31 samples and
run-owned DB projections removed transactionally; pending23 current/162 history/
20 operations preserved with identical content hashes, only4 nullable run links
detached. Other DB runs retained. Scanner existing ignore list adds exact B/D
chips to prevent re-submission. Offline data untouched.25 WGS SFS trees and34
OBS FASTQ/result prefixes removed, final inventories empty. Other15 WGS DB runs
retained. Five old incomplete OBS uploads remain: first abort returned403 and
remaining aborts were not attempted. Subsequent WES authorization/results above.
Temporary cloud helper removed. No code changes/tests or deletion backup.

## 2026-09-27 BS96 WGS d38322e/r3 serial publication complete (latest)

After the WGS conversation's maintenance-window explanation, the user confirmed
there was no running workflow. Coordinated window07:46:11–07:51:38Z temporarily
disabled only WGS manual execution admission/backend auto-dispatch/scanner
auto-dispatch. Fresh checks before/after freeze: active business0, unsubmitted0,
occupied transfer leases0, Airflow queued/running DagRuns0 and TaskInstances0.

WGS owner publishedsource d38322e/assets20260927.2-wgs422/r3 with the same accepted
Master3d180a9/native0.8.7/reference-resource bytes. Production private source/
prepare/template mapping added; official receipt60650a5f registered and CAS
activated wgs-4.2.2-d38322e. This supersedes the earlier same-day3b1dae5/r2 selection.
Exact original admission/dispatch flags and watermark restored and compared;
GATK/Local/SGE policies untouched. Backend/scanner now use private window-control
restore.json; other services and platform source84510df unchanged. Gateway200,
currentrelease/profile/receipt readback match. No samples, smoke/fault tests or
new product changes. User may now test. See the dated d38322e release note.

## 2026-09-27 BS96 P0/Local presentation deployment complete

User authorized production deployment only and will run business tests. BS96
now runs platform84510df from releases/20260927-p0-local-84510df: backend,
observer, frontend and three Airflow services. Six unrelated project containers
are unchanged; scanner/auto-dispatch/watermark and GATK/Local execution gates
are preserved. Additive business schema is20260915_0026. Six switched services
are running with zero restarts and gateway health200. No smoke, fault test,
sample submission or full suite ran in this deployment.

Production node200 WGS gate and matched private native0.8.7/source8323567 are
installed; runtime uses nipttest Python and isolated packages, not a WGS-env
upgrade. Shared r2 binds Master3d180a9f and genuine asset20260927.1-wgs422-p0.
Authenticated API registration/CAS activated wgs-4.2.2-3b1dae5, receiptfc3a7d25.
WGS recovery is enabled for new frozen policies; historical attempts unchanged.
This is the accepted3b1dae5 source, not the separate newer WGS publisher's pending
update. Further shared-SFS publication is held for a separate coordinated window.
Details and exact rollback: docs/releases/2026-09-27-p0-local-bs96.md.

## 2026-09-27 P0 and Local/SGE source promotion

User authorized merging the accepted test branch, including its earlier Local
display work, into main and production. Refreshed origin main and production are
both 43cd0c5; canonical test is 9fb31c3, 170 commits ahead with no target-only
commits. Both integrations are fast-forwards: no conflict resolution or product
code edits are needed. Native batch/node labels, current snapshot sample counts,
percentage progress, shared phase/rule views and Snakemake logs are retained,
along with CCE log downloads, P0 and existing production fixes.

Restored the two 2026-09-22 upload/download waiting release notes dropped by
historical test integration bbbf942. This promotion changes documentation only
relative to the accepted test application. Existing focused BS10610 acceptance
is reused; no repeated runtime suite or production deployment is part of this
task. Other component source synchronization is user-confirmed, not re-audited.
Atomic push and ls-remote confirmed main, production and canonical test all at
e433ea0; closing documentation follows the same refs. A later BS96 release must account
for native schema migrations 0025/0026 before switching backend code, and bind
the approved production runtime/profile/gates rather than test configuration.

## 2026-09-27 BS10610 auxiliary DAG discovery fixed

The canonical Airflow test branch now contains `4fe71cb`, which delays the
main-DAG helper imports in the WGS native monitor, WGS maintenance and GATK
maintenance modules. Their DAG IDs, task graphs and runtime calls are unchanged.
BS10610 mounts only these three patched files from
`releases/20260927-dag-discovery-4fe71cb` in the Airflow API, scheduler and
worker. Backend, main WGS/GATK DAGs and all unrelated services keep their
previous mounts. The precise prior Compose is retained as a private rollback.

The actual Airflow 2.9.3 DagBag regression was RED for two duplicate main-DAG
IDs before the fix and GREEN in an isolated candidate. After the test-node
switch, `airflow dags list-import-errors -o json` returned `[]`/exit 0, all
five DAGs resolved to their own files, nine changed mounts were verified
read-only, and gateway/backend DB health returned 200. No business DAG run or
production change was made. See the release note and latest HANDOFF.

## 2026-09-27 Airflow canonical test branch aligned with deployed P0 code

The existing canonical test branch `jiucheng/test/wgs-local-main-sync-20260917`
was fast-forwarded and pushed to `0203b79e`. Current `main` and production
release branch both point to `43cd0c5`, and both are ancestors of the test
branch. This corrects the earlier delivery only to the isolated integration
branch; it does not merge P0 into production.

BS10610 actual backend and WGS DAG mounts still point to the existing
`20260926-p0-e358aad` release. The canonical branch has no functional file
differences from `e358aad` under `backend/`, `dags/`, `scripts/`, `config/` or
`frontend/`; sampled live backend/DAG SHA256 hashes match the branch. No service
was recreated solely for documentation commits. Gateway health and DB health
return 200, malformed login 422, and unauthenticated workflows 401.

Airflow import acceptance remains **open**: `dags list-import-errors` exits 1
with duplicate `bio_wgs` and `bio_gatk` DAG IDs caused by maintenance/monitor
modules importing their main DAG modules during discovery. `dags list` shows
`bio_wgs` but associates it with `bio_wgs_native_monitor.py`. Do not claim full
Airflow DAG acceptance or launch a business test on this result. See the latest
HANDOFF for exact commands and next action.

## 2026-09-27 P0 source repositories prepared for operator push

The named plugin-owner task `019f9d79-be3f-7701-af33-3595d72bbfac` identifies
the final plugin source in its Windows isolated worktree, not the BS build
evidence directory. SHA-verified Git bundles imported that source and the
0.8.7 cce-pipeline source to the BS10610 umbrella submodules. Their local
`main` branches fast-forwarded to plugin `4f10c276` and native `8323567c`;
umbrella `main` now pins both at `cd82ca7b`. WGS 4.2.2 remains on
`dev_CJC_4.2.2_cloud` at `3b1dae5`; the platform test branch was `44fba4f`
before this documentation entry. None was pushed upstream in this task.

The WGS worktree's `origin` is a local `/bi/.../wgs-4.2.0` clone. A push into
that clone failed before ref creation (`remote unpack failed: unable to create
temporary object directory`), although owner/mode and free space looked
normal. Do not retry blindly or alter shared permissions; an authenticated
operator can push the exact WGS branch directly to its GitLab repository.
The WGS worktree's existing draft docs, the umbrella's old cce submodule
checkout and untracked release artifacts were preserved. No install,
deployment, runtime test, clinical run, production action or upstream push.

## 2026-09-27 acceptance: requested synthetic Step1-6 scope complete

Step1-2 retain their actual earlier PASS evidence; user excludes gen2 pre-START
timeout, not marks it repaired. Same COMBINED01 workdir/config/checkpoint continued
manually. Gen4 Master057dbe3c-f8c2-426d-8387-274cf93e0432 ran only finalize/all,
no Worker; native Step3 SUCCEEDED2/2. Native Step4 publish, Step5 download and
Step6 materialize all returned0. DOWNLOAD_VERIFIED PASS3files/1786B;
MATERIALIZED VERIFIED/PASS. Checkpoint SHA and post-success mtime are unchanged.
Results owned by ctapa6801:520, dirs0755/files0644. Native log archive verified.
Completed within original operator deadline1790478526.9563308; no deadline reset.

Coordinator read raw process receipts, terminal/status, delivery markers,
checkpoint proof, final verification and gen4 exact UID reclamation record under
D:/pipeline/task-artifacts/wgs422-p0-integration-20260926/
p0-native-smoke-20260927/COMBINED01-OPERATOR-G4/. Only synthetic fixture errors
were corrected (post-success timestamp baseline and two omitted manifest files),
with old evidence retained. Gen4 confirmation initially saw stale gen3 START;
existing native same-UID confirmation completed without new Master/state editing.

Scope is manual operator continuation plus actual native downstream acceptance,
NOT automatic recovery, platform API/Airflow end-to-end, uninterrupted normal-case
or biological equivalence acceptance. No product edits, production deployment,
new wheel/image/profile, Step7/data cleanup or extra test scenarios this turn.
Final ledger reconciled: prior18 + COMBINED24 =42 CREATEs. Actual scoped Job/Pod
queries are empty and six storage-helper records CLEANED. Two older completed
setup Jobs without TTL were saved then UID/RV-conditionally deleted; their Pods
are absent. Test directories/results/locks retained. No additional testing needed.
Sections below are historical checkpoints, superseded by this acceptance scope.

## 2026-09-27 latest scope: Step1-2 complete; downstream only

User explicitly closes Step1-2 and excludes gen2 pre-analysis timeout from this
test round. Existing Step1/initial Step2 receipts remain the actual pass evidence;
pre-START replacement failure is not a recovery PASS. Continue Step3-6 only,
preserving the same test workdir/checkpoint and failed evidence. No new product
fix, whole-case rerun or production change. Original runtime owner executes.

## 2026-09-27 correction: preserve this case, replace the pre-START Master

User challenges restarting the synthetic case. Read-only source review confirms
same-workdir checkpoint reuse is valid; fresh-case execution was only a
product-unchanged workaround, not a requirement. Current missing contract is
pre-START failed-Master replacement: the expired gen2 has no START/FINAL, while
ordinary recovery requires them. A legitimate next-generation action must use
explicit pre-START failure evidence and ownership/live-work checks, not fabricate
FINAL or reset gen2 deadlines. No implementation or new Job authorized/executed
by this diagnostic turn. Preserve run/attempt/config/workdir/checkpoint.

## 2026-09-27 test entry corrected; original replacement expired

Owner completed task-artifact-only resume_selection correction, driver SHA256
da909464370c6062ee32593613242b7333f50e012e3d983c998de24fa20330fe.
One node200 nipttest offline RED/GREEN entry check passed; coordinator read exact
diff, check output and hash. This is not cloud replay acceptance. Product code,
running candidate and original REQUEST/pins are unchanged. Gen2 Master actual
Failed/BackoffLimitExceeded at01:05:05Z after pre-START payload timeout; its exact
UID absent at1790471188.1964965. No gen2 Worker; CREATE remains25.
Old deadline expired, so no legal same-operation replay remains. Fresh isolated
execution of the same case is awaiting user confirmation; no new case/run was
submitted. Cross-Master successful completion and Step3-6 remain open.

## 2026-09-27 approved test-driver continuation correction

User approved the minimal same-operation synthetic resume entry correction.
Original runtime owner is continuing; product code and extra test scenarios are
out of scope. First verify the actual gen2 UID/journal/original deadline; preserve
original REQUEST and failure evidence. No deadline reset, fabricated receipt or
new generation is implied. Successful replacement and Step3-6 remain unaccepted.

## 2026-09-27 COMBINED01: same-UID pass, replacement handoff interrupted

Latest user scope is minimal current combined case only; no extra normal rerun
or broad checks. Native register/Step1 returned0. Genuine successful CREATE
response loss returned1 through native Step2; immediate intent reentry returned0,
START_CONFIRMED at UIDf74b3f7c-d998-448a-b343-c5a80d174886, original deadline and
one CREATE. Coordinator read raw process/logs and hidden/reconnected UID records.
First Worker failed as designed, checkpoint succeeded, complete failure evidence
was collected; original Master/Worker terminal+TTL observed by owner.

Manual resume created generation2 Master UIDa17e48cb-1380-41f9-a3ff-cfe3c829604e
and bound owner by CAS. Actual kubectl exec TLS handshake timeout copying
PAYLOAD.yaml returned1; handoff POD_READY, no START and no generation2 Worker.
Cumulative25 Jobs. Product created-journal continuation exists, but the frozen
test driver cannot reach it after current owner is gen2/POD_READY: its resolver
requires START_CONFIRMED, then its resume precondition requires gen1/oldJobabsent.
No blind rerun, pin/REQUEST/lock edits, new Master or deadline extension. Minimal
driver continuation correction requires a scoped decision; only bounded existing
observation continues. Cross-Master completion/Step3-6 and whole smoke NOT passed.

## 2026-09-27 latest authorization: no cumulative test Job cap; timely reclamation

User removes the cumulative test-Job cap if needed and requires timely cleanup.
This supersedes30-count stops below, not the smoke scope or execution gates.
Continue recording every CREATE/UID/terminal/reclamation; retain TTL100 and
bounded native helper deadlines/precise cleanup. Run cases sequentially with
max1Master+1Worker. No blind retries, scope expansion, business-data deletion,
production changes or unbounded running workloads. Combined test is cleared;
count18 was the last confirmed observation, not a reset. No new acceptance claim.

## 2026-09-27 restored image; original normal case not accepted

Exact old Worker image was restored under wgs422-p0-worker-retained-2b807004;
push digest and registry manifest independently matched unchanged bytes. Worker
subsequently completed naturally (owner reports TTL observed). Original Master
had exceeded its1800s deadline. Step3's genuine read used reader18 and returned1:
mirrored RUN_FAILED is stateFAILED but exit_code0, analysis exit null and
evidence_complete=false. Coordinator read the actual file; no repair/fabrication
of this evidence is allowed. Original normal case cannot advance or count PASS.
CREATE18/30. Minimal combined manual recovery driver is being prepared for one
review before submission, estimate10 additional including all helpers (total28).
It may prove controlled replacement/Step1-6 continuation, not independent
uninterrupted normal success, automatic policy, API or Airflow E2E acceptance.
No product/source change, production or shared-profile update in this continuation.

## 2026-09-27 exact-image restoration approved; old normal Master expired

User approves unchanged olddigest2b807004... restoration under a dedicated test
retention tag. Owner completed wgs422-p0-worker-retained-2b807004 push; coordinator
verified raw push digest and fetched manifest. Current Master832 tag stays intact.
Fresh owner observation finds NORMAL01R3 Master absent after its1800s deadline;
Worker23c8c641... still exists. Its terminal result is not inferred from404.
UID-bound event confirms DeadlineExceeded; no404-derived terminal claim.
At restoration no new Job:17/30. Old observer ended at its bounded limit, so incomplete live
coverage remains explicit. Reconcile genuine persisted evidence before deciding
further tests; no frozen-input/context rewrite or automatic new-run launch.

## 2026-09-27 continuation checkpoint: published8323567, NORMAL01R3 active

Original owner published version0.8.7/source8323567 under the original Master
tag. Wheel SHA2565b292b1f393cc362436ac46cf0b9fec851282e8cb10bd09f60f2b19187b066ae;
Master digest3d180a9f074cf38ffaf18446f2910a316e2b784b8f7f859bea5dc4a74d10f1af.
Coordinator read push/build receipts and independently matched wheel hash;
isolated node200 import receipt confirms8323567. No shared release/production change.
NORMAL01R3 Step1 succeeds; Step2 initially times out querying Job, then reenters
within original deadline with the same Master UID9c27d7c1-df2a-457e-abfd-24aedfbd3909.
Worker23c8c641-a1d1-4ebd-a0f1-0713f5501514 is ImagePullBackOff: SWR resolves its
frozen old image digest2b8070049c3a44319af6d6db9bb7f994af744e8b4f8aacf054071a8a4eee6394
as NotFound. Raw kubelet events independently read; not an authentication error.
Owner found the same RepoDigest cached on BS10610 (imageID378289a2e52b68c067021581b2a9390c3279fd183e2ecc5e10a0d6e605a7433b).
Proposed exact old-image re-push under a test-worker retention tag requires scope
confirmation; no rebuild, frozen-input mutation, shared ServiceAccount change
or new Job needed for that proposal. Nothing pushed yet; CREATE17/30, tests held.
Independent FAULT01 is held: three standalone cases estimate33 total. A minimal
task-private driver for one combined response-loss/manual replacement case is
under review (not submitted); no fake platform prepare/FINAL/locks/authorization.
This is independent native runtime acceptance, not Airflow/API E2E. No smoke PASS.

## 2026-09-27 continuation authorized: cumulative CREATE cap30

User explicitly raises the cumulative Job CREATE cap to30 and asks to finish
testing, following the cross-Master feasibility clarification. Prior12 remain
counted (18 remaining at authorization), including all setup/helper/log Jobs.
Original runtime owner resumes same-version0.8.7 candidate8323567 and original
NORMAL01/FAULT01. The distinct T3 new-UID/generation checkpoint acceptance is
also tracked: owner first specifies real fixture, existing authorized recovery
entry and full CREATE estimate; no fake FINAL/binding or guard bypass. All cases
share the30 cap, run sequentially and stay isolated. No production/T4 expansion.
Results are pending; this supersedes older waiting-for24-budget notes below.

## 2026-09-27 resume feasibility clarification (docs-only audit)

Keep Step2 handshake and file-level checkpoints, NOT dependence on the old Pod.
Platform351fdbe/native8323567 have a paired new-UID/generation replacement path
for complete bound final evidence and quiescent writers, including TTL-absent
old Masters. Hard-crash/missing-snapshot cases remain blocked; no blanket
Master-failure recovery claim. Existing same-UID FAULT01 does not close T3
cross-Master live acceptance. Documented in docs46 and linked spec/plan/docs08.
No runtime changes, SSH, tests, Jobs, artifacts or production operations here.
Actual candidate remains d29d1ba; CREATE12/22 and budget question unchanged.

## 2026-09-27 normal-path convergence authorized; same two smoke cases

Final checkpoint (awaiting user budget reply): native8323567 fixes failure-status
projection;4 remote cases PASS and same-seat incremental review approves it.
This latest source is NOT built/published/installed; executed candidate stays
d29d1ba/0.8.7. NORMAL01R2 Step1/Step2 succeed
with START_CONFIRMED (Master UIDef21511a-3644-4efa-93f5-c2412f4cb2ce), same
storage helper reused. Synthetic analysis exits1 because its profile omitted
jobs:1; no Worker. Step3 mirrors genuine RUN_FAILED/logs but its failure branch
also assumed a platform recovery_context;8323567 corrects only native failure
projection, with no fabricated recovery authority. CREATE12/22. User was
asked to allow24 total (12more estimated for original two cases); pending reply,
no new CREATE. This run's Master/evidence-reader are gone and retained helper
is CLEANED by its exact journal/UID; no local data or lifecycle lock deleted.
Existing failure records/inputs remain protected. Full smoke is NOT accepted.

Latest source d29d1ba is incrementally review-approved, including the native
Step3 optional recovery-context consumer correction. The source progression
94fb214/01c43dc/d29d1ba and scoped RED/GREEN receipts are recorded in HANDOFF.
No remaining Critical/Important in this increment; this is not cloud acceptance.
Owner now replaces same-version0.8.7 candidate artifacts from the final exact
archive and pairs an isolated installed consumer/profile. Image01c43dc was
pushed but had no production consumer. Two cases remain pending, CREATE9/22.
FAULT01 is same-UID CREATE-response-loss reconciliation at generation1, not
failed-Master replacement or Airflow automatic recovery. No full-suite rerun.

Runtime owner captured the old-image preSTART failure with diagnostic Job9:
shell line2 pipefail rejects the CR character. Local Git check confirms the
Master script index isLF but checkout isCRLF. Packaging correction is pending;
this is not evidence of a biological rule failure. The one readonly helper can
be reused only while live with fresh identity checks; its600s lifetime/TTL100
is not renewed. Detailed contract is in docs08. No smoke PASS or release yet.

User approves scoped P0 simplification and subsequent testing, preserving timely
Master/Worker cleanup. Keep TTL100 (do not restore86400), original Step1–7,
755/644 and owner/generation/CAS fences. Original runtime owner handles reduced
storage-probe dependence, bounded nonfatal read-only helper cleanup and real
startup-failure diagnosis; no stale identity cache or fabricated terminal proof.
Candidate artifacts remain0.8.7/old tags with new commit/digest provenance, no
version suffix. Only necessary artifacts are rebuilt by their existing owner.
Plan N1–N5 records scope; initial smoke count8/22, NORMAL01 Step1 passed,
Step2 failed beforeSTART, remaining cases NOT accepted. No production/T4 change.

## 2026-09-27 NORMAL01 upload passes; independent Master startup failure

After task-only launcher env correction, real Step1 exits0 (OBS200 for input and
completion marker). Step2 created Master UIDb6b2aeea-dd9c-4442-90fd-f55c8580411d,
but it failed BackoffLimitExceeded about2s after container start. TTL100s removed
Job/Pod. Genuine handoff remains JOB_CREATED; noSTART/Worker. Container root cause
is unknown from retained events. Original Step2 exited1 naturally with Pod Ready
timeout; no retry/new Master/FAULT01 or unrelated product fix is authorized.
Cumulative CREATE8/22: budget corrected only for two mandatory Step5 log Jobs
previously omitted from original two-case estimate. No additional cases.
Cleanup correction4488d10 and5 scoped tests pass; full smoke is NOT accepted.

## 2026-09-27 live reader cleanup passed; task launcher variable supplied

Reader#5 cleaned successfully and native Step1 entered upload. Wrapper exit127
revealed the ad-hoc SSH test process omitted WGS_REAL_OBSUTIL_BIN; existing test
and production runner configuration already defines the executable obsutil path.
Original owner continues with this variable in the task process only, no shared
configuration/credential/code change. Count5/20; upload receipt and Step2–6 still
pending, no Master/Worker yet. This supersedes the earlier cleanup blocker only.

## 2026-09-27 reader cleanup candidate verified; live continuation pending

Native commit `4488d10` extends only helper cleanup confirmation from 30 to 90s.
Coordinator reviewed the two-file diff and copied remote JUnit:5 tests,0 failures,
0 errors,0 skipped. Candidate guard SHA256
`4b3ce8c5e4c02352b753b659d1c9f5faeda90ddd627686416492c337676a0119`.
Original owner reports exact #4 journal reconciled through native Step1 to CLEANED,
with no new CREATE. NORMAL01 Step1 continuation is pending; no smoke PASS yet.
Shared install, Master, profiles and production remain unchanged.

## 2026-09-27 reader-cleanup correction authorized; smoke continuation in progress

Latest user instruction "修复后继续完成" authorizes the original runtime owner
to diagnose and fix only the cloud-reader cleanup blocker, minimally verify it,
then continue the same NORMAL01/FAULT01 native smoke cases. Previous stop below
is superseded only for this scope. Preserve exact identities, UID/RV fencing,
native journal reconciliation and cumulative CREATE budget (currently 4/20).
No production, shared release/profile, formal WGS logic or platform feature changes.
No new smoke PASS: the last verified execution remains blocked before upload.

## 2026-09-27 live smoke blocked at reader cleanup; scoped fix complete

Initial-CREATE correction `ed39d21` and16 selected remote regression cases pass.
NORMAL01 prepare and real test-only schema3 registration completed. Actual Step1
failed twice before upload: first `recovery query: TRANSPORT`; after same-node
identity reconciliation and one authorized retry, `cloud reader cleanup pending`.
No upload receipt, Master, Worker or validated result. Step2–6 and FAULT01 remain
NOT RUN. Stop retries; new reader-cleanup investigation/correction is not silently
included in the completed CREATE fix. Four test Jobs total:2setup+2reader; readers
later absent, last reader journal stillDELETE_INTENT. Shared install/Master,
production and unrelated batches untouched. Full evidence in smoke-entry review.

## 2026-09-27 scoped CREATE fix committed; live smoke pending

Native commit `ed39d21` changes only runtime Step2 and existing handoff tests.
Coordinator reviewed the diff and candidate runtime SHA256
`71d7c041943607e112713b75732e4ba5ade1bf63354b5620d635c1f4dd1998a1`.
Node200/nipttest isolated regression:16 selected cases pass; local read of its
JUnit confirms16 tests/0 failures/0 errors (not a local runtime test).
Normal/START replay and timeout cases accompany the3 new CREATE-loss checks.
Original owner proceeds with the2 live native smoke cases. Installed0.8.7,
Master, shared profile/assets and production remain unchanged. Native commit is
not pushed; pre-existing unrelated test_recovery_monitor.py dirty is preserved.

## 2026-09-27 user confirms scoped initial-CREATE fix and smoke continuation

Latest user "确认" authorizes continuing smoke and the original runtime owner
fixing only first-Master CREATE response-loss reconciliation. This supersedes
the install-only conflict below. Test only; no WGS biological logic, production,
historical runs or platform UI/API/DB expansion. Original owner implements and
minimally validates native correction; coordinator reviews evidence and docs.
Normal and fault smoke remain unaccepted until actual execution receipts exist.

## 2026-09-27 smoke preflight identifies first-CREATE recovery gap

Normal native smoke has NOT RUN; setup Job #1 verified the real SFS PVC.
The planned lost-CREATE-response fault is NOT RUN: nativee2962a2 writes initial
handoff only after receiving CREATE success; a lost response leaves no handoff,
and same-Job re-entry rejects the missing identity record. Coordinator and native
owner confirmed the source path. No fake receipt or product fix is being applied;
The execution owner subsequently received a newer user instruction to install
only (turn started2026-09-27 00:22:08+08), conflicting with smoke execution.
New mutations are stopped pending clarification; no test PASS is claimed.
See the smoke-entry review for exact scope and preserved setup resources.

## 2026-09-26 P0 isolated fixture and fault smoke authorized

User now approves the suggested independent P0 smoke fixture, bounded injected
fault and test-only configuration needed to execute it. Original runtime/Infra
owner is implementing the test assets and execution proposal. Keep installed
0.8.7/Master and formal WGS source/shared release unchanged. No product/API/DB
behavior change, production action or full biological run is included. An
injected API response must be labeled injection; actual plugin/terminal evidence
must still be produced normally. Record exactly which deployed layers are
exercised, and do not claim frontend/Airflow end-to-end coverage from a native
fixture alone. No new test PASS is claimed at this checkpoint.

## 2026-09-26 P0 smoke entry checked; live acceptance not run

User requests completion of isolated P0 smoke testing, not full biological WGS
validation. Scope: BS10610 test normal Step1–6 and one bounded existing recovery
scenario; reuse unaffected synthetic results. Formal batches and BS96 deployment
remain separate. First verify an executable non-clinical fixture and supported
fault boundary against the installed release; do not replace production WGS
scripts, fabricate receipts or use the old submit-rejection smoke as acceptance.
Fresh BS10610 readiness PASS: five service mounts, flags, health and release
receipt agree. Independent test-project gate is false; automatic WGS recovery
is unset/default false. QA and original runtime owner confirm no existing
submit-ready tiny workflow or real allowlisted fault-injection entry in the
inspected sources. The old smoke expects submit409; current test-project prepare
still binds WGS_pipe.smk/all. Further test-fixture/entry and test-only gate work
must be scoped before live acceptance. No smoke run or fault was started; do not
report readiness or earlier mocked transport tests as live normal/recovery PASS.
Evidence: docs/reviews/2026-09-26-p0-smoke-entry.md.

## 2026-09-26 A1–A4 test delivery complete (latest)

BS10610 five-service deployment now consumes platforme358aad: backend/observer
backend source and Airflow API/scheduler/worker WGS DAG. Node200 test WGS12-file
closure and both paired bootstrap/policy readers pass installed-source selection.
Native0.8.7/e2962a2 in nipttest and new Master/r2/SFS assets are installed/published.
Real receipt220c51d3... registered and CAS-selected WGS4.2.2 from4.2.1. Gateway
/api/health200; final mounts/catalog/read-only-consumer checks PASS. AUTH and test
release managementtrue; scan/auto-dispatchfalse. No new business batch submitted.
502 during switch was old Nginx upstream IP; nginx-t and graceful reload fixed it,
without frontend recreation or code changes. Existing service rollback retained.

This closes the authorized A1–A4 slice, not all lifecycle T1–T5 or a real analysis
canary. Production services/GATK private gate untouched; the shared r2/SFS changes
were separately user-authorized. Platform source/docs pushed on test branch only.
Native sourcee2962a2 committed on jiucheng/release/p0-validation-20260925, not pushed:
its sole origin is a read-only local Git bundle. Do not guess a writable remote or
claim main/production promotion. All prior in-progress entries below are history.

## 2026-09-26 final0.8.7 artifacts installed; asset publication running

Original owner reports final nativee2962a2/0.8.7 installed in existing nipttest
via node005; BS10610 reads the same version/commit. Master is pushed at
sha256:2b8070049c3a44319af6d6db9bb7f994af744e8b4f8aacf054071a8a4eee6394.
Authorized shared r2 replacement is complete, with exact old-file rollback copy.
New profile SHA c98b13c6de82470bea48d028a6df1dc78f3ce12f566920a79e4ba55bbdf35e8d.
Assets20260926.2-wgs422-p0 publication Job Complete1/1; live status PASS with
state_verified=true for pipeline130/resource9. Native release.export produced
receipt220c51d3... from that state. Catalog does not yet contain WGS4.2.2, so the
new receipt is a first registration, not an overwrite. Platforme358aad is staged;
precise5-service WGS/backend mount update and paired test gate installation are
in progress. No platform service activation claimed yet.

## 2026-09-26 release version/profile direction superseded by user

User requests a plain release version, not0.8.7+p0.dev1; target is now0.8.7.
The previous candidate was built, pushed and installed in nipttest but is not the
final requested artifact. Original owner must rebuild from fixed0.8.7 metadata;
reuse unchanged code/test evidence. User also requests replacing r2 with r3 content.
Before overwriting, check whether the exact shared r2 path has production consumers;
test-only authority must not silently mutate a production-shared profile.
Changing profile bytes still changes its SHA and requires a valid matching asset
receipt; no bypass or forged PASS. User subsequently authorized shared resource
publication after the same-file/hash impact was explained. Exact r2 replacement
and matching asset publication may proceed with rollback evidence; production
services and real batches remain out of scope. No test activation reported yet.

## 2026-09-26 P0 normal-path correction authorized (in progress)

User now authorizes source correction followed by BS10610 test deployment,
limited to audit A1–A4 and new business-output0755/0644: automatic registration,
initial owner independent of Step2 ID, shared CLI/platform current owner, and
TTL-safe normal downstream. Preserve stage order, frozen inputs and recovery
budgets. T4 pause/delete and production/real-batch actions are excluded.
Existing integration worktree at5165592 was clean at start. Shared native/platform
interfaces and source correction are complete; one joint review closed all three
Important findings (explicit legacy Step1, GATK prepare generation2, missing
prepare process identity). Infra reports33 targeted native checks passing, the
four WGS/GATK normal/recovery cases passing, and3 changed GATK cases passing after
the final correction. CLI main dispatch is covered with mocked cloud transport,
not a live cloud full-run. Existing unaffected evidence is reused.
Native owner committed candidate90abacd/0.8.7+p0.dev1 and is building a distinct
wheel/WGS Master and new r3 profile. No corrected deployment yet; preserve r2.
Only affected normal/recovery synthetic paths will run, not full-suite repeats.

Coordination resumed: user explicitly clarified that "直接安装" was an obsolete
instruction. Native and platform owners are continuing the authorized correction,
then minimal validation and BS10610 test delivery. New artifacts are in progress;
do not reinstall the old artifact as the correction.

## 2026-09-26 P0 lifecycle design revision (current documentation authority)

User confirmed cloud-only cleanup, user-managed local directory movement, same-name
new analysis without stale cloud locks, and business0755/0644 with private secrets.
The original P0 spec now contains R1–R7; run-control and TTL designs plus permission
boundary are aligned. Implementation queue:
`docs/superpowers/plans/2026-09-26-p0-lifecycle-correction.md` (T1–T5, V1–V6).
This supersedes historical source-complete/2770 business-output/no-control-table
wording where conflicting; previous bounded test results are not discarded.
Docs only: no runtime correction, tests, deployment, production or batch action.
T1 documentation complete; code/interface implementation and T2–T5 remain pending.
Native/plugin artifacts already published are historical pins, not proof they
contain this future revision. Rebuilds remain with original owners after changes.

## 2026-09-26 independent P0 normal-analysis audit (latest finding)

Static review of platform b17e1b6/954045a, native dcc1698/ae90b65 and plugin
5ffcb07 finds that initial protected Step1–Step2 is not operationally closed:
the per-bundle registration producer is missing, and initial lock action requires
a Step2 execution ID generated only after Step1. Updating policy at Step2 cannot
transfer the existing same-generation lock. Ordinary CLI also reloads stale
initial owner context after platform UID binding/recovery. TTL100 plus legacy
Step4/5 remains a conditional missing-Job failure if the new profile is used
without the paired consumer. No code/runtime/production change or tests in this
audit. Component acceptance is not end-to-end acceptance. See
`docs/reviews/2026-09-26-p0-normal-analysis-audit.md` for source evidence and the
two bounded post-fix acceptance paths. Preserve the original automatic Step1–6
sequence; do not add manual binding/pause steps.

## 2026-09-26 R4 test integration in progress (current authority)

User authorized the next three steps: integrate the latest production fixes
with P0, bind WGS4.2.2/0.8.6/r2 through existing APIs/UI, then deploy and minimally
verify BS10610. Historical pauses and design-only headings below are not the
current R4 status. No BS96 deployment or main/production merge is in this slice.

- Fresh fetch: main/production `43cd0c5` are already contained in test `781877e`.
- Integrated P0 `fd9a008` into isolated test branch
  `jiucheng/test/wgs422-p0-integration-20260926`, functional merge `0af8367`;
  document handoff `a8f9bc4`. Bounded merge review found no Critical/Important issue.
- R1 SFS release `20260926.1-wgs422`, runtime0.8.6 and WGS Master/profile r2 are
  complete; do not rebuild, reinstall or republish them for R4.
- Original Infra reports eleven focused synthetic cases PASS on BS10610,
  against exact functional source0af8367 (backend10,DAG1). No local/full suites.
  Two new4.2.2 binding regressions reproduced RED inbeba26a and passed GREEN
  in954045a. Total13 focused cases; no repeat of the baseline11. The patch adds
  only the frozen4.2.2 directory mapping and three explicit version sets.
- Candidate payload and immutable host-side3b1dae5 source are delivered.
  The approved ctapa SSH identity reaches node200; the immutable source and
  profile are readable, and the ctapa-owned test gate is writable. The prior
  chenjc-only permission and route blockers are resolved. The source was staged
  in an isolated BS10610 release; no service was switched.
  Actual private catalog current34bfcbf differs from the example;
  preserve existing entries. Registration/CAS selection has not occurred.
- Paired activation is stopped at an already documented P0 gap: native and
  platform consumers require a trusted per-bundle policy binding, but no
  production registration producer exists (tests write fixture bindings).
  An empty binding list would reject new batches. Do not fabricate a clinical
  binding or activate a half-deployed P0; service rollout, test selection and
  post-deploy smoke remain undone. The exact read-only PVC/PV cloud-reader
  identity was verified; storage UID guessing is not the blocker.
  Scanning, dispatch and global automatic recovery remain off. No real batches.
- Accepted source/docs through0ca80a8 were atomically pushed to both the new
  integration branch and existing `jiucheng/test/wgs-local-main-sync-20260917`.
  Main and production refs were not changed.

Detailed evidence and outstanding gates:
`docs/releases/2026-09-26-wgs422-p0-r4-integration.md`.

## 2026-09-23 P0-2E lock contract supplement (design only)
Added owner/generation CAS handoff, TTL-independent directory protection and
conditional release to both P0 documents. Airflow submission control does not
replace CLI/runtime mutual exclusion. No lock or production state was changed.

## 2026-09-23 Huawei incident recommendations: P0-2 documentation revision
P0-2 explicitly includes automatic Job TTL, not only recovery after deletion.
Worker/Master/reader generators propose TTL=100 seconds (project choice using
the vendor example); evidence/consumer compatibility must precede activation.
Pod capacity, AOM reporting and alert notification evidence are production gates.
Only documentation updated; no implementation, runtime test, cloud change or
production release. Existing CR01 progress is unchanged; automatic recovery stays off.

## 2026-09-23 P0-2 original design reprioritized (documentation only)

Revised the existing CCE recovery spec section1.0, not a second retry design.
P0-1 means cluster health only. P0-2 prioritizes Master handoff confirmation,
trusted terminal/binding production and cce-pipeline reconnect using existing
CR01 e921e3a / plugin25297f9 work. Full dispatch/automatic acceptance still open.
No application code, tests, deployment or historical recovery in this revision.

## 2026-09-23 Job TTL and cross-Master recovery design (not implemented)

Design: docs/46_JOB_TTL_CROSS_MASTER_RECOVERY_DESIGN.md.
Defines durable Worker/Master terminal evidence, TTL defaults, recovery journal
reconciliation, directory exclusion and existing P0/Airflow integration.
Documentation only; no code, deployment, cloud operations or runtime tests.
Production adoption and historical recovery require separate authorization.

## 2026-09-23 Step7 integrated into the primary test branch

The accepted Step7 source, BS10610 publication evidence and final safe-entry
record from `ae416fa`, `08696d6` and `8697a8b` are integrated into
`jiucheng/test/wgs-local-main-sync-20260917`.
This integration preserves the existing P0 checkpoint and test-run cancellation
record. It does not promote Step7 to `main` or production.

## 2026-09-23 cancelled stale BS10610 GATK Step1 projection

The user-authorized stop of test run `GATK_20260922_112207_23AD29-a1`
is now reflected in the test control plane. The DagRun is failed,
`start_step1_upload` stayed success, `wait_step1_upload` is failed and
`submit_step2_master` never started. Node200 has zero matching processes.
The business run and 43 samples are cancelled; Step1 and its transfer are
canceled; 60 completed file projections remain success and 26 unfinished
projections are canceled. Its exact input lease was released. No OBS, SFS,
NFS/local input, sampleinfo, runtime/evidence, database or service data was
deleted, and no other test analysis is active.

## 2026-09-23 Step7 deployed to BS10610 after authorized binding correction

Source ae416fa. Test-only wrapper corrected, original effective runtime copied
into isolated test directory with Step7-only delta; production hashes unchanged.
Scoped five-component release20260923-step7-ae416fa active. Healthok, independent
maintenance DAG registered with2tasks/max_active_runs1. No real SFS operation.
Focused40cases already passed; no repeat. Primary test-branch integration is
complete.

## 2026-09-23 Step7 focused acceptance passed; deployment held

Backend/runtime30, DAG9, isolated DAG integration1 passed on BS10610.
Only one harness-noexec failure retried; no real SFS cleanup. Fresh active runs
empty, test node runner inactive. Test wrapper hardcodes production config_dir;
deployment stopped before changes, user confirmation requested for test-only
binding correction. See docs/STEP7_MAINTENANCE_20260922.md for exact evidence.

## 2026-09-22 WGS Step7 maintenance draft

Test-only implementation checkpoint: `docs/STEP7_MAINTENANCE_20260922.md`.
BS10610 has one active GATK Step1 upload; deployment hold remains. Independent
Step7 maintenance/recovery code and focused tests are drafted in the isolated
worktree. Read-only code review findings were addressed. Acceptance, commit and
deployment remain pending the coordinator's explicit release. No production or
runtime changes were performed; no tests have run.

## 2026-09-26 R1 WGS4.2.2 SFS publication complete

Release20260926.1-wgs422 published by normal0.8.6 CLI:validate PASS,apply exit0,
status PASS/state_verified=true. SFS pipeline4.2.2 and resourcewgs-4.2.2-r1 READY
verified by original WGS owner; ACTIVE_ASSETS now binds the new release.
Source dev_CJC_4.2.2_cloud at3b1dae5, includes current upstreamca71cd6; no4.2.1
branch commit/push. BKW whitelist VCF/index content verified in SFS under the
ordinary logical resource name. Source and resource files were not overwritten.
Coordinator read/checked CLI evidence and final owner receipt, no repeat tests.
See docs/releases/2026-09-26-wgs422-sfs.md. R1 complete; R4 Airflow integration,
main/production synchronization and service activation not performed this slice.

## 2026-09-26 direct WGS4.2.2 publication authorized

Latest user asks to publish4.2.2 directly, without old-batch compatibility work.
Normal shared ACTIVE_ASSETS update is now within scope; retain integrity/auth
checks, but no old-release status/consumer audit gate. No unrelated deletion or
Airflow/BS96 switch. WGS owner reports new20260926.1-wgs422 OBS metadata ready,
12unchanged objects server-side copied and2metadata uploads, exit0; SFS pending.
User explicitly requires source branch dev_CJC_4.2.2_cloud; no commits to
dev_CJC_4.2.1_cloud. WGS owner to confirm current merged HEAD matches payload.
Whitelist source explicitly required: GRCh38_primary_assembly/
whitelist.V1_BKW.V20260909.hg38.vcf.gz instead of whitelist.V1.V20260909.hg38.vcf.gz;
VCF/index pairing and payload provenance must be confirmed before SFS apply.

## 2026-09-26 R1 active: stale pause corrected

User explicitly corrected the relayed pause as an OLD instruction and reaffirmed
"先完成发布". Resume R1 SFS publication only. Both original WGS/native owners
notified; no repeated wheel/image work or expansion to Airflow/BS96. The paused
entry below records a coordinator chronology error, not current authority.

## 2026-09-26 historical erroneous pause (superseded)

Original WGS owner relayed "先暂停", incorrectly treated as newer during R1.
Coordinator stopped advancing publication and notified both original owners:
no further uploads, assets apply, switching or cleanup. Existing0.8.6/SWR/r2
results remain accepted. Both owners confirmed only read-only checks, no new
upload/apply/switch/cleanup. R1 is not complete. Await explicit user resumption.

## 2026-09-26 R1 SFS publication resumed

User authorized only next step1: publish WGS4.2.2 to SFS. Original WGS owner
01a09149-ad9d-7e92-b98a-16d9cae075e2 resumed with the accepted0.8.6/r2 contract.
Rebind asset manifest/SOURCE_READY to r2 without overwriting the old candidate;
reuse unchanged payloads. Audit ACTIVE_ASSETS consumers before apply and retain
old4.2.1/frozen batches. Receipt pending; no SFS completion claim yet.
Airflow integration, main/production merges, BS96 deployment, real analyses and
automatic enablement are not part of this slice.

## 2026-09-26 runtime-first slice complete; profile inactive

cce-pipeline0.8.6 installed in nipttest, source dcc1698; minimal version hardcode
fix accepted with RED then3 GREEN cases. WGS Master pushed with RepoDigest
dc22c919d83ee5354b51b650666c9609ce05dc3ebcfb283acac16a3b3fa62597; new shared
profile wgs-4.2.2/r2 SHA4a016a2d0c1006b013a1e66efc147e29275e0ce8dcd2b086f1488bed8c44d6ed.
Unified owner receipt, actual wheel metadata/hash and embedded file hashes,
source diff and profile bytes independently reviewed. See
docs/releases/2026-09-26-cce086-wgs-profile.md for exact evidence and paths.
No Master rebuild: its embedded runtime assets are unchanged by client-only fix.
No old installed-package backup was made under the user's direct-install
instruction; old dev3 wheel remains, not a byte-for-byte environment backup.

WGS/SFS still paused, new profile inactive. Old R1 manifest/SOURCE_READY binds r1,
so future publication must produce metadata matching r2; current payload hashes
remain frozen. Airflow/BS96 and existing batches unchanged. Main/production
integration, API/dashboard updates and SFS publication remain later work.

## 2026-09-25 minimal native release fix authorized

User approved removing the fixed0.8.5 clause from release binding while keeping
catalog/actual version equality and all asset identity/integrity checks. Original
native owner will provide a successor artifact, minimal remote regression evidence
and update the active installation/push/profile receipt. No direct installed-code
patch or automatic Master rebuild; unchanged embedded assets allow image reuse.
User subsequently explicitly selected version0.8.6 for this corrected artifact;
do not use a dev4 local version or overwrite dev3. This supersedes dev3 as final
install pin only after the successor is evidenced.

## 2026-09-25 runtime-first slice resumed; WGS/SFS remains paused

User explicitly confirmed that the pause only covers WGS/SFS publication.
Original native/Infra owner was instructed to resume R2/R3: install dev3,
push the accepted WGS Master and bind a new inactive profile, using the frozen
contract without waking the paused WGS task. Receipts remain pending; no BS96,
Airflow deployment, SFS apply or real analysis is included in this slice.

## 2026-09-25 runtime-first continuation authorized

Latest user scope: first install the new cce-pipeline, push the WGS Master to
SWR, then bind a new profile. Original native/Infra owner is executing these
steps; WGS owner supplies the frozen4.2.2 contract. R1 SFS publication is no
longer a prerequisite for installing/pushing; profile stays inactive until
assets and paired consumers are ready. Follow the formal SOP and current test
scope, do not infer a production environment switch from historical examples.
Installation/push/profile receipts remain pending. No completion claim yet.

Later user-authorized work is SFS publication, Airflow API/dashboard integration
and Airflow main/production-branch synchronization with minimal validation.
The final message narrows this turn to the first three steps; no BS96 deployment,
other-repository main merge, real run or expanded tests is inferred.

Repository audit: platform P0 committed through3bc77a8, functionalfdace86;
GitHub main43cd0c5 does not include P0 and its named P0 branch is not remote.
Plugin P0 committed through4f10c27, artifact5ffcb07; GitHub maind5f720e does
not include P0 and its named P0 branch is not remote. Native functional ae90b65,
build45323e4 committed/clean; this checkout origin is a local bundle, server
main83e7adb does not contain P0. Live GitLab query lacked noninteractive auth,
so upstream native push status is unverified, not reported as complete.

## 2026-09-25 documented SSH path correction

Local BS10610 SSH verified exit0, hostname server10610, configured address
172.17.106.10. User instructs using this or node005 direct IP. Do not require
creation of a global alias solely because node005 lacks the workstation alias.
User confirmed IdentityFile C:/Users/11217/.ssh/id_rsa_chenjiucheng, already used
by the successful local connection. Both owners told to stop default-identity
probes and use the documented existing management path. No home/key change or
publication performed. Existing private OBS boundary still applies; any remaining
release-CLI transport limitation must be described separately from SSH access.

## 2026-09-25 four-step rollout execution authorized

User explicitly says to continue and start execution. R1 is assigned to the
existing WGS-pipeline owner; R2/R3 wait for its refreshed publication contract.
Coordinator retains platform integration and state docs. Scope is the approved
WGS4.2.2/P0 test-release plan, not BS96 deployment, GATK testing or real runs.
ACTIVE_ASSETS consumer impact remains a pre-write gate. No deployment success
is inferred from authorization; individual owner receipts are still required.

Pre-integration correction: test781877e has equivalent Step7 code via255be59.
`git diff ae416fa 781877e -- backend dags scripts config frontend` is empty.
The earlier ancestry-only statement did not mean the fix was absent; preserve
this code without a duplicate cherry-pick. P0 still needs bounded integration.

R1 owner has freshly verified source3b1dae5/upstreamca71cd6 and the changed
whitelist/index; publication is pending consumer-impact checks. R2 read-only
preparation received and hash-verified at task-artifacts/p0-final-native-ops-
20260925/R2_READY.md. Existing test mounts/disabled gates are unchanged, node200
is a confirmed nipttest consumer, and installed native remains0.8.5. No install,
push or profile activation has occurred; R2 compatibility still consumes R1.

R1 candidate20260925.1-wgs422 is now staged and OBS SOURCE_READY verified from
node005 (13 objects,708270164 bytes); SFS is NOT published. BS10610 reading the
same ready object times out. Original Infra owner is checking the existing
supported split-host entry; no route/credential workaround is authorized.
R1_STATUS.md receipt SHA f611c2c752400936130aaa690d642757097961f510eaf3bad1129275fff883bc
was read and verified by coordinator. Old4.2.1 paths/ACTIVE_ASSETS remain unchanged.

Final precondition blocker: supported node005 validate/apply delegates kubectl
over configured admin SSH, but node005's configured BS10610 alias cannot resolve.
No alias/host-key change is made without direction. Updated R1_STATUS SHA
8c38daf1d04a2da823c8db3d7d3c7d7de1986e17130f67f15dbf68b3ed0b74d1 verified.
Both owners instructed to retain staged artifacts and hold environment writes.

## 2026-09-25 replacement four-step WGS4.2.2/P0 rollout plan

User requests a new sequence: WGS4.2.2 SFS publication with WGS-pipeline owner,
nipttest/dev3 WGS Master publication, new profile, then production/test fixes +
P0 integration into the test branch and limited verification. Plan:
docs/superpowers/plans/2026-09-25-wgs422-p0-test-release.md. Both original owners
provided local-record handoff; no remote operation or implementation this turn.
Old4.2.2 staging must incorporate changed whitelist VCF/index; assets apply updates
shared ACTIVE_ASSETS, so consumer impact must be checked separately from platform
activation. Test branch781877e includes main43cd0c5 but not deployedae416fa fixes.
GATK testing and five-group Worker/logger upgrade are excluded. R1–R4 execution
is not started; source/artifact historical acceptance is unchanged.

## 2026-09-25 WGS rollout preflight: divergent test baseline, no writes

Original owner reports BS10610 backend mounted20260923-step7-ae416fa lacks
compute_recovery/publish_recovery; existing WGS DAG is also pre-P0. Coordinator
verified locally that replacing ae416fa with fdace86 would remove newer Step7
maintenance and transfer-queue display fixes. Common ancestor1da45f3. WGS-only
testing does not require stripping GATK code from shared backend; GATK testing
is not the blocker. Stop environment writes pending a bounded integration of
accepted P0 with current test fixes. No package/image/service/gate changes made.

## 2026-09-25 WGS-only test continuation approved

User approves WGS test-entry/candidate-runtime paired deployment and minimum
recovery verification; GATK/WES testing and entry discovery are deferred, not
blockers. Original native/Infra owner performs fresh consumer/mount/rollback
preflight before scoped writes. No production, GATK deployment, new services,
automatic activation or whole-suite retest. Source/artifact acceptance below
is retained; actual installation and test acceptance still need an owner receipt.

## 2026-09-25 corrected candidates ready; paired test rollout needs confirmation

Platformfdace86 and nativeae90b65 source fixes are complete. Original artifact
owner built dev3 from version-only45323e4: one wheel/two Master images. Coordinator
verified delivered hashes and smoke evidence; actual-wheel log is3 pass/1 skip,
not four passes. See docs/releases/2026-09-25-p0-validation-dev3.md.
Nothing is installed/pushed/switched. Actual test execution is ctapa@node200,
whose old WGS gate has no paired runtime. The proposed deployment list still
needs the full module/consumer closure and explicit existing test-service scope;
do not install only the wheel or treat a source fix as completed deployment.

## 2026-09-25 P0 corrections source accepted; installation pending

Native ae90b65 is frozen; paired non-root selector297bcee plus the current
follow-up closes Tasks1/2. Coordinator verified original native final111-pass
log/hash and platform34-pass/two-fixture-error log plus only those two corrected
fixture rechecks passing; DAG8 passed. Focused review findings are closed.
Private plugin process state remains separate from shared final output; existing
legacy directories are neither chmodded nor blocked by the generic writer.
Original native/Infra owner is preparing the affected one wheel/two Master
artifacts and exact nipttest/paired test rollback plan. No installation, test
service switch, production change or automatic recovery activation is accepted.

User authorized V01–V07 fixes and continuation of the blocked step; shared
outputs must not be forced to root or0600. Native/Infra owner is executing Task1
in the existing isolated native/platform entry scope. Platform observation
independent files are now assigned separately; paired entry edits wait for the
native owner's explicit handoff. No overlapping edits. Plan:
docs/superpowers/plans/2026-09-25-p0-validation-corrections.md.
No installation or activation is accepted merely by source acceptance.

## 2026-09-25 P0 source validation audit; fixes not implemented

Static review of platform4a4ed3c/nativef44619d confirms six validation defects
(including the known root-only entry) and one conditional query-budget risk.
Record: docs/reviews/2026-09-25-p0-validation-audit.md. Prioritize non-root entry,
PVC/PV allowlist mismatch and lost eligibility on transient workload movement.
Repeated reader Jobs, cleanup-state handling and global policy equality also
need correction within the existing P0 scope. No source edits, tests, SSH,
installation, deployment or production operations; only review/state documents.
Candidate publication and TTL evidence do not close these integration gaps.

## 2026-09-25 non-root trust contract corrected; source adaptation pending

User confirms Airflow deployer chenjc, analysis user ctapa, WGS source owner
chenjx. P0's root-owned interpreter/scripts/policy/all-ancestor requirement and
mandatory /etc policy location are withdrawn as deployment requirements.
Do not seek sudo/chown, a new service/container or a replacement for nipttest.
docs/13_SECURITY_AND_OPERATIONS.md records the role-scoped trust contract and
retained path/pin/registration/fence protections. Platform/native UID-0 checks
remain a source gap (P0-NONROOT-ENTRY), not an environment permission blocker.
Prior synthetic tests substituted the platform interpreter validator; they did
not validate this deployment premise. This turn is documentation audit only.
No SSH, runtime tests, source edits, installation, permission or service changes.
SWR/TTL historical evidence remains valid; non-root activation is not accepted.

## 2026-09-25 SWR publication and scoped live TTL accepted

User confirmed SWR login and asked to continue. Existing native/Infra owner is
published the exact two accepted Master images with distinct new tags.
Coordinator checked both registry manifest/config identities and8 evidence hashes;
no rebuild or repeated tests. Record: docs/releases/2026-09-25-p0-swr-ttl.md.
Nipttest installation preflight is read-only. Test/production activation, live
Master replacement and Compose changes remain unexecuted. User authorized two
no-data TTL Jobs; exact names/UIDs recorded, Complete/exit0 and Failed/exit17,
then both Jobs and owner Pods automatically removed. No manual cleanup.
Coordinator checked15 original TTL evidence hashes and terminal/owner identities.
Nipttest is0.8.5 while test catalog declares0.8.4; neither is the new candidate.
User has been asked to approve BS shared-nipttest plus BS10610 paired-test update;
preserve rollback, no WGS/production/old-run change or automatic enablement.
Subsequent plan review exposed hardcoded UID-0 checks conflicting with nipttest.
The newer non-root correction above withdraws that requirement; do not seek a
root-owned installation. Source adaptation/affected verification and separate
rollout authorization remain necessary. No new service/container or sudo/chown.

## 2026-09-25 item2 offline artifacts accepted; item3 operational gate still closed

Plugin successor accepted:5ffcb07 /0.6.4+bs8.dev2, actual wheel4 pass and10 Python
payload files matched. Native wheel d84bace /0.8.5+p02.dev2 and two Master images
were built by their owner. Native TTL3 passed and the missing terminal6 passed
against the final WGS image, with no skips in the supplement; both image smokes
passed. Prior harness failures retained; execution ordering/receipts reconciled.
No further runtime tests, installation, deployment or activation authorized.
OPS preflight proves WGS live storage binding but not all writers,
provider capacity or AOM/alerts. TTL writes and cloud-console entry await user
response. Receipt: docs/releases/2026-09-25-p0-final-candidates.md.

After cbb74e7 documentation coordination, user requested items2/3. Plugin final
wheel dispatched to WGS-cloud-plugins; native/Master and read-only operational
preflight sent to huawei-cloude with ownership confirmation required. Actual
remaining environment evidence pending. No coordinator build/Compose
or remote operation. No production enablement, install, service change or push.
Latest HANDOFF records task IDs, dependencies and permission-stop boundaries.

## 2026-09-25 documentation coordination only

Tasks1–6 source/synthetic acceptance is complete within its recorded scope;
Task5's original offline artifacts remain accepted historical artifacts, not
Task6 release candidates. Final successor wheels/Master images and operational
acceptance remain open. The total ledger and runbook now distinguish these layers.

Owner handoff: plugin agent owns its wheel; cce-pipeline agent owns native wheel
and WGS/GATK Master artifacts with authorized Infra assistance; release/Infra owns
actual writer/storage, TTL, capacity and AOM/alert gates. Coordinator only records
dependencies/evidence and reports blockers. These are planned owner cards, not
executed dispatches. See docs/superpowers/plans/2026-09-22-p0-joint-recovery-progress.md.

Locally checked clean source pins before editing: platform4c04545 (runtime6f03dd6),
native1bc67fd and plugin81132cf. No installed-version claim or fresh remote check.
User narrowed this turn to docs/progress coordination: no Docker/Compose, build,
runtime test, SSH, service/CLI/policy change, cloud action, production or push.
Permission/environment problems must be reported immediately; no bypass attempt.

## 2026-09-25 Task6 source acceptance after final review

Task6 source and BS10610 synthetic acceptance are complete. Whole-plan fresh
review found no Critical/Minor issue and one Important selected-terminal
contradiction. Native1bc67fd rejects live Failed/native success and live Complete/
native failure before Step3 emits a terminal observation. Both reproduced RED;
the final affected native monitor/downstream suite passed13 (8.11s). No second
review or broad regression rerun. Platform runtime remains6f03dd6; plugin81132cf.

Together with this turn's PG contention10, WGS/GATK automatic/manual lifecycle4
and deadline/owner denial4, this closes the source gates for CR-02/03/04/05.
Task6 operational acceptance remains OPEN: final pinned artifacts/paired-writer
activation, real Complete/Failed TTL observation, all-entry Pod capacity, AOM
freshness and alert delivery need separately authorized release work. Task5
artifacts do not contain Task6 code. No production access, policy activation,
deployment, installed CLI/image update, merge or push occurred.

## 2026-09-25 Task6 PostgreSQL and automatic lifecycle checkpoint

BS10610 disposable PostgreSQL acceptance: 10 passed (7.42s). Actual blocked
backend PIDs were observed via pg_stat_activity; repeated automatic reservation,
manual/automatic competition, duplicate manual dispatch and committed user stop
retain one owner. No existing service database or shared network was used.

Real fatal producer/FINAL -> backend automatic reservation -> lost Airflow POST
reconciled by GET -> actual DAG registration -> restricted replacement -> fresh
monitor after Job reclamation -> Step4/5/6 -> normal finalize: WGS/GATK automatic
and existing authenticated manual flows all passed (4 cases, 94.49s). External
Kubernetes/OBS/HTTP/SSH transports are synthetic; actual source services, native
receipts, locks and DAG callables are used. This is not live cloud TTL acceptance.

Integration exposed and fixed two bounded reader gaps: same confirmed Step3
action must observe its replacement after TTL, not re-enter replacement against
the old source; selected-journal equality must include the registered producer's
original compute deadline. No new budget, attempt, deadline or recovery path.
Native fd43f88/plugin81132cf unchanged. Task6 remains open for final whole-plan
review and separately authorized operational gates. No production/merge/push.
Checkpoint commit6f03dd6. Task5's immutable artifacts predate Task6 and are not
final release candidates for this source; no rebuild or activation is implied.

## 2026-09-25 Task6 manual monitor handoff checkpoint

Automatic polling no longer treats a failed query-only observer as terminal
compute or releases its action fence. Existing authenticated same-attempt Resume
can hand off an exact ended observer (scoped blocked/exhausted query marker,
confirmed dispatch, current action/DagRun/generation) to one new monitor action.
The prior action is canceled as superseded, NOT compute-failed; history remains.
Registration and retirement commit together under the existing run lock; old
DagRun authority is fenced. Reserved/uncertain dispatch, active reconnect,
foreign identity and user stops are not bypassed. Repeated requests reuse the
same action. GATK now preserves the original Step3 deadline on manual recovery.
No attempt/automatic-budget/deadline reset or unconditional Master replacement.

Existing detail Resume confirmation is reused as "恢复监控" for WGS/GATK query
attention, behind adapter capability/operator gates. No new page/public route.
BS10610 backend82 pass15.32s; frontend2 pass3.15s; TypeScript/Vite build passed.
Native fd43f88/plugin81132cf unchanged. No production, merge/push, images,
installed CLI/runtime updates or live workflows. Task6 remains OPEN: focused
PostgreSQL contention, full automatic lifecycle and one final whole-plan review.

## 2026-09-25 Task6 finite reconnect producer/consumer wiring

Supersedes the unwired prerequisite below. Paired WGS/GATK selected monitors now
attach one query-only owner to strict native GETs (including legacy JSON reads).
Existing current-generation status JSON persists reservations before retry,
retains measured progress, checks registration on every load/save and fsyncs the
GATK reservation. Missing/foreign/terminal status cannot silently reset a budget.
No whole-monitor, CREATE/START, transfer or biological-workflow retry was added.

Outer failed monitor status preserves the query marker. Real WGS/GATK ingestion
retains last confirmed analysis/stage state; the existing recovery view shows
checking or needs_attention, limit6, and explicitly unconfirmed execution after
exhaustion/control errors. Failure callbacks AND periodic DagRun reconciliation
share the current monitor fence. A healthy complete observation clears the
query overlay, not the attempt-level compute budget.

BS10610: affected query/backend regression113 pass8.29s; after final missing-status
guard, producer/consumer16 pass3.63s and actual selected-monitor new/legacy4
pass6.43s. Native source fd43f88, plugin81132cf unchanged. No local runtime tests,
production, push/merge/deploy, activation or artifact rebuild.
Task6/CR-04 remain OPEN pending the final automatic lifecycle/manual reconnect
interaction, focused PostgreSQL contention and whole-plan fresh review. Existing
manual controls and compute-action lifecycle were not expanded in this checkpoint.

## 2026-09-25 Task6 finite query-budget prerequisite

Added the internal query-only budget core: initial GET plus max6 retries at
30/60/120/240/300/300s, each request capped30s and by the original absolute
deadline. Existing-stage-JSON load/save callbacks retain identity, first error,
consumed retries, due time and last confirmed observation. Reservation is saved
before retry; interrupted in-flight calls consume their slot. Partial GET success
cannot reset the outage; only caller-confirmed complete observation can reset it.
Foreign/corrupt state and permission/auth/unknown errors stop without replay.

Paired native strict GET now accepts the exact directory-lock ConfigMap that the
platform already queries, supplies a shorter bounded timeout and separates local/
auth errors from temporary transport errors. Legacy readers are unchanged.
BS10610 native24 + platform17 targeted tests passed0.79s. No production, installed
CLI, images, workflow, service or policy activation; source-only checkpoint.

Important: the budget helper is NOT YET WIRED to the WGS/GATK monitor. Next is its
current-generation status persistence/producer integration and backend/UI outcome
distinction (including GATK/callback/periodic failure projection). Task6/CR-04
remain OPEN, followed by focused PG and final automatic lifecycle/review gates.

## 2026-09-25 Task6 recovery UI checkpoint

Existing Tracker and RunDetail now consume the same optional read-only recovery
projection: waiting/checking/recovering/needs_attention/stale/completed_degraded.
Accepted/queued dispatch is not proof of a started replacement Master. Exact
current monitor schema2 identity plus Job/Pod UID and recovery action are required.
Existing status history/budgets remain unchanged. Pending/uncertain display keeps
last measured progress, disables time-based estimates/ETA and never fills a failed
or complete bar without evidence. No new page, control action or scheduler.

The existing WGS/GATK status consumers retain an allowlisted current-monitor
observation in existing execution JSON; newer degraded evidence cannot be cleared
by an older healthy replay. This closes the real running-evidence ingestion gap,
not only a fixture-only UI path. No schema migration or producer changes.
BS10610 final backend26 GREEN3.03s, frontend13 GREEN6.17s and tsc/Vite build GREEN.
Source-only, original P0 branch; no production, merge/push, image build or activation.
Task6 remains OPEN: finite-reconnect producer-to-UI distinctions, focused PG
contention, final automatic lifecycle integration and whole-plan review. An absent
explicit reconnect signal remains state-unconfirmed, never an invented retry.

## 2026-09-25 Task6 Step4 caller checkpoint

The existing WGS/GATK Step4 runner and reschedule sensor now consume the original
operation probe/budget. First opted-in registration hashes marker1 and freezes
the stage deadline (WGS contract timeout / GATK existing48h). Existing authenticated
stage routes commit begin/poll intents before SSH, check current controls again
at send, and acknowledge only the exact exited local invocation. Timeout/nonzero
SSH hands off to reconciliation, not a task-wide retry or a new generation.
Fixed --publish-dispatch pins generation/hash; both launch gates enforce the
original deadline. Probe success still requires the normal successful stage
receipt before Step5. Default-off/legacy paths and DAG graph are unchanged.

BS10610 final scoped backend/runtime90 GREEN7.11s, real-Airflow20 GREEN3.04s.
No native/plugin change, artifact rebuild, service activation or production access.
Task6 remains OPEN: existing UI projections, focused PG contention and final
automatic integration/whole-plan review next; separately authorized live gates
remain closed. This is caller acceptance, not production readiness.

## 2026-09-25 Task6 Step4 operation/budget checkpoint

Step4 now has a fixed restricted original-operation probe and a separate durable
dispatch budget in the existing RunAction. Probe validates registered identity,
launch/worker locks and exact receipts/process records; missing or ambiguous
evidence does not imply a failed publish. Opted-in WGS Step4 refuses a second
spawn after an uncertain first spawn; GATK's existing intent fence is retained.
Budget keeps the same execution/generation/hash and original stage deadline,
at most two redispatches60/180, with fresh post-delay proof and no in-flight SSH.
It never consumes/resets the Master recovery budget or rewrites stage receipts.
BS10610 final64 targeted cases GREEN3.73s; no native/plugin or service changes.

This is the Step4 source contract, NOT an active automatic caller. Next wire the
existing stage registration and Airflow Step4 runner/sensor to these functions,
freeze the opt-in request marker/deadline there and commit intent before SSH.
No new DAG node/public route; real PG contention/full integration still pending.
Task6 OPEN; no main/production merge, push, deployment or artifact rebuild.

## 2026-09-25 Task6 exact CREATE classification checkpoint

Plugin source now classifies exact Worker CREATE storage RPC Unavailable/peer-reset
HTTP500 and mutation.gatekeeper.sh context-deadline failures. Original Job is
reconciled first; RPC UNKNOWN cannot replay. Backend and inventory independently
require fixed typed CREATE fields, ABSENT, exhausted budget and existing complete
fatal-cause/terminal evidence. No generic500 or policy-denial automatic permission.
BS10610 focused30 source/consumer +2 actual producer/FINAL/reservation cases passed.
Task5 artifacts, native d7bd741, services and default-off policy unchanged.
Source commits only, no production/push/build/activation. Task6 remains OPEN:
next Step4 same-operation reconciliation, then existing UI/PG/final integration
and separately authorized operational gates. See latest HANDOFF for provenance.

## 2026-09-25 Task6 bounded Worker wait checkpoint

Known same-owner active Workers now produce a waiting candidate, not replacement
authority. The existing Airflow recovery action persists wait start/deadline
(max600s capped by original compute deadline), one slot and current-monitor nonce.
Existing sensors call a fixed restricted read-only probe and return its evidence
to the existing internal POST. Only unchanged FINAL/producer/cause plus fresh
zero-active evidence clears waiting; native replacement independently rechecks.
Stop, expiry or changed evidence blocks dispatch. No Worker kill or failed receipt
rewrite; missing terminal evidence after reclamation remains blocked.

BS10610 final focused17 backend/producer (5.52s),2 restricted entry (5.27s),4 real
Airflow sensor cases (3.03s) passed. Boundary preflight unchanged; no service changes.
Platform isolated branch only; native d7bd741/plugin c0b266b and Task5 artifacts
unchanged. No main/production merge, push, build, install, activation or real rerun.
Task6 still OPEN: remaining exact failure classes, Step4 reconciliation, existing
UI projections, PG/final integration and separately authorized live cloud gates.

## 2026-09-25 Task6 controller deadline checkpoint

Original registered Step3 deadline now reaches native replacement and both
WGS/GATK monitor loops. Native journal identity retains the absolute deadline;
DELETE/CREATE/handoff check remaining time and handoff is capped by it. Monitor
restart/replay cannot extend the deadline. Invalid present values fail closed;
absent values retain historical/default-off behavior and Task5 native ABI.
Expiry preserves all evidence and Jobs for reconciliation; no workload kill or
Job activeDeadlineSeconds change, biological change or frozen bundle rewrite.

BS10610 offline focused22 passed16.25s, compute-deadline-final.log. Existing
control/current/RO mounts and disabled scanner/dispatcher preflight passed.
Only original platform/native isolated branches changed (natived7bd741); pluginc0b266b and
Task5 artifacts preserved. No push/main merge/install/build/production/rerun.
Task6 remains OPEN. Next: Airflow-owned persistent bounded Worker wait, then
remaining exact failure classes, Step4 reconciliation, existing UI, PG/final
integration and separate authorized live cloud gates.

## 2026-09-25 Task6 policy and Airflow polling checkpoint

New WGS/GATK CCE creation now freezes its own default-off policy/zero budget.
First Step3 registration fixes the original deadline; duplicate registration
preserves request hash/generation. Historical or legacy manual next-attempt
flows gain no new automatic quota and remain manually executable.
Existing authenticated stage POST and existing Step3 sensors call the due owner;
waiting reschedules, confirmed delegation skips the old chain before observer
deactivation/downstream. Lost responses do not create another action/POST.
Exact current compute terminal evidence releases the active compute fence while
retaining downstream authorization. Two failures consume shared slots60/180s;
older completed compute history no longer blocks current cleanup.

BS10610 offline targeted backend19 GREEN4.70s and real-Airflow5 GREEN3.00s.
No full-suite repetition, local runtime test, production, deployment, main merge,
push or real rerun. Default-off settings are source only and must NOT be enabled.
Task6 remains open: native deadline enforcement, bounded Worker wait, remaining
exact failure classes, Step4 reconciliation, UI, PG and final integration.
Task5 artifacts and native/plugin source pins remain unchanged this checkpoint.

## 2026-09-25 Task6 internal due-dispatch checkpoint

Prerequisite source committed: platform abdba43, native ffe51d4, plugin c0b266b.
Existing reserved automatic actions now have an internal due-dispatch service:
wait without writing requests, revalidate original schema2 proof and budget,
persist the same action/DagRun before writes, then use existing adapter stage
registration and shared Resume POST-intent/GET-only reconciliation. No second
manual action, new attempt, prepare/upload or independent retry engine.
After a prepared-intent crash the original failed receipt is revalidated again.
Late reconciliation cannot overwrite a user stop; missing policy/evidence fails
closed. The frozen original deadline is carried into recovery stage requests.

BS10610 targeted23 GREEN4.68s (14 new cases plus9 affected manual cases).
This is internal source acceptance only: no Airflow automatic caller, new-attempt
policy freeze/enablement or runtime deadline consumption is wired yet. Bounded
Worker wait, remaining exact error classes, Step4 reconciliation, UI, PG and
whole Task6 integration still open. No deployment/main merge/push/real rerun.

## 2026-09-25 Task6 prerequisite accepted — bound failure accounting

User approved “补齐，然后继续”. Existing Master rule-status logger now counts
typed submission/control failures, rule/group failures and unstructured errors;
private phase summary becomes complete only on normal logger close after exactly
one workflow start. Real Snakemake9.24 shutdown notices are separately accounted
for by exact source/function/message, never by text alone. Worker mode is unchanged.
Native handoff-v2 preflight also enables this logger; FINAL binds the optional
summary without inventing completeness for old/missing audits.

The restricted selected-Master monitor verifies native FINAL, all phase audits,
retained Worker lineage and fresh complete Job/Pod inventory before attaching
`cce_recovery_evidence` to the existing immutable verified receipt. Backend
reservation consumes schema2 with distinct platform and native identities,
including a later observer retaining an older Step3 producer. Missing/mixed/
active/unclassified evidence remains ineligible; no automatic dispatch occurs.

BS10610 offline final focused28 passed35.59s. This closes the approved producer/
schema2 prerequisite only; Task6 dispatch, policy freeze, Step4 reconciliation,
UI/PG/final integration and separately authorized operational gates remain open.
No installed CLI/image/policy, production, main merge, push or real rerun changes.
Task5 artifacts retain their original bytes and do not contain this new source.

## 2026-09-24 Task6 preflight — automatic evidence producer gap

Task6 started with source/interface inspection at platform83528cf,
native770934c and pluginb6d1fb8. No implementation, runtime test or activation
in this checkpoint. Tasks1–5 acceptance is unchanged.

The automatic reservation bridge still expects the earlier flat Master binding
and `master-terminal.json` contract. Task4 exports schema2 with separate platform
and native identities; native FINAL proves process exit and submission inventory,
not the complete fatal-cause classification required for automatic recovery.
Do not relabel native IDs as platform IDs or synthesize zero rule/other failures.
Proposed next scope confirmation: complete the existing Master wrapper/logger
failure summary and adapt the existing reader/reservation bridge, then dispatch.
See latest HANDOFF for exact producers/consumers and remaining Task6 gates.

## 2026-09-24 Task5 source and offline artifacts accepted

Task5 only: Worker/Master/evidence-reader TTL100. Generators6 RED then6 GREEN;
affected missing-object/lost-response/deadline15 GREEN; image sibling1 RED then
1 GREEN. All BS10610 offline. Distinct native/plugin wheels and WGS/GATK Master
test images built; actual-wheel acceptance13 passed and both image smokes passed.
Pins: native7232f57, pluginfdf1520, platform consumer074dc55. Full provenance and
scope review: docs/releases/2026-09-24-p02-task5-offline-artifacts.md.
Task6 automatic recovery is next; live TTL/capacity/AOM/alerts remain separate gates.
No Task6, production, installed CLI/policy, old-bundle or service changes.

## 2026-09-24 Task4 manual source acceptance complete

Historical Task4 closure: Tasks1–4 source acceptance complete; the newer Task5
entry above supersedes its then-unstarted TTL/artifact status. Task6 remains open. Earlier
dated checkpoints below describe their then-open slices, not current blockers.

Existing authenticated WGS/GATK manual Resume now reaches the original restricted
adapter/native recovery, fresh-process selected-Master monitoring and normal
Step4–6 receipts. Same attempt/config/workdir; no prepare/upload redo or forceall.
Active Master reattaches, native success continues downstream, unknown evidence
blocks. Initial CREATE/handoff interruption and post-bind crash reconcile the
same UID/action/deadline without a second CREATE. WGS reattach revalidates receipt
authority before archival instead of copying raw binding fields.

Final Step6 release requires materialization, native success, registered generation
lineage, complete live inventories and inactive sibling dispatchers. Retained old
terminal Workers are verified; unknown/active Workers still prevent release.
Native bd41f87 projects generation-local final manifest while preserving shared
history. Plugin5b5d7ee unchanged. Original bundles/output roots remain unchanged.

Latest-requirements cross-check and review: three Important findings reproduced
RED and fixed; final BS10610 selected41 passed/1 skipped76.91s, authenticated
manual WGS/GATK2 passed41.32s. The skip is the WGS-only reattach-worker case for
GATK, not a missing GATK recovery test. See HANDOFF and the Task4 plan checklist.
No local runtime/full-suite tests, images/CLI/policy installation, automatic
enablement, main/production merge/push, production DB/data or real rerun changes.

## 2026-09-24 Task4 selected-Master Step3 checkpoint

BS10610 validation resumed. A fresh WGS/GATK monitor reconstructs the selected
Master from registered Step2 request/receipt, native journal/handoff, frozen
inputs and the exact directory owner. Actual gate polling and rule-log bridge
now use that verified view, preserving the original bundle and producer identity.
Old run-id-only completion markers cannot report a new Master successful.
Reclaimed Job success/failure requires matching native terminal evidence.

Focused selected-monitor tests18 GREEN30.04s; affected Step2 replay2, worker
disconnect1 and unactivated entry2 also GREEN. Native903e1af; no production,
deployment, policy installation, new Job, local tests or full-suite repetition.
Task4 remains OPEN: direct Step3 replacement/initial-submit paths, selected
Step4-6 reconstruction/execution, final protected release and authenticated
service/DAG/native manual flow. Tasks5/6 remain unstarted. This checkpoint does
not authorize activation or represent whole Task4 acceptance.

## 2026-09-24 Task4 registered Step2 recovery checkpoint

BS10610 SSH restored; isolated offline validation resumed. Existing paired
runtime now constructs RecoveryCapability from the registered stage request,
operator-approved frozen binding, physical directory identity and exact native
old owner. Holds shared directory serialization and other dispatcher/launch
locks throughout existing Resume. Missing/foreign locks, changed request and
uncertain dispatcher evidence refuse replacement. WGS/GATK actual Step2 entries
retain verified native/platform identity in normal status receipts; replay
creates/starts only once and preserves frozen inputs.

BS10610: actual entry2 RED; corrected real GATK request shape1 RED; final14
GREEN13.78s and affected legacy/receipt3 GREEN2.17s. No broad suite, local tests,
activation, live cloud workload, production service or DB change.
Task4 remains OPEN: selected-view reconstruction across processes, native
Step3-6 execution, final protected release and authenticated service/DAG/native
manual flow. Activated Step3 replacement fails closed until that continuation
is connected. Operator bindings are not automatically generated/installed.
Tasks5/6 remain unstarted.

## 2026-09-24 Task4 verified normal-receipt checkpoint

WGS/GATK status writers now carry native-verified Master binding metadata from
an internal result, including running/success/failed receipts; GATK receipt hash
covers the metadata. WGS Resume worker retains it when monitoring disconnects.
JSON round trips and generic progress kwargs cannot supply verified authority.
Master submit identity stays distinct from the current observing execution.
BS10610 offline: two receipt cases RED then GREEN; seven affected checks GREEN
7.62s; final observer-identity refinement two GREEN3.51s. No full suite or live
runtime tests. No production, deployment, activation, DB or frozen bundle change.

Task4 remains OPEN: trusted per-run factory, actual GATK Resume routing,
cross-process selected-view reconstruction/Step3-6 execution, final lock release
and one authenticated service/DAG/native manual flow. The status-writer slice
is not cross-process closure. Tasks5/6 remain unstarted.

## 2026-09-24 Task4 cloud identity and paired entry checkpoints

Source commits: native7026528, platformc3cf3c2. Follow-up closes a fallback edge:
activated Resume without verified RecoveryCapability rejects before entering the
legacy lock path. Two adapter cases RED; final12 new +3 affected GREEN0.99s.

User approved the existing cloud read-only reader, not a new SFS host mount.
Native source now validates PVC/PV/Job/Pod identities and resolves directory
aliases in that reader, with durable one-create/reconciled cleanup and no foreign
UID deletion. Frozen binding validation precedes the probe. Cloud10 plus affected
protected-entry13 passed on BS10610 offline synthetic (23 GREEN2.23s).

Platform WGS/GATK stage command and Resume runtime selection now honor fixed
operator-owned paired pins, including the sibling guard; invalid activation
never falls back to old frozen code. GATK custom result-root materialization
enters the same writer without changing its approved output location. New10 and
three existing GATK result-root checks passed (13 GREEN0.82s).

These are source checkpoints, not Task4 acceptance or deployment. Actual trusted
per-run registration/recovery capability, selected-view normal receipts, final
lock release and full service/DAG/native manual closure remain OPEN. Tasks5/6
remain unstarted. No policy, cloud Job, CLI/image or production service changed.

## 2026-09-24 Task4 CLI protected-entry checkpoint (native8ec5415)

Follow-up binds actual stage arguments to the original bundle/contract/config;
new13 checks passed. Historical mapping question (resolved above): reuse the
existing cloud read-only reader (recommended) vs an already mounted SFS path.
No verified local SFS mapping exists in this task; do not substitute local NFS or
create new mounts. The user subsequently approved the cloud reader.

User approved CLI Step1–Step6 compatibility scope. Isolated native source now
guards every stage, preserves v2 locks on early failure, checks operator-owned
paired source pins/physical storage mapping/exact frozen binding at CLI entry,
and serializes shared journal writes. No old bundle/config/policy was installed.
BS10610 new12 GREEN, affected lock/downstream35 GREEN, legacy Step4/5 three GREEN.
Task4 remains OPEN: actual platform registration/gates, selected-view receipts,
final downstream release and complete WGS/GATK manual flow are still pending.
Tasks5/6 unstarted; no production/CLI/image/TTL/automatic activation.

## 2026-09-24 Task4 downstream/binding checkpoints; CLI entry scope confirmation

Native isolated commit08c6cda accepts selected-Master evidence for Step4/5/log
export while keeping delivery/log/output roots under the original bundle. Missing
TTL-reclaimed Job needs validated native success; active/foreign Job blocks.
WGS/GATK Resume now export v2 Master bindings from validated handoff bytes, with
platform identity separate from native generation/hash and no legacy relabelling.
BS10610 offline downstream10 and adapter binding6 affected checks passed.

Task4 is NOT complete: restricted entry selected-view persistence/forwarding,
canonical storage mapping and paired all-writer activation remain open. The CLI
scope was subsequently approved and the source entry checkpoint above supersedes
the missing-entry observation. Actual paired activation remains unproven.
No production changes; Task5/6 have not been started.

## 2026-09-24 Task4 GATK dispatcher fencing checkpoint

GATK Step1–6 now serialize launch/worker ownership, persist a pre-spawn intent
and PID/boot/start identity, and reject unknown or superseded execution writers.
Terminal receipts require full execution identity; ambiguous/dead legacy dispatchers
are not automatically replaced. Prepare and Step7 retain their existing mechanisms.
BS10610 offline synthetic: five behavioral RED cases, then15 affected checks GREEN,
including real fork/lock handoff. No live service or gate changes. Task4 remains
OPEN for trusted storage/all-writer activation, binding and selected-view downstream.

## 2026-09-24 Task4 initial Master binding source checkpoint

User approved initial Master platform identity binding. Native isolated source now
provides an independent initial submission view and internal Step2 opt-in; frozen
inputs/default CLI are unchanged. Platform and native generation/request hashes
remain separate and bound through Master confirmation and terminal evidence.
WGS/GATK Resume forward a fresh platform identity into existing replacement journals.
BS10610 affected native41 passed; actual adapter/producer composition2 passed.
No deployment, image/CLI install or automatic activation. Task4 still requires
trusted binding writer/storage mapping, paired writers/dispatcher proof and normal
downstream selected-view acceptance; Tasks5/6 remain gated by that closure.

## 2026-09-24 Task4 GATK service/DAG checkpoint; native activation still blocked

GATK now has its own frozen-request Resume registration using
PipelineStageExecution, original attempt/profile/bundle, preserved request history,
and the existing RunAction journal. WGS/GATK share only durable Airflow dispatch
and action authorization. The existing operator/CSRF endpoint selects the adapter;
GATK `resume` capability is NOT enabled in the shipped registry. Its DAG skips
prepare/upload/completed stages and carries actual DagRun/action identity.
Registration, slot acquisition and finalization reject superseded/control states.

BS10610 isolated checks:39 affected backend cases passed; the added HTTP routing
and finalize-control cases passed separately; one real-Airflow GATK DAG case
passed. No full suite or local runtime tests; no service/production/CLI/image change.

Task4 is not complete. A concrete producer gap needs confirmation: replacement
Master gets recovery_context, but initial Master submission does not yet bind
platform execution identity. Native handoff request_hash and platform stage
request_hash are DIFFERENT digests and must not be treated as interchangeable.
User asked to authorize this necessary initial-submission source addition; no
such producer edit performed. Trusted binding writer/all-writer proof/selected
view downstream remain open; Task5 TTL and Task6 auto dispatch remain gated.

## 2026-09-24 Task4 checkpoint: WGS authenticated dispatch fence accepted

Task4 STARTED, not complete. Existing WGS Resume journals POST intent before
Airflow, reconciles exact DagRun ID/conf by GET after uncertain POST, and keeps
late replies from clearing newer controls/current-DAG failure. Recovery DAG
registrations now carry actual DagRun ID; scope/control checks cover stages,
slot acquire (recheck after helper commit) and finalize with reused Step6.
No new endpoint/table or recovery engine. BS10610 isolated synthetic acceptance:
31 backend cases covered across affected groups;3 real-Airflow DAG tests passed.
One scoped review,3 Important fixed and rechecked; no open Important/Critical.
No full suite, local runtime tests, production/service/CLI/image changes or push.

Platform base f93ba00; producer32aa7fb and Worker5b5d7ee unchanged. Remaining
Task4: GATK own-service/DAG routing; trusted native binding/canonical lock mapping;
paired all-writer/dispatcher exclusion; selected-view propagation into monitoring
and downstream receipts. Do not advance Task5 TTL or automatic recovery yet.
See HANDOFF for commands, source boundaries and isolated evidence path.

## 2026-09-24 Task3 source implementation accepted

Verified dependency commits: platform321b0a1, producerfa1ac44, Worker5b5d7ee.
Existing WGS/GATK Resume now consumes verified final inventory, trusted lock
capability, native generation view and original adapter journals. BS10610:
capability6 GREEN; initial composition10 RED; expanded composition29 GREEN;
5 affected legacy checks GREEN. Scoped review: no open Important/Critical.
SSH recovered; latest source synced and validated, see HANDOFF for evidence.
Task3 source complete; Task4 authenticated service/DAG/all-writer construction
and selected-view propagation remain next. No automatic/TTL activation, images,
CLI install, production changes, real reruns, main/production merge or push.

## 2026-09-24 Task3 approved snapshot/view dependencies accepted

User approved isolated native final Worker snapshot + independent next-generation
view. Implemented without changing original bundle/config/history. Master seals
completed plugin phase journals/checkpoints/Worker terminals/manifest; this is
NOT an all-writer recovery seal. Current-bound native reader and complete live
run-label/exact Job/Pod reconciliation reject incomplete, unknown or contradictory
evidence. BS10610 synthetic: view6 + final18 + live10 new cases passed;5 affected
checks. Prior query/confirmation/native success checkpoint27 + replay/review4 also
passed. See HANDOFF for individual logs, not a full-suite claim.
Task3 still OPEN: trusted lock capability and existing WGS/GATK Resume side-effect
journal wiring/final matrix. Task4 authenticated all-writer closure stays separate.
No local runtime tests, installs, images, services, production or real reruns.

## 2026-09-23 Task3 confirmation/native success consumers; producer gap identified

Compatible Resume queries use a bounded, classified producer reader; errors are
never absence and incomplete pages block. WGS v2 handoff consumes actual Task1
START_CONFIRMED (original deadline, no repeated START); GATK can reconcile its
same active v2 Master. Native success requires matching handoff, confirmation,
RUN_COMPLETE, three zero stage exit codes and workflow completion, not just a
Job Complete condition. Contradictory/active terminals block continuation.

Task3 is NOT complete. Failed v2 Master replacement blocks BEFORE mutation:
Task1 cannot accept another UID in its frozen generation. Final submission
inventory is not sealed by the Master (evidence_complete=false; submit-context
injection absent at that historical checkpoint). Approval and implementation
above supersede the then-pending scope question for final inventory and
explicit next-generation recovery view in isolated producer source. Do not
rewrite frozen bundles or treat process-only evidence as a full seal. Complete
live inventories/canonical lock callbacks remain open, then Task4.

BS10610 synthetic: RED15 -> GREEN15 query/confirmation; RED9 -> GREEN9 native
success; RED3 -> GREEN3 terminal ambiguity. No local tests, production actions,
install, artifact build, TTL or automatic activation. HANDOFF records provenance.

## 2026-09-23 P0-2 Task3 first guard checkpoint (Task3 still in progress)

Existing WGS Resume no longer submits again after unknown CREATE followed by404,
or after an acknowledged replacement disappears. Recheck exact Master UID/RV
before DELETE; journal writes are exclusive/owner-only, file+directory fsynced,
and preserve existing fields. WGS/GATK reject incomplete Pod inventories;
GATK archived Worker NOT_FOUND without terminal proof now blocks before claim.
BS10610 synthetic RED6 failed/1 passed, GREEN7 new +13 directly affected legacy
passed. Review added delayed-visible failed replacement RED1; fixed guard and
that case + affected normal replacement GREEN2. Eight new cases accepted total.
No full suite, local tests, image/install, service or production changes.

This is a bounded safety checkpoint, NOT Task3/Resume consumer completion.
Next: compatible START_CONFIRMED/native terminal consumption, complete admitted
Worker/live inventories and trusted directory-lock callbacks through existing
Resume; then Task4 authenticated adapter/all-writer closure. No TTL/automatic
enablement. Old frozen bundles remain unchanged; unknown outcomes stay blocked.
Step7 plus manual local deletion does not yet permit platform same-batch
recreation: batch/snapshot uniqueness and old record reuse remain a separate
unimplemented boundary, not fixed by directory lock primitives alone.

## 2026-09-23 P0-2 Task2 source primitives accepted; no production rerun

User clarified the five historical reruns are a lock-compatibility discussion,
not an operational request. Continue the approved P0 plan, no BS96 actions.
Plugin5b5d7ee (0.6.4+bs8.dev1 successor source) persists exact admitted Worker
terminal evidence before callbacks; known terminals avoid status queries,
unknown404 stays unknown. Quota claims remain conservatively managed.
cce-pipeline7926496 adds opt-in directory ownership, journal-before-CAS handoff,
conditional release, stale-generation protection and explicit legacy guard.
Existing two-argument/frozen callers unchanged; no current consumer opts in.
BS10610:15 Worker +17 lock cases;5 +3 affected legacy cases passed. Focused
review issues fixed and rechecked. No full suite, image/wheel or installation.

Five legacy runs will retain analysis_id/attempt/config/workdir/history. The
upgraded recovery entry must verify exact legacy mapping/quiescence, preserve
the old lock snapshot, then conditionally reserve/bind the new generation.
Unknown mappings stop for verification, not automatic lock deletion. Canonical
storage resolution and paired CLI/platform/stage writers are mandatory before
activation; frozen bundles must not be rewritten. These trusted consumers and
end-to-end manual recovery are Tasks3/4, not complete yet. Next: Task3.
All changes on isolated development branches only; no main/production merge,
push, deployment, real batch action, TTL activation or automatic enablement.

## 2026-09-23 P0-2 Task1 source acceptance complete

User requested Task1 only. cce-pipeline source c33740d on independent branch
`jiucheng/runtime/p02-master-handoff-20260923`, verified base83e7adb.
Existing handoff now requires identity-bound persistent Master confirmation;
lost START response/restart reconciles without another START or deadline reset.
Trusted native setup/execution terminal records retain original success checks;
same-Pod atomic claim prevents duplicate entrypoint/config/terminal writes.
BS10610 final24 targeted +18 affected legacy tests passed, synthetic only.
Fresh server10610/current/mount/gates/permissions verified; initial connection
blocker is resolved, though intermittent jump SSH failures were observed.
No product deployment, image build/install, BS96/main/production or frozen-project
changes. Process terminal evidence is not a Worker-finality/recovery seal.
Docs and field mapping updated. Task1 done at source level; Tasks2–6 remain open.
Next planned Task2: Worker terminal persistence and logical-run lock ownership.
TTL remains unchanged; automatic recovery stays disabled.

## 2026-09-23 P0-2 implementation plan integrated; execution blocked

User requested planning and implementation of the latest P0 revision. Integrated
a1af96a/729564c/781877e into the existing CR01 design, retaining prior quota/RPC
coverage and accepted work. Plan: docs/superpowers/plans/2026-09-23-p0-2-master-handoff-ttl-implementation.md.
Order: Master handoff/terminal producer; Worker terminal and P0-2E logical-run
lock handoff; TTL-safe runtime Resume; authenticated manual adapters; compatible
TTL generators/artifact checks; remaining automatic P0 and operational gates.
No product code changed this turn. BS10610 preflight failed twice at BS jump
172.17.61.18 SSH handshake (exit1); host/mounts/permissions not freshly verified.
Producer source ownership also requires verification: reported83e7adb prototype
has uncommitted work, not a verified authoritative baseline. No local tests,
deployment, BS96/main/production writes or policy activation. Tasks1–6 remain
open; resume with fresh test preflight and producer provenance, then Task1 RED.

## 2026-09-23 current-attempt receipt projection refreshed (source only)

WGS runtime stage-status ingestion and GATK stage-status sync now lock and
refresh AnalysisRun before validating/projecting a receipt. GATK refuses old
attempts; both refresh cached execution state so a late failure cannot replace
a durable terminal success. Existing generation rejection remains intact.
BS10610 isolated checks:8 focused cases after4 expected failures, plus5 affected
legacy cases passed. No PostgreSQL concurrency or end-to-end recovery claimed.
Committed on the independent CR01 branch only; no services/BS96/main changes.
Trusted terminal/binding writers, dispatch/adapters, other observer evidence
paths and Step4 reconciliation remain; automatic recovery stays disabled.

## 2026-09-23 bs7 inventory and actual producer acceptance completed

BS10610 connectivity restored; fresh host/mount/gates match the prior test
fingerprint. Control inventory now binds exact existing CREATED/ADOPTED Worker
UIDs and complete manifest; null control UID never means absent, mixed submit
failure or incomplete inventory rejects.34 focused tests passed after RED.
bs7 actual-wheel-generated four WGS/GATK GET/LIST fixtures passed4 platform
checks; no missing-fixture skips. Plugin25297f9 built offline through owner's
guarded script,52 actual-wheel checks passed; bs6 remains0b19bb6 unchanged.
Source/artifact compatibility only, not terminal/automatic recovery acceptance.
Continue existing trusted runtime/query, dispatcher/adapter/observer/Step4 work.
No services, production/main changes or automatic recovery enablement.

### Previous paused checkpoint (resolved above)

First current-disconnection slice committed26d62dd. Follow-on control inventory
test draft added (10cases), unrun: SCP and remote RED command both stopped at
BS jump172.17.61.18 SSH handshake before remote execution. No inventory code
changed or local/production testing substituted. Next: fresh BS10610 preflight,
test RED, inventory adaptation and actual bs7 fixture acceptance. Owner-reported
108 plugin source tests are not platform artifact acceptance; artifact pending.

## 2026-09-23 requested disconnection coverage additions (source only)

GATK idempotent input/result transfer-slot sensors now use the existing bounded
backend transient retry rules. Same identity reacquisition cannot steal a slot;
transfer/SSH/CREATE/publish/release tasks are not newly retried. BS10610 actual
DAG7 checks passed after RED; two backend lease identity checks passed.

Agreed separate HEAVY_SLOT_API_UNAVAILABLE control candidate supports exact
GET Lease / Worker Pod LIST errno111 failures. Internal consumer and controlled
reader implemented and synthetic tests passed; generic500/writes/mixed files/
active Workers/incomplete terminal refuse. Plugin owner is implementing a new
bs7 artifact; actual-source fixture and inventory integration remain pending.
D RPC500 source classification and WES generic kubectl query failure remain open,
not falsely classified from summary text. No production/main/service changes.
P0 is still incomplete and automatic recovery remains disabled. Continue existing
runtime contract, dispatcher/adapter/observer/Step4 and remote acceptance work.

## 2026-09-23 old DagRun cleanup fence completed (source only)

CR-03 WGS/GATK transfer-release endpoints and WGS observer deactivation now
check refreshed current attempt/DagRun/recovery identity under the run row lock.
Old or unbound recovery cleanup cannot release even a terminal transfer or drain
the replacement observer. Current cleanup retains existing terminal-only lease
release. Partial WGS release re-locks before retained-slot state projection.
DAG cleanup callers send actual run_id; no graph/runtime/Step7 changes.
BS10610:24 new backend cases,3 affected legacy endpoint cases and7 actual DAG
tests passed (targeted runs only). Source and progress docs on the independent
CR01 branch; no push/merge/deployment, production or shared-service mutation.
Remaining: dispatcher/adapter wiring, observer generation projection, trusted
terminal closure, Step4 reconciliation and PostgreSQL/end-to-end acceptance.
Automatic recovery remains disabled; P0 is not complete.

## 2026-09-23 old DagRun failure callback fence completed

WGS/GATK failure projection now refreshes the locked run and refuses stale
DagRun identity or an unresolved automatic-recovery reservation. GATK callback
passes actual dag_run.run_id through its existing internal API. Exact current
queued/uncertain replacement may report failure; terminal behavior is retained.
WGS failure deduplication includes DagRun identity so a new failure cannot reuse
the old end time. No history rewritten, no new table, dispatch or policy enable.
BS10610:22 new backend cases,5 affected legacy cases and1 actual Airflow DAG
callback check passed; two observed RED failures. Only affected cases rerun for
the small dedup fix. No shared services/main/production change or deployment.
Remaining CR-03: dispatch/adapter/lease and observer fences, trusted terminal
closure, PostgreSQL concurrency and end-to-end acceptance; P0 is not complete.

## 2026-09-23 existing WGS manual-retry fence completed

Legacy Resume/Rerun failed now take/refresh the AnalysisRun row lock and reject
pending current-attempt automatic recovery before release lookup, attempt/state
mutation or dispatch. Existing resume_stage shares the same check. Missing or
ill-typed action attempt identity blocks; finished automatic history is retained
and permits manual retry. Cancel keeps priority and its existing CCE restrictions.
BS10610 RED reproduced bypass; GREEN22 focused checks passed1.23s (14 new plus
8 affected resume-stage checks). No shared service, production, policy or DB change.
This closes these WGS service entry points only; dispatch/callback/adapter/GATK
integration and PostgreSQL concurrency acceptance remain pending.

## 2026-09-23 bs6 consumer contract acceptance passed

SSH restored. Actual hash-pinned bs6 wheel generated WGS/GATK admission and guard
fixtures; consumer and inventory checks passed14/14 on BS10610 (0.32s,62 unrelated
cases deselected). Guard category alone also rejects with otherwise qualifying
synthetic values. Candidate without terminal rejects for all four scopes.
No production code, allowlist, API/DB, service or automatic-policy change.

This closes bs6 candidate-format compatibility only. Positive terminal objects
in tests are explicitly synthetic, not runtime evidence; complete Master/Worker
terminal support and recovery dispatch/adapter/callback integration remain open.
Next: remaining existing control/dispatch/callback fences and adapter integration,
without restoring the extra audit track or enabling recovery on incomplete proof.
Fresh test backend36ff21f87356 mounts20260923-step7-ae416fa/backend/backend;
test gates scan/dispatch=false, readonly nonterminal-run query returned[].

## 2026-09-23 bs6 consumer acceptance started; SSH preflight blocked

User requested next step. Selected actual bs6 consumer contract acceptance only,
not deployment. One BS10610 preflight failed during ProxyJump BS handshake:
172.17.61.18:22 connection reset, before reaching server10610. No fresh remote
mount/active-run fingerprint, remote writes or tests. Existing results do not
establish current connectivity. Producer owner asked for actual wheel-generated
WGS/GATK admission and quota-guard fixtures; receipt is pending.
Added an unrun guard-category negative case to the existing synthetic consumer
test; no production code/allowlist changed. Resume this exact acceptance after
test-host access is restored; do not substitute local or production execution.

## 2026-09-23 bs6 candidate handoff received (not deployed)

Plugin owner reports clean commit0b19bb605cdff619a7f09b34a6fe774e4b43d357,
0.6.4+bs6 combining biosan5 quota behavior and P0. Source and wheel each passed
86 checks according to owner evidence, not rerun here. New
WORKER_SUBMIT_GUARD_FAILED is UNKNOWN/retryable=false; current consumer's two
category allowlist already rejects it. No policy change needed. No new trusted
terminal producer was delivered; end-to-end automatic recovery remains unready.
Coordinator reports test baseline ab8695d after Step7; fresh mounts/active-run
preflight is required before the next remote action, not the old fingerprint.

## 2026-09-23 P0 scope correction: continue the existing plan

User clarified that the Master failure example is a completeness check, not a
new incident/development track. Runtime owner confirmed its current scope is
bs6 integration on biosan5 with full HeavySlotQuota behavior preserved, without
the additional Master audit producer. Earlier audit-next-step notes below are
superseded. No source hooks/launcher/receipt extension will be assumed available.
The unverified terminal-audit consumer draft is preserved in Git stash
3c617cbd86a4b3d27309689ecdfd7fc820f73c57, excluded from the implementation branch.

Continue CR-01 through CR-05 against the delivered, version-bound producer
contract: consumer/control fences, adapters and DAG continuation. Candidate
evidence alone still cannot authorize replacement; incomplete Master/Worker
proof remains manual. No automatic enablement, production change or extra suite.
Actual bs6 delivery and end-to-end recovery acceptance remain outstanding.

## 2026-09-23 P0 Master failure observations

Extended the existing UID probe to retain the Master Job failure reason and all
observed Master Pod main/init/ephemeral termination reasons/codes/signals and
restart/last-termination evidence. BackoffLimitExceeded is recorded as a terminal
symptom, not an automatic-recovery category; no messages/private stderr returned.
BS10610:34 affected checks passed0.06s. No production query/change/deployment.
20260921D is user-reported context only; its actual root cause and persisted
production record were not examined here. The full trusted Master error audit,
final footer and recovery integration remain pending; no seal/permission emitted.

## 2026-09-23 P0 submission inventory joined to workload probe

Added `scripts/cce_recovery_inventory.py`: verifies bound context, producer
checkpoint/hash chain, every submit intent/result, cumulative failure candidate,
and admitted Worker manifest. The composed probe derives all Worker identities
from that snapshot, not a caller-supplied subset. BS10610:26 focused checks passed
in0.08s, including actual WGS/GATK producer fixtures and the probe connection.
No previous suite rerun, service change, BS96, deployment or policy enablement.

This proves snapshot consistency and current workload observations only. Final
Master audit/digest binding and admitted Worker historical outcomes are still
required; a stale valid snapshot or absent Job cannot establish zero rule failures.
Source review found submission exceptions bypass JOB_ERROR and existing logger
omits ERROR; do not build a positive seal from empty rule errors. Next is the
trusted Master audit producer/terminal integration, then dispatch and fences.
CR-01–05 remain incomplete; shared-service window remains reserved for WES UI.

## 2026-09-23 P0 bound workload probe

Added runtime-side read-only Master/Worker probe with exact UID, namespace,
controller-owner and complete container termination checks, including Pods left
after a Job disappears.25 focused synthetic checks passed0.06s on BS10610.
It observes only caller-bound identities, not submission inventory completeness;
it does NOT issue a terminal seal or authorize recovery. No existing runner,
workflow, shared service or automatic policy changed.

Source review confirmed baseline runtime83e7adb's no-active-worker guard is not
sufficient for P0 (no exact Worker UID/residual Pod checks); RUN_FAILED and the
current logger lack a complete classified Master failure summary. Next: trusted
summary plus full submission journal/manifest binding, then terminal writer and
dispatch fencing. Shared service window is held by the WES UI task; no deploy.
Plugin rename f1d3fa58 /0.6.4+bs5 verified metadata-only and recovery source bytes
unchanged; new wheel hash recorded in HANDOFF. Original fixture provenance retained.

## 2026-09-23 actual plugin candidate contract accepted (not end-to-end)

Verified plugin0d606489 clean worktree and candidate wheel SHA256. Original
pipeline=synthetic fixture was not relaxed into the WGS/GATK allowlist; producer
owner regenerated both adapters' fixtures from the same wheel. Four opt-in
consumer checks passed0.08s on BS10610: candidate alone rejects; actual producer
candidate plus an explicitly synthetic terminal matches the draft contract.
Input bytes are hash-pinned. No runtime seal or live recovery acceptance implied.
No plugin-suite rerun, package install, shared deploy or automatic enablement.
Fresh read-only test DB snapshot still had GATK_20260922_112207_23AD29 running
Step1 upload; only own isolated candidate and network-none container were used.
Next: trusted runtime terminal writer and adapter binding/dispatch/callback fences.

## 2026-09-23 P0 internal reservation bridge and WGS manual fence

Implemented current Master-submit/Step3-monitor lineage binding to the existing
reader, evidence validator and reservation budget.22 focused WGS/GATK synthetic
checks passed (1.04s). Added the WGS resume-stage guard against unfinished
automatic recovery; RED reproduced bypass, GREEN8 checks passed (1.17s).
Tests ran only in the BS10610 isolated network-none cached-image candidate.
No shared service, database, live task, BS96 or main/production change.

The proposed trusted binding fields have no adapter writer/caller yet. Producer
source now exists in its independent worktree but no final producer fixture or
terminal-wrapper acceptance was supplied. Automatic recovery remains unwired/off.
Next: actual producer/wrapper binding, reservation dispatch and remaining control/
callback fences; CR-01–05 are not complete. No repeated unchanged helper suites.

## P0 next slice: controlled reader complete, producer integration pending

Added `cce_recovery_reader.py`;26 focused checks passed on BS10610 in the same
network-none read-only synthetic container. Only the new test file ran. No public
route, adapter, auto policy, recovery dispatch or service deploy changed.
Coordinator reports upload gate released; before any future service mutation,
recheck active runs/mounts and coordinate Step7. Test gate release is not approval
to include P1 pause/delete or production work. Plugin owner continues actual
producer implementation; do not claim draft-fixture tests as producer acceptance.

Draft pure `cce_recovery_evidence` validator additionally completed: exact context
binding, candidate digest, complete terminal summary and quiescence required.
BS10610 RED then GREEN62 checks passed0.13s. This is a proposed wrapper contract,
not evidence that today's plugin/Master emits it; no runtime reader or entry wired.

## 2026-09-22 P0 isolated development released; first budget checks passed

User released code development and partial synthetic testing while BS10610's
existing upload completes. Coordinator confirmed separate candidate/no-network
containers only; shared services, jobs, leases, databases and production remain
untouched. Formal deployment and service integration still await its gate.

Implemented internal `cce_recovery_budget.py`: existing AnalysisRun row lock and
RunAction journal, two reservations per frozen attempt, 60/180s waits, immutable
deadline, replay, transaction rollback and stop/control/maintenance checks.
Both frozen policy and initialized budget are mandatory. No public route, policy
initializer or dispatch is wired: this is NOT enabled automatic recovery.
BS10610 isolated RED observed missing module; GREEN: 54 parameterized WGS/GATK
synthetic checks passed in 1.89s. SQLite checks do not prove PostgreSQL concurrent
serialization or live DAG/runtime behavior. CR-01–05 remain incomplete.
Next: bound producer consumer, shared dispatch fences and adapter/DAG integration;
coordinate Step7-owned files before modifying shared paths. See P0 ledger.

## 2026-09-22 P0 implementation prerequisite

The user approved joint plugin/Master/runtime/Airflow implementation, resolving
the external-scope hold. Producer context/failure schema was agreed with the
plugin owner, and attempt-budget tests were prepared locally but not run.
BS10610 deployment and acceptance are paused by the environment coordinator:
the choice between selective production-fix sync and full test-branch deployment
is still pending. No application implementation or passing acceptance is claimed.
See `docs/superpowers/plans/2026-09-22-p0-joint-recovery-progress.md`.
No production, real-task operation or runtime test was performed.

## 2026-09-22 redundant blanket validation removed

The user confirmed that work already developed, tested and published to
production must retain its existing acceptance evidence and must not be put
through a new branch-wide validation cycle merely because its Git history was
synchronized into test. `TEST-VALIDATION-01` is therefore closed as redundant.
The earlier missing-`S1` test is not rerun as a standalone gate; revisit it only
if a newly authorized change touches that path or it blocks that change's focused
acceptance.

The next development priority is now P0 `CCE-RECOVERY-01`: review the bounded
0918A/0919B recovery policy, then implement `CR-01` through `CR-05` with tests
scoped to those new changes. No remote test or runtime action is authorized by
this planning correction.

## 2026-09-22 completed production fixes synchronized into test

The primary test branch now includes production-completed commits `9ff67d3`
(same-batch sampleinfo import and saved Step2 reference restoration) and
`9b381eb` (the corresponding BS96 release record) through an explicit history
merge. These two commits are completed release work, not pending development,
and add no follow-up implementation task. `main` and production remain at
`9b381eb`; test retains its additional test-only history and planning documents.

No runtime environment was changed by this repository sync. The production
release evidence remains in `docs/releases/2026-09-18-sampleinfo-bs96.md`.

## 2026-09-22 prioritized development backlog refresh

The priority audit originally used test tip `e44dc3e`. Current `origin/main` and
`origin/jiucheng/release/production` both point to `9b381eb`; their two later
production-completed commits are now included in test. They must not be counted
as new development or reopened in the backlog.

The current development order is:

1. P0: review and implement the bounded CCE recovery contract (`CR-01`–`CR-05`).
2. P1: implement two-step WGS submission/editable frozen input, then run control
   on top of the reviewed CCE identity/fencing contract.
3. P2/P3: add two-source supplemental QC, then the read-only CNV plot viewer.
4. P4: operator acceptance, combined BS10610 validation, promotion planning and
   non-destructive repository hygiene after the selected scope stabilizes.

This ordering reflects recent operational evidence: 0918A/0919B recovery gaps
affect execution correctness, while the 0919B manual-preparation rollback shows
why submission side effects should move behind final confirmation. The QC change
is supplemental to existing ordinary QC, and CNV viewing is a read-only usability
feature. This planning refresh changes no application code, runtime, database,
remote environment or real task.

## 2026-09-22 CCE recovery design revision only

Follow-up user instruction authorizes submission to the pending-development
test branch. Integration retains remote cd7771b QC/CNV designs and adds only
the four recovery document changes; main/production and runtime stay untouched.
This supersedes the original no-test-merge boundary below, not the no-code gate.

User confirmed inclusion of0918A Worker-creation transport disconnect and0919B
Gatekeeper admission timeout in future automatic checkpoint recovery;0919C
missing FASTQ/input repair remains excluded. The design now proposes two
same-attempt automatic recoveries (60/180s waits), persistent budget/original
deadline, exact failed Master and inactive Worker checks, shared manual/control
fences, UID lineage, automatic downstream progression and truthful shared UI.
The0918A Step4 dispatch timeout retains query-before-replay semantics.

Only the existing connection-recovery spec and CURRENT_STATE/TASKS/HANDOFF
are changed. CR-01–05 are future work; policy details await written review.
No application code, tests, runtime/environment, real task or data changes.
Worktree: `C:/Users/11217/.codex/worktrees/cce-recovery-design-20260922/airflow-demo`;
branch `jiucheng/docs/cce-recovery-design-20260922`, based on local tracking ref
`origin/jiucheng/test/wgs-local-main-sync-20260917=9333160`. This is an isolated
documentation revision, not a primary-test/main/production merge or deployment.
The older repository/deployment observations below remain dated history.

## 2026-09-22 WGS submission simplification proposal

Documentation-only proposal in
`docs/2026-09-22-wgs-two-step-editable-sampleinfo-design.md`: two user steps,
editable per-run sampleinfo before final submit, unchanged native selection,
and narrow automatic-intake release for cancelled uncommitted manual drafts.
Airflow main9b381eb source was inspected. Current native prepare confirmation
was requested from WGS-pipeline thread01a09149-ad9d-7e92-b98a-16d9cae075e2;
its answer confirms native sampleinfo/all refuse existing files, whereas
analysis accepts a valid frozen copy. Native server HEAD ebf1f4b, script last
change9f4f359; actual production runner binding remains unverified. No production
inspection, implementation or tests.
Work branch jiucheng/docs/wgs-submission-design-20260922 is based on test9333160;
the existing0919B operations worktree and its uncommitted records are untouched.


Updated 2026-09-18 after the user authorized a complete Git lineage sync from
current main/production into the primary test branch. Test-only development
remains on the test branch; main and production are now required ancestors.

## Repository role

- Primary test development worktree:
  `D:/pipeline/airflow-demo-worktrees/wgs-local-main-sync-20260917`.
- Primary test development branch:
  `jiucheng/test/wgs-local-main-sync-20260917`.
- Pre-sync test tip: `f0b07c4`. The approved three-fix integration is committed
  as `8f062f9`; repository-state consolidation is `91060d0`.
- This is the only remote branch under `origin/jiucheng/test/*`.

## Branch relationship rule

Current `origin/main` and `origin/jiucheng/release/production` both point to
`9b381eb`. Test now includes that history, including the completed same-batch /
Step2 fix and its production release record. The branch relationship remains:

- current main and production are ancestors of the test branch;
- test may retain additional test-only implementation and evidence;
- test-to-main promotion remains a separate reviewed and authorized action;
- old worktree/patch branches are not merge sources unless separately selected.

The two former main-only commits `9ff67d3` and `9b381eb` are completed work and
must not create new development cards. Calculate divergence from live refs
because planning documentation itself advances test; do not rebase or discard
test commits.
See `docs/TEST_BRANCH_SYNC_HOLD_20260918.md` for the original decision transition.

## Consolidated development designs

The primary test branch owns the current documentation-only development queue.
Its consolidated designs include:

- Run control from `jiucheng/feature/run-control-20260918` commit `1c631b7`:
  controlled CCE pause, same-attempt checkpoint recovery and exact online
  project deletion. See
  `docs/superpowers/specs/2026-09-18-run-control.md` and `RC-01` through `RC-05`.
- WGS two-source QC from `jiucheng/docs/wgs-qc-two-source-20260918` commit
  `53fc860`: required ordinary `QCstat.tsv` plus conditional source-qualified
  `multi.QCstat.tsv` evidence for `F57J`/`UPC` samples. See
  `docs/2026-09-18-wgs-qc-two-source-contract.md` and `QC2-01` through `QC2-03`.
- WGS CNV plot viewer design: a WGS-only Run Detail tab lists selected sample
  IDs and streams one native bound `03_CNV/<sample_id>.CNV_genome.png` at a
  time. It is not implemented; no generic artifact reader, image conversion,
  workflow/QC change, test run or deployment is authorized. See
  `docs/2026-09-18-wgs-cnv-plot-viewer-design.md` and `CNV-01` through `CNV-03`.
- Bounded CCE recovery for the approved 0918A Worker-create disconnect and
  0919B Gatekeeper timeout causes, explicitly excluding 0919C input repair. See
  `docs/superpowers/specs/2026-09-17-wgs-gatk-cce-connection-recovery-design.md`
  and `CR-01` through `CR-05`.
- Two-step WGS submission and revisioned editable frozen sampleinfo, with final
  submit before analysis side effects. See
  `docs/2026-09-22-wgs-two-step-editable-sampleinfo-design.md` and
  `SUBMIT2-01` through `SUBMIT2-04`.

These designs are documented and their implementation has not started; the
revised CCE policy still awaits review. They are proposals, not available APIs
or runtime capabilities. This consolidation did
not authorize code, schema, application tests, remote validation, deployment or
real task/data operations. Existing `CCE-RECOVERY-01` remains a separate but
prerequisite-aligned implementation track; run control must reuse its execution
versus monitoring-state contract instead of creating a competing path.

## Test environment and readiness

The target is BS10610/server10610 test. Runtime roots, gates and release
fingerprints remain governed by
`docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md`. Selective-sync validation used an
isolated candidate under the BS10610 control root; no service was deployed or
restarted, no analysis was submitted and no execution gate changed.

The branch contains recorded Local/SGE integration, native execution views,
CCE log-package download, native labels, GATK phase projection and worker-child
timing work. It is not declared fully tested or ready for main. Remaining work
includes reconciling the archived open checklist against current code/evidence,
the revised CCE recovery implementation, two-step submission, run control,
two-source QC, CNV viewing, operator-facing visual acceptance and one final
combined BS10610 acceptance after the branch scope stabilizes.

## Repository hygiene

The user reprioritized repository cleanup before the validation matrix. The
2026-09-18 safe pass removed ten worktrees and fifteen local branches. Unique
branches or state-only dirty documents were bundle/patch-preserved before their
worktrees were removed.
Six nonregistered legacy directories and nineteen loose packages were moved to
`D:/pipeline/task-artifacts/airflow-repo-hygiene-20260918` rather than deleted.

Eight dirty worktrees remain registered and protected, including the primary
test worktree. Their content must be triaged before any further removal. See
`docs/REPOSITORY_HYGIENE_20260918.md`.

## Open work

`TASKS.md` is the authoritative compact queue. Continue the remaining dirty-
worktree triage and test validation matrix; begin any documented development
track only after a separate implementation instruction. No production
deployment or live data operation is authorized.

## Historical evidence

The complete pre-consolidation files are preserved with SHA-256 hashes at
`D:/pipeline/task-artifacts/airflow-test-branch-state-20260918`. Git history and
the existing release/design documents remain evidence; they are not reusable
runtime authorization or proof that every test is complete.
