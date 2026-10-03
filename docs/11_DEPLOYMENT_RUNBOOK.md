# Deployment runbook

## 2026-10-03 scoped split-root/producer deployment and downstream completion

The [scoped release](releases/2026-10-03-dtest1-downstream-twofix.md) records
actual installation of native guard64438f44, paired415a45be and policy6c8617a3:
five entries closed at11:12:10Z, three files switched under their original owners,
pinned loading passed11:13:02Z, and original entries reopened11:13:16Z. Native
af05, bootstrapb928 and the immutable registrations were retained; no service
restart was part of this window. The affected combo did not reach full GREEN;
its evidence and the human instruction stopping further tests remain explicit.

The single normal same-attempt observer then completed Step3 and naturally
continued Step4–6. The release records final real receipts, PASS native download
and materialization markers, published results, and consistent Airflow/public
success. This is an existing deployment/completion record, not permission to
repeat a Resume, rebuild a runtime or recreate automatic monitoring. Step7 was
skipped. A future source rollback requires the same quiet closed-entry window
and the exact saved guard e993 / paired3fc / policya64 combination; preserve all
successful generations, frozen inputs and old/new evidence.

## 2026-10-02 paired control-node mode

Production uses the existing runner aliases as a pair: default200 means
`WGS_RUNNER_200_ALIAS=GATK_RUNNER_200_ALIAS=wgs-node200`; temporary96 means both
are `wgs-cce-node96`. Keep each pipeline's original restricted command and accepted
runtime/profile checks.97 is not a fallback. Prepare both actual worker/scheduler
Compose configurations together, verify the exact env-only delta, and apply only
under the existing no-active-TI/empty-worker/native-continuity boundary. Compose
editing or restart alone does not replace container env. Preserve the original
SSH Host mappings; do not repoint wgs-node200 to96.

Current production is the paired temporary96 mode, applied14:15:14Z. Existing
323D3F attempt1 remains on96; node switching does not migrate an active execution.
There was no frontend/progress/core rollback. The target must retain the accepted
pair before future switching; this release did not install/validate current981e
on200. Source/pin/profile installation is a separate scope. Exact current service
IDs, private backups, failed-method records, scheduling pauses, natural handoff
and rollback boundary are in the
[paired-node release record](releases/2026-10-02-common-control-node-bs96.md).

## 2026-10-01 UNIFIED089 actual release and original gates restored

The coordinator-authorized PROD gate completed. Genuine WGS423 registration
and CAS selected `wgs-4.2.3-bafd27c` from `wgs-4.2.2-441d5e7` at 14:52:31Z;
`gate3-prod-catalog-result.json` SHA256 `0856802d...` records the transaction
and catalog-after SHA256 `35c53a2e...`. Six PROD gateway services passed the
minimum installed check: 60 exact mounts, 18 Airflow imports/errors0, loaded
gates, four external HTTP 200 checks. Receipt SHA256 prefixes: gateway apply
`cf052e66`, acceptance `bef51b0c`, full mount `c9d26e88`, HTTP `7b80cb64`.
Historical WGS/GATK Rules GETs returned 200 and existing rows; they did not
replay a new089 producer or create an analysis.

Gate4 restored the original backend env at 14:56:34Z on TEST and 14:57:18Z on
PROD. Final read-only receipts at 15:04:56Z/15:05:16Z are
`gate4-BS10610-final-readback-result.json` SHA256 `d7093fad...` and
`gate4-BS96-final-readback-result.json` SHA256 `18ff3d91...`. WGS/GATK
execution is true on both. TEST scan/auto are false; PROD effective scan is true
and the original watermark literal remains
`2026-09-17T09:34:19.655673+00:00`. PROD env auto is true but the inherited
read-only intake policy's `auto_dispatch_enabled=false` makes **effective auto
false**. Preserve this original business protection. The first PROD restore
checker exited5 by assuming effective auto must equal env auto; retain its
receipt, then use the accepted final read-only policy closure. Do not replay
apply/POST or alter policy to satisfy that checker. Both external gateway
`/api/health` reads were 200; original env/image/mounts and unrelated service
identities remained unchanged. No nginx restart, dist rebuild, new analysis,
canary, UE04/05/06, 17+2 or full test rerun was part of this gate.

Original policy bytes were not independently archived before restoration;
the final read-only mount SHA and unchanged inherited parser establish the
observed state, not a historical byte comparison. Historical WGS422 is
frozen for rollback only; if a marked089 attempt exists, retain the compatible
stack during repair. Exact receipts and limits are in the
[candidate release record](releases/2026-10-01-unified-native089-candidate.md).

## 2026-10-01 PROD selected components; minimum checks in progress (prior Gate3 checkpoint)

The coordinator's complete PROD GO was granted after TEST minimum acceptance.
The initial read-only page-size-200 runs query timed out; the bounded five-run
page refresh subsequently covered all 27 runs, 50 transfers and related DAG/TI
state with nonterminal counts zero (`gate3-prod-activity-v2-result.json`, SHA256
`674720db...`). This clears the recorded activity preflight, not installed
gateway/catalog acceptance.

PROD Heavy entrydc5/core554/original launcher5f2 and its new flock/Python pair
190070/190480 were selected. Two fresh complete payloads and one actual Lease
GET returning25 names per payload passed with held/used/waiting0, limit25,
idle (`gate3-heavy-accept-result.json`, SHA256 `51b87164...`; actual 21-file
index SHA256 `2c3e826c...`). The stop sent TERM once to the old Python only;
flock exited naturally. The finish invoker exited1 in the final new-process
check after entry/core installation and one original-launcher call. The cause
is unproven because fail-moment rows were not recorded. Read-only acceptance
then found the correct pair; no signal, launcher or finish replay followed.

Six reviewed PROD gateway services were selected at 14:46:19–14:46:52Z.
Infra is completing the installed minimum checks. **No PROD catalog POST has
occurred; execution/auto gates remain closed, and `v2.paired` LAST has not been
selected.** Continue only after the exact installed checks and catalog receipt
are recorded. This is an in-progress release, not final production acceptance.
Do not rerun UE04/05/06, 17+2 or the full suite for this checkpoint.

## 2026-10-01 Gate2 TEST accepted; PROD GO granted (prior checkpoint)

Shared nipttest0.8.9 and the four private node envs/five wrappers are now
selected, including PROD WGS/GATK selectors. This is a real production node
configuration change; PROD gateway source/catalog/Heavy remain prior and its
v3 execution/auto admission gates remain closed. TEST has selected six reviewed
gateway services with backend paired-frozen, genuine WGS423 catalog registration
and CAS, and TEST Heavy core554. Its minimum actual imports, loaded gates,
complete mount contract, API/Rules GET, four PVC/PV identities and two fresh
complete Heavy/Lease snapshots passed. Rules GET returned zero historical rows;
there was no real Group replay or new analysis.

Use the [Gate2 receipt and limits](releases/2026-10-01-unified-native089-candidate.md)
for exact installed hashes and rollback. The initial catalog transaction's
final checker confused publisher raw profile SHA with installed canonical SHA
after its POSTs succeeded; the later read-only closure confirmed current423 and
did not repeat POST. The first Heavy read-only checker compared SFS mtime against
node launch wall time and timed out; payload timestamps and independent Lease
GETs passed, while the raw 599/604-second mtime offset remains recorded. These
were checker/invoker issues, without an ad hoc product patch or full test rerun.

The coordinator has granted the complete PROD gate GO. The first read-only
runs request with page size 200 timed out; health/page 1 passed, and Infra is
completing a smaller-page full active-use refresh. Page 1 is insufficient to
establish idleness. Before PROD gateway/catalog/Heavy mutation, finish that
preflight and recheck actual host, current configs, gates and exact rollback.
Preserve the closed gates through bounded PROD acceptance; select `v2.paired`
LAST only after all approved checks. Do not infer a final production release
from shared089 or PROD node selector selection. After a marked089 attempt,
automatic downgrade to old native/backend/DAG is unsafe; retain the compatible
stack with gates closed for repair.

## 2026-10-01 final423/shared089 candidate packet (pre-Gate2 plan)

The following candidate wording records the earlier preparation/freeze phase;
the Gate2 status above supersedes its pending-install observations.

The sole card W423-R1-UNIFIED089 prepares AF80abdfc(parent0afd), native089/1f5/f843,
WGS423/bafd/e481/profile436a and GATK7.6.0/a4f/r5/profile17d2. The422-native089
transition is cancelled. Window CLOSED: no pip, catalog activation, active
wrapper/env change or restart. Follow the
[fixed candidate/rollback record](releases/2026-10-01-unified-native089-candidate.md).

Use only reviewed gateway v2 variants: actual effective `/app/app` and DAG
`common` copies with exact selected deltas, not whole `/app` replacement or v1
new-file binds beneath read-only parents. Per-service images/env/project roots
and rollback are pinned privately. Config --quiet is syntax-only; later authorized
application uses --no-deps --pull never and still requires actual loaded hashes.

Native alone installs shared nipttest/bootstrap. AF pairs common source and four
private consumers; complete TEST producer/client/backend/Group acceptance precedes
PROD new-request selection. Preserve scanner/watermark and restore original gates.
Reuse accepted tests; supplement only approved affected pairing/import/mount checks.

First-gate GO authorizes fresh preflight then admission-only v3.freeze using old
code/mounts. Preserve actual original watermark literal+00:00; coordinator's +08
display wording was corrected. Report closure before native independent install GO.
Strict sequence: v3.freeze -> native install/pair -> v2.paired-frozen or
paired-management -> TEST acceptance -> PROD catalog CAS -> v2.paired LAST.
After any marked089 attempt, old backend/DAG automatic rollback is invalid as
well as package downgrade; retain089-compatible stack with gates closed for repair.

Heavy standalone wiring uses existing `scripts/heavy_global_snapshot.py` entry
and same-directory `heavy_snapshot_core.py` from `backend/app/heavy_global_snapshot.py`.
Retain launchers/config/evidence/Python/flock/log. Backend-only binds cannot update
the loaded node core. The two private candidate/backups and PID/starttime maps
are in the packet. Approved replacement requires loaded SHA and fresh snapshot;
no new collector framework, Lease clearing or forced slot count.

The following 2026-09-28/29 entries retain historical configuration and rollback
provenance. Later accepted releases above supersede their current-path wording.
Consult the latest release and actual consumer pins before any separately
authorized deployment or rollback; do not replay old repair actions.

## 2026-09-29 downstream-stage presentation rollout

At the 2026-09-29 checkpoint, backend and WGS observer definitions were preserved in
/data/airflow-WGS/downstream-stage-20260929-control. Both consume the corrected
observer; only backend consumes corrected timing. Their rollback.json restores
just these two consumers. All prior overlays, especially Step4 hash correction,
are retained. Never use partial Compose orphan warnings to remove other services.
Check actual dashboard stage and transfer values after health200/nginx reload;
service health alone does not demonstrate corrected Run Tracker presentation.
Native operator57483541 uses the same immutable-selector mechanism described
below, keeping previouse5752ea closure for rollback; no Master rebuild/restart.

## 2026-09-29 bounded Step3/Step4 production repair

At that earlier checkpoint backend composition was publish-hash-20260929-control/compose.json;
only the cce_publish_recovery.py read-only overlay changed (source9c7fc93).
Use its private rollback.json for backend-only rollback, never whole-stack up.
Current paths/hashes are in SERVER_INFO; current symlink is not authoritative.
Preserve all scanner/auth/profile/env/other overlay pins. Existing nginx ACLs
remain unchanged; if backend address changes, nginx-t then graceful reload.

At that checkpoint, the native0.8.8 selected operator was installed in an immutable ctapa-owned code
directory with matched native bootstrap/policy. Atomically switch only the
private platform selector after pin validation, retaining previous closure for
rollback. Do not overwrite files used by running workers or change Master
images, business data permissions, dependencies or analysis inputs. A live
monitor retry exposed a second reader transport issue; first operator rollout
alone does not constitute full A acceptance. See latest HANDOFF before retry.

## 2026-09-28 approved production client subnet

BS96 gateway additionally allows172.20.13.0/24. When deploying the source nginx
template, preserve other approved live rules: the active config also contains
172.20.8.0/23 and172.21.4.221/32. Additive configuration update only; nginx-t and
graceful reload, no Airflow/backend restart. See SERVER_INFO/HANDOFF for backup.

## 2026-09-27 BS10610 auxiliary DAG discovery release

Only Airflow API/scheduler/worker were recreated with three updated read-only
auxiliary DAG file mounts. `bio_wgs.py`, `bio_gatk.py`, backend and all other
services retain their existing pins. Active and rollback private Compose paths,
live checks and source hashes are in
[the exact release note](releases/2026-09-27-dag-discovery-bs10610.md).
Do not use `current` to infer the running source or apply this test release to
BS96. No scanner/dispatch gate or business run changed.

## 2026-09-26 P0 normal-path test delivery (completed)

Source e358aad plus native0.8.7/e2962a2 closes the registration/current-owner
normal-path audit. User explicitly authorized replacing shared WGS4.2.2 r2 and
same-content asset publication; assets20260926.2-wgs422-p0 passed live verification.
This does not authorize production services, real batches or T4 lifecycle actions.

Use actual test service pins, not current: backend/observer consume new backend;
Airflow API/scheduler/worker consume new bio_wgs.py only, preserving unchanged
common/GATK/other DAG mounts. Config-check then explicit --no-deps --pull never
service recreation after active0. Retain exact per-service rollback configuration;
no DB/Redis/scanner/reference/telemetry recreation or network changes.
Test catalog management follows the writable-parent contract below. Keep AUTH,
scan/dispatchfalse and existing execution/recovery gate settings. Node200 uses
the existing ctapa airflow-wgs-test wrapper/key, not the production-hardcoded
repository wrapper. Install the matched gate/helper closure and paired bootstrap
before claiming readiness. Record final mounts/gates/API results in the receipt;
staged source and published Master alone are not a completed platform deployment.

Final installed-source selection, five-service mount check and gateway/API/catalog
readback passed. Authentic receipt220c51d3... first registered WGS4.2.2 and CAS
changed test current from4.2.1. Test managementtrue, AUTHtrue, scan/dispatchfalse;
no business workflow launched. During replacement, Nginx cached old backend IP:
backend was healthy, nginx-t passed, graceful reload restored gateway200. Do not
rebuild the frontend or change network for that stale-upstream condition.

## 2026-09-25 corrected paired entry rollout gate

Native ae90b65 and the paired selector/observation correction have affected
synthetic and source-review acceptance; old dev2 artifacts are not the corrected
build. The original native/Infra owner handles the required new native wheel and
two Master images (both consume the changed standalone assets); unchanged
plugin/Worker images and WGS rules are not rebuilt. No new TTL validation.

Keep Operator installation in nipttest, from its writable node005 view only.
Before installation freeze the final platform/native commits, wheel/image pins,
byte-for-byte package/dist-info rollback and exact test catalog/profile release.
Both fixed `cce-paired-deployment-v1.json` files sit beside their respective code,
point to one test policy and declare per-component approved roots/maintainers and
canonical Python target. Confirm the absolute paths from each actual consumer,
not only NFS inode equality. Shared journals/output roots require the approved
effective group/default ACL; private plugin process spool is separate.

Do not overlay the current release or assume changing its symlink updates a
container mount. Record exact existing-service actions before any test switch;
no new service/Compose, production change, real workflow or automatic recovery
activation is included. Source/artifact/installation/activation remain distinct.

## 2026-09-25 non-root deployment requirement correction

Do not seek root-owned interpreter/script landing points to satisfy the current
P0 selector. That is a code/contract defect, not a deployment prerequisite.
Retain chenjc deployment, ctapa analysis and the user-declared chenjx source owner;
no sudo/chown, new runtime service/container or WGS installation is required.
Policy may live at a fixed deployment-managed non-root location. Follow
[the revised trust contract](13_SECURITY_AND_OPERATIONS.md#p0-non-root-deployment-correction-2026-09-25-user-confirmed).
`P0-NONROOT-ENTRY` must align the two existing readers and pass the small affected
non-root checks before activation. This correction does not itself change the
installed CLI, authorize installation or make the old candidate compatible.

## 2026-09-25 publication / limited TTL acceptance, no activation

Two final Master candidate images are published with verified SWR manifest pins;
the two user-approved no-data success/failure TTL Jobs were auto-reclaimed with
their owner Pods. See [publication/live-gate receipt](releases/2026-09-25-p0-swr-ttl.md).
This updates the earlier pending publication/live-canary status, not the paired
writer/installation/capacity/AOM gates. Test shared nipttest and platform versions
still require a coordinated rollout; no production or automatic policy activation.

## Task6 source accepted — activation gate remains closed (2026-09-25)

New backend-only environment switches WGS_CCE_RECOVERY_ENABLED and
GATK_CCE_RECOVERY_ENABLED both default false. No Compose/environment/production
change accompanies their source addition. Original-deadline enforcement, bounded
Worker wait, planned error classes, Step4 reconciliation, integration/PG and final
source review are accepted in isolated BS10610 evidence. Do not turn them on yet:
final Task6 offline artifacts are now accepted, but installed-writer/storage/live
TTL/capacity/AOM/alert acceptance is still outstanding. Neither source nor offline
artifact acceptance is rollout approval. Exact artifact pins and prior harness
failures: [final candidate record](releases/2026-09-25-p0-final-candidates.md).
Later authorized rollout must pair backend and DAG versions and the already
required native/plugin/writer registration gates. Enabling later affects new
runs only; never edit old params_json or freeze fresh quotas for failed history.
Task5 wheels/images are unchanged and do not contain Task6 additions. Their
successor wheels/Master images belong to the corresponding repository agents,
not the coordinator. After documentation checkpointcbb74e7, the user requested
items2/3: corresponding owners now handle isolated candidates and read-only
operational preflight. No install, service/Compose change or cloud mutation is
authorized by this handoff. Permission/environment failures must be
reported before proceeding, not worked around. See the
[current owner handoff](superpowers/plans/2026-09-22-p0-joint-recovery-progress.md).

User-confirmed test installation boundary: Operator tests use the existing
`/sg2/33.chenjiucheng/software/miniforge3/envs/nipttest` contract, never install
into the host WGS environment/repository. Master/executor dependencies are a
separate image layer, not a reason to upgrade nipttest. The original Task5 build
used cached-image Python and read-only nipttest build dependencies; do not
compare host WGS package versions as though they were that build environment.

## P0 paired runtime rollout remains closed (source accepted, 2026-09-25)

Do not install writers-v2.json based only on source acceptance. Native cloud
identity, restricted entry selection, per-run trusted registration, selected-view
normal receipts and final lifecycle release have passed isolated acceptance;
actual installed writer and storage identity coverage is not established by it.
Later authorized paired rollout must install the runtime and
sibling guard together, pin scripts/cce_paired_runtime.py, use the approved
deployment-maintained Python (not necessarily root-owned) and exact namespace/PVC/PV
identities, and cover every CLI/platform writer.
Invalid activation fails closed; removing policy while v2 owners remain is not
a safe rollback. No new SFS host mount is required by the approved design.

## Same-batch / Step2 publication (2026-09-18)

BS96 backend/frontend-nginx use
`/data/airflow-WGS/sampleinfo-9ff67d3-control/compose.json`; `rollback.json`
restores their exact prior `ui-4f4d45a` pins. Reference-worker and all other
services remain on their own existing compositions. Only target
backend/frontend-nginx with `--no-deps --pull never`, validate configuration
first, and reload nginx afterward. Do not repoint global `current` or deploy
unrelated runtime scripts from this tree. See
[publication and acceptance](releases/2026-09-18-sampleinfo-bs96.md).

## BS10610 native root preservation (2026-09-17)

User-approved native registration root /sg2/33.chenjiucheng/wgs_test/WGS_Clinical
must be retained in WGS_ONPREM_PROJECT_ROOTS by future test backend deployments.
Read current live container config and latest code mounts; do not replay an old
main-sync composition that omits this entry. Native source/view updates need only
backend/frontend recreation, never restart Local/SGE controllers or Airflow workers.
Preserve the user-deployed GATK workflow_phases.py r2/r3 fix when layering this
test branch on the current test deployment. No promotion to main/BS96 is implied.


## BS10610 main + Local/SGE refresh (2026-09-17)

Test application282dfb0 includes mainc6ac6ce plus accepted native integration.
Use candidates/onprem-main-282dfb0-control/compose.json, explicit backend,
wgs-run-observer, frontend-nginx; --no-deps --pull never. Rollback.json restores
those3 services only, followed by nginx reload. No DB migration, DAG update or
production gate/root copy. Receipt: releases/2026-09-17-onprem-main-sync-bs10610.md.
## UI/Phase/ledger publication (2026-09-18)

BS96 backend/frontend-nginx/sample-reference-worker now use
ui-4f4d45a-control/compose.json; rollback.json contains their exact prior pins.
Worker has ONLY the tested ledger reader delta on its independent baseline.
Other services must retain their existing compositions. Run config --quiet,
then up -d --no-deps --pull never only for the affected services and gracefully
reload nginx after backend address changes. No global current redeployment.
See [publication and acceptance](releases/2026-09-18-ui-phase-ledger-bs96.md).

## Automatic intake activation (2026-09-17)

Production WGS scan period is now600 seconds and automatic analysis is enabled
for the Clinical Samplelist source. See [activation receipt and rollback](releases/2026-09-17-auto-intake-bs96.md).
Do not restore older auto-disabled or1800-second settings from historical
release descriptions. Preserve current per-service sources and recorded gates.
## Complete QC count publication (2026-09-17)

BS96 backend/frontend now use qc-all-counts-4e9196d-control/compose.json;
rollback.json retains the preceding paired QC policy release. Other services
keep their existing compositions. Use only backend/frontend-nginx with --no-deps
--pull never, then nginx reload and real-client API checks. Do not redeploy an
old global current composition. Receipt: releases/2026-09-17-qc-all-counts-bs96.md.

## QC policy and UI publication (2026-09-17)

BS96 backend/frontend now use qc-policy-fcc3fc9-control/compose.json;
rollback.json restores the exact preceding two services. Other services retain
their independent composition. Source mounted at releases/20260917-qc-policy-fcc3fc9/backend,
frontend image airflow-demo/frontend:qc-policy-fcc3fc9. Preserve GATK r2, WGSv2,
scantrue/autofalse and all unrelated settings. Do not deploy QC UI without its
audited backend policy. See releases/2026-09-17-qc-policy-ebf1f4b.md.

## GATK logger settings and proxy verification (2026-09-17)

Latest GATK private effective Compose is gatk-logger924-r2-20260917-control on
both hosts (under candidates on BS10610). It preserves the existing application
source and WGS gates; do not restore an older full Compose merely to change GATK.
After backend recreation, run nginx -t and graceful reload, then check actual
gateway /api/health and an empty-JSON /api/auth/login request (expected422).
HTML or backend-direct health alone will miss nginx caching a retired backend IP.
See [exact settings and rollback](releases/GATK_LOGGER_20260917.md).

## 2026-09-17 WGS sampleinfo/v2 follow-up

Production runs the complete f72a12e backend source, with user-approved
WGS_CONTRACT_V2_ENABLED=true for new WGS tasks. The former false value was legacy
configuration, not evidence that v2 code was absent. Existing tasks retain their
frozen version. See latest HANDOFF and sampleinfo-f72a12e-control private Compose
for exact service restart/rollback scope. Do not disable v2 after new v2 runs
have started without considering their continuation. No native prepare changes.

## 2026-09-17 Clinical release executed

The Git-first checkpoint below is superseded by the approved e9a6644 production
rollout. Use docs/releases/2026-09-17-clinical-roots-bs96.md for exact source,
five-service Compose/rollback, root configuration, data copies and SFS outcomes.
No legacy-root compatibility was added; existing historical frozen request files
were not rewritten. Native prepare defaults and CCE release pins remain intact.

## 2026-09-17 Git-first checkpoint; release not performed

The user requested source synchronization before the remaining production work.
Future complete release must include wgs_release_runtime.py beside the WGS gate,
retain private release runtime/config/profile pins, and preserve existing resume
and test gates. Do not replace the gate with an older live snapshot or add backend
file-overlay mounts. CCE packages/versions are not upgraded by this source sync.
Pending and exact two GATK result copies, Clinical roots, scanner configuration
and verified WGS/GATK SFS cleanup remain pending. No offline/OBS/FASTQ/DB deletion.
Use the latest HANDOFF inventory and refresh live mounts/gates before publishing.

## 2026-09-16 BS10610 enabled test deployment

Native registration/claim/monitor enabled, additive schema0026, bounded synthetic
API/controller acceptance and user browser retest passed. HTTP is explicitly
authorized; no TLS gateway required. Use actual composition/mounts, not unchanged
current symlink, to identify test source. Scanner/auto-dispatch remain false.
See [release and rollback details](releases/2026-09-16-onprem-bs10610.md).
The new DB dump was deleted at user request; rollback preserves schema/data and
restores code composition only. No BS96/main publication was authorized.

## Native views candidate verification (2026-09-16)

Views add no service, environment variable, migration or scheduler. They require
the earlier approved native snapshot/project readable mounts at enablement;
do not widen filesystem permissions or silently use another project directory.
Latest QC cache resides in existing params JSON; keep it and private execution
snapshots on rollback. Production/native feature gates remain unchanged.

BS10610 candidate root candidates/wgs-local-sge-20260915 only: backend3 tests,
frontend3 tests and tsc/Vite build passed using cached backend:t235-232154f and
frontend-test:gatk-recovery-20260914 images, --pull never --network none.
Frontend package-lock matched the cache before testing; no dependency download.
Evidence native-view-backend-check.log and native-view-frontend-check.log under
candidate root. No running container/mount/release/DB was modified. Next bounded
enabled candidate API/browser acceptance needs a separate installation decision;
do not promote to BS96, main or production as a side effect of these checks.

## Native terminal/attachment candidate (2026-09-16)

Source adds fixed-path controller-exit consumption and personal-session monitor
attachment. Keep all native gates off and bio_wgs_native_monitor paused until
joint acceptance and separately approved install. No Compose/live migration.
Helper spawn succeeds independently of monitor attachment; on attachment503 or
lost response use monitor-only repair, never rerun the analysis command. Missing
final or supervisor loss remains unknown. Signal/SGE-error needs remaining-job
verification before new execution; no automatic qdel or override endpoint.
Retain binding/receipts/history on rollback and keep needed existing monitoring
running. Do not revert a running supervisor into replaying its saved launch context.

## Native monitor candidate hold / WGS baseline (2026-09-15)

Keep WGS_ONPREM_MONITOR_ENABLED=false; bio_wgs_native_monitor remains paused and
is not added to deployed mounts. Only isolated BS10610 cached synthetic tests run.
Automatic monitoring attachment and final controller-exit evidence are not ready.
Candidate observation cannot authorize new native analysis after raw result files.
No live migration, actual service update or analysis was performed.

Per user instruction the WGS task uses deployed source34bfcbf with isolated thin
integration commitb07bbc4 on jiucheng/wgs-onprem-deployed-34bfcbf. Newer ba7b272
and integration7115ea6 branches are retained, not deleted or deployed. This pins
the declared deployment baseline supported by completed Job/profile configuration,
not an assertion that all worker files were independently inspected. Native
runtime/sampleinfo/local+sge profiles were verified unchanged against34bfcbf.

## R2-3 one-shot launch candidate hold (2026-09-15)

User confirmed BS10610 backend was deliberately synchronized with main: actual
/app source is releases/20260915-main-359df11/backend, despite current still
pointing to20260912-opt-4d3d24e6. Use inspected mount, not current, for identity.
Only independent candidate tests were resumed; no current service modified.
Keep WGS_ONPREM_LAUNCH_ENABLED=false. Claim API tests are not caller/observer/DAG
acceptance. Never enable a route that consumes permission without an accepted
caller/recovery observation path; unknown launching must not be auto-requeued.

## R2-2 deployment hold (2026-09-15)

New candidate migration0026 adds immutable execution input references; tested on
disposable SQLite only. Future authorized rollout must apply0025 then0026 and
configure WGS_ONPREM_SNAPSHOT_ROOT as backend-private0700 outside project storage.
Do not relax source permissions automatically. Registration remains disabled and
execution receipt explicitly has launch_allowed=false: monitored launcher/DAG,
scope-aware readers and joint acceptance are not delivered. No current mount,
container, scanner, credential or database changed. Rollback disables registration
or restores code without removing binding, input evidence, identities or history.

## R2-1 registry deployment hold (2026-09-15)

Do not deploy current registration candidate without joint acceptance/authorization:
GREEN and disposable SQLite migration0025 checks passed after SSH recovery, not
a live or PostgreSQL migration. Later rollout must validate/apply additive
0025 before starting source with the new AnalysisRun ORM column, even if registration
is disabled. Keep WGS_ONPREM_REGISTRATION_ENABLED=false meanwhile; no changes to
current services, DB, mounts, instance ID, registration roots or credentials.
Use personal session cookie/CSRF in private client config, never distribute the
internal service token; require HTTPS or separately approved secure transport.
See [exact contract](superpowers/specs/2026-09-15-wgs-onprem-registration-contract.md).

## Local/SGE R2 documentation gate (2026-09-15)

Follow [R2 implementation plan](superpowers/plans/2026-09-15-wgs-local-sge-platform-integration.md)
before enabling native monitoring. Prior GREEN instructions below cover only R1
source, not the newly required backend-first registration, editable execution
snapshots or project movement handling. Keep the flag off; do not deploy old
strict-hash launch checks as R2. No deployment or credential/account permissions
changed in this turn. Multi-account and real-node acceptance require separate
authorization; do not store secrets in project scripts or relax directory access.

## Local/SGE source checkpoint (2026-09-15, not deployed)

Keep `WGS_NATIVE_PREPARE_ENABLED=false` (the default). The new source requires
`WGS_CONTRACT_V2_ENABLED=true` before opting new normal catalog submissions into
the frozen native prepare contract. Do not enable yet: targeted GREEN tests,
native target/DAG routing and observer integration are still pending. Existing
runs are not retroactively upgraded by this flag.

The native Local controller reads `WGS_LOCAL_TARGET`, default `node-97`; a future
approved node-96 installation must explicitly configure `node-96`. This is a
binding check, not automatic host selection. Deploy the shared
`scripts/wgs_onprem_runtime.py` alongside both runtime gate modules when the
complete integration is approved; no new service or port is introduced here.

BS10610 source transfer failed twice at the SSH gateway before GREEN verification.
No deployment environment, running service, scanner or dispatch setting changed.
Restore test connectivity and run the focused tests recorded in `HANDOFF.md`
before any commit/activation; do not use BS96 as a testing fallback.
## Latest BS10610 test composition (2026-09-15)

Main359df11 is deployed to all eight running application/DAG/probe/collector
services through `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/
main-359df11-control/compose.json` (join the line; private0600). Actual code
mounts use releases/20260915-main-359df11. Historical current symlink remains
old and is not the active application source. Preserve environment/config/data
mounts, external network, PostgreSQL/Redis and scanfalse/autofalse. Existing
schema0024 is additive and not downgraded during rollback. Use explicit service
names and --no-deps --pull never, never remove-orphans. See
releases/2026-09-15-main-bs10610.md for exact receipt and rollback.json command.

## Latest96 UI composition (2026-09-15)

UI93069eb now supplies backend/observer/frontend through ctapa-private
/data/airflow-WGS/candidates/ui-93069eb-control/compose.json.
Its rollback.json restores only those three services to platform-f69c577.
Airflow API/scheduler/worker still use the preceding f69c577 DAG composition;
do not run generic current or recreate all services to align them.
Use explicit service names with --no-deps --pull never; retain protected services,
environment and data. Health/static/source parity passed,0911A untouched.
See releases/2026-09-15-ui-bs96.md. This supersedes the three app services below,
not the retained DAG/runtime gates or deferred recovery restrictions.

## Current96 application composition (2026-09-15)

Sourcef69c577 is deployed for backend/observer/frontend and bio_wgs only; retained
GATK/common/config and other-service mounts remain pinned. Use ctapa's private
`/data/airflow-WGS/candidates/platform-f69c577-control/compose.json`, not the old
current symlink or a generic mainline Compose. Its rollback.json captures exact
previous six-service images/environment/mounts. Use explicit service names with
`up -d --no-deps --pull never`; never remove orphans. See
releases/2026-09-15-platform-bs96.md. Runtime gates/packages and contractv2 remain
unchanged/disabled; this application rollout does not make old v1 runs compatible
with resume_stage. User explicitly deferred0911A, including recovery operations.

## WGS resume_stage packaging (2026-09-15, not deployed)

Future approved rollout must include backend wgs_resume_service.py, updated
bio_wgs DAG and frontend assets. Install scripts/wgs_resume.py beside the existing
restricted wgs_runtime_gate.py under the same owner/mode/launcher; no original
bundle, native workflow, CCE package or cluster settings are upgraded. Preserve
old gates/releases for rollback and do not restart running executors merely to
change their stage generation. Source0.8.4 compatibility inspection is not live
production acceptance. Validate the actual frozen bundle in a separately approved
production task before executing recovery. No real0911A resume was performed.
Detailed evidence and rollback: releases/2026-09-15-wgs-resume-stage.md.
## CCE 0.8.5 release-management enablement prerequisite (not deployed)

Keep `WGS_RELEASE_MANAGEMENT_ENABLED=false` until a separately authorized
deployment provisions a writable catalog directory and points
`WGS_RELEASE_CATALOG_PATH` at the catalog inside it. Do not chmod or remount the
current read-only `/config`. The same catalog directory must be visible to every
consumer: backend writer plus worker/observer readers. Mount the parent directory,
not the single YAML file, because atomic replacement is not visible through an
old file bind mount. Retain `AUTH_REQUIRED=true` and the existing private internal
service token; never place that token in the receipt or catalog.

Before a future enablement, verify the directory owner/group/mode, sibling lock
creation, atomic replacement visibility from every consumer, schema-3/4 readback,
and keep the feature flag false until those checks pass. Registration accepts a
producer-attested `PASS` receipt; it is not evidence that a node200 wheel was
installed or that a fresh Kubernetes probe ran. Explicit activation changes only
the catalog current pointer and does not enable execution or configuration gates.

An inactive catalog does not make in-place SFS asset replacement safe. Retaining
old releases requires new frozen profile and asset paths, while the existing
active-Master gate remains mandatory. No replace/delete manifest, old-asset
cleanup, package installation, mount change, production activation, or analysis
submission is authorized by this source release. Rollback disables the flag and
restores the prior catalog bytes; retain all release assets and run evidence.

## REL-02 local WGS process timezone (not deployed)

On an explicitly selected96/97 target, the approved local gate initializes
Asia/Shanghai for itself and inherited workers. Its POSIX runtime requires the
host timezone database to provide Asia/Shanghai. Keep system timezone and UTC
receipt/API timestamps unchanged. Do not use timedatectl or change /etc/localtime.

For an authorized direct invocation of original prepare outside the gate, prefix
the existing approved Python command with `TZ=Asia/Shanghai`; retain the exact
original script path and arguments. This is a shell process environment prefix,
not a new prepare argument. Do not generate projects on18 (jump only exceptqsub).
Cloud preparation remains on200; this change neither moves it nor modifies its gate.

User requested no publication: installing this gate on96/97 still requires a
separate rollout and fresh target/identity/active-worker check. No existing worker
needs restarting to change future-launch behavior. Verify a non-workflow clock
probe on the actual selected host before enabling new work; no full prepare or
pending mutation is an acceptance test. Restore the previous gate for rollback.


## Resource response compression (2026-09-15)

Both nginx templates enable gzip only for exact `/api/platform/resources`
responses (JSON, minimum 1024 bytes, level 5, Vary: Accept-Encoding). Auth and
other API routes are unchanged. This does not cache or downsample telemetry.
For an existing gateway, preserve its approved allowlist and apply only this
location block; do not overwrite a live config with a generic template.
Validate `nginx -t` before graceful reload. Frontend assets must be copied before
switching index.html; retain the previous index/assets for rollback. Backend,
collectors, scanner and Airflow need no restart. See the dated resource loading
release note for exact deployment evidence.

## GATK recovery/Step7 candidate (2026-09-14)

Validate the candidate on BS10610 before production. Deploy bio_gatk.py network
polling retries and the independent bio_gatk_maintenance.py to all three Airflow
services. Inspect actual per-file mounts; replacing a host inode alone does not
replace the file already bind-mounted in a running container. Check no executing
Airflow task before a scoped control-plane recreation; retain CCE Masters and
all task/run identities. Existing rescheduled TaskInstances may retain old
max_tries: inspect them and clear only the exact wait task if needed, never
upload/prepare/Master submission just to adopt a polling retry policy.

Backend and observer must consume the same tested registry/reconciliation code.
The observer's GATK overlay sets DEPLOYED_PIPELINES=wgs,gatk explicitly; its
Airflow synchronizer requires DB/Airflow access, not a new GATK filesystem mount.
Install gatk_maintenance_gate.py adjacent to the restricted gatk_runtime_gate.py;
preserve private runtime.env, SSH identity and existing execution gates. Verify
the external forced-command dispatcher accepts the authorized Step7 invocation.

Step7 is an explicit administrator maintenance action, not an ALL_DONE analysis
tail and not a deployment smoke-test deletion. Its approved identity/hashes,
latest Step5/6 receipts, no-live-workload checks and shared maintenance lock must
pass. Unknown runtime status blocks retry; retain local results/OBS/evidence.

For0823A use scripts/gatk_resume.py first without --execute, with freshly read
binding/contract SHA256 and exact failed Master UID. Validate raw Kubernetes
DeleteOptions preconditions against an owned diagnostic Job before execution.
Preserve attempt/workdir/run-id/frozen versions and successful outputs. Never
use Step0, --forceall, arbitrary unlock or an unverified replacement UID.
Record exact runtime and control-plane recovery separately from batch completion.

Rollback restores recorded service source/images and node gate copies only.
Preserve databases, leases, runtime receipts, diagnostic evidence and outputs;
do not roll back a resumed Master by deleting it.

## 2026-09-14 original-file ledger / compact controls

Git promotion does not deploy services. BS96 currently uses backend/source worker
from /data/airflow-WGS/releases/20260914-ledger-c2e491c and frontend controls-20260914.
Use that release/private/compose.json with compose.controls.json for frontend;
the current symlink alone is not the actual service composition. Never remove
orphans. Source registration and identity secret stay server-private, not in Git.
Worker: python -m app.sample_reference_worker; SAMPLE_REFERENCE_ENABLED defaults
false, SAMPLE_REFERENCE_SOURCES_FILE names operator registration, and
SAMPLE_REFERENCE_IDENTITY_SECRET must be stable and private. Only wgs_files is
approved, using registered project_root and optional runtime_root. Polling is
one pass plus60s; no public registration or write endpoint. Preserve scan/dispatch.
See releases/WGS_LEDGER_BS96_20260914.md and UI_CONTROLS_BS96_20260914.md.
Do not restart backend during active GATK waits: outage tolerance/recovery is
deferred. Rollback retains all files, schema and rows. Future formal path reset
requires separate explicit authority.

## GATK terminal transfer recovery (2026-09-14)

After BS10610 targeted backend and DAG tests, compare actual mounted backend
gatk_runtime_service.py/wgs_observer.py and bio_gatk.py against the exact patch.
Check zero executing Airflow tasks; restart only backend to load its GATK
evidence reader, preserving the separate WGS observer release and cloud Masters.
For a prior stuck transfer, call the existing authenticated GATK stage-status
endpoint for its exact attempt/Step1 or Step5. The handler validates latest
receipt identity and repairs/releases idempotently; do not directly update DB
or forcibly clear a lease. Verify successor acquisition and actual upload start.
Rollback copies retained .pre-transfer-terminal-20260914 bytes back to the same
mounted files and reloads backend; retain all receipts, transfer rows and data.

### AF05 scan-only overlay (2026-09-13)

BS96 scanner/backend/frontend use release2121061 with `compose.af05.json`;
BS10610 backend/frontend use the same source with scanner disabled. Existing
current symlinks are not sufficient to recreate these services. Use private
`candidates/af05-scan-20260913/command.json` for the exact Compose file set.
Scanner-only `/af05-config/source.json` fixes discovery to Target_Capture and
does not alter WGS prepare defaults. Keep auto dispatch false. Preserve source
identity path and baseline records on future releases; do not replay old files.
Schema0021 includes inactive0020 prerequisites. Code-only rollback retains the
additive schema/data and disables scan; do not downgrade/drop reference or intake
tables. See [AF05 release ledger](releases/AF05_SCAN_ONLY_20260913.md).

### OPT20260912 retained-gate catalog guard

Keep `WGS_CONFIG_OPTIONS_ENABLED=false` and
`WGS_CONFIG_OPTIONS_RUNTIME_CONTRACT=` in the current candidate deployment.
Compose forwards both to backend, defaulting false/empty. The retained private
node gate lacks the new caller/effective-configuration contract; owner source
drift is not repaired by this release. `WGS_TEST_PROJECT_ENABLED=false` alone
does not guard ordinary catalog overrides.

Only a separately verified paired runtime/owner rollout may declare
`WGS_CONFIG_OPTIONS_RUNTIME_CONTRACT=wgs-submission-options.v1` and enable
`WGS_CONFIG_OPTIONS_ENABLED=true`. Setting the flag alone is insufficient.
This is an explicit operator compatibility declaration, not observed runtime
identity. No node gate, owner, live environment or service change is performed
by the activation-guard patch. Legacy requests without overrides and existing
stored submissions remain usable.

## OPT20260912 test resource producers

Deploy only after current test preflight/review. Do not replace the production
`/home/ctapa/.config/airflow-wgs` launcher or existing SFS Cloud Eye process.
Private test root is `/home/ctapa/.config/airflow-wgs-test` (owner ctapa,0700).
Install script files0700 from the exact reviewed commit:

| Repository file | Private test filename |
| --- | --- |
| scripts/heavy_global_snapshot.py | heavy_global_snapshot.py |
| backend/app/heavy_global_snapshot.py | heavy_snapshot_core.py |
| scripts/start_heavy_slot_collector.sh | start_heavy_slot_collector.sh |
| scripts/collect_bss_resources.py | collect_bss_resources.py |
| backend/app/bss_resource_snapshot.py | bss_resource_snapshot.py |
| scripts/start_bss_resource_collector.sh | start_bss_resource_collector.sh |

Use `config/resource_collectors.test.env.example` as a non-secret variable map.
Export the reviewed variables (`set -a; source <private collector env>; set +a`)
before invoking a launcher; do not overwrite the existing runtime.env.
Required Heavy variables: HEAVY_COLLECTOR_CONFIG_ROOT, WGS_PYTHON,
CCE_OPERATOR_CONFIG, HEAVY_EVIDENCE_ROOT. BSS requires BSS_COLLECTOR_CONFIG_ROOT,
WGS_PYTHON, BSS_EVIDENCE_ROOT. Launchers use flock; no boot service is installed.
Node backend source/collector validation code must match the same commit.

Dedicated BSS credentials are currently **not configured/authorized**. Leave
BSS_READONLY_CREDENTIALS unset; `collect_bss_resources.py --root <test evidence>
--once` publishes not_configured without loading SDK or making a request.
For future separately approved activation, provide an owner-only0600 JSON in
an owner-only0700 directory containing exactly ak, sk, domain_id and
purpose=billing_readonly. Identity requires billing:resourcePackages:view.
Never reuse Cloud Eye regional credentials or copy keys into Git/spool/images.
No endpoint override is supported; HTTPS global bss.myhuaweicloud.com only,
no redirects or environment proxy/netrc forwarding. SDK GlobalCredentials uses
explicit domain and signs only three read-only official routes, never IAM
auto-discovery. The package query covers the official default account scope;
it does not claim enterprise-project aggregation outside that API scope.

Root validation: invoke Heavy `--config <existing private CCE config> --root
<test evidence> --once`; this only queries Leases/Masters and writes telemetry.
Verify actual spool/API field states; do not label enforcement tested.
Start separate launchers only after reviewed install. Preserve SFS producer,
private runtime.env, workloads and scan/dispatchfalse. Backend needs only the
existing read-only evidence mount. Rollback exact collector files/owned process
and application release, retain telemetry/evidence; never reclaim/delete quota.

## OPT20260912 test submission rollout

After fresh BS10610 active-state preflight, deploy matching backend/frontend and
the standalone test node gate. Backend Compose now forwards
`WGS_TEST_PROJECT_ENABLED` (false by default). Test-only activation requires
`PLATFORM_ENVIRONMENT=BS10610-Test` (existing display label; `test` is also
accepted for isolated tests) and `WGS_TEST_PROJECT_ENABLED=true` in backend and
the existing `/home/ctapa/.config/airflow-wgs-test/runtime.env`; retain its test
runtime/request roots and all existing execution gates. Never set these in the
production node gate. Keep scanner/dispatch unchanged.

Review fix requires runtime/root-owned output ancestors and sticky protection
on group-writable parents. The current test WGS_test2770 directory fails closed;
an exact2770→3770 change requires separate user approval and is not performed by
the gate. New target/namespace directories are private0700 with no-follow inode
markers and portable atomic mkdir/flock (compatible with node glibc2.17; no
renameat2 dependency). A mkdir/marker crash gap requires manual audit recovery,
never automatic adoption. Audited prepare/template hashes are verified before
private snapshotting; a changed live configuration needs a reviewed contract.

Backend needs same-path read-only /sg2 and /bi visibility already supplied by
the current test deployment. Do not grant backend write access or silently
change mounts. Node ctapa checks write permission on the requested output's
existing parent; missing/unwritable parents fail explicitly without fallback.
The observer consumes unchanged receipt schemas and needs no new test-mode
environment value or new producer; normal source-version coordination applies.
No Airflow DAG/schema migration is required. Rollback disables the test flag
and restores backend/frontend/test gate; retain drafts, run records and output
for audit. Never rollback by deleting a project or touching formal pending.

## GATK selective promotion, 2026-09-12

Use `docker-compose.gatk.yaml` as an optional overlay on the verified WGS
Compose contract. Configure independent `GATK_RUNTIME_HOST_ROOT`,
`GATK_RUNTIME_NODE200_ROOT`, `GATK_EVIDENCE_HOST_ROOT`, `GATK_RESULT_ROOT`,
`GATK_REPOSITORY_ROOT`, `GATK_OPERATOR_CONFIG` and restricted runner command.
`GATK_SOURCE_POLICY` is restricted by default; this user-approved release sets
unrestricted for explicit valid input projects, never for writable outputs.
`GATK_EXECUTION_ENABLED` remains false until profile, gate, mounts, permissions,
API and DAG import acceptance. GATK inherits global active-run concurrency and
Step2 uses default_pool; no dedicated GATK one-slot pool is required.
Unpause `bio_gatk` at final manual activation. Preserve WGS scan/dispatch.

### GATK concurrency update (2026-09-14)

First run `dags/tests/test_gatk_concurrency.py` in cached BS10610 Airflow using
`/usr/local/bin/python` and fresh processes with global defaults16 and7; run
`test_gatk_success_dependencies.py` too. Do not use the Snakemake venv Python.
Before authorized production switch, verify API-wide running task count is0,
global default, actual DAG mounts, OBS pools both1, and existing Master UID.
Patch only the two concurrency declarations in the actual mounted DAG with
old-content hash guard and retained rollback bytes. Individually bind-mounted
files require preserving inode; do not replace their parent symlink or restart
workers/Masters. Confirm scheduler-parsed DAG reports16 and queued run advances.
Retain OBS pools, durable leases, scan/dispatch settings and all run state.
Rollback restores prior bytes only after another zero-running-task check;
it does not stop existing external workloads or delete any state.

Production may reuse the verified `wgs-node200` SSH host alias with the separate
GATK forced-command path; this avoids editing WGS SSH keys/configuration. The
test environment continues its own `gatk-node200` alias and `airflow-gatk-test`
private directory. No test credentials, results or runtime are promoted.

The normal production clone is `D:/pipeline/airflow-demo-production`.
New development worktrees must branch from the published production main,
inherit research documents and run runtime tests only on BS10610. Original
dirty repositories and historical test refs are retained, not merged wholesale.
See `docs/releases/GATK_PROMOTION_20260912.md` for actual completion and rollback.

For the user-approved 2026-09-11 non-Git exact-source selection/refresh patch, use [release evidence and rollback](selection-refresh-20260911.md). Only backend/observer restarted; frontend updated hashed assets then atomic index; current Worker/scanner/Master must remain untouched. WGS prepare source writable alias verified on BS10610, not node200's read-only /bi mount. No environment variables or public ports added.

Environment selection, host aliases, directory ownership and image-retention
rules are authoritative in `docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md`.
Dated release sections below are historical evidence. They must not override a
fresh `ssh BS10610` or `ssh BS96` preflight.

## T240 rollout boundary

T240 changes backend projections and frontend presentation only. Validate the
backend through the approved cached image and build the frontend with the T234
offline builder. A production rollout may reuse the currently approved backend
image because application source is bind-mounted, then recreate only `backend`
and `frontend-nginx`. Do not recreate the scanner, observer, Airflow,
PostgreSQL, Redis or telemetry services.

The production environment must retain `WGS_AUTO_DISPATCH_ENABLED=false` in
both backend and scanner. The 30-minute discovery scanner remains enabled and
unchanged. This rollout does not submit a run, retry Step7, release SFS data,
rewrite sample/rule history or migrate the database.

The 2026-09-09 production release is
`/data/airflow-WGS/releases/20260909-t240-dashboard-attention-r1`. Its
`PRODUCTION_COMPOSE_BASE` marker records the approved T239 WGS Compose contract
used for the application-only rollout. Do not satisfy the later mainline
`GATK_RUNTIME_HOST_ROOT` interpolation by inventing a dummy mount: GATK runtime
is outside this WGS release and remains disabled. Only backend and
frontend-nginx are recreated for T240.

## Identity and location

- Project: `ngs-huaweicloud`
- Candidate root: `/sg2/50.ctapa/project/HWcloud/ngs-huaweicloud`
- Production account and secrets are external to Git.

## Offline image policy

Production hosts must not contact Docker Hub. Use an approved cached base image or the internal image registry. The backend uses `python:3.11.9-slim-bookworm`; on BS10610 this short name is tagged locally from the already cached equivalent image before building with `--pull=false`. Never run `docker pull` as part of acceptance.

### Frontend builder bootstrap

The approved T234 builder is:

```text
airflow-demo/frontend-builder:node22-lock-35420d5e3ec0
image ID: sha256:25e83a56052d63d900e253c618d342679bb46b66e4566390fa52eb3233702fdf
package-lock SHA256: 35420d5e3ec0f9555738f61e983cb05de30640db82f034d2659f87fd40a324b1
archive SHA256: b5df43b3e26748d08580464832f7688fa36d67c6b2eb12fe681ce57b7dfde1cc
```

It is already loaded on BS10610 and production `.96`. Do not move a complete
frontend image from fengxian for an ordinary source-only release. From a
candidate release on BS10610 run:

```bash
FRONTEND_SOURCE_COMMIT=<git-sha> \
  scripts/build_frontend_offline.sh airflow-demo/frontend:<release-tag>
```

Each host first binds its approved gateway to the same host-local alias:

```bash
docker tag <approved-current-frontend-image> \
  airflow-demo/frontend-runtime:nginx-1.30.3-local-contract

FRONTEND_SOURCE_COMMIT=<git-sha> \
  scripts/build_frontend_offline.sh airflow-demo/frontend:<release-tag>
```

The script tests and builds with `--network none --pull=false`, and writes
`.build/frontend-offline/frontend-image-provenance.json`. A lock mismatch is a
hard stop. Rebuild the base with `scripts/build_frontend_builder_base.sh` on an
approved connected builder only when `package-lock.json`, Node major or the
approved Node base changes. Export one tar plus provenance and SHA256, relay it
through the local workstation, and load it independently on each target.

## Network policy

Compose joins an existing external network named by `NGS_PLATFORM_NETWORK`. This repository does not create the network, assign its subnet, or open additional ports during validation. Use `--network none` for tests that do not need services.

## Candidate validation

1. Synchronize source to the candidate root without secrets, `.git`, or local dependency caches.
2. Run backend tests in a clean image derived from the approved cached Python base.
3. Run DAG import/contract checks.
4. Run frontend tests and production build using the approved cached Node image.
5. Render Compose configuration without starting services.
6. Run an isolated migration upgrade against a disposable database.
7. Record exact commands and results in `HANDOFF.md`.

Production deployment and restart require separate approval. Candidate validation must not connect to the running CCE task path.

## T227 production runtime requirement

The node200 restricted runtime must define:

```text
WGS_RUNTIME_RUN_ROOT=/sg2/50.ctapa/project/HWcloud/airflow-wgs/runtime/runs
```

Deploy the T227 runtime gate and environment without stopping an active
Step1-Step6 worker. Apply migration `20260908_0018` before exposing the Step7
retry UI, then restart only backend/observer/frontend components required by
the release. Do not restart Airflow scheduler/worker or release an active OBS
lease. Restore failed Step7 generations only after exact target, CCE workload,
and lease identity checks; an absent target may be recorded as
`verified_absent`, while partial or ambiguous remnants remain failed.

## T239 lifecycle/QC frontend and Step7 projection rollout

1. Confirm `WGS_AUTO_DISPATCH_ENABLED=false`, no active AnalysisRun, no active transfer lease and no live CCE workload before switching the release.
2. Build the frontend with the approved lock-bound builder using `--network none` and `--pull=false`; run the targeted backend lifecycle/workspace/Step7 tests and logger tests from the candidate source.
3. Recreate only backend and frontend-nginx. Do not recreate the scanner, observer, Airflow scheduler/worker/API, PostgreSQL, Redis or telemetry services.
4. Verify `/api/health`, `/workflows` static markers, workspace `batch_qc_status`, workflow operator and Step7 eligibility for a completed WGS batch.
5. Do not invoke Step7 as part of deployment. The button only exposes an administrator action that still performs the runtime target, live CCE and lock checks.

Rollback by repointing `current` to the preceding physical release and recreating only backend and frontend-nginx. Preserve the auto-analysis pause, databases, run evidence, OBS/SFS data and all Airflow state.

## T241 obsutil checkpoint rollout

1. Keep `WGS_AUTO_DISPATCH_ENABLED=false` and confirm zero active
   AnalysisRuns, transfer leases and WGS CCE workloads before changing the
   node200 operator configuration. Preserve the existing `bio_wgs` pause state;
   the current production DAG remains available for explicit manual runs.
2. Store all synthetic validation material below
   `/sg2/50.ctapa/project/HWcloud/WGS_test/cce-evidence/T241-obsutil-checkpoint-20260909`.
   Do not use another user's test tree or write evidence below `/tmp`.
3. Run the bounded two-file upload/download canary with the private-line
   `obsutil` identity. Require exact aggregate bytes, observed multipart
   checkpoints, checksum verification, privacy-safe JSON and verified removal
   of both synthetic remote objects.
4. Atomically back up and replace node200
   `wgs_obsutil_progress.py` and `wgs_runtime_gate.py`, then run
   `configure_node200_cce.py` so `obs.transfer_adapter=obsutil` and
   `obs.obsutil_bin` selects the wrapper. No cce-pipeline package or
   Step2/Step3/Step4/Step6 implementation changes are required.

## GATK Cloud disabled rollout

1. Keep `GATK_EXECUTION_ENABLED=false` while applying migration 0019 and
   deploying backend, Airflow and frontend.
2. Install the GATK forced command and runtime gate below the restricted SSH
   account's `.config/airflow-gatk` directory. The wrapper resolves
   `runtime.env` and `gatk_runtime_gate.py` relative to its installed path.
   Create `runtime.env` from
   `config/gatk_runtime.node200.env.example`, add no secrets to the repository,
   and set mode 0600.
3. Verify the GATK repository is exactly the approved release and the pinned
   Master image provides the `rule-status` logger contract.
4. Verify the backend has same-path read-only mounts for every approved FASTQ
   root. The initial deployment requires both `/sg2/T7new/result1/OutputFq`
   and `/bi/fastq/T7_Fastq` because existing `a.raw` links use both spellings.
5. Run preview/prepare, CCE dry-run and logger smoke before any real transfer.
6. Execute one controlled SCMC Step1-Step6 smoke. Confirm source FASTQ hashes,
   terminal rule evidence and the materialized result root.
7. Enable manual confirmation only after the smoke passes. Do not enable an
   intake profile; none exists for GATK v1.

To rollback, set the gate false and recreate only affected control-plane
services. Preserve database/evidence/result state for diagnosis.
# 2026-09-14 Heavy producer compatibility

Keep node200 `/home/ctapa/.config/airflow-wgs/heavy_global_snapshot.py` aligned
with `backend/app/heavy_global_snapshot.py`. Backend-only deployment does not
update this standalone producer. Restart only the verified collector under its
existing lock; validate at least two fresh snapshots. Preserve its code backup.
Do not restart Masters or alter quota Leases to repair telemetry.
