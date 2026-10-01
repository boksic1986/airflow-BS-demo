# Handoff

## 2026-10-01 — disabled-options static chain and selected TEST entry

Coordinator selected the ordinary catalog/no-merge path for this round.
Static trace only: SubmitPage omits algo/reference overrides when configuration
options are disabled; the catalog request defaults them to None and skips the
explicit-options attestation branch. Its run specification normalizes reference
to all; stage requests retain algo=None and reference=all. The gate therefore
passes no --algo override and passes --use-reference all. Haplotyper remains
the frozen WGS owner's declared native default; no execution is claimed.

Independent test-projects/source-import preview requires explicit caller and
reference choices and rejects bafd's empty, unaudited option inventory with
HTTP400 WGS_TEST_PROJECT_INVALID / Unsupported release options. Coordinator
explicitly deferred that entry for this release; it is not the selected TEST
path and no cc9 attestation is inherited. No request, API, source/test change
or remote action occurred. Static provenance is retained in ignored
`static-disabled-options-chain.json` beside the pairing draft.

This documentation update reuses product5415 GREEN26 unchanged. Exact phase
registration is approved only after owner final module/rule provenance arrives;
evidence and installation choice remain pending. No A-path retest, B-path
development, package installation, selector/service switch or batch action is
authorized by the selected entry. Document diff-check is the only new check.

## 2026-10-01 — owner profile receipts added to pending TEST pairing

Goal: consume the coordinator's final GATK r5/WGS publication inputs after
the completed R1 card; continue the existing pairing task. Product source
remains `5415b13f6d699deb5809d925f99fd4706520bc47` over retained b3 baseline.

Read only the supplied local `gatk-profile-candidate-receipt.json`; whole-file
SHA matches the coordinator's `3c05056f16f1a50393ec726c2676bc20501dafba8d5ed0d15409ffd1c0d32af0`.
It binds raw profile SHA17d2bb59 to the independent external r5 path and
reports exactly revision r3-to-r5 and Master ee93-to-a4f. The old raw profile
62265 remains the source baseline; separate accepted r4/P0 is not replaced.
WGS/GATK raw file hashes are recorded independently from canonical revision
digests, which remain uncomputed pending the actual consumer contract.
This is receipt consumption, not another remote asset/TEST validation.

Static final-field review: all13 owner catalog fields match receipt.release;
all6 required shared asset fields match. Existing phase registration lacks
`wgs-4.2.3-bafd27c` and `gatk-scmc-v7.6.0@r5`; the exact-release consumers
therefore retain Unknown for those identities. The WGS base has262 mapped
rules and14 module blobs; it is not proof of final423 inventory. Current AF
source has no generic rule-inventory exporter, only the existing pinned
source/rule registry. Reported both gaps and the existing registry paths to
the coordinator before proposing any new source change; final owner module/
inventory evidence is still required. Existing cc9-only config-option audit
also remains closed for bafd. Static report: ignored
`.codex-artifacts/w423-integration-20261001/static-final-pairing-gaps.json`.
Initial rg searches named two nonexistent phase/management module paths;
resolved actual paths via rg --files. These searches performed no mutation.

Updated current state/tasks/this handoff and the current Group audit inventory;
ignored TEST_PAIRING_DRAFT/config-reference-plan now carry actual frozen owner
paths, source/hash provenance and the completed R1 product commit. No executable
or test file changed. Only local JSON/file/hash and document checks ran; the
already-recorded BS10610 GREEN26 remains the R1 evidence without repetition.

Remaining: user installation choice,423/r5 source inventory and exact phase
identity registration after evidence/coordination, exact consumer
canonical/runtime/private-config bindings, actual TEST pairing/acceptance and
rollback. Package/profile/config/selector/service state is still unchanged.
There is no operational rollback for this documentation update; previous
pairing draft/history and source b3/5415 remain retained. New docs commit is
reported separately from the tested product commit.

## 2026-10-01 — W423-R1 version compatibility source handoff

Goal/confirmation: user requested that task alignment be resent because the
coordinator had been busy. `airflow-cloud-demo` replied with the unique current
card `W423-R1-GROUP-FIRST-20261001 / AF-V423-BINDING`: preserve accepted UE04/05/06
source, continue the narrow WGS423/native089/two-Master Group release, and
defer FQ synthesis/async prepare. Worktree remains
`C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo`, branch
`jiucheng/airflow/W423-test-group-release-20261001`, parent
`b3f017477ba4f1814f14291cc36e8c17d5b816e8` (consumer product `0048c36`).

Completed: product delta is exactly three version-set additions of `V4.2.3`
in `scripts/wgs_runtime_gate.py` (repository validation and split-prepare
handoff) and `backend/app/main.py` (required receipt). The two-stage filter,
repository allowlist/approved root, source/profile/config hashes, receipt and
execution/generation identities, and artifact_pending logic are unchanged.
No API/schema or new preparation protocol was introduced. The existing gate
and backend test nodes now share version/stage parameters; the gate negative
uses truly unsupported `V4.2.999`. Valid backend receipts use the real decision
projection, with filesystem imports stubbed only to isolate the receipt fence.
This is synthetic compatibility evidence, not final catalog or native-package
integration. AF catalog candidate remains `wgs-4.2.3-bafd27c`; CCE asset ID
`20261001.1-wgs423` is a separate identity.

Environment: `ssh BS10610`, hostname `server10610`, uid/gid6708:520. Fresh
read-only fingerprint verified control root
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`, current link
`releases/20260912-opt-4d3d24e6`, full current source
`4d3d24e6c0308b682a92e2b09824026b7a888818`, actual backend P0 mount
`releases/20260926-p0-e358aad/backend` and cached backend image
`sha256:8491604ee01d9b3a84d74e7edf233a9d5dd20ddbf14f8a646c25c05f8729efed`.
Airflow worker/scheduler/API mounts retain the accepted P0/discovery mappings;
scanner=false and auto_dispatch=false. New candidate/evidence/scratch roots
were absent before creation, resolved below approved TEST parents and created
as chenjc:bioinfo mode700. The retained b3 archive hash was verified before
extraction; no prior evidence was overwritten.

Commands/results: local scripts `preflight.sh`, `setup.sh`, `run-red.sh`,
`run-green.sh` were piped literally to `ssh BS10610 "tr -d '\r' | bash -s"`.
Only the changed test files were copied to the b3 candidate before RED; only
the two product files were copied after RED. Pytest used the cached image,
uid6708:520, --network none, --read-only, --cpus1/--memory1g, task scratch and
no cache/dependency installation. RED selected the new 423 parameters of the
three existing affected test nodes: exit1, 5failed/2passed/18deselected in3.56s.
Failures were the historical-version rejection, missing --handoff-request for
both stages, and missing-receipt artifact_pending=False for both stages.
GREEN selected those same nodes plus the existing 422/unknown-version node:
exit0, 26passed in8.33s. Raw remote `red.log`/`green.log` were mirrored locally
as `raw-red.log`/`raw-green.log`. Existing dependency deprecation and kernel
swap-limit warnings did not affect the test outcome. Local apply_patch context
checks rejected an initial expected ROOT line and abbreviated doc lines;
the attempts changed no files. Actual context was read before correction.

Evidence root:
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/w423-r1-b3f0174-20261001`;
candidate root: control/candidates/w423-r1-b3f0174-20261001/source. Local
mirror/command scripts: `.codex-artifacts/w423-r1-20261001`. Runtime tests were
not run locally. Full backend/gate, Group/UI, UE/P0/Worker suites and clinical
or CCE canaries were deliberately not repeated under the coordinator's narrow
acceptance instruction. No additional independent review was opened.

Changed files: the two product modules, their existing test modules,
CURRENT_STATE/TASKS/HANDOFF, docs08, and the two current W423 release records.
Local diff-check passed; source hashes match the files mounted for GREEN.
No running service, database, profile, package, runtime workdir or clinical
batch changed. Artifacts remain untracked and retained.

Subsequent owner input: coordinator and WGS owner supplied the final WGS
publication receipt. Its local `cce-release-receipt.json` was read;
assets.status=PASS/state_verified=true, source=bafd27ce5f38e736aae516d5c00247e449872479,
raw profile436a6608/pipelinecf2b6bdf/resource7cd067fb, AF and CCE IDs separate.
Receipt canonical SHA is16f131a4ed501bd3c2f7747e3532f34bd84b18d024d39f90525b55693282893f;
whole JSON file SHA is006b405fcee225baeb5d7150e3d9a74199b95f6abe69dede694d01fd0676eef3.
This receipt is owner-reviewed publication evidence, not a new AF runtime
check. No release registration or service switch was inferred from it.

Remaining: user installation choice; final GATK profile and423 rule inventory;
canonical profile revision and runtime pins; exact catalog/private prepare
config/console/import/bootstrap/policy pairing; deployed TEST acceptance and
verified rollback. This patch does not register the 423 repository or bypass
missing final pins. Source rollback is a revert of this three-set delta on the
candidate branch; there is no deployment from this task to roll back. Existing
deployment bytes/mounts must be captured and verified before any later switch.

## 2026-10-01 — W423 Group source and bounded native impact handoff

Goal: latest human requested the already merged WGS4.2.3/native089/two-Master
TEST release and Group member states. Prepare/FQ synthesis and broader W423
QC/delivery work are deferred. Coordinator reconfirmed this scope after the
user requested that task confirmation be resent. Original product/deployment
owners remain exclusive; this agent stops before installation/switch gates.

Completed source: branch `jiucheng/airflow/W423-test-group-release-20261001`,
base827dc56004ddf7857644499c85835ded8ae93a85. Added Group column and explicit
waiting-for-member-start text to the existing Rules table; no inventory rows,
new state system, backend schema or event protocol. New frontend case and two
synthetic WGS/GATK persistence/API cases cover actual member evidence. Sole
earlier prepare test preserved on deferred branch08e4cbc, not run/uploaded.
Changed files: frontend RunWorkflowTab/component test, new backend
test_group_rule_release.py, docs06, current state/tasks/handoff/server record,
joint-release scope banner and the new Group consumer audit release record.

Verification: BS10610 server10610/6708:520, actual P0 backend image8491604;
isolated, network-disabled tests reused cached dependencies. Group case actual
RED missing column then GREEN1; API2 passed; affected UI file9 passed; tsc
noEmit exit0; application/browser harness Vite builds passed. Browser checked
WGS/GATK waiting/running/terminal with two actual rows, independent timestamp/
status/failure and zero console errors. This is synthetic ingest/API/component
evidence. Accepted producer reports reused; complete real Snakemake JSONL was
not available and downloaded canary event files were Kubernetes EventLists.
Do not label this real producer-to-deployed-UI acceptance. No UE/P0/Worker
suite or CCE canary rerun. Temporary browser harness/tunnel stopped afterward.

Actual native impact: node200=t640/ctapa6801:520. Production WGS declared
private088 import/console and selected private088-step3 runtime/guard are
independent of changed shared assets, although paired interpreter is nipttest.
Production GATK frozen runtime/guard remain copied, but actual frozen
cce_delivery.py:24 prioritizes shared cce_pipeline.shared_permissions, importing
changed __init__ metadata on a later process. Permissions itself is unchanged;
failure is not inferred. Its latest prepare instead uses separate WGSenv088
console/source095f1e93. TEST WGS paired runtime/guard/console and GATK prepare
are shared consumers. Old TEST writer hashes and WGS catalog/profile digest
already drift, so restoring those bytes is not asserted a working rollback.

Commands/errors: remote pytest2, vitest affected-file9, tsc noEmit and vite
builds above; raw logs under `.codex-artifacts/w423-integration-20261001`
and approved remote WGS_test/cce-evidence/w423-platform-827dc56-20261001.
Harness-only failures (environment/cache path/shell positional/index mount,
SQLite UTC assertion, remote Python3.6 encoding/subprocess API and first
PowerShell-interpolated temporary-server stop) were corrected from diagnosed
causes. First stop did not reach Docker remotely; literal stdin Bash stopped
only the named task harness. Details, exact paths/SHAs and results are in
[W423 Group audit](docs/releases/2026-10-01-w423-group-test-consumer-audit.md).

Remaining gates: user chooses shared installation vs proposed TEST private
complete089 prefix; coordinator review; WGS owner's new profiles/resources and
release/rule inventory; final package/import/console/bootstrap/policy/catalog
hash pairing and refresh of active-use/rollback. Native uniquely installs;
Airflow uniquely pairs TEST afterward. Final native source1f5/wheelf843 and
both pushed Master digests are fixed. No pip, production migration, TEST gate/
service switch, old profile rewrite, batch resume/delete or BS96 action here.
Rollback proposal: capture exact TEST configuration bytes/mounts, restore only
those selectors after a private installation, preserve shared088 and all
artifacts, then verify pairing. Installation and rollback are not yet executed.

Final source review: product commit0048c3694164f087b686ad69303538b166244262,
whole range ce497d61..0048c36, one fresh read-only reviewer found no Critical,
Important or actionable Minor issues. It checked exact UE merge parents,
TTL blob preservation, merge-sensitive backend fences and the Group delta,
read tests/browser/import logs and verified all eight evidence manifest hashes.
Coordinator independently accepted this consumer candidate. Neither review
approves package installation, final423 phase/profile/resource pairing or
deployed TEST acceptance. Product source archive `source-0048c36.tar` has
SHA-256 `71b4dd92ba63d808ffd5d8619197b7d48d39ea4814abb8b9ad60da2592ac30ad`;
local and BS10610 copies match. This final handoff update changes only docs.

## 2026-10-01 W423 Airflow integration source checkpoint

## 2026-09-29 — WGS C Step5 Tracker stage regression candidate

Goal: show WGS C's real Step5 download in Run Tracker and `/progress` after
its original DagRun advanced, without changing transfer execution or measured
progress. The source of the wrong Step4 display is a late Step4 status replay
that overwrites `AnalysisRun.current_stage` and status; `/progress` then trusts
that field even after a later Step5 execution and stage row exist.

Changes: `backend/app/wgs_observer.py` skips only Step4 run-level writes when
the same attempt has a Step5/6 execution registered after the current Step4
generation; it still projects the Step4 receipt. `backend/app/wgs_timing_service.py`
read-only projects a later registered Step5/6 stage and retains the live BS96
Airflow-current-step override. Row ID order prevents old downstream history
from hiding a newer Step4 recovery generation. Tests cover both orders and
recorded transfer fields. `docs/05_API_CONTRACT.md`, `CURRENT_STATE.md`,
`TASKS.md` and this handoff describe the behavior.

Commands/results: BS10610 identity `server10610`, current control release
`20260912-opt-4d3d24e6`, backend image `sha256:8491604ee01d...`, `/app`
read-only from `20260926-p0-e358aad/backend`. An isolated candidate under
`candidates/wgs-stage-regression-20260929` used the actual BS96 observer and
timing overlays plus focused synthetic tests. A network-disabled, read-only
container with scratch under task-specific `WGS_test/cce-evidence` passed
`python -m pytest -q -p no:cacheprovider tests/test_wgs_timing_service.py
tests/test_wgs_observer.py::test_step4_receipt_does_not_regress_newer_downstream_execution
tests/test_wgs_shared_transfer_progress.py --tb=short`: 45 passed in 3.27 s.
First focused run exited 1 only because the synthetic fixture expected null
speed while the TransferJob model stores zero by default; expectation was
corrected to the stored value, and the rerun passed 26 tests. `git diff --check`
passed. No BS96 database, service, DagRun or transfer was changed here.

Production release boundary: only the exact `wgs_timing_service.py` and
`wgs_observer.py` candidate overlays are intended. The observer module is
mounted by both backend and WGS run observer containers; both need the updated
overlay for the prevention half of the fix. The current BS96 overlays are the
rollback bytes. The local branch's separate unreleased GATK observer edits
must not be included in a production overlay. Coordinator must confirm C's
Step5 live status and heartbeat at release time; the projection preserves the
recorded transfer snapshot and does not certify that a stale transfer is live.

## 2026-09-29 — WGS original Step4 begin digest repair candidate

## 2026-09-29 GATK r4 Rules phase source candidate

Goal: classify Rules/phase summaries for the new frozen GATK r4 release.
Read-only BS96 and BS10610 inventory confirmed r4 `SCMC_GATK.smk` SHA-256
`ebee79067e17544774ff9607fc714d197189abb49cc5b82af297abbee8b03701`
and Git blob `1cf9fe6f1672e919517bd1392bb2fd4496eab702`; r3 is byte-identical
and all 17 rule names match `PINNED_GATK_PHASES`. The running production phase
module/policy overlay was copied byte-for-byte into source first (commit
`a85cfb6`) to preserve the existing WGS `441d5e7` phase additions. The GATK
change adds only the exact `gatk-scmc-v7.6.0@r4` catalog identity plus focused
test and API-contract wording. Unknown versions/rules still display `Unknown`.

Modified source: `backend/app/workflow_phases.py`,
`backend/app/policies/wgs_phases_cc9bde3.json`,
`backend/tests/test_gatk_phase_revisions.py`, `docs/05_API_CONTRACT.md`,
`CURRENT_STATE.md`, `TASKS.md` and this `HANDOFF.md`. The first two files' WGS
content matches the existing production overlay, not a new GATK behavior.

BS10610 `server10610` preflight confirmed its test control root/current release,
backend mount and disabled intake/auto-dispatch gates. The focused command was
`python -m pytest -q -p no:cacheprovider tests/test_gatk_phase_revisions.py`
inside an isolated backend image with network disabled, read-only source and
no runtime credentials. Before the r4 entry: 2 expected r4 failures, 4 passes;
after: 6 passes. Raw logs:
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/gatk-r4-phases-20260929-e634ca4/red-pytest.log`
and `.../green-pytest.log`. The full backend suite was not run because this
task was explicitly scoped to the minimal phase regression; production review
and live Rules acceptance are pending.

No production deployment, database update, run status edit, upload or CCE action
was performed. Risk: deploying a source module without its existing WGS policy
overlay would regress WGS phase labels; keep both baseline files together.
Rollback of a future approved GATK-only overlay removes the r4 catalog entry;
retain the WGS baseline files and all runtime state.

## 2026-09-29 — WGS C Step5 Tracker stage regression candidate

User's direct coordinator message authorizes the original owners to coordinate
WGS4.2.3 cloud release and Airflow/native upgrade. Scope follows JR01–05 and
W42302–06; current production scope question is pending. Airflow is the sole
platform source/test-entry/deployment owner, WGS owns native business/contracts
and images/profile, native owns package/core/logger runner. No old task reopened.

Fresh exact remote main and jiucheng/release/production both equal ce497d61;
new branch is jiucheng/airflow/W423-integration-20261001 in the retained linked
gatk-prod-compat worktree. Accepted UE3c094fc remains a separate branch parent.
First fetch used nonexistent short ref production, exit128, then corrected to
the exact refs successfully; no production SSH/service operation occurred.

Merge-tree and actual merge found seven expected conflicts. Preserve distinct
state history and API/runtime sections from both sides; main.py keeps the added
UE force-new-generation/runtime artifact sync fence. GATK TTL helper fallback
automerged and remains present. Only explicitly approved W423 plan/spec/release
documents are copied from the coordinator; no dirty product code is imported.
Audited candidate gaps were reported and approved for continuous integration:
a85cfb6 WGS441d mapping,6d11712 GATKr4 mapping,e634ca4 later-stage projection fence.
These will be integrated once, without unrelated parent branch contents.

Current verification is static git/diff/semantic review only. No runtime test,
package install, current/service/policy switch, image build, clinical run or
BS96 access is claimed. Changed files are the UE merge closure and approved
W423 documents; source-only commit is not final integration acceptance.
The plan-owned ledger is .superpowers/sdd/2026-09-30-wgs423-upgrade-integration/progress.md.
It records scope, exact refs, dependencies, commands/failure and rulings.

Next: finish the merge/candidates; freeze the WGS prepare/QC contracts before
new adapter/UI fields, preserve original prebinding ref through final bundle
publication and default closed LIMS. Then BS10610 tests only for integration
and new deltas, followed by a paired candidate/test cutover with exact rollback.
Rollback for this source checkpoint is retaining the previous branch/parents;
no deployed state or protected data has changed.

## 2026-09-29 — GATK TTL downstream node release and original-run Step4 recovery

### Goal and completed scope

Restore WES/GATK `20260927B`, analysis `GATK_20260929_024231_F246CD`
attempt 1, after its successful Master Job disappeared before Step4. Source
is the current-main candidate `5945f26` + `22e5535`; the prior node200 gate
candidate was `4870e2b` + `eb1b8aa`. This release changed only the node200
private GATK gate and adjacent helper. No Master/Worker, workflow, TTL, DAG,
API, DB, backend/worker container or mount changed; no service restarted.

BS10610 `server10610` test evidence: the old gate's two synthetic files
passed 45 cases; the main-integrated TTL subset passed 21. The latest
complete-kubectl-response bytes case produced 2 expected RED failures before
the fix and 5 GREEN cases (17 deselected) afterward. These are test results
reported by the release coordinator, not commands rerun by this docs agent.

### Production identity and bounded continuation

`ssh BS96` targets `server96`, control root `/data/airflow-WGS`; the private
node200 host is `t640` under `ctapa`. The actual server96 control was
`/data/airflow-WGS/downstream-stage-20260929-control/compose.json` with
backend `7ac6a8e6b412` and observer `80f6d137f9ef`; those services and
their mounts were retained. This note does not treat the stale `current`
symlink or an older 2026-09-28 overlay as the effective deployment.
No new server96 release path or service switch was made. The node gate is
`/home/ctapa/.config/airflow-gatk/gatk_runtime_gate.py`; its prior SHA-256
began `b3230de8` and its exact backup is
`/home/ctapa/.config/airflow-gatk/gatk_runtime_gate.py.pre-ttl-downstream-20260929`
(mode 0700). The installed gate SHA-256 is
`cb0903e262b3b80a2b56f43a883906bf95ce0ca4e4c9b463ef63d261a81edd9c`;
the adjacent `gatk_ttl_downstream.py` SHA-256 is
`cfe0a5266342ca5275f46aa62cd9a33a73aea294687f8eef625780a7f51f96a4`.
Both installed files are mode 0700. No directory permission or container
mount change was reported. Scanner and auto-dispatch settings were not touched;
their last documented 2026-09-28 state was enabled/disabled respectively,
not a fresh observation by this docs agent.

The original Master UID is `faecf4ae-562d-42f9-a449-18bf50b90c9c`.
Its frozen manifest has terminal TTL 100 seconds, and the exact Job and Pod
were absent; the actual deletion event was not observed. Both run-label
Job/Pod inventories were empty and the batch lock still belonged to this run.
The old run lacks `publish_deadline` and generic GATK resume capability remains
disabled in production. Airflow 2.9.3 API dry-run on the exact original
DagRun selected 10 Step4-and-downstream task instances; the exact clear
returned HTTP 200 and excluded Step1–3. It did not create a new analysis,
attempt or Master.

The constrained read-only reader accepted native `RUN_COMPLETE` state
`SUCCEEDED` for the original UID, three exit codes 0, matching
`START_CONFIRMED`, present `workflow-completion`, and absent `RUN_FAILED`.
The reader's temporary Job/Pod were absent after use. Step4 generation 2
succeeded at 2026-09-29T14:39:35Z with receipt hash
`c72a693c827bc66a51eb01998acd2cb3e69148b65d71dca08c712482fd4ea5a3`;
`wait_step4_publish` also succeeded. At this checkpoint Step5 awaited the
result transfer slot; Step6 had not started. No final delivery or whole-batch
success is claimed.

### Docs verification, limits and rollback

Updated `CURRENT_STATE.md`, `TASKS.md`, `HANDOFF.md`,
`docs/08_WORKFLOW_RUNTIME_INTEGRATION.md` and
`docs/releases/2026-09-29-gatk-ttl-downstream-bs96.md`.
`git diff --check`, release-note links, task ID and receipt references passed
the documentation check. No runtime suite was repeated for documentation
alone; the BS10610 tests and production runtime checks are recorded above.

Next, inspect exact original DagRun Step5, Step6, final receipt and delivered
artifacts before closing `GATK-TTL-DOWNSTREAM-20260929`. If recovery fails,
retain the original UID/binding and collect stage-specific evidence; do not
rerun Step1–3 or use generic resume. Rollback requires a fresh active-stage
check, restores only the backed-up private node gate and removes only this
new adjacent helper. It does not alter tasks, output, local project data,
SFS, OBS or cloud workloads. The private backup is the available gate
recovery copy; no wider data snapshot is asserted.

## 2026-09-29 — GATK terminal-Master Step4/5 code checkpoint

Goal: repair only WES/GATK `20260927B` Publish results after its successful
Master disappeared; do not rerun analysis. The isolated candidate adds
`scripts/gatk_ttl_downstream.py`, routes unpaired Step4/5 through it after
`cce_paired_runtime.stage_command` has had precedence, and adds focused tests.
No DAG, API, database, TTL, original workload or frozen bundle is changed.

Read-only production evidence: BS96 `server96`, node200 `t640`; original run
`GATK_20260929_024231_F246CD` attempt 1, Master
`cce-master-f0db57be1ca1a60a6628` UID
`faecf4ae-562d-42f9-a449-18bf50b90c9c`. Step3 completed, Step4 failed
with `Step4 requires a successful Master Job`, and Step5/6 did not start.
Master manifest TTL is 100 seconds; exact Job/Pod were absent. A prior
short-lived reader saw native SFS `RUN_COMPLETE.json` state `SUCCEEDED` for
the original UID, but deletion event was not observed. On node200, the real
frozen module under configured `nipttest` Python reports writer inactive and
handoff/binding matching. Its local mirror lacks `RUN_COMPLETE.json`, so
native success has not yet been accepted; the constrained reader must refresh
the mirror before any downstream stage.

BS10610 `server10610` isolated candidate
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/gatk-ttl-downstream-20260929`
used backend image `8491604ee01d`, `--network none`, source mounted read-only.
`python -m pytest -q -p no:cacheprovider
scripts/tests/test_gatk_runtime_gate.py scripts/tests/test_gatk_ttl_downstream.py`
returned 45 passed in 0.68s. Focused RED reproduced six pre-fix safety
gaps. No test service restart, real submission or BS96 mutation occurred.

Current-main integration kept `cce_paired_runtime.stage_command` first and
added the helper only to its unactivated fallback. BS10610 then ran the
TTL-specific subset of those same two test files: 21 passed, 24 deselected
in 0.32s. A broader two-file run on this partial isolated candidate returned
38 passed, 7 failed: five old Step3 fixtures could not resolve the main gate's
`cce_paired_runtime` import from their isolated module-loading path, and two
old prepare/CLI fixtures lacked
the lock-file parent directory required by current main. These are not
claimed as passing and were not changed to expand this scoped repair.

Next: record exact commit, actual production mounts/gate path/hash, active-run
check, rollback copy and service restart list. Follow
`docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md` for production approval.
If released, only the same-attempt Step4 action may resume; then verify
Step4–6 and delivery. Rollback restores the previous node gate and removes
only the new helper; preserve all run data, evidence and cloud resources.

## 2026-09-28 — BS96 WGS Tracker and GATK wait display release recorded

### Goal and result

Record the coordinator's completed, user-authorized limited BS96 deployment of
the reviewed WGS Tracker recovery and GATK transfer-wait projections. This
agent changed documentation only. Production source pin was `a8ae5fe`; actual
runtime kept base `84510df`, prior overlays and the historical `current`
symlink. No new business task, upload, cloud operation, lease change or direct
database edit was performed for the release.

### Environment, selected services and checks

- Coordinator preflight: `ssh BS96` reached `server96`, `chenjc` (`6708:520`).
  New read-only file-overlay release is
  `/data/airflow-WGS/releases/20260928-tracker-wait-a8ae5fe`; private control
  is `/data/airflow-WGS/tracker-wait-a8ae5fe-control`. No directory permission
  mutation was reported. The private `rollback.json` contains the prior full
  backend/observer Compose configurations including environment values; do not
  copy or print it into Git or logs.
- Backend has four reviewed overlays (`gatk_workspace_service.py`,
  `pipeline_registry_service.py`, `diagnostics_service.py`,
  `wgs_observer.py`); observer has only the latter two. Step3 `main.py` was
  already active and was not overwritten. Exact source SHA-256 values are in
  [the release record](docs/releases/2026-09-28-tracker-wait-bs96.md).
  Effective Compose structure, environment and mounts matched the prior
  service apart from these selected read-only overlays; `compose config -q`
  passed.
- Coordinator ran `up --no-deps --pull never backend wgs-run-observer`.
  Backend ID `0d69172001b2 -> 6718484b355c`; observer ID
  `442874a2b576 -> 4d27b967e20d`. Same image ID prefix `0e2d6f0c`, zero
  restarts; every other container ID was retained. Nginx syntax check and
  graceful reload passed; LAN port 12959 `/api/health` returned 200. Scanner
  stayed enabled=true and auto-dispatch=false.
- Only C's existing attempt-1 PREPARE generation-2 success receipt was
  re-ingested through normal stage-status: success, ready=true,
  artifact_pending=false. Tracker C showed running / Uploading FASTQ / waiting
  / null percentage (11 samples); A showed the same waiting display. WES
  `GATK_20260928_105710_C05CE4` showed the same display (43 samples). D still
  showed 100% while running; terminal completion is not claimed.

### Commands, files, limits and next step

This docs agent read `AGENTS.md` instructions, the environment boundary and
prior release format, then used only local Git/document checks. No BS96 command,
runtime test or service operation was run in this docs task. Focused BS10610
evidence was reused: two WGS Tracker and four GATK waiting cases passed.
Changed files: `CURRENT_STATE.md`, `TASKS.md`, `HANDOFF.md`, `SERVER_INFO.md`
and `docs/releases/2026-09-28-tracker-wait-bs96.md`. The integration worktree
was clean at `a8ae5fe` before documentation edits; `git diff --check` and
release-note link/path checks passed. The final docs-only commit and remote
branch heads are verified in this task's Git delivery record.

C's old `pipeline_finished_at=13:10:00.716975Z` persists because C was
already running, outside the failed-to-running cleanup condition. Leave it
untouched pending a separate scoped decision; do not infer completion from
D's 100% progress. A coordinator read-only review probe used unsupported
`limit=100` and got HTTP 422, followed by a local `KeyError`; using the
documented limit 50 succeeded. This was not a production service failure.

Rollback, if separately needed, uses the private control `rollback.json` with
Compose project `airflow-wgs` to recreate only backend and wgs-run-observer,
then gracefully reload nginx; preserve other services and batches. The next
work is a separate decision on C's historical finished timestamp and normal
observation of D's true terminal state. No product-code or database change is
authorized by this handoff.

## 2026-09-28 — WGS/GATK repair source synchronized to main and production

### Goal and completed work

User authorized syncing the already reviewed repair chain to Git `main` and
`jiucheng/release/production`; the coordinator owns BS96 deployment. The source
branch `7e936ea` and both target refs `744cd22` diverged at `84510df` (five
source-only versus 23 target-only commits), so a direct fast-forward from the
source would have dropped deployed fixes. An isolated integration worktree at
`C:/Users/11217/.codex/worktrees/main-prod-sync-20260928/airflow-demo`
started from `origin/main` and cherry-picked the five source commits in order:
`a2d0eef`, `b3e1e40`, `4763e1a`, `ac2fc11`, `7e936ea`. Their integrated
commits are `84ef722`, `b38f748`, `a3e953a`, `0ba2730`, `9f98617`.

The Step3 lock code, WGS recovered Tracker projection and GATK transfer-wait
projection match the reviewed source exactly. Target release catalog, WGS
runtime adapter, WGS DAG, paired runtime and gate code were preserved. Conflict
resolution was additive in `CURRENT_STATE.md`, `TASKS.md`, `HANDOFF.md`,
`docs/05_API_CONTRACT.md` and `docs/08_WORKFLOW_RUNTIME_INTEGRATION.md`; all
target content remained. Remote `main` and production were atomically pushed
without force to code checkpoint `9f98617d70e50f9d62bddb6abff14b95b1377da1`.
Both unattached local branches were fast-forwarded to the same checkpoint.
This separate closing commit updates only `CURRENT_STATE.md`, `TASKS.md` and
`HANDOFF.md`; its final remote SHA is verified after pushing it. The original
source worktree and UE01 worktree remain untouched.

### Verification and limitations

- `git merge-base` confirmed `origin/main` as ancestor of the integration;
  `git rev-list --left-right --count origin/main...9f98617` returned `0 5`.
- `git diff --exit-code 7e936ea 9f98617` across the five backend product
  files and three focused test files was empty. The same comparison against
  target `744cd22` for release catalog, runtime adapter, WGS DAG, paired
  runtime and gate was empty.
- The five affected documentation files had zero deletions relative to target;
  `git diff --check` passed and no conflict markers remained. Both remote refs
  read back as `9f98617` after the atomic push; the integration worktree was
  clean before this closing entry.
- Existing BS10610 focused evidence is reused: Step3 lock two cases and GATK
  wait four cases passed; WGS Tracker projection two cases passed. No runtime
  suite was rerun because source code is byte-identical and the user requested
  minimum testing. No BS96 SSH, deployment, database, lease or running-batch
  operation occurred in this Git task.

### Remaining work and rollback

Coordinator performs the separately authorized BS96 preflight, limited release,
health checks and rollback documentation. Any source rollback should use scoped
reverts after review; never reset shared branches or assume Git changes reverse
a live deployment. The integration adds no database migration. Source worktrees
are retained for review.

## 2026-09-28 — UI-TRANSFER-WAIT-20260928 GATK waiting display candidate

### Goal and completed work

Show the exact unregistered GATK Step1/Step5 acquire-slot wait in WES Run
Tracker and Run Detail as `Uploading FASTQ` / `Downloading GATK results`,
`waiting`, an English current item, and unavailable progress. The existing
frontend therefore displays `Waiting to start` and an empty bar. The database
keeps its Chinese `queued` stage row and `gatk-transfer-slot` source. No DAG,
slot, lease, persisted run status or scheduler behavior changed.

Source branch: `jiucheng/backend/ui-transfer-wait-20260928`, in the existing
isolated worktree; this change is a separate commit for review.

Only the current run/attempt and Step1/Step5 acquire-slot marker is projected.
A registered `PipelineStageExecution` or `TransferJob`, a stage already running
without telemetry, or a terminal run is left alone. Both API paths use the same
read-only helper: `gatk_workspace_service.py` for Run Detail and
`pipeline_registry_service.py` for Run Tracker.

Changed files: `backend/app/gatk_workspace_service.py`,
`backend/app/pipeline_registry_service.py`,
`backend/tests/test_gatk_transfer_wait.py`, `docs/05_API_CONTRACT.md`,
`docs/06_FRONTEND_SPEC.md`, `CURRENT_STATE.md`, `TASKS.md`, and `HANDOFF.md`.

### Verification and environment

Before remote work, BS10610 resolved as `server10610`. Its control `current`
symlink was `releases/20260912-opt-4d3d24e6`; the running backend `/app`
bind was read-only from `releases/20260926-p0-e358aad/backend`. Backend image
was `sha256:8491604ee01d9b3a84d74e7edf233a9d5dd20ddbf14f8a646c25c05f8729efed`.
Observed gates: `PLATFORM_ENVIRONMENT=BS10610-Test`, scan=false,
auto_dispatch=false, execution=true, contract_v2=true. The disposable test
container used `--network none --read-only --tmpfs /tmp` and mounted only
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/ui-transfer-wait-20260928/backend`
read-only. It did not touch running services or a business database.

- Command in the isolated image: `python -m pytest -q -p no:cacheprovider
  tests/test_gatk_transfer_wait.py` with `PYTHONPATH=/candidate/backend`.
  Before product edits: **2 expected failures, 2 passes** in 1.16s (both
  upload/download workspace waits still showed their stored queued labels).
  After product edits: **4 passes** in 2.34s; after strengthening the stored-row
  and terminal Tracker assertions, final rerun **4 passes** in 1.77s. These
  cover both Tracker paths, unchanged stored rows, acquired-but-not-started
  item, missing-telemetry
  running stage, registered execution, and terminal run guards.
- Failed preflight command: a combined `docker inspect --format` invocation;
  exit code 1; stderr `template parsing error: unexpected "\\" in operand`.
  Cause: PowerShell-to-remote quoting of the Go template. Fix: inspect mounts
  and image separately; both succeeded before the test was run. No runtime
  change or retry of a failing workload resulted.
- Local runtime tests were not run because this workstation is for editing/Git
  only. No broader backend suite, frontend test, production SSH, real batch,
  deployment, push, or lease mutation was performed.

### Remaining work and rollback

Coordinator reviews this independent source commit and owns any authorized
release. This is display-only source with no migration: revert the two backend
projection edits to restore the previous API display. The principal risk is a
stale queued marker temporarily displaying as waiting; the current-attempt,
registered-execution/transfer and terminal guards limit that case.

## 2026-09-28 — WGS A/C Tracker recovery projection candidate

### Goal and result

Repair two persisted display artifacts after same-attempt Airflow recovery:
C's `prepare_analysis` execution generation 2 was successful while the older
`run_stage_state` still showed failed; A/C had returned to running through the
normal sync API while `pipeline_finished_at` retained the prior failure time.
This branch changes only the projection paths. The coordinator reports A/C
overall status already restored through the normal API. No production state was
changed by this task, and deployment remains with the coordinator after review.

### Changes

- `backend/app/wgs_observer.py`: PREPARE projection may reopen an old failed
  row only after current contract-v2 execution identity/generation validation
  and a newer generation's accepted/running/success receipt. Existing timestamp
  and terminal transition guards remain in force. Old or foreign generation,
  current failure/cancellation, and success regression do not gain authority.
- `backend/app/diagnostics_service.py`: failed-to-submitted/running WGS
  `sync-airflow` clears the prior `pipeline_finished_at` alongside the existing
  `ended_at` and error reset.
- `backend/tests/test_wgs_tracker_recovery_projection.py`: two synthetic
  regressions for both reported symptoms, including old/foreign and terminal
  replay rejection. Contract notes in `docs/05_API_CONTRACT.md` and
  `docs/08_WORKFLOW_RUNTIME_INTEGRATION.md`; state in `CURRENT_STATE.md` and
  task in `TASKS.md`.

### Verification and environment

BS10610 hostname was `server10610`. The test control root's `current` symlink
resolved to `releases/20260912-opt-4d3d24e6`, while the running backend and
observer `/app` mounts used `releases/20260926-p0-e358aad/backend` read-only.
The backend reported `PLATFORM_ENVIRONMENT=BS10610-Test`, scanning false,
auto-dispatch false, execution true, and contract v2 true. No running service
was restarted or remounted. An isolated source copy under
`candidates/tracker-recovery-20260928/backend` was mounted read-only into a
disposable backend-image container with network disabled.
The local `a2d0eef` baseline `main.py` SHA-256 is `975e1504…`, and its
`wgs_observer.py` SHA-256 is `6526bad1…`, matching both production hashes
reported by the coordinator. No production host was queried by this task.

- Before product edits: `python -m pytest -q -p no:cacheprovider
  tests/test_wgs_tracker_recovery_projection.py` yielded **2 failed** for the
  exact stale stage and finished-time assertions.
- After product edits and an exact already-successful generation-2 replay
  fixture: the same BS10610 command yielded **2 passed in 0.70s**.
- `git diff --check` passed before the final documentation update. Local
  runtime tests were not run, per the user instruction. No broader suite,
  production SSH, cloud operation, database edit, or deployment was run.

The periodic Airflow observer selects WGS statuses only from submitted,
queued, and running in `pipeline_registry_service.py`; a persisted failed row
is therefore skipped by `sync_active_airflow_once`. This patch leaves that
global polling policy unchanged. The coordinator used the normal per-run
`sync-airflow` API to restore A/C overall status.

### Remaining work and rollback

Coordinator review and an authorized limited production deployment remain.
After deployment, the existing authenticated internal `stage-status` GET for
C's `prepare_analysis` can re-ingest its existing bound status file; a missing,
older, or identity-mismatched receipt remains blocked and must be investigated
without direct DB edits. A/C overall status needs no synthetic rewrite.
Rollback restores these two prior source files and restarts only affected
services under the normal release preflight; there is no migration. A residual
failed display remains possible if the bound status file cannot be re-ingested.


## 2026-09-28 — WGS B Step3 stage-registration self-lock

### Goal and result

Remove the PostgreSQL self-lock from contract-v2 stage registration without
resubmitting Step2 or replacing the active WGS Master. The source fix is
committed as `a2d0eef` on
`jiucheng/backend/20260928-step3-registration-lockfix`, based on production
source commit `84510df`. The tested `backend/app/main.py` SHA-256 is
`975e1504441784162420691528ca3afbaa3fb6d0980f8b5b217b1d2e2d582ba5`.

The endpoint now checks the current run/attempt in a short unlocked session,
closes that session, imports the relevant runtime evidence, then obtains the
original `FOR UPDATE` lock and repeats the active-run and remaining gates.
`resume_action_id` retains its original early-return path. Forced Step7 cleanup
also pre-validates the maintenance action and still re-authorizes it under the
locked transaction. No API schema or database migration changed.

### Files

- `backend/app/main.py`
- `backend/tests/test_wgs_only_platform.py`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Verification

- BS10610 (`ssh BS10610`, hostname `server10610`), using the disposable test
  database through a unique temporary schema: targeted regression
  `test_runtime_stage_sync_does_not_self_lock_run_row` passed both parameter
  cases in 1.89 s. Output: `2 passed, 1 warning`; the warning is the existing
  Starlette `anyio.abc.BlockingPortal` deprecation.
- The imported module path was the isolated candidate under
  `/tmp/step3-stage-lockfix-20260928-84510df/backend/app/main.py`; its hash
  matched the worktree source. Each temporary PostgreSQL schema was dropped in
  the test `finally` block. The test used a synthetic service-token override;
  no deployed credential or DSN was printed.
- `git diff --check` passed before commit.
- The full backend suite was not run; the coordinator requested only this
  focused PostgreSQL lock regression. No production or Airflow command was run
  by this implementation task after scope narrowed to the fix. Earlier
  production access was read-only source/log inspection; no production
  mutation was performed here.

Harness corrections before the passing run: the create-run endpoint returns
201; the internal token getter needed an in-test synthetic override; the test
reads `request_hash` from the execution row rather than the endpoint response.
An earlier lock-timeout result came from the old `/app` source because Docker
copied candidate files with unreadable permissions. The final run explicitly
preloaded the verified candidate module at SHA `975e1504…` and passed.

### Runtime coordination and boundaries

BS10610 preflight found the test backend `/app` bind mount read-only. Test source
was staged only under `/tmp/step3-stage-lockfix-20260928-84510df` on the test
host/container; no service was restarted and the actual `/app` mount was not
modified. The test uses the disposable BS10610 backend database in a unique
schema and removes that schema. No workflow dispatch was made.

The coordinator reports that BS96 activated this exact backend file by
rebuilding only the backend; other container IDs were preserved, and LAN/API
health returned 200. The loopback gateway's 403 remained the pre-existing LAN
allowlist behavior and was not changed. For batch `20260927B`, the coordinator reports clearing
only the 14 failed/upstream-failed task instances in the original DagRun
`WGS_20260928_101112_11111E-a1`. Step1/Step2 were excluded, the Master UID was
unchanged, and the DagRun returned to `queued`. Step3 task pickup and subsequent
progress were subsequently confirmed by the coordinator. The production release
and rollback release paths were not included in the status sent to this
task; record those from the coordinator's deployment audit rather than infer
them.

The coordinator confirmed the first bridge observation at 12:57:48Z:
`start_step3_monitor` succeeded, `wait_step3_analysis` was `up_for_reschedule`,
Tracker was `stage3running`, and the same Master was `RUNNING` with
`normal=true`. Monitoring was healthy with no error; the initial rule snapshot
showed 3/223 (1.3%), including `pre_process_Dedup` and
`pre_process_mapping`. The first bridge result took about four minutes after
dispatch but completed. A read-only node200 `/bin/true` probe returned 0 in
0.27s. Step3 monitoring is recovered while the analysis continues to run; the
original Master was left in place.

Read-only review of the repository source found the normal rule-evidence path
uses `kubectl exec` to read cursor-based JSONL chunks, but the bridge's
`subprocess.run` calls do not set a timeout, and the runtime gate also waits for
the bridge without a timeout. The outer Step3 monitor deadline is checked only
after evidence synchronization returns, so it cannot bound a hung bridge
invocation. The documented large-run path optimizes Job-state reads by
projecting compact snapshots and fetching full Job JSON only for nonterminal
Jobs. This source review did not verify the installed node200 bridge hash, so
it does not establish that the repository code is byte-identical to the
production bridge or explain the earlier delay. The successful bridge response
and fast `/bin/true` probe show the monitor and SSH path were responsive at the
reported observation time.

The pre-hotfix backend source was mounted from
`/data/airflow-WGS/releases/20260927-p0-local-84510df/backend` and can be
reconstructed from `84510df` (`main.py` SHA
`ff0f3be345680893893e5d52875f4a7be96a286c4e3a37427694a5595df27bf9`). No
database rollback is needed because there is no schema change.

### Next action and risk

The Step3 monitor has registered and returned live rule progress. Coordinator
continues ordinary observation of the same running analysis. No recovery action
is requested from this backend task. Do not resubmit Step2, restart the Master,
or create a new DagRun for this fix.
If the hotfix must be rolled back, use the normal release rollback procedure
to restore the recorded pre-hotfix backend source; do not mutate the run or
workflow state as part of code rollback.

## 2026-09-30 UE-06 AF/platform isolated installation closeout

**Task and authority.** Current task is `UE-06-TEST-PAIR-20260930`. Coordinator
`airflow-cloud-demo` (`019fa8d1-0d81-7e92-abee-8154dd1cf0a7`) verified the direct
user instruction `检查如果没问题 进行下一步`, confirmed UE05 final pairing,
and authorized original owners' BS10610 isolated installation/loading. After
the user's request to resend, it explicitly reconfirmed this owner's AF/platform
scope, accepted both owners' real loader evidence and instructed final raw-log
and state closeout without another approval or test round. This is the latest
scope; old Step1, UE04 and batch-cleanup checkpoints below are historical.

**Source and ownership.** Worktree is
`C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo`, branch
`jiucheng/airflow/UE06-paired-installation`, starting state commit `a0666e5`.
AF product source is unchanged at
`03bab6c768a2c84537ee4e4a6189072256841b63`. Tracked changes are only
CURRENT_STATE.md, TASKS.md, HANDOFF.md and SERVER_INFO.md; scripts/raw outputs
stay in untracked local artifacts. Native owner alone built source
`7172573223308f1ca89616a5f81d14fec995a659`/wheel0.8.9 and its isolated install.
No native directory was written by this owner.

**Exact candidate and evidence.**

- AF candidate: `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/ue06-platform-03bab6c-20260930`.
- AF product extraction: candidate `source/`; AF bootstrap:
  `source/scripts/cce-paired-deployment-v1.json`; AF policy:
  `policy/cce-paired-writers-v2.json`.
- AF raw evidence: `/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue06-platform-03bab6c-20260930`.
- AF local scripts/logs/manifests: worktree `.codex-artifacts/ue06-platform/`.
- Native root: `/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue06-native-089-20260930`;
  wheel `wheel/cce_pipeline-0.8.9-py3-none-any.whl`, isolated `install/site`.
- Native local raw evidence: `D:/pipeline/WGS-noncoding-model/.codex-artifacts/ue06-native-089-20260930/`.

Fresh preflight verified target absence and canonical parents. New candidate,
evidence, source/scripts, source/dags and policy directories are chenjc:bioinfo
`0755`, files `0644`, without additional write ACL. Extraction used umask022
and `tar --no-same-owner --no-same-permissions`; existing modes were untouched.
The AF `git archive` contains backend/dags/scripts/config/airflow_image from03,
not .env, clinical data or shared artifacts. Twelve source/dependency input
hashes match the archive in `platform-inputs.sha256`. No dependency was installed.

| Pinned input | SHA256 |
| --- | --- |
| AF source archive, 4,546,560 bytes | `4f66ebfeefce33d4f11011a78e4e5b707257a78f186e61c89ccaa8a7f42b7090` |
| AF scripts/cce_paired_runtime.py | `fdc23a33f0d805bd923b6a31d5f70a381164f5b2a523160c621167aaf3d285ab` |
| Native0.8.9 wheel, 153,323 bytes | `bda21dd22fd5fbcea23c40ae5ed9e3fc324b41ff2f56bf31c59022acacd8f6d4` |
| Native installed assets/cce_batch_runtime.py | `c2988621e4552f4240f3f8c2254d99be315ad1633ed51b8f712bf310acced7c7` |
| Native installed assets/cce_writer_guard.py | `e99378dcb1a0f71d3561c6705f4b5fe2f9886bc9e0307b5dc7c1b822de6e6d0f` |
| Native installed cce_pipeline/stage_execution.py | `21b505da319cc752c5694f2b42e4082dd02dc47e3c7ddad895fdb87b08581bd2` |
| Native package_build_id | `b94b66a0d391a662416154d515a1ac495fc2efeeeb334da2b068e97ca2916dd4` |
| Both identical bootstraps | `8e47ad3f5d456a31b617d183f0b5421525e0169f835c145c9f25d30b6d495706` |
| AF schema2 policy | `458472513c5ee071b6f7fa755911df3229c84504581149beb872bb4c3eee674e` |

Native console CLI is `install/site/bin/cce-pipeline`; policy `writers.cli`
pins the installed runtime asset, not that console script. Bootstrap has exactly
five top keys: schema_version, policy, writers, runtime_guard, operator_python.
Maintainers are UID6708/GID520 and each root/path is exact. Approved Python is
`/sg2/33.chenjiucheng/software/miniforge3/envs/nipttest/bin/python`, canonical
`bin/python3.9`, version3.9.23; PyYAML6.0.2 unchanged. Policy namespace is
`ue06-install-only`, `bindings=[]`; no invented journal/PVC/storage setting.
Native owner wrote its bootstrap; AF copied identical bytes to its own source
directory and wrote the sole AF policy. Actual loaders passed without mocks,
constant replacement, environment/request trust overrides or relaxed validation.

**Commands and actual results.** Literal task scripts were copied or piped with
CR stripping through `ssh -o BatchMode=yes -o ConnectionAttempts=1 -o ConnectTimeout=10 BS10610`.
Successful `preflight.sh`, `prepare.sh`, `stage.sh`, `read-native-inputs.sh` and
`pair-policy.sh` returned0; their raw logs retain boundary, creation, archive,
installed input and policy/bootstrap results. Preflight DB transactions were
explicitly read-only and rolled back: business analysis/transfer and Airflow
queued/running DagRun/TaskInstance counts were all0. No DB write occurred.

Actual installation checks used:

```text
bash /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue06-platform-03bab6c-20260930/run-loaders.sh       # exit1; retained first diagnostic
bash /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue06-platform-03bab6c-20260930/run-loaders-v2.sh    # exit0; platform0 + Airflow0
```

The scripts specify PYTHONDONTWRITEBYTECODE=1/PYTHONNOUSERSITE=1, approved
nipttest Python and exact candidate/native PYTHONPATH. The Airflow portion uses
existing pinned image `sha256:58195672af685cfa6551cfc44b37b6218bd2039c44b717163a6e8072f78dfd2b`,
actual Worker identity50000:0, `docker run --rm --pull never --network none --read-only`,
CPU1/memory1g, tmpfs scratch/tmp and only candidate/evidence readonly mounts.
It does not mount SSH keys/live data or initialize a service database. The
kernel swap-limit warning is retained; the command still returned0.

1. Real `paired.selected_runtime()`/`load_runtime()` selected the exact native
   asset, guard, engine, wheel and code-anchored trust configuration above.
2. Actual native `_recovery_native_success` and `_bound_downstream_master`
   origins are the selected asset. Step4/5 guard wrapper origins match the
   selected guard; unwrapped business origins match the selected asset.
   `inspect.unwrap` is used only for provenance, never called or rebound.
3. Actual WGS `_step_command` and GATK `_step` read task-only synthetic
   binding/bundle inputs and constructed pinned canonical-Python/asset
   `step3-status` argv. Those commands were not executed.
4. Actual P0 `downstream_registered` entered the real paired/native loader,
   then refused the task-only synthetic request's missing frozen registration
   before bundle/writer/stage/cloud effects. This proves installed wiring and
   fail-closed entry; it is not a successful business-stage execution.
5. Real candidate imports of common.ssh_transport, common.stage_execution,
   bio_wgs, bio_gatk, cce_worker_wait and cce_publish_dispatch matched03 paths
   and hashes. All four callers reference the same real shared `run_ssh` object.
6. Native owner's independent installed trust/policy/CLI/module checks passed
   and were accepted by the coordinator. Its raw native-loader-pass.json and
   final HANDOFF are retained at the native local/remote paths above.

No pytest/unittest, two-DagBag replay, six-stage replay, cloud Job or actual
batch was run in UE06. Prior UE01-05/14-case/two-DAG evidence was reused.
Stage/cloud calls, run/attempt/SGE/CCE identities:0/N/A for these checks.

**First failure and repair.** First command exit1 at loader-candidate.py:50:
`assert Path(inspect.getsourcefile(function)).resolve() == ASSET` on step4.
Pinned inputs and native downstream functions already matched. Read-only
inspect-wrappers.sh confirmed existing `@protected_stage` wrapper code is in
the trusted guard, while `inspect.unwrap` identifies the asset business function.
Only loader-candidate-v2.py corrected this artifact assumption to assert both
precise pinned origins, retaining identity protection and original failed log.
Synthetic v2 inputs use a new task child; no failed input/output was deleted.
No product, wheel, source, policy/schema or security behavior changed.

| Raw AF evidence | SHA256 |
| --- | --- |
| preflight.log | `cf964f280478081c3f600143d53edfa7de28e5db2c19797b113166b907991d69` |
| stage.log | `092f6e9d1ac7d2df30cc6f896d62339353fe27227c2bd47874474c3ce125edc3` |
| pair-policy.log | `8e2dc5dc59511edb5068aa0c4586ece9b9ea2036d2cba1c6ca621acff47e5ad3` |
| platform-loader.log, first exit1 | `c0384f8433d842e0da72d58877c965f5fcbd7df0969fab501b9c022c05681db6` |
| platform-loader-v2.log, exit0 | `fc2663557ace419167304ddec1427cf5e5003177598450a661ae3cf8f1e4ce49` |
| airflow-loader.log, exit0 | `d4f0aa94ce3ecd2d154ac1ee9fc5744fd1f584d5ac9f2f4f0a38d246eb5fd7d2` |
| loader-v2-inputs.sha256 | `b1d02fd1024e96dbdde26c6d34fde925631d75be77806d01274e07435ea3544e` |
| loader-v2-results.sha256 | `9fa92addf52c6c78b0db1f8b1482e8c56b630359c52d10158c23117420c2a16c` |
| retained-state-comparison.log, local static artifact review | `9e2a190d3fe2671b7fa91a93454fbbd4ee02107e9553a4abfc042523493c8c9b` |

The three original loader logs and remote results manifest were downloaded by
exact filenames; local hashes match all three remote entries. Inputs manifest
pins loader-candidate-v2.py857bbcff, airflow-load.py5ad3ffca and
run-loaders-v2.shbcb2deac. Full hashes, complete commands and the first scripts
remain in the artifact directory; these are evidence, not a request to rerun.
Native raw native-loader-pass.json SHA is
`ffa9626e72166e3ece2ecce5add09c760502e7b85012dc72b9a96f5f2b293b3f`;
native final HANDOFF SHA is
`6b0899e2429db24077c01c72f69c74f97b1619419789ffc931f964702d4181ed`.
Local final-evidence.sha256 indexes 28 exact AF archive/input/script/raw-log
files, SHA `65079407accc11536b6f50d7c6794172561fd74ada059bc56adf3beeffc79b74`.
`git diff --check` returned0, and `git diff 03bab6c --name-only` lists only the
four state documents above. No product source/dependency difference exists.

**Retained state and rollback.** Static comparison of existing AF preflight
and native post-install environment-final.log matched all ten service IDs,
backend/WGS e358aad and GATK/common359df11 mounted sources, current link
`releases/20260912-opt-4d3d24e6`/SOURCE_COMMIT4d3d24e6, scan=false/dispatch=false.
Backend image remains8491604e, Airflow58195672; no service was recreated or
mounted to the candidate. No extra remote environment/test round was added.
Native shared-before/after JSONs are byte-identical SHA
`0d3541a45b15764e55693c946293214d0b37c029664a6db3143bbe9bc7cc1aab`;
shared-runtime-before/after JSONs match SHA
`78059919fedec016265909e2cb380138752808a9940884418aaf647c3652f791`.
They retain shared0.8.8/source417de59, dependency versions and old bootstrap.

Accurate readable rollback wheel is
`/mnt/biodevrwbi/33.chenjiucheng/wgs_test/cce-runtime-info-088-20260927/wheel-417de59/cce_pipeline-0.8.8-py3-none-any.whl`,
SHA `45c99c0c8fb2d39442088d5c5ee7ad6c7be004d2c30495d80d96a4e8a20672c8`,
matching installed shared files. Existing private600 p0 control compose.json
and discovery rollback.json match SHAbe192cef; discovery compose SHA89571729.
They and old mounted source files were only stat/readability/hash checked,
retained in place; private Compose contents were not copied to artifacts/Git.

Current rollback is to keep existing services/shared package/pins and not
select this isolated candidate; no reinstallation is needed. The old shared
bootstrap points to `/home/ctapa/.config/airflow-wgs-test/paired-writers-v2.json`.
`/home/ctapa` is absent on BS10610 (ENOENT, not permission denial). Old paired
policy loading and complete activation rollback have not been verified.
Before any actual switch, the original environment owner must confirm the
active old configuration on the real execution host. No directory was created,
permission widened, pointer fixed or node200/BS96 accessed for this gap.

**Limits and next step.** Candidate bindings are empty; no operational
storage/PVC/business run or production behavior is accepted here. Protected
shared dependencies, production0.8.8, active configs, source/result/FASTQ/sample
and existing evidence remain unchanged. No deletes, push, merge, image rebuild,
deployment or production database action occurred. Coordinator accepted the
technical loading evidence; this final four-document commit completes this
owner's closeout. Any later activation or broader task requires its own scope.

## 2026-09-30 UE-05 AF source delivery accepted; final pairing pending

**Coordinator decision.** The coordinator separately accepted source delivery
`03bab6c768a2c84537ee4e4a6189072256841b63`, closed both Important findings and
confirmed current AF R2/R4/shared-SSH source and its bounded isolated validation.
It checked fourteen unique passing behavior cases, two DagBag file imports,
eighteen evidence-manifest entries and eleven tested inputs against that commit.
The first R4 audit-counting fixture failure is preserved separately; rerunning
only the repaired node was accepted. No further AF source work, review or test
is requested. This final update changes only CURRENT_STATE/TASKS/HANDOFF.

Overall UE05 final pairing awaits the native owner's one narrow static check of
the final AF commit. The coordinator has sent that request and owns closeout;
the AF owner need not wait or add tests/frameworks. W423-01 is unrelated.
UE06, production, merge and deployment remain unauthorized.

**Task and authority.** The user requested another message to `airflow-cloud-demo`.
The coordinator explicitly reconfirmed UE05, the same worktree/branch and these
two corrections, and instructed direct completion of the remaining unique checks.
Do not repeat old RED or accepted UE01-04/F7/final-release tests. No second full
review, UE06, production, merge or deployment is authorized. Checkout remains
`C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo`, branch
`jiucheng/airflow/UE05-native-recovery-consumers`; reviewed source `8617dfa`,
state baseline `a9a326d`. Correction commit is
`03bab6c768a2c84537ee4e4a6189072256841b63` (nine scoped paths).
After that commit, tracked Git state was clean and only `.codex-artifacts/`
was untracked. No rollback of accepted UE04 was performed.

**Corrections.** `bound_compute_terminal` preserves manual Step1/2 entry metadata
and resolves the actual same-action Step3 row, predecessor lineage, current/latest
registration and version-correct frozen requests/native terminal. The durable
compute-only binding records both identities; historical action settlement uses
its own saved Step3 and cannot settle a newer monitor. The existing WGS R2 case
uses real `request_resume_stage(step2_master)` and `register_recovery_stage`
calls: entry generation2 versus Step3 generation3, with wrong-execution refusal.
The existing GATK parameter keeps its Step3-entry case. No stage matrix was added.

`poll_compute_recovery` seals the first exact source-monitor failed permit on the
existing reservation/action/evidence/original caller. Only that current identity
can reuse it past stale `query_unconfirmed`; Worker nonce/quiet validation stays
in the existing wait path. The existing R4 case now performs the real second
backend POST without native snapshot, rejects a superseded monitor, and checks
one action/budget slot, unchanged deadlines and consumed nonce. No new API,
schema model, route, recovery engine or native owner implementation was added.

**Fresh environment and command failures.** The successful hostname preflight
returned `server10610` as chenjc UID6708/GID520. Control root is
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`, current link
`releases/20260912-opt-4d3d24e6`, SOURCE_COMMIT
`4d3d24e6c0308b682a92e2b09824026b7a888818`.
Live source mounts remain backend/WGS DAG `20260926-p0-e358aad`,
GATK/common `20260915-main-359df11`, discovery `20260927-dag-discovery-4fe71cb`.
Actual Compose project is `airflow-wgs`; WGS intake scan and auto dispatch are
false, WGS/GATK execution gates are true. No mount/service/gate was changed.

The first read-only script assumed project `ngs-huaweicloud`, found zero matching
services, and did not run its interpreter probe. Read-only image/label inventory
resolved the project. The corrected UID6708:520 Airflow path probe exited1 with
PermissionError under `/home/airflow/.local/lib/python3.11/site-packages`.
The live Worker is UID50000:GID0, and the same pinned image with that identity
successfully loaded `/usr/local/bin/python`, Airflow2.9.3 (exit0). UID is not0;
no chmod, dependency installation, wheel or image change was needed. Raw scripts
and outputs are in `.codex-artifacts/ue05-review/`.

Images used without pulls:

- backend `sha256:8491604ee01d9b3a84d74e7edf233a9d5dd20ddbf14f8a646c25c05f8729efed`
- Airflow `sha256:58195672af685cfa6551cfc44b37b6218bd2039c44b717163a6e8072f78dfd2b`

Tests used disposable `--network none --read-only --cpus 1 --memory 1g` containers,
source read-only, isolated scratch/tmpfs and only synthetic task evidence.
Backend UID6708:520 writes JUnit/temp data in its task directory. Airflow
UID50000:0 uses tmpfs scratch and no host write mount; outer chenjc redirects
stdout to the task directory. No live DB, runtime root, SSH secret mount or real
batch was used. Kernel swap-limit warnings did not fail any test.

**Unique results and repair.** Remote child is exactly
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue05-native-consumers-20260930-continue/review-20260930`.
Only this previously absent child was created (chenjc:bioinfo755); no deletion or
permission change occurred. Raw artifacts were downloaded to the matching local
`.codex-artifacts/ue05-review/` and result SHA256 matches remote manifest.

1. `python -m pytest backend/tests/test_cce_recovery_poll.py::test_manual_terminal_allows_one_budgeted_recovery backend/tests/test_cce_recovery_cleanup_fence.py::test_unknown_stage_cannot_fail_or_release -q --tb=short -p no:cacheprovider --basetemp=/evidence/backend-green-tmp --junitxml=/evidence/backend-green.xml`
   produced R2 WGS/GATK **2 passed**, R4 **1 failed** in2.49s. R4 failed at the
   no-actions assertion because the earlier genuine failure callback deliberately
   leaves an `airflow_dag_failed` audit action. Recovery-count assertions queried
   all audit/control actions. This was a fixture scope error; the runtime source
   did not change. Assertions now select only `cce_compute_recovery`, preserving
   the callback audit record. The first mixed log/XML and input tar are retained.
2. Rerun only that corrected existing R4 node with analogous flags and
   `--basetemp=/evidence/r4-green-fixture-tmp --junitxml=/evidence/r4-green-fixture.xml`:
   **1 passed** in1.49s, no skipped/error. R2 source and test files were byte-compared
   unchanged between source inputs, so its two cases were not repeated.
3. `/usr/local/bin/python -m unittest discover -s dags/tests -p test_ssh_transport.py -v`:
   **9 passed** in3.118s, no skipped. Fake clock/process fixtures, no real SSH
   invocation or wait. Original reconnect budget and uncertain-dispatch refusal
   are covered once; no old Step1/full-batch suite was run.
4. Same interpreter, `-m unittest discover -s dags/tests -p test_native_callback_observation.py -v`:
   **2 passed** in2.836s, WGS/GATK callback/cleanup/Worker wire assertions.
5. Same interpreter, `/evidence/dagbag-two-files.py`: exactly `bio_wgs.py` and
   `bio_gatk.py` each load their expected DAG, `import_errors={}`, exit0.
   No full-folder scan, metadata initialization or live DAG run was performed.

There are **14 unique passing behavior cases plus two file imports**. The R4
first failure remains reported separately. Existing old RED logs/XML were also
fetched successfully to `.codex-artifacts/ue05-continue/`; earlier unavailable
hash statements below are historical. No RED was rerun after coordinator direction.
SSH's earlier missing-pytest log remains an environment ERROR, not behavioral RED.
No local runtime test, compile or DagBag was used.

**Input and raw result hashes.** Local/remote source inputs are preserved separately:

- first corrected source tar: `9380958b4778932c16758e3ffcf3aa39c8b2b8bec5393675fe8041985f50f271`
- final fixture-corrected tar: `c9170c42bc2adf4f17ee7f3b94c55bdd18520df2001b580aeaaf8c476dc6fa07`
- `backend-green.log`: `1b67c12a032b2b8164af9beaba91e27256f8708ea4f2a0219981ebd295b8a5f3`
- `backend-green.xml`: `8a4403556365fb493afe7d2014aaff3d102518ebd256eaf3502dfa6fcfcc3711`
- `r4-green-fixture.log`: `e01296fc9a700d445ebe6116f42490af268eccb7683a49bb1da4f55d4eebaf57`
- `r4-green-fixture.xml`: `6fe83413d91dbcbee9dad528f5c7c438aff35624fb847fb698ca0691c3982c1a`
- `ssh-green.log`: `1733dcd19d9dcc1ecb0f3eaee3615732bce4aa180a90c83d926c793df36c2a82`
- `callback-green.log`: `84a8b9ae0aacedb4d0e57ffafe65aaaf23b5cd4a84a02bf35af62add3270ad2d`
- `dagbag-green.log`: `bbc847968d48d01874934e29b8afe2224e40c3dddf935034d7773d6b04e1bed7`

`validation-v2-inputs.sha256`, `validation-v2-results.sha256` and
`downloaded-evidence.sha256` record script/input/raw evidence provenance.
The two consumer input hashes are budget
`77c8879fe0c694ef9ff367f36032074b313b7f36c7849ffb0a66553661320ebb`
and poll `dd67aa1f4ab4e0cd71c14cc739841fe7adc37fc83a83077f44b926dc3949ef73`.

**Files and next step.** Exact correction paths: backend app budget/poll,
backend tests recovery poll/cleanup fence, docs05/08, CURRENT_STATE/TASKS/HANDOFF.
`git diff --check` passed. The precise correction commit and raw evidence were
sent to the coordinator for the agreed two-finding/evidence closeout.
No broad second review is needed. Manual Step1 and GATK Step1/2 entries were not
added as runtime matrix cases; the chosen real WGS Step2 path proves the changed
shared consumer boundary. Native internals and installed/production behavior are
not covered. Rollback: leave isolated commits unmerged; deployed state/data are
unchanged. AF source delivery is accepted; only overall UE05 final native/AF
pairing remains with the coordinator. UE06 remains gated.

## 2026-09-30 UE-05 reviewed corrections authorized

The coordinator completed the previously agreed one cross-consumer source
review, independently confirmed two Important findings and instructed the
original owner to correct them under the existing user continuation authority.
Report: coordinator worktree
`docs/reviews/2026-09-30-ue05-source-handoff-review.md`.
Correct only actual Step3 identity selection after a Step1/2 entry and the
durable source-monitor native permit for the independent Worker follow-up.
Use the original R2/R4 test nodes; no new recovery framework or stage matrix.
Current source baseline is `8617dfa`, status record `a9a326d`, same worktree
and UE05 branch. The existing checkpoint is not accepted or deployed.

Fresh external connectivity evidence is the WGS owner's successful BS10610
read-only W42301 document access as `chenjc` on `server10610`. The original
gateway reset remains a historical failure, not permanent network state.
One fresh restricted environment/interpreter preflight is authorized, followed
only by the planned isolated SSH/R2/R4/thin-bridge/two-file-import delta if it
passes. Stop if pre-session SSH fails again; no blind retries or local/production
runtime substitute. Do not install dependencies, alter services, databases,
data, node200, BS96 or UE06. The existing pinned images and task-specific
synthetic evidence root are retained.

## 2026-09-30 UE-05 task reconfirmed; static completion only

**Task confirmation.** The latest user asked airflow-agent to speak with
`airflow-cloud-demo` and confirm its task. The coordinator checked the actual
message timeline: the current task is UE-05; the earlier UE-04 instruction
was historical and had been misread after compaction. Its reply explicitly
keeps UE-04 `a6c31d1`/`7976f25` as the accepted prerequisite and retains the
UE-05 drafts. The scope-check turn performed only read-only Git/document
operations; no source was reverted, no SSH/test/commit occurred in that check.
Current worktree is `C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo`,
branch `jiucheng/airflow/UE05-native-recovery-consumers`, baseline `06bf30a`.

**Current scope.** Finish R2 current action/DagRun/frozen Step3/native terminal
binding, R4 six-stage failure/cleanup protection and existing DAG snapshot
producers. Preserve the independent Worker nonce, Worker quiet proof, original
policy/budget/deadline, genuine business failures and all `.codex-artifacts/`.
Formal spec/plan remain in the coordinator's `wgs422-p0-integration-20260926`
worktree. No new stage, production, real batch, installation, dependency,
service/database mutation, deletion, merge or deployment is authorized.

**Network and validation boundary.** After the earlier successful read-only
BS10610 fingerprint, backend RED logs were produced in
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue05-native-consumers-20260930-continue/`:
`r2-red.log`/`r2-red.xml` report two failures in 1.35 seconds at the missing
action/DagRun binding rejection; `r4-red.log`/`r4-red.xml` report one failure
in 1.19 seconds because the baseline callback rejected the new optional
argument. The latter is interface RED, not behavioral GREEN. `ssh-red.log`
reports missing pytest in the image's default snakemake Python environment;
this is an interpreter environment ERROR, not application RED. Subsequent
explicit-interpreter attempts could not import Airflow. Tests now use existing
standard-library unittest without adding a dependency, but have not run.

The next isolated interpreter/identity check failed before SSH opened:
exit 1, `kex_exchange_identification: read: Connection reset`,
`Connection reset by 172.17.61.18 port 22`,
`Connection closed by UNKNOWN port 65535`. No command in that session,
including the proposed task-directory permission adjustment, is known to have
run. The likely failing component is the gateway/session path; the exact
cause is unconfirmed. No further SSH attempts followed. Remote raw logs remain
at the exact paths above, but their file hashes have not been fetched.

**Remaining work and rollback.** Complete only static source/docs, record an
exact reviewable source checkpoint and unverified delta commands, then request
the coordinator's scoped source audit. No fixed-source GREEN or final two-DAG
import exists. External connectivity recovery is required before BS10610
preflight and runtime validation; local or production tests cannot replace it.
Rollback is to leave the isolated source unmerged. Deployed services and data
were unchanged by this task.

**Source checkpoint delivered for review.** R2 persists a minimal compute-only
permit bound to the action ID, DagRun, exact frozen Step3 tuple, business receipt
and native terminal. Current polling also compares that permit to the latest
monitor; historical actions cannot settle a replacement execution. Before the
first action exists, marked native unknown/missing evidence blocks reservation,
while fresh matching failure can resolve an obsolete UI reconnect phase. This
does not remove queued downstream authorization or change the budget/deadline.
R4 uses the shared terminal validator and trusted current run/cleanup-route stage,
not the snapshot-selected stage. Failed Step3 cleanup still requires existing
complete schema2 Master/Worker quiet evidence; Step2 handoff alone cannot release
global ownership. WGS/GATK callback and cleanup producers read the existing
stage-status/native observe paths. Worker probe follow-ups contain only their
nonce-bound Worker proof. No new route, table or recovery engine was added.

Source checkpoint commit: `8617dfa26b53d8371567fd1000a6a598ab87deff`
(`UE05 bind native recovery and cleanup evidence (source only)`). Commit touched
only the 22 paths below. After commit, Git reported no tracked changes and only
the preserved untracked `.codex-artifacts/`. Nothing was pushed or merged.

Changed files are the 19 paths listed in
`.codex-artifacts/ue05-continue/source-delta-files.txt`, plus
`CURRENT_STATE.md`, `TASKS.md`, `HANDOFF.md`: eight backend app modules,
two backend test files, four DAG modules/helpers, two DAG test files and
docs05/07/08. The shared SSH implementation remains in baseline commit
`06bf30a`; its delta test is now standard-library unittest. `git diff --check`
exited 0 after integration. No local runtime test, Python compile or DAG import
was run. The checkpoint is SOURCE ONLY, unaccepted until source audit and
BS10610 fixed-source GREEN; no merge or deployment follows this commit.

**Preserved evidence and SHA256.** All files below are local untracked artifacts
in `.codex-artifacts/ue05-continue/`, preserved without uploading or deleting
anything after the gateway reset. `source-final.tar` contains tracked backend,
DAG, config and script inputs plus the new thin callback test; it is a final
source input, not executed evidence. The earlier RED checkpoint is retained
separately and differs from the final source.

| File | SHA256 |
| --- | --- |
| `baseline.tar` | `0eecf948ff0816d6226cec3c7e988d28715100ba9935111690ba701d2f42832b` |
| `checkpoint.tar` (earlier RED input) | `959f7c0614372a281e71101875fac4d98bde6d8b072329ae1e081c60a4470ea5` |
| `ssh-before.tar` | `9fe002bc89ce7e0069db22a193518f5aade5f16fa2f68723aab5ee8b25862f41` |
| `source-final.tar` | `737ca9035231749caadd62468a597a8aa5ecd02f51339d207ac7e771ccdc2ecf` |
| `source-delta.sha256` (19 individual input hashes) | `d720176fb858835b5ca77125b2195603d6bc6bb7f81c47fdb90b6d8f4a9b2461` |
| `captured-red-output.log` | `dbca03d13b23d77ac8b99db255ba89aeb3579e29920a7344d13008344b33ceea` |
| `captured-red.json` (exact command and result) | `fcc947a23e2cc63e671d215250e4369ad33309b5c68406c7baeca4ffbd170122` |
| `captured-gateway-reset-output.log` | `6a7df1d387672173138a66e19eca461b33f7805b7094a454a2184e0c037fb55d` |
| `captured-gateway-reset.json` (exact failed command) | `37a3659e9cbde950e539c62fcda15470ea7d6386ef013869cc6f432061a7e12e` |

The captured command records are exported verbatim from current-thread tools
`exec-b11ad1d7-47f4-46eb-9bbb-da75771e7fbf` (2026-09-30 04:23 UTC) and
`exec-388de163-0127-462b-934a-d39bc51963ab` (04:33 UTC). The RED output is the
captured log tail, not the complete remote log; complete remote `.log`/`.xml`
hashes remain unavailable. The RED wrapper exited 0 to report individual test
exit codes, all 1; it did not pass the tests. The reset command exited 1 before
its streamed Bash script ran. Its proposed UID50000/package-path check and
task-directory chmod are unexecuted ideas, not verified environment changes.

**Unique pending delta commands.** Run only after external SSH recovery and
fresh BS10610 boundary verification, against this final source in isolated
network-disabled containers using the existing pinned images. Backend uses its
existing pytest environment; DAG tests use the existing `/usr/local/bin/python`
and Airflow module path. The effective Airflow identity/package visibility must
be resolved read-only first; do not install dependencies. These commands have
NOT run against the final source:

```text
python -m pytest backend/tests/test_cce_recovery_poll.py::test_manual_terminal_allows_one_budgeted_recovery backend/tests/test_cce_recovery_cleanup_fence.py::test_unknown_stage_cannot_fail_or_release -q --tb=short -p no:cacheprovider --basetemp=/evidence/final-backend-tmp --junitxml=/evidence/final-backend.xml
/usr/local/bin/python -m unittest discover -s dags/tests -p test_ssh_transport.py -v
/usr/local/bin/python -m unittest discover -s dags/tests -p test_native_callback_observation.py -v
```

Also import only `bio_wgs.py` and `bio_gatk.py` with the existing isolated
two-file DagBag check; do not run the full DAG folder or metadata-backed CLI.
Backend count is two parametrized R2 cases and one R4 node; SSH has nine methods,
and the thin bridge has one method per deployed adapter. No flow-by-six-stage
matrix, full suite, accepted UE01-04/F7/final-release rerun or real batch.

## 2026-09-30 UE-05 resumed after SSH recovery (development in progress)

Direct user instruction: SSH should now be connected; continue development.
The pause is lifted. Continue the existing UE-05 branch/worktree from HEAD
`06bf30a`, preserving the R2/R4 drafts and `.codex-artifacts/`. Formal spec/plan
remain in the coordinator's `wgs422-p0-integration-20260926` worktree. This
checkpoint covers only R2 exact action/compute terminal binding, R4 failure and
cleanup fences, the existing authenticated native snapshot channel and DAG
producers, plus docs05/07/08. No production, real batch, new dependency,
installation, deployment, data cleanup or UE-06 operation is authorized.

One bounded SSH hostname preflight exited 0 in 1.3 seconds, returning
`server10610`; the read-only environment fingerprint then completed.
Identity: `chenjc` UID6708, `bioinfo` GID520, docker group998. Control root:
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`; current resolves to
`releases/20260912-opt-4d3d24e6`, SOURCE_COMMIT
`4d3d24e6c0308b682a92e2b09824026b7a888818`. Actual backend source remains
`releases/20260926-p0-e358aad/backend`; WGS DAG source is pinned to that release,
GATK/common to `20260915-main-359df11`, discovery DAGs to
`20260927-dag-discovery-4fe71cb`. Backend image is
`sha256:8491604ee01d9b3a84d74e7edf233a9d5dd20ddbf14f8a646c25c05f8729efed`;
Airflow image is
`sha256:58195672af685cfa6551cfc44b37b6218bd2039c44b717163a6e8072f78dfd2b`.
Scanner/auto dispatch are false; execution gates true are existing test state,
not changed here. The evidence root is `chenjc:bioinfo` mode0755.

All new runtime validation will use task-specific
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue05-native-consumers-20260930-continue/`
source/evidence, existing pinned images, network-disabled disposable containers,
and synthetic files/SQLite. No application service or live database is used.
Required delta nodes are `dags/tests/test_ssh_transport.py`,
`backend/tests/test_cce_recovery_poll.py::test_manual_terminal_allows_one_budgeted_recovery`,
`backend/tests/test_cce_recovery_cleanup_fence.py::test_unknown_stage_cannot_fail_or_release`,
the thin `dags/tests/test_native_callback_observation.py` bridge, and two-DAG import.
UE-01-04, F7 and final-release accepted evidence is referenced without rerunning.
No new GREEN has yet been produced by this resumption.

## 2026-09-30 UE-05 paused while SSH is unavailable

The user directed the airflow agent to finish its current checkpoint and then
pause until SSH recovers. The isolated branch is
`jiucheng/airflow/UE05-native-recovery-consumers`; HEAD `06bf30a` is the
independent shared-SSH **source** commit. It has no BS10610 GREEN. The one
necessary BS10610 preflight in this turn failed before a session opened with
`Connection timed out during banner exchange` (exit 1); no retry or remote
command followed. Do not poll SSH, start another development phase, deploy,
install, clean data, or treat this source as released while paused.

The current R2/R4 checkpoint is **uncommitted and incomplete**. R2 edited only
`backend/app/cce_recovery_budget.py`, `backend/app/cce_recovery_poll.py`, and
`backend/tests/test_cce_recovery_poll.py`: it drafted a frozen Step3 request,
latest business row/receipt, and exact native terminal binding persisted on the
action; it kept the Worker nonce separate and drafted synthetic positive and
negative cases. The draft tests were not run. Additional source edits are in
`backend/app/stage_execution_contract.py`, `backend/app/main.py`,
`backend/app/diagnostics_service.py`, `backend/app/gatk_airflow_sync.py`,
`backend/app/gatk_runtime_service.py`, `backend/app/wgs_submission_service.py`,
`dags/bio_wgs.py`, `dags/bio_gatk.py`, and `dags/cce_worker_wait.py`.
`main.py` and service callers now pass optional native snapshots and settings,
but the R4 backend failure/cleanup fence signatures and DAG callback/cleanup
snapshot producers are still missing. The combined dirty source is therefore
not an integrated or validated change. The existing `.codex-artifacts/` remains
untracked and must be preserved.

Static command: `git diff --check` exited 0. No runtime tests or DAG imports
were run after the failed preflight; local runtime tests do not substitute for
the required BS10610 isolated synthetic validation. On authorized resumption
after SSH recovery, finish the R4 fence/producers and source review, then
revalidate BS10610 hostname, control root, release, mounts and execution gates
before the narrow synthetic nodes. Preserve the original recovery budget and
Worker nonce boundary. Rollback is to leave this isolated branch unmerged;
deployed state and data were not changed by this checkpoint.

## 2026-09-30 UE-05 approved continuation and transient network boundary

User-approved scope: shared OpenSSH transport for current WGS/GATK Step1-6 and
P0 dispatch/observe, followed by R2/R4 optional exact native snapshots through
existing authenticated poll/callback/cleanup requests. Worker nonce observation
remains a separate contract. UE-04 source is complete; Step1 historical handling
is not part of this task. Source baseline is HEAD `1e84714`; preserve the three
uncommitted R2 draft files and existing `.codex-artifacts/`. SSH is to be an
independent commit before R2/R4. Current work is isolated source and BS10610
synthetic validation only; no BS96, node200, real batch, wheel, service,
database, cleanup, deployment or release. This continuation adds only the
shared SSH source/test and docs 07/08 plus this state record before the separate
R2/R4 work. The coordinator reports a recent
BS10610 gateway connection timeout; current-turn network access remains
unverified. The one necessary read-only preflight command was
`ssh -o BatchMode=yes -o ConnectionAttempts=1 -o ConnectTimeout=10 BS10610 hostname`.
It exited 1 after 10.2 seconds, stderr:
`Connection timed out during banner exchange` and
`Connection to UNKNOWN port 65535 timed out`. The SSH gateway did not establish
a session, so hostname/control root/current release/mounts/gates and remote
synthetic nodes could not be checked. No retry, code execution, data change or
local runtime-test substitution followed. Likely cause is the currently
unreachable gateway or pre-session SSH path; the exact network component is
unconfirmed. Continue source and static review; rerun the full test preflight
only after external connectivity changes. Rollback is to leave this isolated
branch unmerged; existing deployed services and data are untouched.

SSH source files: `dags/common/ssh_transport.py`, `dags/bio_wgs.py`,
`dags/bio_gatk.py`, `dags/cce_publish_dispatch.py`, `dags/cce_worker_wait.py`;
focused fixture `dags/tests/test_ssh_transport.py` and one corrected ambiguous
disconnect in `dags/tests/test_stage_execution_wait.py`. `docs/07` and `docs/08`
describe the new boundary. Shared helper enforces `ConnectTimeout=30`,
`ConnectionAttempts=1`, strict existing pre-session allowlist, cumulative
three-failure cap, 5/10-second backoff and one monotonic deadline. The original
WGS request-visibility business retries, P0 check/finish sequence, 30-second
Step4 read probe and 150-second Worker nonce probe retain their semantics.
Marked dispatch timeout goes to same-ref observe. Independent static review
found and corrected one exhausted-budget reentry that could have spawned a
fourth connection. `git diff --check` passed. Tests not run: BS10610 targeted
synthetic nodes and DAG import, because the single SSH preflight above failed;
local runtime tests are outside this repository's acceptance boundary. The
gateway must recover before remote validation and any later UE-06 gate.

## 2026-09-30 UE-05 work started (source only)

**Goal and boundary.** Continue after committed UE-04 on branch
`jiucheng/airflow/UE05-native-recovery-consumers`. Implement only R2, R4 and
final writer read-only transient reconnect, using BS10610 isolated synthetic
delta evidence. No node200, BS96, production, real batch, wheel, database,
service, cleanup, deployment or release is authorized. Preserve the existing
untracked `.codex-artifacts/` directory.

**Current findings.** R2's queued action and compute terminal currently have
separate checks, and poll can persist a terminal marker before the bound
terminal receipt is fully validated. R4's Step3 reconnect observation is a
read-only UI diagnostic; failure/cleanup callers do not currently carry a
fresh six-stage native snapshot. Do not infer failure or quiet from unknown.
Final release already has two intentional inventory rounds (pre-release and
CAS verification); only typed transient query reads may reconnect. Native
owner confirmed the narrow `release_query_deadline` internal signature and is
validating its separate source; this platform checkpoint does not include or
verify that native change.

**Preflight.** Local source/document reading and `git status` were read-only.
`ssh BS10610 hostname` returned `server10610`; native `RecoveryQueryError`
and `_recovery_query` signatures were read from its separate source checkout.
All UE-05 execution evidence below is isolated synthetic, with no application
service or live database write.

**Open work and rollback.** R2 and R4 need a narrow authenticated native
snapshot transport decision before implementation. The Worker-probe nonce and
its 600-second quiescence check must remain distinct from the stage snapshot.
No deployed state exists; rollback is to leave this isolated branch unmerged.

**Platform checkpoint review.** The R2 three-file draft in the working tree
passed its preliminary WGS/GATK node (2/2), but follow-up review found that it
does not bind the action to the frozen Step3 request/ref and accepts a business
success row before the DAG's fresh native observation. It is not accepted,
committed or counted as R2 proof. The frozen-request and exact native snapshot
handoff must be designed together with R4; do not treat the existing
`worker_observation` Worker-probe nonce as a stage snapshot without an explicit
shape check. The R2 RED/GREEN logs remain diagnostic only at
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue05-r2-20260930/`:
`r2-red-true.log` reproduced WGS/GATK `needs_attention` instead of expected
`waiting`; `r2-final.log` recorded 2 passed, SHA-256
`4cb12f7705a528eb45dd4e1a7f5b0292a10da786772f950c0ab37b5d42577aa9`.
These results do not cover the newly identified frozen-request/native-terminal
gap; no R2 acceptance or source commit follows from them.

**Accepted partial source commit.** `4cb6e0d` contains only F7, platform
final-release read-window source, their two focused fixtures, and docs/05 and
docs/08. The R2 draft and R4 are outside this commit. No push, merge or
deployment was performed.

F7 WGS Step4 digest source is limited to `backend/app/cce_publish_recovery.py`
and its one existing test node. On BS10610 the node first failed at the
registered authority digest check, then passed 1/1 in a network-disabled,
read-only backend container. The command selected only
`backend/tests/test_cce_publish_recovery.py::test_wgs_publish_control_accepts_initial_and_recovery_frozen_digests[wgs]`
with `python -m pytest -q`, using `docker run --network none --read-only
--tmpfs /tmp` and isolated candidate `candidates/ue05-f7-20260930`.
Evidence root is `/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/`.
Raw RED `ue05-f7-20260930/red.log` SHA-256
`49e7a4b64e1066019dbae9943fa27a5267ff925d794e68416138ae56e385dce4`;
GREEN `ue05-f7-20260930/green.log` SHA-256
`2ba01686be7c8a931be88186592674924cf06a514ef11f71f1f7f39dafe467e7`;
the raw log ends `1 passed, 26 deselected in 0.53s`.
GREEN JUnit SHA-256
`548e0d176233d8e66c9e6243c707c37a7e35d96c50a37d2d2aef6795fb561653`.
Candidate source/test SHA-256 were
`b27660639b5c3b5e7434e58c9ccc772a6f86c6786e98ee86e104e0f8f9f6d2f5` /
`72bdd5c0475359e7ada6e26513f326ca6daff35ef59451e10260dbca2697507c`.

Final-release platform source is limited to `scripts/cce_paired_runtime.py`,
`scripts/cce_recovery_workloads.py` and the single delta node in the existing
bulk-inventory fixture. BS10610 `server10610` control root resolved to release
`20260912-opt-4d3d24e6`; intake/auto dispatch remained false. In isolated
candidate `ue05-final-release-20260930`, the pinned native read-only query
source SHA-256 was `ae52b7601c3ea59e5e294bb3bf695802efc69f3d5b60333bd6b422c47bd14c53`.
The command selected only
`scripts/tests/test_cce_final_bulk_inventory.py::test_final_release_reconnect_does_not_repeat_materialization_or_cas`
with `python -m pytest -q --tb=short -p no:cacheprovider`; it used the
candidate and native `src` on `PYTHONPATH`, plus `CCE_PLUGIN_SOURCE` and the
fixed `CCE_NATIVE_QUERY_SHA256`. No application container or live database
was involved.
The revised node injected typed transient at the CAS-proof read, exhausted
the shared budget after preflight, and denied a stubbed missing lock: 3/3
passed. Raw `ue05-final-release-20260930/final-release-green2.log` SHA-256
`55425a44f4e6135845da2ab1ca1820f7d67faf2a96c6f6ec55e32faf4394e8d4`;
JUnit SHA-256
`d6cd8aa43d29f25da5f7b4397c723b0d1596076ce526f814710374904f31ddd8`.
Matching local/remote candidate source SHA-256: paired runtime
`fdc23a33f0d805bd923b6a31d5f70a381164f5b2a523160c621167aaf3d285ab`,
workloads `18842e5d31362ff4029c7398370f103c329ada87812f97ae2498cab092ec2145`,
test `712ddbd9d57b62596436387acbb0d19e87194478178f215cf3d7a40c35467373`.
The native `_release_batch_lock` was stubbed for this platform delta, so this
does not prove the real native signature, CAS, installed wheel or cloud path.
Native owner source changed during a subsequent baseline attempt; its fixed
SHA guard rejected all three cases during fixture setup, so that attempt is
not a valid RED and was not rerun. Raw log SHA-256
`04017d46f0f9ffb95d13f5d3bfabd49266babce5df172b6862a5abcc5040ba7f`.

**Final-read backoff refinement.** Follow-up platform commit `be0adb8`
replaces the fixed three-attempt cap with shared-deadline-bound 2/5/5-second
backoff only for final-release typed read-only `TRANSPORT`/`SERVICE` queries.
The existing single CAS and preflight/CAS inventory rounds remain. The same
fixture's `reconnect` parameter injects four brief typed failures at the
second (CAS-proof) inventory using a fake clock. An isolated copy of native
query source was pinned under candidate `ue05-final-release-20260930/native`
with SHA-256 `0a544c77bcbeb26249c2369eb6992dfc9239f85f185998721cbb9a978615f896`,
avoiding concurrent edits in the native owner's worktree. With the previous
fixed-three platform source, only this parameter failed 1/1 on the fourth
`TRANSPORT`; raw `backoff-red.log` SHA-256
`37daed57def1275c557749298b125bf6e1d55e0d1e1c4f99af336ab855ee333b`.
With the refined platform source, only this parameter passed 1/1 in 0.20s;
raw `backoff-green2.log` SHA-256
`a5661b00cbecc1e68a12fba8ecc0bc387e39a4e0685ca0771cdab3fbaa483098`,
JUnit SHA-256
`e3f3284d3828de54a648f78b2adb6df445a0218e82e4dd3ac7811671ff4bb49e`.
Matching local/remote source SHA-256: workloads
`aabf27cf7b39eaeb591b5742dac1c8f74892f7d9a446154cf41fb7a0cd906a4d`,
fixture `556bfa9d27db0441b7d3a66ffd51c9e32abdf6322285277b19f30b8668b03656`.
The already-passing budget and missing-lock parameters were not rerun for
this backoff-only change. The native owner separately committed the matching
`release_query_deadline` interface and its own targeted evidence as `7172573`;
no native wheel was installed here. Neither side's synthetic node proves the
paired installed entry, live CAS or production behavior.

## 2026-09-30 UE-04 source checkpoint committed (not deployed)

**Goal and authority.** UE-04 registered WGS/GATK Step1–Step6 source
integration is committed as `a6c31d1` on the isolated
`jiucheng/airflow/UE04-unified-stage-execution` branch, after platform gate
commits through `0feec86`/`5fd01a9` and DAG client `7ee7d7c`. The old
`20260927B` Step1 case was complete before this work. No node200, BS96,
production, real-batch, wheel, service, database, cleanup, deployment or
release action was authorized or performed. Pre-existing untracked
`.codex-artifacts/` was preserved.

**Implemented.** R1 now ingests the latest Step2 receipt outside the first
run-lock session and rechecks attempt, DagRun, recovery action and stop state
before normal/P0 Step3 registration or public Resume side effects. Reused
Step3 remains tied to its exact predecessor execution/generation/hash. F4
requires the current Step6 business receipt and a fresh exact native succeeded
snapshot to finalize marked WGS/GATK; WGS additionally rechecks the frozen
producer digest before selecting marked versus legacy behavior and refuses
late finalize after a stop. Airflow success alone cannot project full CCE
business success; WGS canary/local projection remains intact. F3 recognizes
only the persisted authorized current GATK recovery DagRun and its frozen
`conf`. Marked Step1–Step6 sensors without submit XCom re-observe the exact
current native ref before advancing. Legacy unmarked paths remain explicit.

**Files.** Backend source: `main.py`, `wgs_resume_service.py`,
`wgs_stage_execution_service.py`, `diagnostics_service.py`,
`stage_execution_contract.py`, `gatk_runtime_service.py`,
`gatk_airflow_sync.py`; WGS/GATK focused backend tests. DAG source:
`bio_wgs.py`, `bio_gatk.py` and their focused tests. Contracts:
`docs/05_API_CONTRACT.md`, `docs/07_AIRFLOW_DAG_SPEC.md`,
`docs/08_WORKFLOW_RUNTIME_INTEGRATION.md`; state: `CURRENT_STATE.md`,
`TASKS.md`, this handoff. No database model, frontend or production workflow
core file was changed.

**BS10610 environment and commands.** `ssh BS10610 hostname` returned
`server10610`; the current test release resolved to
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260912-opt-4d3d24e6`.
All Python checks used isolated candidate mounts, `docker run --rm --network
none --read-only --tmpfs /tmp`, no application service or live database.
Backend image `8491604ee01d` ran `python -m pytest
tests/test_wgs_resume_stage.py tests/test_wgs_f4_airflow_sync.py -q
--tb=short -p no:cacheprovider`: 50 passed, 1 dependency deprecation warning;
JUnit `/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue04-r1-20260930/ue04-wgs-f4-digest-combined.xml`
SHA-256 `71063ac4a566f4c9954d628c4e43ca3b5bbda7516a08f12ecc03f90a29306c4c`.
After the final WGS status-reader refinement, only `-k missing_marker` ran:
1 passed, 45 deselected; JUnit `ue04-wgs-f4-downgrade-delta.xml` in the same
evidence directory, SHA-256
`f9a129f8a6412a2868f8f382e1bfee0643be3521c215aed268757de1f16bb628`.
GATK backend `python -m pytest -q tests/test_gatk_resume_stage.py
tests/test_gatk_runtime_service.py --tb=short -p no:cacheprovider` passed
28 before the last marker/conf change; new focused cases then passed 7/7.
Raw delta log `/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue04-gatk-f4-20260930/backend-marker-conf-green.log`
SHA-256 `7b250f88b42211589717e3548646056eb8cf1771ab1ad4fd75a8fb469061a2e7`
ends `7 passed in 0.78s`.

Airflow image `58195672af68` ran the WGS DAG test file as Python unittest:
18 passed before the no-XCom change. Its new focused test passed 1/1; raw
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue04-dag-sensor-20260930/delta-green.log`
SHA-256 `e4fbc219285698b658a6ec4d15173e66dd46f2483a179b6c111a47c9fd09ecc2`
ends `Ran 1 test in 0.852s`, `OK`. GATK DAG focused 4 and shared 16
passed before its no-XCom change; new focused 1/1 raw
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue04-gatk-f4-20260930/dag-no-xcom-green.log`
SHA-256 `4728cb3e361fc1f8a702d5c4e94259b238800ad86136c2306f729e548db81368`
ends `Ran 1 test in 0.001s`, `OK`. Earlier shared client 16/16 and
targeted two-DAG DagBag import passed. Latest source matched the BS10610
candidate SHA-256: `main.py` `52d8cb9b8bc56ad1e35d6a493af79e711fe1d4a424ad19bfe1f69f6bffd8960b`,
WGS DAG `bde72f6946465d690ae3856be4bb760071c14c68479bfa7406d4cf39616ddfa0`,
GATK runtime service `145f7469332eebac3118f75a20312a5ee1bd4dc513512a1dc1b9c3be56f1fdbd`,
GATK DAG `fe7665d8ce697772d257958a1f338638a5188f6b1d1e75703dae62a0884712ef`.
`git diff --check` and the source commit's staged diff check were clean.

**Master TTL source and evidence limit.** Platform
`scripts/cce_paired_runtime.py:174-193` selects only deployment-trusted,
SHA-pinned CLI/platform/guard paths. `stage_command:200-209` routes registered
Step4/5 to the fixed platform entry; `_predecessor:1149-1182` validates the
previous exact business receipt; `_selected_registered:1355-1363` reads its
`cce_master_binding`; `downstream_registered:1256-1270` passes the selected
bundle and UID to native `step4`/`step5`. The adapter's fixed handler/worker
route is in `scripts/cce_stage_execution_adapter.py:444-485`; request fields
cannot select executable code. The separately committed native `4fa85874`
has `cce_batch_runtime.py` SHA-256
`ae52b7601c3ea59e5e294bb3bf695802efc69f3d5b60333bd6b422c47bd14c53`.
Its existing ordinary v2 Step3-to-Step4/log-export TTL test passed 1/1;
Step5 follows source delegation, not that test's direct invocation. Existing
platform selected-Master Step4/5 tests stub log download, and
`test_gatk_thin_binding` stubs the adapter itself. These tests do not prove a
complete paired TTL run or an active deployed policy pin to `4fa85874`.

**Failure and next phase.** A WGS DAG check initially used backend image
`8491604ee01d` and exited 1 during collection with `ModuleNotFoundError:
airflow`; cause was the image choice. Repeating on the Airflow image yielded
18/18. Earlier full DAG-folder import lacked unrelated
`snakemake_interface_logger_plugins`; `airflow dags list` lacked an initialized
ephemeral metadata DB, so neither is acceptance evidence. No full latest
backend suite, installed native wheel, node200 behavior, deployed policy pin,
paired TTL end-to-end run or production validation was performed. The planned
UE-06 candidate installation must check its actual entry and pin with its
approved minimal runtime validation; this UE-04 source checkpoint does not
authorize that phase. Rollback is to leave the branch unmerged or revert
`a6c31d1`; there is no deployed state to undo.

## 2026-09-29 UE-03 bounded inventory and Heavy role source checkpoint

**Goal and authority.** Continue the approved unified-stage UE-03 source work
in the isolated
`C:\Users\11217\.codex\worktrees\gatk-prod-compat\airflow-demo` worktree,
branch `jiucheng/airflow/UE03-inventory-probe`, based on UE-02 platform commit
`3d5174ca7b53a6b304b39f5a74c76eff6af617c2`. Only platform source,
synthetic tests and state documents changed here. The existing untracked
`.codex-artifacts/` UE-01 backup was preserved. No user batch B/D, original
FASTQ, analysis directory, database, production release, node200, wheel,
service, Git remote or live CCE Job was touched.

**Paired native interface.** On BS10610 the owner committed query-only native
source `6f5c12027a8d3d88424ef0b335f7dddcc9a35f5a` in
`/mnt/biodevrwbi/33.chenjiucheng/project/wgs-cloud-platform/projects/huawei-cloud-runtime`.
`_recovery_query(config, "jobs", "--chunk-size=0", timeout=...)` and the
equivalent `pods` form return native parsed JSON, enforce the 4 MiB cap,
reject pagination and preserve typed query errors. Exact source file SHA-256
for the platform acceptance was
`d4f09a557f2edc93c7010b7a2d1a41a0ed7bc392a004a16bf8451d52ba1eae4f`.
The platform no longer calls `_run/_kubectl` or `subprocess.run` for the
bound inventory.

**Completed platform slice.** `probe_final_workloads` and
`probe_bound_workloads` use one run-label Job/Pod pair, one namespace Job/Pod
pair, and one exact Master GET per proof. Full lists are indexed by frozen
name/UID/run label and every relevant Pod owner reference; unrelated batches
in the namespace are ignored. Pagination, malformed inventory, identity
conflicts, active work at a replacement/release gate and missing persisted
terminal proof fail closed. A legitimate move between reads raises
`InventoryMoved`. Failure evidence, `RecoveryCapability.inspect`, active
Worker observation and final writer release inherit this common query path.
Inspect and lock CAS perform separate fresh rounds. The bound submission
helper derives its Kubernetes selector through the pinned native
`master_job.run_label(raw run_id)`; it does not use the raw ID as a label.
Each query is bounded by 30 seconds and each inventory by 120 seconds;
recovery inspection additionally uses its frozen original compute deadline.

The Heavy global collector now skips only nonterminal Jobs annotated
`cce-pipeline/action=evidence-reader`. The fixed native source confirms
both evidence-reader and directory-probe helper producers carry this action,
although the current production objects were not inspected for this field.
An unmarked WGS Master without the required Heavy env still yields
`master_configuration_inconsistent`. GATK's quota distinction is unchanged.

**Changed files.** `scripts/cce_recovery_workloads.py`,
`scripts/cce_recovery_inventory.py`, `backend/app/heavy_global_snapshot.py`;
the new `scripts/tests/test_cce_final_bulk_inventory.py` and updated
`scripts/tests/test_cce_recovery_workloads.py`,
`scripts/tests/test_cce_recovery_inventory.py`,
`scripts/tests/test_p02_final_inventory.py`,
`scripts/tests/test_heavy_global_snapshot.py`; this handoff,
`CURRENT_STATE.md`, `TASKS.md`, and
`docs/08_WORKFLOW_RUNTIME_INTEGRATION.md`.
`scripts/cce_recovery_failure.py` and `scripts/cce_paired_runtime.py`
remain unchanged consumers of the shared entry.

**BS10610 synthetic evidence.** Read-only preflight confirmed
`server10610`, current control release `20260912-opt-4d3d24e6`, disabled
test intake/automatic dispatch and the source commit above. The only copied
platform candidate was
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/ue03-inventory-probe-20260929`;
evidence is under
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue03-inventory-probe-20260929`.
The first 275-Worker target failed as expected: **554 native-query calls
versus the required five**. The final fixture imports the real native module
from the fixed absolute source, verifies its file SHA-256, and substitutes
only the subprocess transport with synthetic JSON. It covers failed
classification, active observation versus replacement, final release and
fresh lock-CAS proof. The final scoped command, using nipttest Python and
`PYTHONDONTWRITEBYTECODE=1`, was:

```text
python -m pytest scripts/tests/test_cce_final_bulk_inventory.py scripts/tests/test_cce_recovery_workloads.py scripts/tests/test_cce_recovery_inventory.py::test_validated_inventory_drives_one_native_inventory_round scripts/tests/test_heavy_global_snapshot.py -q --tb=short -p no:cacheprovider --junitxml=<evidence>/ue03-platform.xml
```

The command required `CCE_PLUGIN_SOURCE=<fixed native repository root>`,
`CCE_NATIVE_QUERY_SHA256=d4f09a557f2edc93c7010b7a2d1a41a0ed7bc392a004a16bf8451d52ba1eae4f`,
`PYTHONPATH=<fixed native repository>/src`, and
`HEAVY_TEST_MODULE=<candidate>/backend/app/heavy_global_snapshot.py`.
Result: **35 passed, zero skipped, 0.38 seconds**. Raw log SHA-256
`ff6b43805e71905fa2e83010e53c6cc9cadc1215eac2296bb68df530844a0c3f`;
JUnit SHA-256
`9cd207ecb92d2b1f8f45dd3073ef5fca672505292ca51b798bc2d10309e20e5b`;
input manifest SHA-256
`e9d2edf38c119cbc0abefcffeb76face70351b251fb7bb7a7c5a90ee003a116e`.
Every listed candidate input hash matched the local source. The Heavy role
test separately showed the expected RED result `waiting/mode=None` before
the fix and 5/5 GREEN after it. Local syntax parsing and `git diff --check`
were clean.

**Failed command and limitation.** A targeted run of
`scripts/tests/test_p02_final_inventory.py` in nipttest exited 1 during
collection, first because the plugin source path was absent, then after
adding it because that current plugin imports `typing.Self` and nipttest is
Python 3.9. No test body ran, and no compatibility shim or environment
upgrade was applied. The existing selected-monitor fixture includes
`probe_waiting_workers`; it was not rerun under this incompatible plugin
source. The new 275-Worker fixture exercises its real shared failure
collector but does not recreate the entire registered monitor process.

**Recovery probe deadline handoff.** After the query/Heavy checkpoint, the
platform passed only the authenticated Step2/3 `cce_recovery_deadline` from
`scripts/cce_paired_runtime.py:resume_registered` to native
`writer_for_bundle(..., probe_deadline_epoch=...)`. The registered request is
checked before reading the deadline; the existing `monitor_wait(payload, 0)`
check now runs before writer construction. The same parsed epoch is used by
`RecoveryCapability`. Requests without a frozen deadline keep the previous
writer call. Normal Step3 observation does not validate the writer. Step4
`publish_deadline` limits fresh dispatch and was deliberately not passed to
an already started worker. No request, `ExecutionRef`, CLI or database field
changed.

The new isolated BS10610 synthetic file
`scripts/tests/test_cce_probe_deadline_handoff.py` first failed as expected:
6 failed, 3 passed because the original writer call omitted the frozen value
and malformed deadlines reached writer construction. The first post-edit
candidate run exited 1 during import because its isolated copy lacked the
unchanged `scripts/cce_recovery_deadline.py`; that dependency was copied into
the candidate, not edited. The final scoped command was:

```text
PYTHONPATH=<ue03 candidate> PYTHONDONTWRITEBYTECODE=1 <nipttest python> -m pytest <candidate>/scripts/tests/test_cce_probe_deadline_handoff.py -q --tb=short -p no:cacheprovider --junitxml=<evidence>/ue03-probe-deadline-final.xml
```

Result: **10 passed, zero skipped, 0.08 seconds**. Candidate source SHA-256:
`scripts/cce_paired_runtime.py`
`8f41e690c745ee821a0c2a928fe67d7dcf0c49e17193491fc3a21484d7949505`,
unchanged `scripts/cce_recovery_deadline.py`
`91bdf3559dbd9643c1d2c9bb607ad51c1f16a4d7c1017dd1b1c7c1c44fd2cc38`,
and focused test
`489989f0806f6c91415fbb7728d18dcbb2ae12083279fa88eaf7c72546fa2fcd`.
Final raw log SHA-256
`39bfbb45c5e58525f3aa3d49882de78d6995eb885dd8b35e2f146811755f3724`;
JUnit SHA-256
`3d7a998f0b1eaf9cfed3c1d8daaaf6d5f4b9ec4e448ac197eecc4087cfc13fbd`.
Evidence is under the same `WGS_test/cce-evidence/ue03-inventory-probe-20260929`
root. The existing 35-query/Heavy set was not rerun. Native optional-writer
signature and directory retries still require their separate source commit
and targeted acceptance before this platform call can be used in a release.

**Open work, risk and rollback.** Native directory-probe retry is **not in
commit `6f5c120`**. The native owner is implementing same-bound-Pod read-only
2s/5s retries with a 120-second total and 30-second per-operation limit.
These bounds are **not** a newly created business stage deadline. Ordinary
Step1/4/6 have no applicable frozen absolute deadline and retain their
external Airflow stage timers. The frozen compute recovery deadline must cap
its own writer probe. Run the targeted native
`tests/test_directory_probe_retry.py` and review the paired source before
declaring UE-03 complete.
Synthetic source tests do not establish live-cluster or installed-wheel
behavior. This source slice can be reverted by its scoped platform commit;
no runtime state was changed.

**Directory-probe deadline map (read-only, no implementation).** Ordinary
registered Step1/4/6 reaches native `writer_for_bundle.validate` through
`scripts/cce_paired_runtime.py:192-209` (`stage_command`),
`:1252-1274` (`downstream_registered`) and `:1322-1397`
(`_selected_registered`). The native CLI also constructs the writer in
`cce_batch_runtime.py:3545-3579`. Native `ProtectedWriter.claim/enter`,
`writer_for_bundle.validate` and `protected_stage` lead to either
`current_master_storage_identity` or `cloud_storage_identity`, then
`_directory_probe_identity` (`cce_writer_guard.py:247-264`), whose current
read-only exec timeout is 30 seconds. The live-Master path checks UID and
volume binding before and after. The helper path checks its exact Job/Pod and
PVC/PV; CREATE 30 seconds, Pod wait 60 seconds, cleanup 90 seconds and helper
Job `activeDeadlineSeconds=600` are separate operation/helper limits, not
the original stage deadline. The helper journal does not freeze an absolute
helper expiry, so retry must not restart a 600-second helper lifetime.

WGS `config/wgs_stage_contract.yaml` supplies relative Step1/4/6 timeouts
of 172800/172800/86400 seconds, and Airflow WGS sensors have corresponding
relative timers. GATK has relative Airflow wait timers and a separate
15-minute runner execution timeout. None is an absolute deadline passed to
the native writer. Only opted-in Step4 freezes `publish_deadline` at first
registration (`backend/app/cce_publish_recovery.py:23-39`), but that value
governs fresh dispatch only; it is not a deadline for an already started
worker or writer probe. Step1 and Step6 frozen requests contain no
authenticated original absolute deadline. Registered Step2/3 compute recovery
has an applicable `cce_recovery_deadline`, now passed internally in
`resume_registered` only. The helper's original lifecycle and local probe
budgets stay separate; no new `ExecutionRef` field is needed.

## 2026-09-29 UE-02 native platform gate source closeout

**Goal and boundary.** Connect only marked, registered WGS/GATK Step1–Step6
requests to native `StageExecutor`, including Step4 publish observation and the
paired writer fence. Worktree:
`C:\Users\11217\.codex\worktrees\gatk-prod-compat\airflow-demo`, branch
`jiucheng/airflow/UE02-stage-executor-gates`, starting at source checkpoint
`ca15d6ea6a077208ff870b7a17178f0b050fc558`. Native source HEAD on BS10610
is `6c0aee2b326b774c5d6dff570f31718048a8eec7`; no native file was edited
here. No DAG/backend shared observation, wheel install, node200, production,
analysis submit, deployment, service restart, push or deletion was authorized or
performed.

**Completed source.** New `scripts/cce_stage_execution_adapter.py` provides
read-only `executor_for_registered` and the `submit_registered_stage` /
`run_registered_worker` paths. Its selected gate, worker command, handler and
paths are fixed by trusted local code. The adapter freezes exact request bytes,
batch binding and native ref in per-generation private registration, validates
business terminal identity/schema/hash, and publishes a separate private
per-generation native receipt. Old refs resolve from that registration and
optional equal request-history; an older dispatch can coexist with a first
successor freeze, but native submit still decides receipt and worker
quiescence. Private control directories are owner-only 0700 and files 0600.
Legacy worker/status/log evidence and invalid explicit markers fail closed.
`ComputeIdentity` is not projected; the private receipt records null.

`scripts/wgs_runtime_gate.py` and `scripts/gatk_runtime_gate.py` select the native
path only for marked Step1–Step6, retain their existing business handlers, and
reject marked requests at old worker entries. WGS keeps the native-open
`.worker.log` while archiving old business status. `scripts/cce_publish_recovery.py`
routes marked Step4 dispatch/observation through native evidence;
`scripts/cce_paired_runtime.py` checks native writer quiescence under both exact
stage locks, including missing WGS `<stage>.json` and GATK
`<stage>.request.json` with residual private evidence. Opted-in Step4 publish
rechecks deadline under native launch lock for a fresh launch, while a duplicate
can reattach after expiry. Ordinary Step4 without publish opt-in follows its
existing handler and stage timer. Four independent review findings on valid
successor freeze, explicit null marker, missing WGS request and ordinary Step4
were corrected with focused assertions. The independent delta review concluded
Ready with no remaining Critical or Important finding.

**Changed files.** Five runtime files above, plus
`scripts/tests/test_cce_stage_execution_adapter.py`,
`scripts/tests/test_wgs_native_stage_gate.py`,
`scripts/tests/test_gatk_stage_execution_gate.py`,
`scripts/tests/test_cce_native_consumers.py`, this handoff, `CURRENT_STATE.md`,
`TASKS.md` and `docs/08_WORKFLOW_RUNTIME_INTEGRATION.md`. The existing untracked
`.codex-artifacts/` is a UE-01 backup and was left untouched. No current
production data or B/D batch record was modified.

**BS10610 verification.** Read-only preflight confirmed hostname `server10610`,
current control release `20260912-opt-4d3d24e6`, disabled test intake/automatic
dispatch and native source HEAD above. Only the isolated candidate
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/ue02-stage-executor-gates-20260929`
was updated. It used nipttest Python with `PYTHONPATH` pointing at that exact
native source and ran:

```text
python -m pytest -q scripts/tests/test_cce_stage_execution_adapter.py scripts/tests/test_gatk_stage_execution_gate.py scripts/tests/test_wgs_native_stage_gate.py scripts/tests/test_cce_native_consumers.py --tb=short --junitxml=<evidence>/ue02-platform-gates.xml
```

Final result: **30 passed, 0 skipped in 0.29s**. Raw log:
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue02-stage-executor-gates-20260929/ue02-platform-gates.log`,
SHA-256 `f02db17e9e2f808ae7be4375beeb6dbbb29cce1d12dfe4de3b949ab0a1b3b6ed`.
JUnit SHA-256 `a6521601dc3e88206ee69fbdf4b42c27671e3b05e47631a393d4144e824508b4`.
Exact candidate/native input manifest:
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue02-stage-executor-gates-20260929/ue02-platform-inputs.sha256`,
SHA-256 `6627b11b2b22b8230a4db11354075b95341f6033aa3ad2ad237763ada7ab4394`.
Candidate input hashes were checked against local source; native module SHA-256
is `21b505da319cc752c5694f2b42e4082dd02dc47e3c7ddad895fdb87b08581bd2`.
Local `git diff --check` and Python syntax compilation passed. The earlier
selected-gate package/standalone import check was 4/4 in the same candidate.

**Failure record.** First focused pytest exited 1 during collection because
the new GATK test imported an old helper absent from the minimal candidate;
its assertion was made self-contained. The next run exited 1 with 25 passed /
5 failed: four tests lacked the unchanged `wgs_release_runtime.py` candidate
dependency, and one orphan-dispatch assertion expected a different fail-closed
message. The dependency was copied only into the candidate, and the assertion
now supplies a valid same-ref dispatch without frozen registration. The final
run above is green. No blind retry or broader test suite was run.

**Outstanding and rollback.** UE-04 must decide DAG/backend acceptance of native
asynchronous launches, shared read model and active old-request overwrite
recovery; GATK `resume` remains disabled in the shipped registry. A worker whose
active old request was overwritten before it wrote terminal evidence stays
unknown and requires reconciliation. Synthetic tests do not prove a real FASTQ
transfer, CCE Job, installed native wheel or production compatibility. Source
rollback is a scoped revert of this UE-02 commit; no runtime state changed.

## 2026-09-29 UE-02 platform selected-gate checkpoint (adapter blocked)

Follow-up source map after checkpoint commit
`7b199f07e2cd214727a2a232e237907b76a52d1d`: the pending adapter
consumer list is in `docs/08_WORKFLOW_RUNTIME_INTEGRATION.md` under "UE-02
adapter wiring map". It includes both gate CLIs, Step4 `--publish-dispatch`
and `observe_locked`, paired `_inactive_dispatcher` calls from recovery and
final writer release, and the backend's old request-only archive. WGS archives
old status/worker/log but not its overwritten request, so native old-ref
resolution cannot read the current request as history. WGS's old
generation archiver also moves `.worker.log`; native submit opens that same
path before its child runs. A direct reuse would misfile a live new-generation
log. This map is documentation only; no gate executor code or runtime state
changed. Native needs to settle trusted previous-generation receipt resolution,
legacy active-writer checking under the launch lock, and the WGS control-log
collision before platform wiring proceeds.

Goal: wire trusted WGS/GATK Step1-Step6 gates to native `StageExecutor` after
UE-01, without changing DAG/backend shared observation, deploying a wheel, or
touching production. Worktree/branch:
`C:\Users\11217\.codex\worktrees\gatk-prod-compat\airflow-demo`,
`jiucheng/airflow/UE02-stage-executor-gates`, from UE-01 `eac84ea`.

The native owner committed `StageExecutor` at `9272f2cc0fbf590c7820e0bc37f67ae35ab774ee`
in the BS10610 cce-pipeline source. Its binding requires absolute request,
dispatch and status paths in one directory, file mode 0600, and a distinct,
resolvable previous generation status path with a terminal receipt and a
quiescent old process group before submitting a successor. Unknown evidence
keeps the successor unstarted. Native focused synthetic lifecycle evidence is
recorded by its owner under
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue02-stage-execution-20260929-native/`.

Platform source changes so far: `scripts/cce_paired_runtime.py` imports only the
trusted selected pipeline gate; `scripts/tests/test_cce_paired_selected_adapter.py`
covers WGS/GATK in package and standalone import modes; `docs/08_WORKFLOW_RUNTIME_INTEGRATION.md`,
`CURRENT_STATE.md`, `TASKS.md` and this handoff record the checkpoint. The
selected gate still checks the exact registered request identity before using
the existing business handler. No WGS/GATK gate executor path was switched.

BS10610 read-only preflight confirmed `server10610`, control root
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`, current release
`20260912-opt-4d3d24e6`, actual backend mount
`20260926-p0-e358aad/backend`, and disabled intake/auto-dispatch gates. The
synthetic test candidate is
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/ue02-stage-executor-gates-20260929`.
The focused RED test on old selected-dispatch code failed as expected in two
cases for importing the unselected gate (`selected-import-red2.log`, SHA-256
`2e268d649617dded1a61e5fde23026f1a4782582af7311a4fca314eb364d7320`). After patching, the final focused GREEN command in that candidate
was `python -m pytest -q scripts/tests/test_cce_paired_selected_adapter.py`,
with `PYTHONPATH` set to the native source and the BS10610 nipttest Python;
result 4 passed in 0.35s. Raw evidence is
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue02-stage-executor-gates-20260929/selected-import-green2.log`
(SHA-256 `fd18a4da724fec169567e0bb4f48b9b6b70de87b21fe3e66c44b6d74cdeab98c`). The candidate module SHA-256 is
`b22696d27dd2297fbd4d21ce14f76f13e181125ff5d7c1dc578e43062c3998f7`;
test SHA-256 is `e9bf75bfd4fb2c18d170833336ff8c8465d885ef8a8a274c99e1a1b70b9f1014`.

Blocker: current GATK gate overwrites a fixed per-stage `.status.json` and
archives only the old request during recovery. WGS also writes a fixed status;
its archived old status lives under `history/<stage>/generation-N/`, outside the
native same-directory binding. Pointing two generations at the same status is
rejected by native; inventing a status path or copying a DB projection would
discard the terminal/worker-quiescence safety gate. The native owner and
platform coordinator need to settle a narrow trusted historical receipt
binding before adapter wiring. Preserve shared business status permissions;
0600 applies to new executor control sidecars only.
Also update the existing paired runtime `_inactive_dispatcher` fence when a
native dispatch becomes selectable: it currently recognizes only the fixed
GATK/WGS legacy worker sidecars. It must recognize the native dispatch/worker
identity or explicitly fail closed before considering a prior writer inactive.

No full suite, service/container test, cloud Job, node200, production check,
batch submit, push, merge or deployment was run for this checkpoint. This
selected-gate source checkpoint is committed in the isolated UE-02 branch;
the overall UE-02 remains open pending the binding interface and coordinator
closeout. Rollback is a scoped source revert; no runtime state changed. The
next owner should resolve the binding contract, connect
thin adapters while preserving WGS `run_stage` and GATK `_execute_stage`, then
run only focused UE-02 acceptance and record exact evidence.

## 2026-09-29 UE-01 stage-execution contract source closeout

Goal: finish only UE-01's platform request marker, pathless identity/snapshot
mapping and one cross-repository synthetic fixture. Worktree/branch:
`C:\Users\11217\.codex\worktrees\gatk-prod-compat\airflow-demo`,
`jiucheng/airflow/UE01-stage-execution-contract`, base `dcd7390`.
The 2026-09-28 blocker entry below is historical and superseded by this result.

BS10610 read-only preflight confirmed `server10610`, control root
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`, current release
`20260912-opt-4d3d24e6`, actual backend `/app` mount from
`20260926-p0-e358aad/backend`, and disabled intake/auto-dispatch gates. The
approved synthetic candidate was
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/ue01-stage-execution-contract-20260928`.
Its older platform module/test copies (SHA-256 `e6ff0363...` / `1df50728...`)
were replaced with the exact current worktree bytes after local backup. Final
candidate SHA-256: `scripts/cce_paired_runtime.py` `b1eedef3f2ca23f57492dcf928b314b16af94ca0e50b930998e706f87715fc3e`,
single fixture `f0601651c2da2b0104b1f6aa985e2002b9938ba669fd9d8cbd160eb4c6a048bf`,
and platform marker module `895955cde9d562e683f45c151b98656869b02d9e319fb514806a1fb41d5eb170`.
Native source was the real BS10610 checkout, commit `254527c573a525f8663ba567666eadf9fe45252e`,
module `src/cce_pipeline/stage_execution.py` SHA-256
`d9f69cdc8eb998b0dc1257f00fb1a21fffcdb1fb086ece415e2c75127c603b40`;
both prior token/SHA-256 regex anchors are now corrected. We did not edit native.

Exact single fixture command, from the candidate directory:

```bash
PYTHONPATH=/mnt/biodevrwbi/33.chenjiucheng/project/wgs-cloud-platform/projects/huawei-cloud-runtime/src \
/sg2/33.chenjiucheng/software/miniforge3/envs/nipttest/bin/python -m pytest -q \
  scripts/tests/test_cce_stage_execution_contract.py::test_current_execution_contract --tb=short
```

The SSH invocation ran from that directory and redirected stdout/stderr to a
task-specific evidence file. The first run after native correction passed (exit
0, `1 passed in 0.45s`):
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue01-stage-execution-20260929-platform/pytest-single.log`,
SHA-256 `718af798eb1450a812074f301573c1f498edd3575a2450f85ee649d7e03c3c72`.
Final static review found that the platform registry mapping accepted a present
but disabled handler, whereas native `resolve_handler_key` rejects `None`,
`False` and empty string. Added assertions within this same fixture: RED exit 1,
`1 failed in 0.10s`, because no `RuntimeError` was raised. A three-line platform
guard now matches the native resolver; final GREEN exit 0, `1 passed in 0.07s`.
Raw logs are in the same evidence directory as `pytest-disabled-red.log`
(SHA-256 `f2e6cab3c818c9b09e6cec72701d1952a36a5935554f21c628c0d70b5ccac0a0`)
and `pytest-final.log`
(SHA-256 `e8c2ebdecc6c68bd31c948de0b0c1dd4c57dd47d093194a6c1d241c65727824d`).
The earlier native regex failures are historical contract failures, not the
RED for this final platform change. `git diff --check` passed. Local pytest,
full suites, backend registration integration, service/container runs, cloud
Jobs, node200 and production were not run or touched: the approved UE-01 gate
requested only this fixture. The WGS/GATK registration call sites were reviewed
statically, not accepted by a running backend. No push, merge, wheel install or
deployment. UE-02 waits for coordinator approval. Rollback of
this source-only change is a scoped commit revert; runtime state is unaffected.

Related deltas to retain when later phases integrate (prior recorded deployment
fingerprints are not a fresh production recheck in this UE-01 task):

| Source and status | UE-01 need | Later handling |
| --- | --- | --- |
| `744cd22`/`03dc8d7` baseline WGS initial/recovery hash and control-root fix | Required baseline; keep request/hash semantics and historical registrations | Preserve through UE-02–06 |
| Production private GATK gate SHA `b3230de8...`, no paired module/manifest | Leave untouched; not a UE-01 consumer | Define trusted resolver/handler boundary at UE-02 before selecting a gate |
| Deployed backend overlays: `9c7fc93` Step4 digest, `e634ca4` Stage4-to-5 fence, WGS phase policy later synced to source by `a85cfb6` | Not in this branch; do not overwrite or bulk copy | Reconcile per consumer in UE-04/05/06 |
| Test-only `5c29d86` and integration worktree's uncommitted P0 paired/inventory/recovery changes | Do not copy the dirty tree for UE-01 | Select exact dependencies in UE-02/03/04/05 |
| Production frontend Resume visibility, separate GATK transfer `a3c177a` and r4 phase `6d11712` candidates | No UI or phase promotion here | Keep separate release decisions; no dirty UI copy |
| Production WGS selector 0.8.8/`57483541`; candidate native 0.8.9/`254527c` | Use real 0.8.9 source for this fixture only | UE-06 checks wheel/consumer/mount/selector pins; frozen WES bundles do not auto-upgrade |


## 2026-09-28 UE-01 stage-execution contract (in progress; shared fixture blocked)

Goal: implement the approved UE-01 producer/consumer contract in the Airflow
platform only, coordinate with the native owner, run only the exact synthetic
fixture on BS10610, update this handoff/state, and stop before UE-02–06 or any
production deployment. Worktree `C:\Users\11217\.codex\worktrees\gatk-prod-compat\airflow-demo`,
branch `jiucheng/airflow/UE01-stage-execution-contract`, based on audit docs
commit `dcd7390893e3d4b6e25b7c15d4b1de96dbf231ef`.

Platform implementation adds the request marker before the first new WGS/GATK
stage request hash, keeps existing matching legacy WGS registrations reusable,
leaves immutable GATK prepare unchanged, maps v2 `generation` to native
`stage_generation`, validates trusted pipeline/stage registry keys, and maps
native snapshot state without treating unknown or canceled as authorization to
advance/retry/release. `docs/08_WORKFLOW_RUNTIME_INTEGRATION.md` records canonical
JSON, digest envelope, identity, snapshot, status and deadline boundaries.

Modified/untracked platform files: `backend/app/gatk_runtime_service.py`,
`backend/app/wgs_stage_execution_service.py`, new
`backend/app/stage_execution_contract.py`, `scripts/cce_paired_runtime.py`, new
`scripts/tests/test_cce_stage_execution_contract.py`, and
`docs/08_WORKFLOW_RUNTIME_INTEGRATION.md`. `git diff --check` passed. No platform
test was run locally.

Only authorized runtime fixture command so far (on synthetic candidate
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/ue01-stage-execution-contract-20260928`):

```bash
PYTHONPATH=/mnt/biodevrwbi/33.chenjiucheng/project/wgs-cloud-platform/projects/huawei-cloud-runtime/src \
/sg2/33.chenjiucheng/software/miniforge3/envs/nipttest/bin/python -m pytest -q \
  scripts/tests/test_cce_stage_execution_contract.py::test_current_execution_contract --tb=short
```

First run failed at native `resolve_handler_key("wgs", ...)`: `_TOKEN_RE` used
a raw pattern with a literal `\\Z`. The native owner corrected that one anchor.
The same test node then advanced to `ExecutionRef.from_trusted_registration`
and failed because `_SHA256_RE` still uses a literal `\\Z`, rejecting the
valid 64-character `request_hash`. Current observed native source hash is
`104eb78c6e804f01359f1081c17e567acb508bd308612a30508ef7692cabfbd0`; its token
anchor is corrected but SHA anchor is not. The coordinator has re-dispatched the
native owner to correct the SHA line. This Airflow task must not edit the
separate native checkout. Rerun only this same node after that exact source line
changes; do not mask the native validation in the platform fixture.

Boundary: BS10610 host-level synthetic fixture only. No node200 connection,
test/production container, production database, deployment, data operation,
native checkout edit, or push was performed by this platform task. The user
provided node200 access guidance (`ssh NGS` or cpata SSH key); it does not change
the agreed BS10610 target. Native source remains on its separate owner branch.

Next: wait for a visible native source correction, then rerun the single fixture.
If green, perform final diff review, finish this section and the
task trackers with exact result, then commit only UE-01 Airflow files/docs. If it
still fails, diagnose that failure and again limit reruns to this node. No commit
or completion claim yet. Rollback for the Airflow task is a scoped revert of its
UE-01 commit; no running platform release was changed.

## 2026-09-28 GATK-PROD-COMPAT (no patch)

Goal: assess only whether the recent WGS P0 changes need GATK equivalents. User
explicitly excluded a full GATK/history audit, runtime rerun, native upgrade and
production change. Worktree `C:\Users\11217\.codex\worktrees\gatk-prod-compat\airflow-demo`,
branch `jiucheng/airflow/GATK-PROD-COMPAT-gatk-runtime`, base/HEAD
`744cd22e09127137a55468cad0c9f14760fb6901`; integration comparison was
`744cd22..257931c9b6cb157f7de29c45b0b73a30b0a85dfa`.

| WGS P0 item | Actual recent diff and GATK applicability | Decision |
|---|---|---|
| Request hash / control root | The integration HANDOFF records the earlier paired-validator fix aligning WGS initial/recovery request hashes; that WGS contract is already in the comparison base. The committed delta here normalizes only WGS `control_workdir`. GATK keeps a separate recovery validator. | No port. |
| Initial CREATE deadline / first Master after upload resume | The uncommitted paired-runtime diff now takes the original deadline from native `_master_create_intent`; that shared helper would also serve GATK if paired runtime were loaded. The no-Master upload-resume/prestart branch is explicitly WGS-only. Current production GATK has no paired module or activation manifest. | Common helper unreachable today; no current GATK patch. |
| Step2 successful predecessor receipt | The uncommitted `_inactive_dispatcher` shortcut handles synchronous Step2 terminal status only under `pipeline == 'wgs'`, with registered-request/receipt identity checks. The normal predecessor-receipt contract is unchanged. | No GATK port. |
| Step3 reconnect progress / Master identity | The uncommitted monitor change preserves nested Master/job/namespace/run-label fields only for WGS. `cce_recovery_policy.py` explicitly records GATK's existing 72-hour Step3 timeout. The paired reconnect identity path is not loaded by current production GATK. | No duplicate GATK patch. |
| Step4 old action / old generation | `cce_publish_recovery.py` accepts sealed previous-generation Step4 evidence only for WGS (`pipeline == 'wgs'`). | No GATK port. |
| Step6 dispatcher evidence sync | The uncommitted `_inactive_dispatcher` synchronous-status shortcut includes Step6 only for WGS (`pipeline == 'wgs'`). | Do not transplant. |
| Successful final bulk inventory | The uncommitted workload probe adds namespace bulk inventory, but `_release_registered_writer` enables it only with `bulk_inventory=(pipeline == 'wgs')`. The deployed GATK gate has no paired-runtime binding. | No current GATK patch. |

Read-only production evidence: SSH as `ctapa` through the approved BS96 TCP
jump, using strict host-key checking against the existing node200 IP entry; the
observed t640 ED25519 fingerprint matched the recorded
`SHA256:KKSrhbpZdPlBe7ej63ZaYhvYwWhQpdEnGejD59NGMv4`. The installed GATK gate
SHA256 is `b3230de8fcdba8806a91e247679c38d40ae57cd8b02280276e64f33e6f88ec0f`.
The same private GATK root has no `cce_paired_runtime.py` or
`cce-paired-deployment-v1.json`; its gate source contains no paired-module
reference. Its hash matches the existing 2026-09-16 GATK deployment record and
does **not** match the integration worktree gate SHA256
`9d2585d74aa40d2172d4098c716e14fc349aabcea2b62b294ebefcbf7c68cac7`. The
forced-command wrapper hash is
`0c4fc77ccf3f12c991f418bf03a898287a0c4f3a4e7dfc93e7d647525276940a`; its
resolved entry is `readonly runtime_gate="${config_dir}/gatk_runtime_gate.py"`
followed by `exec "${GATK_PYTHON}" "${runtime_gate}" "$@"`. The latest
recorded successful GATK run is from 2026-09-24 and completed Step3-Step6/finalize;
this is historical evidence, not a fresh live run check.

Commands/effects: inspected only the integration diff and HANDOFF, then read the
GATK gate, paired-module/manifest presence and forced-command entry on t640.
Integration worktree working-tree diffs were inspected only in the specified
paired runtime, publish recovery, inventory and workload files. No tests,
database/cloud query, batch submission, runtime modification, deployment, native
upgrade or push. Direct local SSH to `172.17.61.200` timed out before remote
execution; `ssh -J NGS` reached node005 but timed out forwarding to t640. An
initial strict check using `HostKeyAlias=t640` found no local alias entry; the
same pinned host key was present under the IP, and a strict BS96 TCP jump then
succeeded. A first forced-command read timed out during SSH banner exchange; one
bounded retry succeeded. The initial activation import returned `FileNotFoundError`
because the paired module is absent; a metadata-only read confirmed absence. A
source-text probe hit Python 3.6's default ASCII decode on a non-ASCII comment;
the corrected bytes-only reference check succeeded. A keyscan probe was
incompatible with the server's preferred KEX. No failed probe ran a command on
t640; the successful reads were metadata/source inspection only. The temporary
local SSH forward was stopped.

Conclusion: no GATK patch. Keep the future unified-runtime work in its separate
UE review/release; this compatibility gate does not authorize production rollout.


## 2026-09-27 authorized main/production repair synchronization

User requests Airflow repair code on main and production. Fetch/ls-remote show
both targets at0b35278; clean integration source03dc8d7 is a strict descendant.
Reviewed20 intervening commits:4 code fixes (SSH timeout e307328, Operator schema3
a1c5387, qualified release identity953ff94, paired request validation03dc8d7),
plus tests and their operational documentation. No conflicting or unrelated code.
Existing focused remote results are6,6,7,8 passed respectively; no new code is
introduced by fast-forward, so no redundant runtime tests are run. git diff --check
and exact code-tree identity are the integration checks, not a new runtime claim.

Authorized operation:fast-forward local main and jiucheng/release/production,
then `git push --atomic origin main jiucheng/release/production`; verify both remote
SHAs equal the integration head. Never force-push. Keep source/worktree and dirty
primary workspace unchanged. This task does not redeploy BS96, restart services,
touch runtime data or resubmit the running batch. If a future rollback is needed,
use a scoped revert; do not rewind shared branches or imply Git rollback changes
the deployed module. Remote command output is the push completion authority.


## 2026-09-27 approved paired-validator repair deployed, Step1 resumed

Only scripts/cce_paired_runtime.py implementation changed: initial WGS digest omits
post-hash version envelope, recovery keeps the existing frozen-body version, GATK
unchanged; control_workdir must equal approved runtime root/analysis/attempt.
Public request equality, digest, v2 entry and predecessor protections retained.
Added one producer-derived synthetic test file, updated docs08/state/tasks/server.

BS10610/server10610 actual backend image8491604ee01d and source20260926-p0-e358aad
verified. Disposable cached-image test: network none, read-only root, uid6708:520,
candidate source read-only and scoped evidence writable; no DB/credentials/business
mounts. Final `python -m pytest -q -p no:cacheprovider
scripts/tests/test_paired_request_contract.py` passed8 in0.73s. Evidence:
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/20260927-paired-request-contract/evidence`.
RED reproduced original mismatch, then recovery-specific regression before final
GREEN. Full suites/canaries not run per user's minimum-test scope. Setup issues:
initial tar referenced nonexistent context module (exit1, rebuilt source archive);
first pytest invocation lacked writable TMPDIR (exit1, corrected to /evidence).
Host reports unsupported swap accounting, memory limit still enabled.

Production BS96/server96 live backendd898d622b254 /84510df plus953ff94 overlays
unchanged. Unfiltered runs API read timed out25s; bounded active-status reads returned
no running/queued/publishing/downloading runs, node200 had no gate workers. No DB
direct mutation. Node200/t640 ctapa6801:520 actual old module matched repository
except these two checks. Module SHA7b12e143d2aa48c8c1db3a48cb141f263638d7fa9ab48a9d2990082c1ce49bfc;
policy paired-writers-088-441d5e7.json SHAfc1c6379379fec1b59cfa8665811e2b257ca53b2a460292092db5bee21d8c9e6.
Private control file modes0600 preserved; no project/output permission change.
Rollback copies and deployed.json under
`/sg2/50.ctapa/project/HWcloud/airflow-wgs/runtime/repair-backups/paired-request-20260927`.
Restore module and policy together only in an idle window. Native0.8.8, WGS441d5e7,
r3 profile, bootstrap, scanner flags, images and all services unchanged. Deployment
first shell wrapper did not execute (readback old hashes); copy-then-run executed
once and validated existing request without rewriting it.

Normal POST resume-stage for WGS_20260927_141652_146B51, attempt1, step1_upload,
idempotency key paired-request-contract-fix-20260927-146B51 returned queued;
action resume_aa5a2aca4e8ad16435f6752b, generation2,
execution wse_7a08827725c2f24671d54622. At14:53Z node receipt running, worker72768;
8 files/482168174652 bytes planned, initial byte count0. At14:54:50Z readback:
1688899418 bytes uploaded,335061972 B/s, healthy running generation2. Backend API
running/error null, recovery DagRun suffix resume_aa5a2aca4e8ad16435f6752b; worker
log contains advancing obsutil progress. Upload recovery confirmed. No manual
status rewrite, new attempt, prepare, data deletion or changes to pending.
Later workflow stages and entire analysis completion not verified. Next: let the
existing DAG continue; do not resubmit this already-running recovery action.

## 2026-09-27 new run Step1 rejection: paired request contract mismatch

User reports upload failure and requests repair. BS96/server96 backendd898d622b254
unchanged. New runWGS_20260927_141652_146B51 attempt1 now failed after the user
approved config/execution;4 selected samples. Preparation succeeded. Worker log
74ce1286c69cbeaf53df shows cce_paired_runtime._registered_request rejected before
transfer Popen: `registered recovery request changed or hash differs`.
No evidence of an OBS transfer error; native Step1 was not launched by this worker.

Read-only node200 calculation confirms backend request hash11e1222e matches when
orchestration_contract_version is excluded along with execution/predecessor envelope
fields. Backend computes hash first, then adds version2; paired consumer erroneously
includes version2. Existing synthetic fixtures calculate hash with the consumer and
miss this producer/consumer mismatch. Second wrong assertion requires control_workdir
== request.parent, while actual contract uses runtime/runs/<id>/attempt-1 and requests
live under runtime/runner-requests/<id>/attempt-1. Deployed gate _workdir matches the
approved RUNTIME_RUN_ROOT/<id>/attempt-1. Do not edit the immutable request/hash to
hide either mismatch or weaken identity fences.

User approved bounded repair: only paired request validation changes,
producer-derived synthetic regression on BS10610, then deploy exact platform module
with updated deployment pin and use same-attempt resume-stage Step1. No WGS/native
source release, dependency install or cloud cleanup. BS10610 reachable/server10610;
No retry submitted during diagnosis. Authorization includes exact node200 module
and platform policy pin update, then one same-attempt Step1 resume-stage action.
Preserve all project/raw/result/pending/request evidence and all other releases.

## 2026-09-27 failed submit deleted and original sampleinfo resubmitted

User explicitly requested deletion/recreation instead of one-record release rebind.
Verified source hash unchanged0a8cba37/4 rows and exact final project absent;
old4 DagRuns failed with no active tasks, no committed CCE execution. Backed up
database rows and Airflow run/task payloads privately at backend-visible
`/data/wgs-runtime/repair-backups/submit-replacement-20260927-56DC81` (host equivalent
`/sg2/50.ctapa/project/HWcloud/airflow-wgs/runtime/repair-backups/submit-replacement-20260927-56DC81`).
Scoped transaction deleted only old AnalysisRunWGS_20260927_090701_56DC81 and
FK-owned records:4 samples,4 run_attempts,11 run_actions,7 run_stage_state,
7 wgs_stage_execution,1 execution_dispatch,1 input_snapshot. Kept4 audit rows
and added deletion audit. All3 pending ledger table digests exactly unchanged.
Normal Airflow API deleted only its -a1/-a2/-a3/-a4 terminal DagRuns. Original
sampleinfo, offline project/raw/output paths, request receipts and logs untouched.
Snapshots exist, but restoration is manual; no automatic rollback promise.

Normal POST /api/wgs/runs used original project/platform/batch/source, omitted
inactive optional algorithm overrides. Created WGS_20260927_141652_146B51-a1,
batch20260919A-test/currentwgs-4.2.2-441d5e7. Fresh GET verifies old404, newrunning/
config_review, source SHA unchanged/4 rows, no error and execution approval null.
prepare_wgs_sampleinfo and wait_prepare_wgs_sampleinfo both success; waits at
wait_wgs_config_approval. No configuration or final execution approval granted.
User completes step2 review then step3 if desired; no need to submit again.

Commands: bounded replace-submit.py through backend container exited0; API/task
readback exited0. Local helper D:/pipeline/task-artifacts/wgs-088-bs96-20260927/
replace-submit.py is not repository code or an authorization for reuse. No new
tests, deployment, workflow source changes or unrelated database mutation.
Repository changes are CURRENT_STATE/TASKS/HANDOFF documentation only.

## 2026-09-27 user authorizes replacing the failed submit

Latest user supersedes rebind proposal: delete this submit and resubmit sampleinfo.
Exact online target: AnalysisRun WGS_20260927_090701_56DC81 / 20260919A-test,
attempt4 failed, 4 terminal failed bio_wgs DagRuns (-a1 through -a4). Delete only
this analysis row and its FK-owned preparation/sample records, plus those exact
Airflow runs after private backup. Preserve independent audit rows and all raw
runtime/request/log files. No public run-delete API exists; scoped transactional
database deletion is required by this explicit deletion request.
Protected: original hanjj sampleinfo (SHA0a8cba37,4 rows), FASTQ, pending database
and files, other analyses, all offline results. Exact final project path is absent.
No cloud execution was committed; no transfers/workloads/pending-operation links
exist for the target. Source/config and DB/Airflow snapshots must be saved privately
before deletion; no claim of automatic rollback. New POST /api/wgs/runs uses same
project/platform/batch/source and current441d5e7/native0.8.8. Stop at manual review;
do not grant final execution approval. No broad tests or service restart required.

## 2026-09-27 original submit recovery preflight (awaiting scoped binding approval)

User asks to fix the previously failed submit. Live API identifies only
WGS_20260927_090701_56DC81 / 20260919A-test, failed attempt4, still frozen to
wgs-4.2.2-d38322e-permissions/native0.8.7. Current catalog is441d5e7/native0.8.8.
BS96 hostname/current/mounts match latest deployment; execution dispatch remains
preparing, committed_at null, execution approval null. ctapa read-only stat confirms
the exact final WGS_20260919A-test_T7Hg38V4.2.2 project is absent (expected exit1).
Resume implementation deliberately preserves CCE release binding; it cannot adopt
the corrected source through normal Resume alone. No rebind API is present.
Requested explicit authorization for one-record version-binding repair with old
params backup/audit, then normal preparation Resume; final execution approval stays
with user. No database update, API mutation, data removal or retry done yet.
Do not reuse historical one-off repair scripts as authorization. No new tests.

## 2026-09-27 WGS441d5e7 / native0.8.8 production deployment completed

Goal: consume designated WGS owner's external-CLI fix and matched genuine release,
update BS96 without retrying analysis. Official publication PASS/state_verified,
receipt43d88c; node200 ctapa private0.8.8 bound with new prepare3e5a6e20/profile12b25bf6
and paired policy. Actual deployed gate validation, profile digest and paired
selection passed. Normal catalog API registered/CAS-activatedwgs-4.2.2-441d5e7.

Production server96 admission window restored via exact `restore.json`; complete
env/image/mount comparison passed14:02:18Z, backendd898d622b254/scanner2fe75b327b2b,
all10 other container IDs unchanged. Nginx check/reload and production-address
gateway/API/DB health ok. A loopback gateway probe returned403; actual documented
production address returned200, no security config changed. Publisher retained
Job Complete/receipt evidence and removed only its exact temporary Job/ConfigMap.

Changed repository files: CURRENT_STATE.md, TASKS.md, HANDOFF.md, SERVER_INFO.md,
docs/releases/2026-09-27-wgs441d5e7-088-bs96.md. Local task helpers live outside Git
under D:/pipeline/task-artifacts/wgs-088-bs96-20260927. Executed bind.py,
verify-binding.py, activate.py, compose restore, readback.py; all exit0. Native9
and WGS6 existing focused checks reused; no extra tests, build, workflow submit,
retry, data deletion or pending mutation. This is deployment acceptance only.

Source branch jiucheng/test/wgs-local-main-sync-20260917; this turn only deployment
documentation changes, no platform product code. No push in this turn. Failed
historical attempt4 not retried or rebound; user controls next submission.
Rollback requires coordinated SFS/profile/catalog/node restoration in idle window,
not a lone current-pointer change. Exact retained backups and pins in release note.

## 2026-09-27 user authorizes441d5e7 publication and BS96 activation

User confirmed continuing new WGS source441d5e7/profile-r3/official receipt
publication and BS96 registration, after source completion by the WGS owner.
Scope includes read-only production idle/count checks, bounded admission freeze,
matching node200 ctapa runtime/prepare/paired pins, normal catalog registration
and activation, then exact setting restoration. No business retry, database-row
repair, batch/sample/pending/data deletion, new cloud tests or image rebuild.
WGS owner prepares and publishes only after explicit OPEN notification; this
thread owns platform binding and window. Existing immutable releases are retained.
Current BS96 mounts/IDs still match recorded953ff94 overlay and84510df baseline.
Record actual idle result before any freeze or shared SFS change. Rollback must
keep source/profile/catalog/runtime coherent and never touch analysis data.

## 2026-09-27 authorized 0.8.8 installation and consumer update (in progress)

Final native interface delivered417de597fe3e83cc42160cf14102ad78db789bf8,
sameversion0.8.8 wheel45c99c0c installed offline/no-deps on node005. Actual
runtime-info JSON confirms source, package path andbuild38cc11db. Bootstrap
hash unchanged. Nativeowner9 focused tests reused, not rerun. WGSowner is actively
implementing the actual-CLI consumer on its designated branch. Platform has no
hardcoded0.8.7 restriction; avoid needless backend/DAG edits. Production activation
awaits WGS source/profile/receipt and matching deployed runtime selection.
Read-only comparison of production private0.8.7 cce_batch_runtime.py and
cce_writer_guard.py with installed0.8.8 confirms identical content excluding
CRLF (`diff --strip-trailing-cr -q`); raw hashes still differ and may not be reused
as deployment pins. No runtime/guard logic change was found in those two files.

User supplied the exact cce_pipeline-0.8.8 wheel and authorized installation in
nipttest, followed by platform and WGS repository updates. SHA256 verified on
node005:33cb78f664ce562cdaae7f1334a891cba132a2ec4ba07d66bf33c107d61aaa06;
owner delivery source095f1e937d8cb5815c62435f4875a88921d7afe3. Delivery explicitly
excludes external-CLI consumer compatibility; do not report that as completed.
Use writable node005 nipttest, not WGS production environment. Retain exact
installed package/dist-info/launcher rollback before offline no-dependency install.
BS96 read-only preflight matches recorded mounts and three consumer IDs; existing
production private0.8.7 runtime stays pinned until a matched release is ready.
WGS source owner resumes minimum dev_CJC_4.2.2_cloud consumer work. No business
retry, rule change, data deletion, broad tests or unrelated image rebuild.

Installation completed: node005 offline/no-deps pip returned success; CLI/import
version0.8.8 and SOURCE_COMMIT095f1e9 confirmed. Backup archiveSHAd3748140 in
the exact evidence root recorded in docs/releases/2026-09-27-nipttest-088.md.
BootstrapSHAa16ecf15 unchanged, installed ownership remainschenjc:bioinfo.
Platform catalog version is already generic; no backend/DAG version patch needed.
Native runtime/guard assets differ from production pins: owner asked to explain
before activation. No pins were changed. WGSowner confirms actual wheel lacks
runtime-info; nativeowner now supplies the minimal interface while WGSowner
implements its consumer, without duplicate implementation here.

Read-only inspection correction: first asset comparison used nonexistent
cce_runtime.py (exit1/FileNotFoundError); inspected declared policy and used its
actual cce_batch_runtime.py path successfully. No runtime command was retried.

## 2026-09-27 owner correction: hand off to WGS-cloud-plugins

User explicitly identifies0.8.8 owner as019f9d79-be3f-7701-af33-3595d72bbfac
(WGS-cloud-plugins) and asks that agent to continue. Verified its active approved
0.8.8 simplified-release implementation onjiucheng/cce-release-simple-088.
Sent full handoff: actualsiblingPython failure, privateCLI layout, completed
platform registration/permissions repair, failedattempt4 state, minimum external
CLI introspection plus WGSconsumer scope, evidencepaths and production boundaries.
019f8355 notified to stop this item (confirmed no edits/install/publication);
WGSowner01a09149 notified to avoid duplicate work and coordinate under designated
owner. This thread does not implement0.8.8 in parallel. No production actions.

## 2026-09-27 latest decision: external-runtime compatibility belongs to0.8.8

User explicitly says cce-pipeline0.8.8 is underdevelopment and externalcce support
can be added there. Supersedes proposed0.8.7 installation repair. Sent scope to
existingnativeowner019f8355-2b77-7413-9553-6670c35a1a2f andWGSowner
01a09149-ad9d-7e92-b98a-16d9cae075e2: agree minimal actual-CLI version/source/runtime
introspection contract; WGSdev_CJC_4.2.2_cloud consumes it without assuming sibling
Python orWGSenv installation. Preserve provenance/exactapprovedpaths, no secrets,
support boundarymust explicitly handle0.8.8 rather than bypass versionchecks.
No production0.8.8 upgrade/publication or additionalretry authorized by this
development decision. Current productionregistration fix953ff94 remainsdeployed,
permissionsr3active; originalattempt4failed before formalprojectpublication.
Native/WGSownersreport exactplan andminimaltests; do not duplicate their work.

## 2026-09-27 platform binding repaired; user redirects next WGS fix

Source953ff94 minimal identity compatibility deployed as2 readonly backend modules,
catalog-only overlays on scanner/observer. Officialfe530b receipt registered and
CASactivated; ctapa config mappingc9cc826a... installed, oldmaps retained. Exact
originalservice environments restored; health200. Originalrun retained-history
binding updated with privateparamsbackup andRunAction; resumeAPIcreatedattempt4.
Sampleinfo andconfigurationall/default passed. Nativeprepare then exited2:
`cce-pipeline Python is unavailable: .../runtime/tools/cce-pipeline/0.8.7/bin/python`.
Permission check passed. Final batch directory was explicitly checked ABSENT;
staging nativeprepare was removed by its own exception handling, not agentcleanup.

Live private installation hasbin/cce-pipeline launcher using nipttest shebang and
prefix/site-packages insertion, wheel0.8.7/operator.yaml; no siblingpython. WGS
d38322e _validate_production_package assumes siblingpython and imports below CLI
prefix even for configured externalCLI. User now explicitly requires fixingthis
assumption: cannot writeWGS productionenv, oftendeploys cce in test/externalenv.
Stop proposedvenv/reinstall route; no installation done. WGSowneraskedminimal
externalCLI/interpreter compatible design, nativeownerexistingintrospectionAPI.
No version/provenance bypass, no more run retries, nofinalexecutionapproval.
Currentrunattempt4failed,3 serviceshealthy,currentpermissionsreleaseactive.
Next work is ownerWGS sourcefix ondev_CJC_4.2.2_cloud and necessary sourcepublication,
not further permission changes. Await owners' exactboundedimplementation proposal.

## 2026-09-27 user approves platform registration and original WGS repair

User: update platform registration, then fix WGS workflow. Scope remains exact
permission-only r3 release and failed WGS_20260927_090701_56DC81. Minimal catalog
and runtime identity qualifier compatibility developed; no workflow algorithm or
native changes. BS10610 isolated cached image/no network synthetic reproduction
2 failures5passes before,7passes after. No broad tests. First pytest used ephemeral
container default /tmp; corrected green run to explicit mounted task evidence.
Registration retains hashes/receipt/conflict checks; old entry not overwritten.
Production deployment authorized for these consumer modules; preserve old mounts,
flags, audit history, exact before snapshot before bounded run registration change.
Only prepare retry/all-default previously approved configuration; final execution
approval remains with user. No data deletion or successful-analysis rerun.

## 2026-09-27 authorized permission publication completed; identity blocker

Scope: user explicitly authorized139 manifest files and prior publisher metadata.
Publisher owner verified beforeUID10001/GID520 matched staging;138 ordinaryfiles
0644->0664 andmonitor0755->0775. All139 postchecks passed,14 existing parent
dirs unchanged, publisher metadata35files0664/6dirs2775/group520. No ACL mutation;
ACL xattr unsupported, so no ACL backup promise. Same content payload hashes.
Persistent before/after POSIX records localD:/pipeline/task-artifacts/
wgs-422-release-20260927 and remoteWGS_test/cce-evidence task root:
beforeSHA5f4cc57380c8be81e2363dc50b59bd71f063369ece5f3963e9c52114f4d3f7c7,
afterSHA73fe878ee2bdd2907294d08fd2cc7f7ee94c9e0fb480af1b68298db147224e6e.
No business batch, FASTQ, result, pending deletion or modification.

BS96 server96/source20260927-p0-local-84510df verified;11:38:26Z idleall0.
Private freeze/restore Compose both validated. Recreated only backend/scanner,
backendexecutionfalse, bothautodispatchfalse;11:39:15Z idleall0 confirmed.
Publisher officialpublish succeeded: asset20260927.3-wgs422-permissions,
profile revisionr3/SHAdaad51fc..., receiptfe530b2022a536e0a106d90f1d49b233051016ad5e8d066e46a9162c4614f31d,
PASS/state_verified=true. Localregistration-permissions.json preserves genuine
receipt. Owner reports both reader Jobs/ConfigMaps and formal asset Job/ConfigMap
precisely cleaned after evidence retention. No new tests/nativeinstall/imagebuild.

Audit correction: previous claim newcatalogID could use-permissions was incomplete.
Livebackend RELEASE_ID_RE onlyaccepts wgs-X.Y.Z-7hex; _validate_release alsochecks
lastsegment against sourcecommit. register model calls this validator. Therefore
heldctapa binding/catalog activation and asked user for minimum compatibility
scope. Never fabricate receipt or overwriteoldentry. User approval pending.
Original attempt3 remains failed, noDB mutation/retry/executionapproval this turn.

11:45Z restored privatecontrol/restore.json (not historic scanner config).
nginx -t then graceful reload succeeded. Gateway direct --noproxy health200;
firstproxy-routed curl returned403, not application health failure. Initialhost
python command unavailable(exit127), usedpython3 for boundedflag verification.
Unusedactivate.py/bind_node.py remain taskhelpers only, not run. No source edits
this turn; platform docs updated. Native/WGS payloadversion remain0.8.7/V4.2.2.
Next: obtain ID-compatibility scope; minimalremote regression andconsumer audit,
then shortwindow forregistration/ctapabinding, preservedhistoryprepare recovery.
Rollback: originalPOSIXrecord retained; do not blindly roll back sharedpermissions
while consumers active. Oldprofile/catalog/ctapamappings were never changed.

## 2026-09-27 — user authorizes139 listed file permission correction

Latest user says the139 files may have permissions corrected directly, and only
if that is cumbersome considers native0.8.7 changes. Prefer existing standard
publication; do not develop/reinstall native preemptively. Keep r3, identical
payload bytes and current owner where verified, no business batches/FASTQ/results.
Publisher assigned one necessary reader/metadata-backup preflight for exact139
files and .cce-assets, including uid/gid/mode/ACL, without broad business backup.
If staged UID10001 differs from existing target owners, report rather than
silently treat chown as authorized permission-only work. Shared apply remains
held pending platform freeze/idle notification. No new P0 tests or image build.

## 2026-09-27 — native owner confirms no supported profile-only publication

Read-only native owner audit: accepted0.8.7 main8323567ce2e7 release.py binding
requires both pipeline and resource update-only components; documented release
publish runs assets validate/apply/status before genuine receipt. Profile CLI only
diff/validate; register only consumes a receipt. Empty-manifest behavior is not a
documented/tested contract and must not be used as a workaround. Existing parent
dirs remain untouched; manifest files are replaced with normalized staging modes.
No native edits, tests or publication performed. User has been asked to approve
the exact130 pipeline+9resource file side effects in PERMISSION_SCOPE.md; until
then no production freeze, shared writes, new receipt or recovery retry.

## 2026-09-27 — corrected precise publication side effects, still no writes

Read owner report D:/pipeline/task-artifacts/wgs-422-release-20260927/PERMISSION_SCOPE.md
and its permission-pipeline-files.tsv companion. Correct prior parent warning:
native _ensure_shared_parent538-552 skips existing dirs; only missing dirs created
2775/group520. Update nevertheless replaces130 pipeline files (129 regular0664,
one script0775) and9 resource files (2 control,6 reference,1 index;0664), group520,
stage UID10001. Content hashes unchanged; this is not merely metadata permissions.
Current lstat/ACL not observed (no existing SFS reader), so old contract0755/0644
is expectation only. Staging backup removed on successful apply; final validation
later, so no guaranteed durable permission rollback. Any expanded publication
must first capture exact-target metadata/backup with approved reader, not assume
existing backup. No new reader Job, data mutation, freeze or tests performed.
Native owner checking only existing profile-only capability; do not develop one.

## 2026-09-27 — publication preflight stopped before freeze: resource mode side effect

BS96 verified server96, actual backend365beab02248 and scanner87a7f1876d42 mounts
unchanged; read-only check11:15:55Z returned businessactive0,drafts0,leases0,
Airflowrunning/queued0/tasks0. No admission freeze or service restart performed.
WGS publisher then identified native stage normalization plus update replacement
would also change the9 resource component files and selected parents, even with
unchanged payload hashes. User approval followed metadata-only explanation and
does not cover this additional reference-resource permission migration. Hold all
shared writes. Publisher asked for exact affected paths/modes (including pipeline);
native owner asked read-only whether an existing profile-only receipt route exists.
No new runtime feature, ad-hoc receipt, production chmod or broad test authorized.
Report exact scope and obtain direction if existing runtime cannot stay in bounds.

## 2026-09-27 — user approved r3 permission publication and bounded recovery

After the combined publication/recovery question and explanation of .cce-assets,
user replies consent. Authorized scope: publisher-owned metadata normalization,
same revisionr3 with2775/0664/0775, official new receipt/registry binding, retained
history recovery of WGS_20260927_090701_56DC81 only (pre-execution failed attempt3).
No data deletion, business-tree recursive chmod, WGS prepare/algorithm/image
change or automatic final execution approval. Production window touches only
backend WGS admission and backend/scanner auto-dispatch, records exact rollback,
and restores previous flags. Fresh read-only business/Airflow/lease checks precede
freezing and publication. Any exact run registration correction must preserve
old attempt evidence and record before/after/audit; no other batch/DB mutation.
Original WGS publisher owns shared release, platform owns BS96/ctapa binding.

## 2026-09-27 — latest user retains r3; r4 superseded before publication

Publisher follow-up: r3 candidate now at
D:/pipeline/task-artifacts/wgs-422-release-20260927/wgs-4.2.2-r3-permissions-candidate.yaml,
SHAdaad51fcbaaa35352e7504a1943890ab75f5285f9677db17f7cbc5ec034e282a (local check).
Static consumer audit confirms uniqueness byrelease_id, not profile_id/revision;
new catalog identity with same revisionr3 and separately frozen profile path can
retain old hashes/history. Proposed asset20260927.3-wgs422-permissions and catalog
wgs-4.2.2-d38322e-permissions are not published/registered. Permission scope and
original-run rebinding still await user decision. Source/receipt validation stays.

User replied to publication-boundary question: stillr3, do not updater4. This is
a revision constraint, not explicit consent to metadata normalization or run
rebinding. Sent correction to WGS publisher: retainr3, only2775/0664/0775;
verify official same-revision receipt path without overwriting catalog identity
or historical frozen config. No production publication/mutation authorized by
this record. Earlier r4 candidate remains an unpromoted task artifact only.

## 2026-09-27 — r4 permission candidate prepared; awaiting publication boundaries

WGS publisher's exact candidate:
D:/pipeline/task-artifacts/wgs-422-release-20260927/wgs-4.2.2-r4.yaml,
SHA4eea1a03b1aded68e5843d70e9cc2cd016af949ce60e24558f28cd4ab38e8d67.
Owner reports diff limited to revisionr3->r4 and three user-selected permission
values2775/0664/0775, retainingbioinfo/520. Local hash independently confirmed.
Owner found native assets/release_runtime.py:731 normalizes the entire publisher
.cce-assets state tree; line639 handles staging and selected parent chmod also
exists. Asked user whether standard publisher-owned metadata normalization is
allowed, excluding business batches/FASTQ/results/reference trees. Separate
question asks exact failed run retained-history rebinding versus user resubmit.
Both unresolved; no production freeze, publication, catalog/DB mutation or retry
this turn. No redundant tests: only static candidate field/hash inspection.
Next: obtain these scope decisions, fresh idle window, publisher official receipt,
normal catalog/ctapa binding and exact flag restoration. r3 remains rollback/current.
No WGS prepare or platform product source change is needed for this chosen fix.

## 2026-09-27 — user chooses2775/0664/0775; minimal profile publication coordination

Current authorization: use WGS prepare'sbioinfo/520,2775/0664/0775. This supersedes
the prior proposed source fix; no WGS prepare behavior change, recursive chmod,
old-result migration or secret widening. Target remains production BS96/server96,
control/data/airflow-WGS; live backend365beab02248 consumes20260927-p0-local-84510df.
Current release d38322e/r3; original runfailed/attempt3, no committed execution.
Original WGS-pipeline publisher (01a09149-ad9d-7e92-b98a-16d9cae075e2) requested
to stage profile/receipt only and hold shared writes until explicit idle window.
Platform owns bounded admission freeze/restoration and registry/ctapa mappings.
No image/native/package/version bump or repeated P0 tests are authorized here.
Ordinary Resume retains recorded CCE release; asked user whether exact run may
be rebound for a new attempt with retained history, or user will submit anew.
Do not overwrite catalog identity/frozen r3 or mutate DB without that decision.

## 2026-09-27 — Operator fix deployed and retried; separate WGS release blocker

Sourcea1c5387 committed on jiucheng/test/wgs-local-main-sync-20260917 (not pushed).
Gate atomic deployment succeeded asctapa; exact before/after SHA, preserved mode,
backup and minimal test command recorded in dated Operator release note. No
containers restarted, native helper/policies unchanged. Standard resume accepted
attempt3. Sampleinfo succeeded; reused prior user-approved all/default through
approve-wgs-config only. Execution approval was not requested or granted.

Live17:45:58 CST attempt3 prepare_wgs_analysis failed with native exit2. Private
prepare log reports WGS CCE permissions must be bioinfo/520 with2775/0664/0775.
Read-only source inspection locates hardcoded expected_permissions at immutable
WGS release prepare/cce_pipeline_adapter.py:338-348. Registered r3 profile has
bioinfo/520 and0755/0644/0755; SHA5e83e5ed63300fd26de51e84dea137fdd3f3413f3bb15651862563719335aad6
is unchanged and matches release registration. Attempt3 frozen Operator exists,
schema3 without paths, proving original compatibility failure was passed.
Exact project directory remains absent. API failed/attempt3, execution approval
unset; no actual cloud jobs, workflow results, patient data or pending modified.

Next: coordinate correction in WGS dev_CJC_4.2.2_cloud and matching audited release,
not an in-place immutable patch, profile permission downgrade or broad chmod.
This extends beyond the single platform gate fix; ask user before source/release
changes. No more retries while the native/profile contract conflicts. Local rg
with a wildcard path failed once; corrected to directory plus -g filter.

## 2026-09-27 — Operator schema3 correction authorized and verified

User explicitly requests fix, commit and retry. Scope: shared Operator transform
in wgs_runtime_gate.py, focused fixtures and runtime/state docs. Native0.8.7
schema3 may lack legacy paths; do not fabricate fields or disable frozen checks.
BS10610 isolated no-network cached backend image:6 passed,77 deselected (0.33s).
Initial red fixtures reproduced both prepare and Step7 mismatch. Harness first
lacked unchanged cce_paired_runtime.py; after supplying it the existing test
loader needed sys.modules registration. Corrected that fixture, all6 passed.
No full suite or business-data tests, per requested minimal scope.

Production preflight: ssh BS96/server96, control/data/airflow-WGS, actual backend
mount releases/20260927-p0-local-84510df/backend (current symlink is historical).
node200 via BS with id_rsa_ctapa: t640,ctapa6801/bioinfo520; gate ownerctapa mode600,
baseline SHA60ef3d78497347565d061491abf19176fd8a8dd9012685b7ead0ed841e53796e.
Paired policy does not pin gate; runtime/helper/policy files remain unchanged.
One read-only inspect used an incorrect container name and failed; resolved via
previously verified backend ID365beab02248, actual nameairflow-wgs-backend-1.
Exact test project absent and original run failed/attempt2. Plan: atomic gate
replacement with exact backup and preserved mode/owner; no service restart,
credential update or business-output permission changes. Standard API resume
creates next attempt; retry configuration preparation only with the previously
approved values, preserving final user execution approval. No direct DB edits.
Rollback: restore exact backup only when no gate operation is in flight.

## 2026-09-27 — second-step prepare failure diagnosed; no mutation

User reports step2 error in the same run, attempt2. This is UI configuration
prepare_wgs_analysis, not native step2_master. User config approval09:27:27Z;
SSH failures triggered the corrected2/3 and3/3 reconnect at17:27:44/17:27:59 CST.
Third invocation reached node200 and failed17:28:14, exit1 at installed
wgs_runtime_gate.py:943, _release_operator_config: paths are invalid.
ctapa read-only check using id_rsa_ctapa confirms active Operator0.8.7 schema3
contains identity/hosts/kubernetes/obs/huawei_cloud and NO paths. Native
validate_cce_operator_config succeeds. Platform gate wrongly requires legacy
paths/repository_root. Same assumption exists in Step7 frozen config comparison
(source lines2029-2032). Existing fixture only covers legacy paths-based config.
Follow-up must align the prepare-time transformation and Step7 comparison with
schema3 while retaining approved release/config identity and historical support;
do not merely add a dummy paths object or disable validation. Native version,
workflow rules, keys and permissions need no change for this diagnosed mismatch.
No retry, DB edit, file permission change or runtime modification performed.
Exact stage executionwse_07e4e997b769602deb837130, generation1/retry0; sidecarfailed.
Diagnostics: scoped API/task log/sidecar reads, installed gate code and sanitized
Operator field names plus native schema validation. No clinical payload emitted.

## 2026-09-27 — SSH timeout fix deployed and original prepare recovered

Completed planned correction with sourcee307328; affected BS10610 regression6/6
after observing original2-line fixture fail. Exact change is one trailer pattern,
not broader runtime/retry behavior. Production three Airflow DAG binds switched,
other9 services unchanged, hashes match and import errors[]. Existing run resumed
once through authenticated API; attempt2 prepare_sampleinfo succeeded17:26:59 CST
and phaseconfig_review. No direct database edit, forceall, new batch, or approval.
User next reviews configuration in UI, then uses normal confirmation steps.
Exact paths, commands, hashes, IDs and idle-only rollback are recorded in
docs/releases/2026-09-27-ssh-banner-bs96.md. Updated DAG/test/spec and state docs.
No full suite or unrelated tests, per user scope. No remaining blocker for this
prepare failure; network delay's underlying cause was not established.

## 2026-09-27 — SSH timeout correction authorized; deployment planned

User says continue after proposed narrow fix and original-run recovery.
Scope: bio_wgs.py SSH trailer classification, affected retry fixture and docs.
BS10610 isolated no-network cached Airflow image reproduced1/6 failure on the
new two-line fixture; after minimal classifier fix all6 tests pass. No clinical
test/network/database mounted. Output/stdout/unknown-error refusal preserved.
Production preflight: server96, existing P0 Airflow mounts, no active DAG/task.
Plan: immutable single DAG file, change only its bind on Airflow API/scheduler/
worker after config validation, preserve all other services/flags/mounts; retain
exact rollback. Recover only WGS_20260927_090701_56DC81 through normal API;
three-stage resume creates next attempt for sampleinfo and retains approval gates.
Do not auto-approve configuration or analysis. No new batch, no data deletion.

## 2026-09-27 — sampleinfo preparation SSH diagnosis (read-only)

Follow-up check requested by user: actual worker SSH configuration is ctapa to
172.17.61.200:22, ConnectTimeout10, BatchModeyes. Authentication-only ssh -N -T
with the existing configured identity succeeded using publickey; no remote
command was requested. Exact attempt request directory contains only
prepare_sampleinfo.json, no status/log sidecars. Corresponding control workdir
and expected WGS_20260919A-test_T7Hg38V4.2.2 project directory are absent.
Therefore no observed preparation outputs or receipts exist for this attempt.
No credentials, permissions, code, database, Airflow state or tasks were changed.
Local rg wildcard-path invocation failed with Windows path syntax; corrected to
rg scripts -g filename-pattern. No remote failure/retry occurred in this check.

User reported production run WGS_20260927_090701_56DC81, batch20260919A-test.
Read-only diagnosis only; no retry, deployment, database or workflow changes.
Airflow worker task prepare_wgs_sampleinfo/attempt=1.log records SSH exit255:
Connection timed out during banner exchange, followed by
Connection to 172.17.61.200 port 22 timed out. One invocation at17:07:09 CST;
unclassified failure at17:07:19, no terminal receipt visible after30s, task failed
17:07:50. This is before authenticated remote execution, not a biological rule
or cloud-data missing-file error. Cause of node200 banner delay is not established.
Live worker-to-node200 TCP banner probe subsequently received OpenSSH_9.3 in3.89s;
this proves current banner reachability, not authentication or workflow success.
Deployed bio_wgs.py classifier accepts first line but rejects the second line:
all stderr lines must match, so intended5s/10s reconnect path was not entered.
Existing test fixture covers only the single-line banner error. Proposed narrow
follow-up: classify exact known pre-auth timeout trailer and add two-line fixture,
retain refusal for ambiguous post-execution errors. No implementation authorized
or performed this turn. Do not blindly rerun or clear Airflow tasks.
Host/mounts unchanged: server96, worker/backend releases/20260927-p0-local-84510df.
Protected runtime traversal encountered Permission denied on unrelated
ops/rollback-20260919B-20260920; no permission bypass or retry. Scoped run request
file exists. No business test run. Only HANDOFF/CURRENT_STATE/TASKS/SERVER_INFO
documentation updated; no rollback needed for the read-only diagnosis.

## 2026-09-27 — WES cloud cleanup authorized; preflight

Completed: all8 listed SFS directories removed and both parent inventories empty;
8 OBS prefixes/134 objects removed with zero failures, parent listings0 files/0B.
Dedicated maintenance Job deleted. Detailed per-target receipts/outcomes in
docs/releases/2026-09-27-wes-cloud-cleanup.md. No DB/offline/pending changes,
no business tests. Nothing to roll back in code; deleted data has no backup or
guaranteed recovery. Old WGS multipart permission issue remains deferred.
Changed files: this handoff, CURRENT_STATE.md, TASKS.md and dated WES record.
Commands: read-only DB/Airflow/Pod inventory, precise SFS rmtree and OBS rm,
post-action inventories and own maintenance Job removal, all successful.

User explicitly includes 20260921B and requests clearing WES cloud batch data.
Scope: exact batch children inventoried under SFS gatk-cloud/runs/WES_Clinical,
wgs-obs-sync/Project_result/WES_Clinical and OBS Project_fastq/WES_Clinical,
Project_result/WES_Clinical. Record each resolved target before deletion.
Read-only BS96 DB/Airflow occupancy checks are part of cleanup preflight only.
Protect all offline projects/results/FASTQ/sampleinfo, pending, WES database
records, shared resources/pipelines/evidence and unrelated cloud prefixes.
No multipart-upload retries, no business tests, no workflow/service changes.
No backup is requested or created; deletion recovery is not guaranteed.
Exact pre-action targets: docs/releases/2026-09-27-wes-cloud-cleanup.md (8 SFS
directories and8 OBS prefixes). Five GATK records are success; active Airflow
DAG list empty; no live analysis Pod targets these paths. Only the dedicated
bs96-wes-cleanup-20260927 maintenance Job may be deleted after this operation.

## 2026-09-27 — Authorized BS96 WGS cleanup; incomplete uploads/WES outstanding

Completed: four exact AnalysisRuns/31 samples and owned projections deleted;
pending ledger content hashes match,23/162/20 rows preserved.25 SFS target trees
and34 OBS complete-object prefixes removed, final inventories empty. Other15
WGS database runs retained; no offline changes or business tests. Per-target
outcomes and failures in dated cleanup record. Cloud helper Job/Pod removed.
No backup was created; deletion recovery is not guaranteed.
Outstanding: exact first multipart abort returned403 AccessDenied (remaining4
not attempted), five uploads still require authorized AbortMultipartUpload.
WES date-based cloud scope asked separately, no answer yet; WES untouched.
Two B/D scanner dedup rows retained/unlinked and existing ignore list extended,
to prevent automatic re-submission. Active scanner Compose is now
/data/airflow-WGS/cleanup-20260927-control/scanner.json; private prior config
scanner-before.json. Reverting exclusions without a replacement linked analysis
can cause re-submission, so do not blindly roll back. Other services unchanged.
DB transaction script/log in same control. OBS per-prefix records stay in
WGS_test/cce-evidence/cleanup-bs96-20260927 at node005's /sg2/biodevrwsg2 view.
Only documentation changed in integration worktree; no source tests necessary.

Exact live IDs, 31 run-associated sample rows, 34 OBS prefixes and25 SFS paths
are itemized in docs/releases/2026-09-27-authorized-cloud-cleanup.md before any
deletion. Pending content hashes will be compared; only nullable analysis links
detached. Existing scanner ignore list gains the exact B/D chips to prevent
automatic recreation after deletion. No broad scanner disable or workflow test.

Original pre-action authorization/preflight (retained below; outcomes above):

User authorizes deletion of analysis database history and run-associated sample
records for exactly 20260921B/C/D/E, preserving pending transfer ledger records;
also corresponding online SFS batch data and OBS FASTQ/result objects. User
clarifies expired cloud batches mean batch dates strictly before 20260921.
That extra date scope applies to cloud SFS/OBS only, not additional DB records.
Production read-only inventory is authorized to resolve exact IDs/paths first.
No deletion yet; itemized targets and live occupancy must be recorded before
mutation. Do not reuse old cleanup scripts as authorization. No backup is yet
created or verified; do not promise recovery.

Protected: all offline /sg2 and /bi projects/results/FASTQ/sampleinfo/pending/
runtime evidence (including ctapa and hanjj trees), all pending database ledger
rows, other-run same-ID samples, reference/workflow assets, cloud batches dated
20260921 or later except the four named batches. Ambiguous date/path ownership
is excluded pending clarification. No analysis/test submissions or code changes.
BS96 preflight: server96/chenjc, control/data root unchanged; backend365beab02248
mounts release20260927-p0-local-84510df; actual WGS execution/scan/auto=true,
recovery=true, original watermark retained. Current symlink is historical.

## 2026-09-27 — coordinated WGS d38322e release window complete

Authority verified by reading WGS-pipeline thread01a09149-ad9d-7e92-b98a-16d9cae075e2:
after explanation of temporarily closing manual submissions/automatic dispatch,
waiting for idle, updating shared pipeline/profile/catalog and restoring admission,
user replied "目前没有流程进行". Earlier source publication and cross-thread
coordination were explicitly authorized. Continue that narrowly scoped window;
do not start samples, test faults, change Local/SGE/GATK policy, kill active work,
delete data or modify business algorithms. Deployment/debug and runtime skills
apply; this is production BS96/server96, control/data paths remain unchanged.

Save the exact backend/scanner service configurations and original flag values;
only temporarily disable WGS_EXECUTION_ENABLED and WGS_AUTO_DISPATCH_ENABLED in
backend, and auto-dispatch in scanner. Preserve scan/watermark/runtime adapter/
recovery/GATK/Local flags, source mounts, images and credentials. Check fresh idle
before changes and again after admission closes. If active work appears, report
and preserve it; no shared-SFS release permission until idle. Original WGS owner
owns newasset20260927.2-wgs422, source d38322e, profile r3 and genuine receipt.
Airflow owns subsequent immutable source prepare/gate mapping and authenticated
catalog CAS activation, then restores exact original admission values. No new
code or redundant business testing is authorized. Window status is communicated
through D:/pipeline/task-artifacts/wgs-422-release-20260927/WINDOW_AIRFLOW.md.

Result: frozen07:46:11Z and restored07:51:38Z. Idle checks immediately before
and after closing admission returned business active0/unsubmitted0/leases0 and
Airflow queued/running DagRuns0/TaskInstances0. Backend execution and backend+
scanner auto-dispatch were the ONLY changed flags; scan/watermark/GATK/Local/SGE/
recovery remained unchanged. WGS owner also checked external CCE occupancy;
reported only two unrelated old GATK Pending check Pods, no WGS-path user, and
left them untouched. Publisher completed same-resource two-component official
release; no source/SFS writer overlapped this window.

Node200 promoted exact receipt-derived immutable source/profile paths with new
private prepare config hash86b41bf7; old mappings preserved. No source edits or
new native install. Registration/CAS activation succeeded fromwgs-4.2.2-3b1dae5
towgs-4.2.2-d38322e with receipt60650a5ff7751f7bfb749eb1e4efd4fca60a5f1e9b18669b2e8d09abd99e55db.
API current readback after restoring services matches newrelease/r3/receipt.
Exact prior service configuration restored: backend365beab02248/scanner4ec5abb4d79b,
running; each captured flag equals its original value, including absent keys.
Gateway health200. No other service recreation or business/test batch submission.

Private server control /data/airflow-WGS/wgs422-d38322e-window-control keeps
freeze.json(INACTIVE), restore.json(ACTIVE), original/restored flag records,
idle evidence, real registration JSON and activation output. Node env backup:
/home/ctapa/.config/airflow-wgs/.wgs422-window-20260927/runtime.env.before.
The original WGS owner was told windowCLOSED and no further shared-path writes
scheduled. No ongoing monitor promised; user testing is next. Full details in
docs/releases/2026-09-27-wgs422-d38322e-bs96.md. Rollback requires a NEW idle/admission
window and coordinated genuine prior-source asset publication; do not merely
switch old catalog selection while SFS remains new. Data and history are retained.

Git changes: only current-state/tasks/server-info/handoff, new release note and
exact exported receipt. Local git whitespace/hash/ancestry checks only; no
pytest/npm/business smoke was run or needed for this configuration rollout.

## 2026-09-27 — BS96 P0/Local production rollout complete

Current user explicitly authorizes deployment to BS96, then user-led testing.
Pinned platform source: 84510dfc83fce8b566014ac573e3a8518bfffe4e, identical on
main, production and canonical test. This authorizes the necessary additive
0025/0026 business schema migration and production release registration, not
clinical submissions, deletion, old-batch mutation or a new smoke campaign.

Read-only preflight: ssh BS96 -> server96/chenjc, control /data/airflow-WGS;
actual backend /app is releases/20260923-gatk-waiting-ui/backend, independent
service pins recorded separately. Current symlink is historical and is not
used to infer deployed sources. Business schema is 20260914_0024; no active
analysis_run, queued/running Airflow DagRun/TaskInstance or occupied OBS slots.
Scanner/dispatch remain enabled with their existing watermark. Node200 is
t640/ctapa via id_rsa_ctapa and BS jump. No service mutation at preflight.

Scope: production backend/observer/frontend and affected Airflow DAG services;
preserve independent scanner/reference worker, database/Redis, external network,
GATK runtime/profile and Local execution gates. Original native artifact owner
coordinates final 0.8.7 wheel/profile/assets; platform owns production gate and
paired policy installation. Final native source8323567/Master3d180a9 must not be
confused with older shared e2962a2/Master2b80700 assets. No new build/version or
test-to-production credentials/database copy. Business outputs0755/0644;
private deployment controls remain0700/0600. Exact rollback configuration is
captured before switching services. Additive schema is retained on code rollback.

Preflight command errors: guessed wgs_transfer_lease table then status column
were absent; schema/model inspection corrected to obs_transfer_lease.analysis_id.
Default Airflow-container python lacked airflow; executable shebang confirmed
/home/airflow/.local/bin/python. node200 short hostname was not resolvable from
jump; documented IP172.17.61.200 succeeded. These read-only checks changed no
data and are not product failures. Completion, paths and acceptance follow.

Completed: immutable source84510df archived/transferred, offline frontend build
exit0/image13e960ad; additive Alembic upgrade to0026 confirmed. Original native
owner installed private0.8.7/source8323567 and published genuine matching
Master3d180a9/r2 profilecccb04c5/assets20260927.1-wgs422-p0. Production12-file gate
closure, prepare config using the actual immutable4.2.2 template, compatible
Operator and paired bootstrap installed as ctapa. Existing real obsutil env
retained; no WGS-environment install. selected_runtime resolves exact production
native/Python pins. Previous files/env saved in the private gate backup.

Six selected services switched successfully at07:32Z; no active/queued business
tasks or occupied leases immediately before cutover. Actual app/DAG mounts
match release; six services running/restarts0, other six project IDs unchanged.
Gateway LAN health200 after nginx config/reload. Authenticated API registered
receiptfc3a7d255642c11aedef2410e03c63f212acaf519094e7b29463cd609732f831 and CAS
activated wgs-4.2.2-3b1dae5 from4.2.1-ebf1f4b. Current readback matches. WGS
recovery flag istrue for new frozen policies; old attempts remain unchanged.

Additional deployment errors/corrections: untouched legacy Compose interpolation
needed unavailable secrets, so assembly uses only six affected live effective
configs; removed dependency startup from scoped --no-deps control. Catalog host
access was denied to chenjc; obtained rollback copy through existing backend
mount, no chmod/chown. Backend lacks requests; use urllib, no package install.
Source release deliberately has no prepare/config.yaml; private pinned prepare
config points at its existing cfg/config.template.yaml. Native Operator legacy
extensions required a schema-compatible private copy; original file retained.
Missing exact-node known_hosts was populated from that same node's authenticated
public host key, no trust bypass/key copying. Asset publication additionally
needed the existing WGS_REAL_OBSUTIL_BIN exported in its standalone shell.
Coordinator initially specified /bi for historical bs10610_repo_path; API422
correctly rejected it. Native owner re-exported SAME verified assets with /mnt
field, no product patch or repeated publish. Initial proxied localhost curl403;
documented LAN endpoint with no-proxy returned200. All are deployment assembly
issues, not test failures, and are now resolved.

Concurrent WGS publisher reported newer source4e3094b assets in the same SFS path.
It stopped further writes; both original owners received the exact current
deployment contract in local COORDINATION_AIRFLOW.md. This deployment is
specifically accepted source3b1dae5, not the proposed new r3/source. No further
SFS apply window granted; coordinate a later user-scheduled admission freeze
before overwriting the active path. No repeat source audit, smoke or samples.

Files changed in Git: this handoff, CURRENT_STATE.md, TASKS.md, SERVER_INFO.md,
dated release note and exact CLI-exported registration JSON. Product code is
unchanged. Runtime tests intentionally not run: user explicitly reserves all
business testing. Only installation/build/configuration, service startup/mount
and existing release administration were executed. Details, IDs, exact rollback
and caveats are in docs/releases/2026-09-27-p0-local-bs96.md. Next action is user
testing. Before any rollback, check no live paired writer; restore matching
service/gate/native/catalog set, preserve additive schema/data/journal. No deletes.

## 2026-09-27 — authorized P0 and Local/SGE source promotion

Goal: merge the accepted canonical test branch, including earlier Local display
commits, into main and jiucheng/release/production, then push. User explicitly
authorizes this source integration; BS96 service deployment is a later task.
The user confirms other source repositories are synchronized; they were not
queried again.

Source review: refreshed origin refs show both targets at 43cd0c5 and test at
9fb31c3; git rev-list --left-right --count reports 0/170 for each target.
Thus no textual merge conflict exists. Local commits 95b0144, 38bdca1, d76edd3
and 76915d8 retain short batch/node labels, current snapshot samples, percentage
progress, simple rule rows/shared phase summaries, Snakemake logs and CCE log
archive download. Shared Rules retain Phase/Sample/Family selectors and running
default; native routing is conditional on native_monitor_only. Existing CCE
Overview/Samples and upload/download waiting behavior remain present.

Historical merge bbbf942 had dropped only two standalone production release
documents. Restored docs/releases/2026-09-22-upload-waiting-bs96.md and
docs/releases/2026-09-22-download-waiting-bs96.md byte-for-byte as Git blobs from
origin/main. Other edits in this task are CURRENT_STATE.md, TASKS.md and this
handoff. No implementation changes relative to test 9fb31c3.

Validation: use Git ancestry, diff/whitespace checks, restored-blob equality
and final code-tree equality. Reuse documented BS10610 Local/backend/frontend
acceptance and latest DagBag/import acceptance; no pytest/npm/cloud smoke is
rerun for a fast-forward with documentation-only additions. A discovery rg
command initially passed shell-style wildcards as explicit Windows filenames
and returned exit 2; subsequent searches use rg -g filters. No product failure.

Target environment: source repository only; no SSH, container/mount/permission
change, DB migration, service restart, scanner or dispatch change. Original
dirty D:/pipeline/airflow-demo and other worktrees remain untouched. Native
0025/0026 schema and production-specific gate/profile binding must be handled
during the later BS96 release, not assumed deployed by this Git promotion.

Rollback reference is pre-promotion main/production 43cd0c5. Remote history
must remain non-rewritten; use a reviewed revert if source rollback is needed.
No runtime rollback is needed because no service changes here. Existing P0
acceptance limitations remain as documented.

Completion: commit e433ea0 restores the two release records and adds the promotion
notes. Both main and production fast-forwarded from 43cd0c5. Atomic non-force push
updated main, production and canonical test together; git ls-remote confirmed
all three at e433ea0ce809bb7bded1b2e7618efca5fa27f4a9. Working tree is clean.
git diff --check passed; restored document blobs equal original main; application
directories equal accepted test 9fb31c3; target branch trees equal; no production
file deletions remain. Production RunResourceTabs/WgsQcTab and transfer/timing
projections are byte-identical to 43cd0c5. This final documentation-only closure
will be synchronized to the same three refs. Next is the separately requested
BS96 release with migration/runtime configuration accounted for.

## 2026-09-27 — duplicate main DAG discovery fixed on BS10610

Goal: address the user's duplicate-DAG finding without deleting a real DAG or
changing task behavior. Source commit `4fe71cb` on pushed canonical test branch
`jiucheng/test/wgs-local-main-sync-20260917` changes only the parse-time imports
in three auxiliary DAGs, adds one real DagBag regression, and updates the DAG
spec. The main DAGs, task graphs and execution gates are unchanged.

Test boundary: `ssh BS10610`, hostname `server10610`, identity `chenjc`, control
root `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`. Read-only live
preflight showed the old three helper files byte-identical to the branch and
zero queued/running DagRuns for the five related DAG IDs. The Airflow 2.9.3
DagBag test was RED on the actual old mounts with two duplicate IDs, then GREEN
on an isolated candidate containing the five live DAGs plus common helpers.
Candidate WGS native monitor unittest 2/2 and GATK maintenance script passed.
No full suite or business batch was run.

The first disposable candidate parse erroneously included a non-runtime
Snakemake logger plugin package and failed for its missing dependency; copying
the exact running DAG file set removed that test-fixture error. A standalone
candidate test initially called `DagBag.get_dag`, which queried an uninitialized
scratch SQLite DB; the test was corrected to inspect `bag.dags` directly.
Neither failure changed deployed code or the product fix.

Released only three helper files to
`releases/20260927-dag-discovery-4fe71cb/dags` (directories 0755, files 0644,
`chenjc:bioinfo`); their SHA256 hashes matched local committed sources.
Private `candidates/dag-discovery-4fe71cb-control/compose.json` changes exactly
nine read-only bind sources across Airflow API/scheduler/worker; `rollback.json`
is an exact copy of the prior active control. Both private files are 0600 in a
0700 directory. `docker compose config --quiet` passed. `up -d --no-deps --pull
never --force-recreate` succeeded for only those three services; Compose's
orphan warning was informational and no orphan was removed.

Post-switch: actual mounts 3/3 in each affected service; `airflow dags
list-import-errors -o json` returned `[]`/exit 0; `dags list -o json` resolved
`bio_wgs`, `bio_gatk` and the three auxiliary DAGs to their own files. Gateway
`/api/health` and `/api/health/db` returned 200. Backend/observer/frontend/
metrics/Redis/Postgres retained their pre-switch uptime. No scanner/dispatch
setting, SFS, runtime image, clinical data, production service or live batch
was modified. Rollback, if ever needed after an active-run preflight, uses the
private `rollback.json` for only the three Airflow services; do not delete DAG
metadata or project data. Full platform/API/recovery acceptance remains separate.

## 2026-09-27 — Airflow canonical test branch push and BS10610 live check

Goal: correct the earlier isolated-branch delivery, include Airflow P0 and
current production fixes on the canonical test branch, push it, and check the
test deployment without restarting equivalent code. The clean isolated
integration worktree was switched to `jiucheng/test/wgs-local-main-sync-20260917`.
Remote test `b17e1b6` was an ancestor; `main` and production `43cd0c5` were
ancestors. A non-force push advanced the remote canonical test branch to
`0203b79ebc23d8dae4b46d52c1d06698544189b2`. `git diff --check` passed.

BS10610 hostname `server10610`, SSH identity `chenjc`. Actual backend `/app`
and Airflow WGS DAG mounts remain under
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260926-p0-e358aad`;
the historical `current` link is not the live source. `git diff --name-only
e358aad..HEAD -- backend dags scripts config frontend` was empty. Live
`backend/app/main.py` and `dags/bio_wgs.py` SHA256 values matched the pushed
branch. Thus P0 functional code was already deployed on BS10610; this turn did
not recreate the five services, alter mounts/gates, or run a clinical batch.

Minimal check: on the actual bound gateway `172.17.106.10:12959`, `/api/health`
and `/api/health/db` returned 200; malformed `/api/auth/login` returned 422;
unauthenticated `/api/workflows` returned 401 as expected. All relevant Compose
containers were running. The initial health probe against loopback
`127.0.0.1:12959` failed with curl exit 7 because Docker publishes only on
`172.17.106.10`; inspecting the precise port binding corrected the check.

**Open failure:** `docker exec airflow-wgs-airflow-scheduler-1 airflow dags
list-import-errors -o json` exited 1. It reported duplicate `bio_wgs` from
`bio_wgs_native_monitor.py` importing `bio_wgs`, and duplicate `bio_gatk` from
`bio_gatk_maintenance.py` importing `bio_gatk`. `airflow dags list -o json`
exited 0 but warned that not all files loaded and associated `bio_wgs` with
the native-monitor file. Cause is module-level DAG imports during Airflow file
discovery; no fix or blind retry was attempted. Next: narrowly correct DAG
discovery in the test branch, perform targeted import check and gateway health,
then decide on exact test-node redeployment. This check does not establish
Airflow/API end-to-end or automatic recovery acceptance.

No production host/DB, SFS data, clinical workdir, credential, or shared runtime
was changed. Existing test release remains the rollback baseline; no rollback
action is needed for this source-only branch alignment. Other P0 repositories
remain separately governed by their own source/push status.

## 2026-09-27 — P0 Git source synchronization, no upstream push

Goal: prepare the four P0 source repositories and BS umbrella gitlinks for
operator push without deploying or repeating runtime tests. Read the named
plugin-owner task, component provenance, test/production boundary and current
state. The plugin source is
`D:/pipeline/snakemake-executor-plugin-kubernetes/.worktrees/p02-worker-terminal-20260923`
at `4f10c276`; the wheel under `WGS_test/cce-evidence` is only a built artifact.
The cce-pipeline source is the isolated 0.8.7 worktree at `8323567c`.

Transferred complete Git bundles to BS10610 task-specific evidence and
verified SHA256 on both ends. Imported branches and fast-forwarded the clean
server plugin/native `main` worktrees to `4f10c276`/`8323567c`. Umbrella
commit `cd82ca7b` stages only their two gitlinks. Existing umbrella untracked
release artifacts and the old cce checkout remain untouched; its worktree
therefore still reports a modified submodule after the parent commit. WGS
`dev_CJC_4.2.2_cloud` is already committed at `3b1dae5`; its unrelated draft
docs were not staged. This platform test branch was `44fba4f` before this entry.

Commands/results: `git bundle verify` passed twice; server ancestry checks
and both `git merge --ff-only` passed; parent staged diff contained exactly
two gitlinks. A WGS push to local `/bi/.../wgs-4.2.0` failed, exit 1, with
`remote unpack failed: unable to create temporary object directory`. Read-only
check found matching owner/mode and 133T free, but no proven cause; no permission
change or retry. Use authenticated direct GitLab push instead. No upstream
push, install, deployment, clinical data access or runtime test. Minimal Git
status/ancestry/bundle checks replace redundant runtime testing for this
source-only synchronization. Next: operator push children first, umbrella next,
platform test branch separately; non-force push protects against remote drift.
Rollback: move only the newly advanced local refs back to recorded bases after
review (plugin `1ca1e88`, native `83e7adb`, umbrella `646d445`); do not use
`reset --hard` or delete worktrees/artifacts. No deployed state to roll back.

Target was test/source preparation on SSH alias `BS10610`, verified hostname
`server10610`; BS96 and its release path were not accessed. This entry changes
only `CURRENT_STATE.md`, `TASKS.md` and `HANDOFF.md` in the platform test branch.
No service, scanner/dispatch setting, mount, runtime directory or permission was
changed; release pointers and rollback release paths are therefore not applicable.
Current source status: platform test worktree clean after commit; native/plugin
`main` worktrees clean; WGS has pre-existing draft docs; umbrella has pre-existing
untracked release artifacts and an old cce submodule checkout. Upstream GitLab
heads remain unverified without credentials, so push must be non-force and may
reject if those heads have moved.


## 2026-09-27 — requested native downstream smoke passed

Goal: close Step1-2 as requested, exclude gen2 timeout, finish original synthetic
COMBINED01 Step3-6 without whole-case restart or product/production changes.
Original runtime owner used BS10610/server10610 chenjc for Kubernetes and
node200/t640 ctapa nipttest task-private runtime, source8323567/0.8.7. Candidate
Master digest3d180a9f074cf38ffaf18446f2910a316e2b784b8f7f859bea5dc4a74d10f1af
unchanged. No service/scanner/dispatch/release/profile changes or runtime install.

Actual gen4 same-workdir result: Step3 SUCCEEDED2/2; operator_continue.py
publish-final/download/materialize all rc0. DOWNLOAD_VERIFIED PASS3files/1786B,
manifest MD5d509bf1af8592b6af82bfcea724d8366; MATERIALIZED VERIFIED/PASS.
Native log archive4672B verified, SHA69efb294509893b1b3ed375097419a567892a593932eb36681496dab5b984d56.
Final verification1790478371.3316016 precedes unchanged deadline1790478526.9563308.
Checkpoint before/after SHA37fc1795eae2e970363b212a8b7aa429144cb4117c9b794658b13bebb2e8a86a
and mtime1790470262562322098 match; original in-rule baseline preserved separately.
Results ctapa6801:520, directory0755/files0644. No checkpoint/payload rerun in gen4.

Coordinator independently read COMBINED01-OPERATOR-G4/FINAL_VERIFICATION.json,
execution/{status.log,publish-final-process.json,download-process.json,
materialize-process.json}, cloud_delivery/{DOWNLOAD_VERIFIED,MATERIALIZED},
and observations/057dbe3c-f8c2-426d-8387-274cf93e0432-reclaimed.json under
D:/pipeline/task-artifacts/wgs422-p0-integration-20260926/p0-native-smoke-20260927.
No redundant remote test execution. Docs-only local diff check precedes commit.
Files changed: CURRENT_STATE.md, TASKS.md, HANDOFF.md on existing test branch.

Synthetic-only corrections and initial failures documented below. Exact own
manifest partial also remained in OBS after SFS removal; owner preserved its
366B copy, verified SHA08566d8952468e4ff84635f80b32083a2bcb6f41979426eeab326afb3e41a378
and removed only that object before successful publish. No other data deleted;
original manifest, results, requests, failed logs and generation history retained.
Gen4 Master terminal+TTL proven. Final COMBINED_CREATE_LEDGER.md reconciles prior18
plus24 real COMBINED UIDs =42 CREATEs (no count reset). Coordinator read
FINAL_RECLAMATION.json: exact scoped Jobs/Pods absent; six storage histories CLEANED.
EXACT_SETUP_RECLAMATION.json proves saved terminal and UID/RV Foreground deletion
of cce-p0-smoke-setup-20260927 UID9c2889e8-2583-42e4-a24f-e849db159a84 and
cce-p0-smoke-setup-2-20260927 UIDc34a17d7-2fb0-4b74-9141-1f7dcb102ff0;
both Job/Pod absent. Both lacked TTL. Saved specs permit recreation, not recovery
of original UIDs. No directories/results/locks removed. Final report is local
COMBINED_FINAL_REPORT.md; raw evidence/fixtures remain outside Git.

This is manual operator continuation plus native downstream PASS, not proof of
automatic pre-START recovery, stale-event race resolution, platform API/Airflow
E2E or biological equivalence. Step7 not run; no production authorization implied.
Next: this requested test scope is closed; no further tests. Rollback is docs revert;
no deployed product changed. Fixture prior versions and all failures remain in
task evidence; do not roll back successful outputs or reopen excluded tests.

## 2026-09-27 — gen4 analysis succeeds; downstream manifest fixture correction

Actual gen4 Master UID057dbe3c-f8c2-426d-8387-274cf93e0432 completed only
finalize/all, no Worker. Native same-UID START confirmation and Step3 reported
SUCCEEDED/100%/2of2. Earlier confirmation read stale gen3 START and failed;
all failure logs remain, no manual state edit or additional Master. Owner observed
gen4 terminal and TTL reclamation. This is manual operator continuation evidence,
not proof that automatic pre-START recovery or every handshake edge is fixed.

Coordinator read COMBINED01-OPERATOR-G4/execution/status.log, publish.log and
inspect-publish.log. Native Step4 correctly rejected five OBS objects because the
synthetic manifest lists only archive, while fixture also writes payload.txt and
checkpoint-proof.json under results. Read-only source check confirms read_manifest
accepts explicit artifact types and materialize selects the unique batch archive.
Authorized only adding those two existing synthetic files with actual bytes/MD5
to the manifest via bounded helper. Preserve original manifest and hashes outside
delivery prefix; do not change existing result bytes, frozen gen4 script/request,
terminal evidence or product code. A separately derived fixture source records
the correction. Continue native Step4-6, not analysis rerun. No production changes.

Owner reports helper37 rename of manifest partial failed EPERM; helper38 stopped
at existing backup and preserved old171B manifest. Same UID10001 verified exact
files/checksums. Approved original fixture's direct-write method only after old
manifest byte/hash recheck, followed by byte/read_manifest verification; preserve
backup and failed logs, no sudo/chmod or result/terminal changes. Only its own
exact hash-verified partial may be removed. Original operator deadline unchanged.

## 2026-09-27 — downstream fixture timestamp baseline correction

Actual gen3 operator handoff START_CONFIRMED, UID5bb3436d-06af-4e64-8658-60095e2ef42a;
Worker UIDb055a3e5-e65c-4f03-921a-306efdc51ead succeeded. Native Step3 rc0 returned
FAILED because synthetic finalize compared a baseline recorded inside checkpoint
rule before Snakemake success postprocessing. Gen3 did not execute checkpoint.
Both workloads terminal+TTL observed. Do not report this gen3 as successful.

Coordinator independently read reader31's actual checkpoint/metadata and image
Snakemake source in COMBINED01-OPERATOR/checkpoint-reader-r2.log. SHA remains
37fc1795eae2e970363b212a8b7aa429144cb4117c9b794658b13bebb2e8a86a.
Origin mtime1790470262552336995 vs current1790470262562322098 (9.985103ms);
metadata endtime1790470262.5623221 agrees with current time, long before gen3.
Snakemake dag.py775 check_and_touch_output explicitly touches successful outputs.
checkpoint file10001:520/0644. Reader30 completed but log retrieval failed;
reader31 repeated only the same fixed read-only evidence, not analysis.

Owner may correct ONLY this task's synthetic finalize baseline: retain original
origin/Snakefile/REQUEST/all failed evidence, write a new separately pinned
post-success baseline bound to actual metadata+same SHA+pre-gen3 mtime, retain
original fixture copy before task-private fixture change. A bounded write helper
and next real native Master/CAS may finish finalize/all in the same workdir,
reusing checkpoint and successful payload; no new Worker is expected. Then
actual native Step3-6, minimal output/permission/reclamation checks. No product
code or production change, fake FINAL, old deadline reset or whole-case rerun.
Inherit operator deadline1790478526.9563308. This is correction of proven test
fixture error within the user's downstream test scope, not a new P0 feature.

## 2026-09-27 — user closes Step1-2 and requests downstream-only tests

Exact latest instruction: ignore the second Master's pre-analysis timeout,
mark Step1-2 testing complete and directly finish subsequent tests. Step1 and
initial Step2 already have actual pass evidence; the pre-START recovery edge is
explicitly excluded, NOT relabelled as passing. Do not repeat upload/initial
submission fault tests or restart the whole case. Preserve original workdir,
checkpoint/config/results and all failed-generation evidence. Original runtime
owner continues downstream Step3-6 in test only, with necessary bounded test
Master/Worker creation and timely reclamation. No product changes, fake terminal
records, rewriting old deadlines or production actions are implied. If the only
continuation requires a new contract or unsafe state override, report the precise
minimum action rather than expanding development. Previous fresh-case proposal
is superseded; no fresh full-case rerun is authorized by this instruction.

Execution interpretation: a task-private, independently pinned operator driver
may compose existing native view/CAS/CREATE/handshake primitives for this manual
downstream continuation. This is test-only operator evidence, not native FINAL
or automated recovery acceptance. Preserve old requests/journals/deadlines and
lock identity; move ownership only through real native CAS after exact terminal,
inventory and no-writer checks. A new explicitly recorded manual continuation
operation may have its own bounded execution window (same native1800s Master
limit/TTL100); it must not amend or pretend to reuse the expired prior window.
No additional scenario, production code or broad state override is authorized.

## 2026-09-27 — corrected explanation: new Master, not a whole-case restart

User asks why not simply replace Master and finish remaining steps. Coordinator
and original runtime owner performed read-only code inspection, no test/CREATE.
Same workdir/config/run/attempt and completed checkpoint can be retained:
classify_cce_master_run.sh selects resume; analysis uses rerun-incomplete/mtime.
The previous fresh isolated case proposal is ONLY a no-product-change workaround,
not a technical need to restart biological work and not the preferred P0 design.

Actual gap: run_cce_master_job.sh26-33 exits pre-START before trap137. Runtime
_recovery_final_evidence1758+ requires bound START/terminal/FINAL; platform
RecoveryCapability consumes it. _advance_recovery_view1825+ created-state replay
requires the original replacement Job/UID and cannot recreate it once expired.
Thus driver-only correction does not handle a failed pre-START replacement.
Desired scoped route is explicit pre-START failure proof plus current ownership/
live-worker checks, then a new-generation Master/action with its own handshake
window, same outputs and original compute-budget rules. Never relabel old FINAL
or rewrite old deadline. Implementation not performed in this diagnostic turn.
Coordinator updated these three state docs only; no runtime tests needed for
read-only diagnosis. Production/data/services untouched. Prior fresh-case
confirmation prompt is not a prerequisite for explaining the correct route.

## 2026-09-27 — minimal entry fix done; original gen2 expired and reclaimed

Goal: execute only the approved synthetic same-action continuation correction.
Owner changed task-artifact combined_driver.py only. New resume_selection reads
the actual created journal's original gen1 source, validates gen2/action/UID,
manifest/directory owner/platform and original deadlines, and retains native
storage validation/RecoveryCapability/CAS. No production/runtime source change.
Driver SHA da909464370c6062ee32593613242b7333f50e012e3d983c998de24fa20330fe;
original4852af86 preserved. No in-place active REQUEST/pin/trust migration.

Owner ran one offline entry RED/GREEN check on node200 nipttest Python, using
real JSON/path guards and read-only API fixture. It is not cloud replay PASS.
Coordinator read exact patch, full green output and actual driver hash, not
another test execution. Artifact root D:/pipeline/task-artifacts/
wgs422-p0-integration-20260926/p0-native-smoke-20260927/harness-reentry-review:
RESULT.md, combined_driver.patch, combined_driver.before.py, reentry-{red,green}.log.

Actual gen2 Master UIDa17e48cb-1380-41f9-a3ff-cfe3c829604e terminal Failed /
BackoffLimitExceeded at2026-09-27T01:05:05Z; owner captured payload upload
600s timeout log. Coordinator read its terminal JSON and exact UID reclamation
record: absent_epoch1790471188.1964965. Original deadline1790471074.5420542
expired; no gen2 Worker, no additional CREATE (cumulative25). Existing observer
finished. No claim that every earlier helper has independent cleanup evidence.

Same-operation replay is now unavailable. Ordinary gen3 needs gen2-bound FINAL;
pre-START timeout exits before terminal-writer installation, so gen1 FINAL must
not be relabelled. Minimum product-unchanged route is fresh frozen identity and
isolated output for the SAME synthetic case, with corrected driver pinned before
freeze; retain old lock/data/evidence. User confirmation requested asynchronously,
not yet received. No fresh run prepared/submitted. Successful recovery/checkpoint
invariance/Step3-6 remain unaccepted. Do not silently add pre-START product fixes.

Coordinator files: CURRENT_STATE.md, TASKS.md, HANDOFF.md only. git diff --check
passed; no coordinator runtime tests/SSH or service changes. Production, scanners,
shared profiles/assets and existing data untouched. Rollback is docs-only; new
driver is not deployed and original task-artifact copy is preserved. Next action
depends on user decision, not more diagnostics or a repeated full test suite.

## 2026-09-27 — approved minimal same-operation test-driver continuation

User answered "同意" to correcting only the synthetic driver's same-operation
resume entry and continuing the remaining combined smoke steps. This authorizes
the necessary narrowly scoped trusted test-entry/pin update, not product changes,
guard bypass, evidence replacement, deadline extension or an extra test suite.
Original runtime owner must first check the actual replacement UID/journal and
original deadline. Reuse the same action/generation/UID where still legal; retain
the frozen request and all original failure evidence. If its deadline has elapsed,
report that state and the legal continuation requirement instead of resetting it.
Coordinator delegates runtime execution to the existing owner; no production or
data deletion is authorized. Remaining success chain is not yet accepted.

## 2026-09-27 — COMBINED01 actual progress and interrupted replacement

User further requests fewer redundant tests and fast completion. Owner was told
to execute only the reviewed current combined case, not another normal/full suite.
Task-private REQUEST fixed42 pins; source8323567 and reviewed driver/fixture
hashes unchanged. Profile naming normalized to task-private r4 before submit,
not a shared release/profile publication. No production/service changes.

Actual CREATE tally25: historical18, setup19, initial helper20, Master21,
reentry helper22, failed Worker23, failure-evidence reader24, replacementMaster25.
Setup19 succeeded+TTL; late log fetch timed out after reclamation, not setup
failure. Native register/Step1 rc0. submit-lost rc1 and submit-reentry rc0;
Master UIDf74b3f7c-d998-448a-b343-c5a80d174886, original deadline1790470733.864905,
START_CONFIRMED, exactly one CREATE. Coordinator independently read actual
process/logs plus CREATE_RESPONSE_HIDDEN/SAME_UID_RECONNECTED. First Worker
UIDde3bf8ac-8ba4-4d42-b10f-4282c7b50150 failed normally as designed (retries0);
checkpoint success and bound failure/FINAL collected, old workloads TTL observed.

resume rc1 after actual gen2 CREATE/CAS binding: UIDa17e48cb-1380-41f9-a3ff-cfe3c829604e.
Native _advance_recovery_view -> _finish_master_handoff -> kubectl exec copy
PAYLOAD.yaml hit TLS handshake timeout. Real journal statecreated/replacement_uid;
handoff POD_READY, no START/gen2 Worker. Original handoff deadline1790471074.5420542,
compute deadline1790473402 retained. Owner traced existing product same-created
journal continuation, but frozen driver resume first resolves START_CONFIRMED
owner and then requires gen1/absentoldJob, so it cannot reach that continuation.
Not proof that production resume is broken; also not a completed recovery PASS.

Current writes stopped: no new Master, no modified frozen REQUEST/pins/locks,
no deadline extension or fabricated receipt. Existing bounded read-only observer
may capture native timeout/TTL; newest Master terminal/reclamation not yet proven.
Need scoped decision on minimal test-driver same-action continuation entry.
Do not claim Step3-6/new-output invariance/full P0 accepted. No extra scenarios.
Evidence: D:/pipeline/task-artifacts/wgs422-p0-integration-20260926/
p0-native-smoke-20260927/COMBINED01-8323567/{execution,control}; original failures
and successful checkpoints preserved. Coordinator made docs-only changes;
git diff --check is the local check, no local runtime tests or extra SSH.

## 2026-09-27 — user removes cumulative Job cap; cleanup remains mandatory

Exact new instruction: "后续如果测试jobs还不够，建议不设上限，只需要及时回收即可".
Supersedes cumulative30 authorization; does NOT authorize unlimited live Jobs,
new cases, production or arbitrary cleanup. Original owner continues approved
normal/reconnect/manual-replacement scope. Record every actual CREATE and UID,
keep max1Master+1Worker/consecutive cases, native deadlines and TTL100; observe
terminal reclamation or precise already-approved runtime cleanup. Do not delete
local/SFS/OBS data or locks. Failures require diagnosis, not blind retries.
Original18 count retained. The prior combined29 estimate remains informational.
Scope/identity/product changes still require review/clarification when uncertain.

## 2026-09-27 — combined runtime case cleared after two fixture fixes

One QA review's two Important findings resolved in test artifacts only. Final
driver4852af86a5affa25f7a99a24751d14fa7b15c519e70971f180f3e1aab8b7fe44;
Snakefile07e7d20750ba220074e0d51e5e8c284cbb709910488607bd2969e03510c88971.
Coordinator checked exact hashes, actual node200 strict native materialization
receipt, and Step2 source: injected exception escapes real CREATE call; reentry
uses original durable intent/current UID, disallowing a second CREATE. The tiny
archive uses existing libzstd, no dependency install or image rebuild. Earlier
fixture/CLI ABI failures retained; only final actual node200 check is accepted.

Cleared original owner to execute COMBINED01 under existing30 authorization,
starting18, expected11 more=29 (one reserve). New task-private request/producer
pins and actual environment/identity checks precede launch. No extra product
change, shared release or production. Same-UID response-loss and new-UID manual
resume have separate assertions; no normal/automatic/API/Airflow E2E claims.
All helpers/readers included; no status-query loops that repeatedly CREATE.
Actual cloud execution and acceptance pending; preserve evidence if blocked.

## 2026-09-27 — exact historical Worker image restoration authorized

User replies "同意" to restoring the cached old image unchanged under one
test retention tag. Scope is digest2b8070049c3a44319af6d6db9bb7f994af744e8b4f8aacf054071a8a4eee6394,
cached imageID378289a2e52b68c067021581b2a9390c3279fd183e2ecc5e10a0d6e605a7433b.
Original runtime owner may tag/push those exact bytes; preserve current8323567
Master tag, frozen run/profile, shared ServiceAccount, references and production.
First refresh exact existing Job state: elapsed time may have reached the native
deadline; do not assume the same Job is still active or force its status.
Cumulative cap remains30 from17, all future helper/reader/fixture Jobs included.
No new image build, version suffix, business Worker change or evidence rewrite.
Continue normal test if existing lifecycle permits, then review minimal combined
fault/resume driver and its exact budget before cloud submit. No PASS claimed.

Restoration result independently checked: worker-retained-push-2b807004.log
reports tag wgs422-p0-worker-retained-2b807004 with exact original digest above;
worker-retained-manifest-2b807004.json is a retrieved registry manifest whose
config digest equals the cached imageID. Current832 Master tag preserved.
NORMAL01R3-master-events-after-restore.json records original Master UID with
DeadlineExceeded at2026-09-26T23:03:12Z; absence is not the source of this finding.
No clinical data or frozen Job/profile changed. One original native Step3 read
authorized within remaining budget to mirror real evidence; result still pending.

Step3 result: original native call returned1; one evidence reader created/removed
as18. Mirrored NORMAL01R3-8323567/mirror/RUN_FAILED.json independently read:
correct original Job UID, stateFAILED, exit_code0, analysis exit null,
evidence_complete=false. Strict validator rejects incomplete/inconsistent failure
observation. Preserve as deadline-interruption evidence, never rewrite to pass.
Owner reports original Worker naturally Completed and TTL-reclaimed after image
restoration; raw terminal/cleanup records requested for independent reconciliation.
Current18/30, no new analysis submitted. Owner preparing small task-private
combined driver for single review, expected10 more Jobs (total28), no product
changes. This cannot close the uninterrupted NORMAL acceptance or auto/API/E2E
claims; separate assertion scopes retained. Local runtime tests not run per
environment policy; current coordinator changes are documents only.

One same-seat QA review of new combined_driver.py2d343007/Snakefile51dd532b:
two Important findings block execution. Fixture must generate the actual
results/<batch>.results.tar.zst required by native materialization; current
text-only manifest cannot pass Step6. Also CREATE exception is swallowed by
the driver wrapper, so it does not exercise native durable-intent reentry.
Owner is correcting these two test-only issues, not product code. Recalculate
helper count (potentially29 total) and validate the precise fixes before cloud
submission. Driver currently unexecuted, count18/30. No additional broad review
or regression suite; no fake results or reduced evidence to fit the budget.

## 2026-09-27 — reviewed candidate installed; normal smoke pending Worker pull

Owner refreshed isolated host/mount/gate checks (PREFLIGHT_8323567.md), built
and pushed8323567 as0.8.7/original tag, installed task-private nipttest target.
Coordinator read raw push/build/import/pin receipts and independently hashed
wheel; pins recorded at CURRENT_STATE. No coordinator SSH or duplicate test.
Evidence root D:/pipeline/task-artifacts/wgs422-p0-integration-20260926/
p0-native-smoke-20260927; candidate-8323567-receipts/{install,import,pins}.log.

NORMAL01R3 actual Step1 return0. Step2 initial kubectl get Job10s timeout leaves
JOB_CREATED/handoff_timeout; same original deadline/UID reentry returns0.
New storage probe is counted, not hidden: count17/30 includes setup13, storage14,
Master15, reentry storage16 and Worker17. Master9c27d7c1-df2a-457e-abfd-24aedfbd3909;
Worker23c8c641-a1d1-4ebd-a0f1-0713f5501514 ImagePullBackOff, actual events pending.
Setup13 TTL-reclaimed. No synthetic-fault acceptance inferred from real timeout.

Budget review: separate normal/reconnect/replacement conservatively33 exceeds30.
Hold standalone FAULT01; existing QA read-only review permits only a task-private
fixed-pin native driver for a new combined case, with real initial context,
writer/request/lock validation, actual CAS and RecoveryCapability checks. Owner
prepares minimal driver for review before cloud submit. No fake WGS prepare or
platform API/DB identity, no lambda-true authorization or forged terminal markers.
Manual synthetic rule failure validates manual resume, not automatic policy.
All additional Jobs count; stop before30 or any uncertain scope/authority change.
No source changes, production, clinical data, profile/catalog pointers or deletion.
Resolved diagnosis: NORMAL01R3-worker-pull-events.log records SWR NotFound for
frozen digest2b8070049c3a44319af6d6db9bb7f994af744e8b4f8aacf054071a8a4eee6394;
coordinator independently read actual kubelet error, not auth/network speculation.
Owner read-only Docker inspect finds exact RepoDigest cached on BS10610,
imageID378289a2e52b68c067021581b2a9390c3279fd183e2ecc5e10a0d6e605a7433b.
Proposed minimal recovery: original bytes re-push under a historical test-worker
retention tag, retaining current Master tag832 and frozen run references. This
would need no new Job/rebuild, but registry-tag expansion not performed pending
user confirmation. No causal assertion that tag overwrite deleted the old blob.
Owner instructed to hold submits/publication and preserve raw logs; Master keeps
native activeDeadline1800, no forged terminal or SFS deletion. CREATE17/30.
Next: obtain precise registry scope decision, then finish normal if possible and
recalculate remaining budget before combined case. Existing evidence protected.

## 2026-09-27 — user approves cumulative30; continuation dispatched

Coordination interruption resolved: after compaction the original owner treated
historical "install only" as current, and performed no new publication/CREATE.
It then directly verified latest userMessage01a0dfc6-306a-7fc2-9d99-a37bb8461675
in this thread (turn01a0dfc6-2ffc-7853-9adc-1d991643c4c8, startedAt1790460702)
approves30 and continued tests; its own latest five turns contain no overriding
user message. Owner confirms resuming12/30. No authority bypass or owner change.

Exact authorization: "确认允许上限调整到30个，然后继续完成测试". Prior12
CREATEs remain counted; all setup, storage/evidence/log readers, Masters and
Workers share the30 cap. This supersedes the unanswered22-to24 proposal below.
Following the just-discussed T3 gap, track true replacement separately from the
original same-UID FAULT01; original runtime owner must first specify the real
fixture/injection/registered entry and full remaining count, not invent evidence
or bypass guards. Existing two cases may proceed while that plan is checked.

Dispatched to existing owner chat019f8355-2b77-7413-9553-6670c35a1a2f. Owner keeps
native source/artifacts/remote commands; coordinator owns docs and evidence review.
Approved candidate source8323567 uses version0.8.7 and original Master tag; record
new digest/hash. Only task-private nipttest --target install and fixture jobs:1
correction, no WGS install/sharedprofile/catalog/ACTIVE_ASSETS or production changes.
Sequential cases, max1Master+1Worker concurrently. Preserve all old failed runs,
local/SFS inputs/results/evidence/locks; precise test-Job retirement only via
existing scoped runtime/TTL. No namespace-wide cleanup or data deletion.

Target remains isolated BS10610/node200/CCE smoke roots recorded in prior ledger;
owner must refresh live hostname, effective identity, gates and mounts before
remote mutation. Coordinator has not run SSH or runtime tests. Initial platform
worktree clean atc0d19e7. Tests/results not complete. Next: review owner raw release,
normal/reconnect/replacement and counter evidence. Rollback keeps old immutable
pins/evidence; never roll back by deleting project outputs or historical locks.

## 2026-09-27 — audit resume feasibility; no cloud continuation

User challenged preserving the old Pod-dependent resume mechanism. Read-only
source audit: platform351fdbe on this test worktree and native8323567 at
D:/pipeline/cce-pipeline-worktrees/p0-validation-artifact-20260925. Actual
executed candidate remains d29d1ba; no artifact/source installation this turn.

Traced cce_paired_runtime.resume_registered -> WGS/GATK Resume capability ->
native _advance_recovery_view. Failed, TTL-absent old Job is accepted only with
bound final snapshot and full current/lineage Worker quiescence. Replacement
creates new UID/generation, retains frozen inputs/attempt/workdir; shell resume
classification reads config/run-id and uses unlock/rerun-incomplete, not an exec
into the old Pod. Active reconnect and replacement are different operations.
Native _recovery_final_evidence requires START, RUN terminal and sealed snapshot;
SIGKILL/OOM/pre-confirmation failures may not produce these, so they are NOT
guaranteed recoverable. No proposal to bypass this guard or fabricate evidence.

Corrected ambiguous docs46 handoff sentence; added feasibility/acceptance limits
to docs46, spec, lifecycle plan, docs08, CURRENT_STATE and TASKS. Existing
FAULT01 lost-CREATE-response/same-UID case cannot prove new-Master checkpoint
continuation. T3 needs one genuine replacement and unchanged successful-output
proof before closing; scenario/entry/budget must be confirmed separately, not
silently added to the existing two cases. No new implementation authorized here.

Commands: Get-Content/rg/git status/rev-parse for local source and docs; final
git diff --check and scoped diff/link review. Some initial rg arguments used
Windows-incompatible wildcard paths and returned errors; corrected to explicit
files or directory plus -g, no runtime side effects. No pytest/cloud tests run:
this is a documentation/source audit, not execution. No SSH, so no hostname,
mount, directory permission or deployment revalidation claimed. No services,
scanner, dispatcher, credentials, data, locks or Jobs changed. Existing native
dirty tests/test_recovery_monitor.py preserved. This worktree was clean initially.

Next: communicate conditional feasibility and the real acceptance gap before
resuming owner smoke work. CREATE12/22 and unanswered24-cap request unchanged;
this audit is not that approval. Rollback is docs-only Git revert; no runtime
release or data rollback is involved. No main/production merge or push.

## 2026-09-27 — user authorizes normal-path convergence and smoke completion

FINAL WAITING CHECKPOINT: native8323567 fixes only the ordinary native failure
projection;4 remote tests PASS and same reviewer approves the increment with
no new Critical/Important. Coordinator parsed GREEN XML and raw real
START_CONFIRMED/RUN_FAILED/analysis.log, not only the owner's summary. This source
has NOT been rebuilt/published/installed; actual candidate remains d29d1ba.
Source is on jiucheng/release/p0-validation-20260925; origin is the existing
read-only bundle, not a claim of remote source push. Unrelated dirty
tests/test_recovery_monitor.py remains untouched.

Native RUN_FAILED binds Master UID/config/START, scope master_process and
preflight0/analysis1; native failure display does not grant replacement recovery.
Synthetic profile jobs:1 correction/new fixture is planned, not a completed run.
Owner retired storage helper#10 UID2e2732a8-6d63-4289-8d53-4ffb8b814d52 through
its exact native journal/cleanup_only to CLEANED. Owner's final exact GETs for
Master/#10/#12 are empty. No Step6, lifecycle-lock release or local deletion.
Observer exited on empty Pod list and logs API was NotFound; complete observer
coverage is NOT claimed. Native SFS terminal and analysis/preflight logs persist.

User22→24 budget reply is still pending:12used,12additional expected for the
same two cases (setup1+normal5+fault6). No new cloud CREATE/relaunch or further
publication until continuation. Full smoke NOT accepted: Step4–6 and FAULT01
remain unexecuted. Evidence: CANDIDATE_RELEASE_AND_SMOKE_STATUS.md and
REMAINING_SMOKE_CREATE_BUDGET.md under the original task-artifacts smoke root.
Next after approval: fix only synthetic jobs profile in a new fixture, rebuild
8323567 as same0.8.7/original tag, pair isolated consumer, run same NORMAL01/
FAULT01 throughStep6 with exact budget and final permissions/TTL evidence.

Latest live checkpoint: d29d1ba Master published under original tag with digest
sha256:d463693b7a309a3c1f21a072d6882f9a571d66e1ac1d0da2a4482fad314f3b24.
Final wheel0.8.7 is under task-artifacts/p0-native-smoke-20260927/wheels-d29d1ba,
SHA b48c50f9f115cf1d5ee8e71013080bbae29b1caf919bd97d50762519a98753e0;
coordinator independently hashes it and reads23-source/commit verification.
Root-level same-name wheel is older01c43dc provenance, NOT final delivery.
Owner reports isolated candidate-d29d1ba install/pins/real registration PASS.

NORMAL01R2 Step1 returns0; storage helper#10 is reused by Step2, no extra storage
probe CREATE. Master#11 UIDef21511a-3644-4efa-93f5-c2412f4cb2ce reaches
START_CONFIRMED/preflight0, then analysis1/noWorker because synthetic Snakemake
profile lacks jobs:1. Exact log says maximum parallel jobs/nodes must be set.
Step3 creates/deletes evidence reader#12 and mirrors real START/RUN_FAILED/logs,
then fails on platform-only recovery_context in its failed branch. This is a
native status-consumer defect, not authority to fabricate context/recovery proof.

Owner may correct only native UID-bound failure projection and its focused
case; platform recovery validation stays strict. Synthetic jobs:1 correction
needs a new isolated fixture/run, preserving old frozen inputs and failure
evidence. Cumulative12/22; estimated remaining normal5+fault6+setup1 needs24
total. Async user question requests22→24, with no new scenarios/production.
Until answered, no new cloud CREATE/relaunch; only code correction, evidence
retention and previously authorized precise cleanup/TTL observation continue.

Latest checkpoint d29d1ba: native Step3 compares optional recovery_context
correctly while rejecting foreign annotations. Two parameter cases RED2;
foreign case GREEN, normal fixture assertion corrected to actual PENDING
status and only that case rerun GREEN. Coordinator read all3JUnit receipts;
same-seat reviewer approves this increment with no remaining Critical/Important.
Original owner continues final same0.8.7 archive publication, isolated install
and the two native smoke cases. No new cases, production changes or full tests.

Final source checkpoint01c43dc supersedes94fb214: incremental reviewer found and
owner fixed cleanup_only first GET bypassing nonfatal cleanup. Real runtime
Step6 case RED1/GREEN1 independently read; same reviewer now approves source
with no remaining Critical/Important in this scope. No additional full-suite
tests. Owner is cleared to publish the final exact archive as version0.8.7 and
the original candidate Master tag;94fb214 build stays unpublished provenance.

Consumer scope: existing nipttest interpreter, wheel --target --no-deps into
task-private candidate/site-packages, exact installed-source test pins and
synthetic-only profile. Do not overwrite shared site-packages/paired config,
shared r2/catalog/ACTIVE_ASSETS or production. Record actual import path and
hash; isolated install is not global deployment. Same NORMAL01 replacement
uses batch NORMAL01R2 and run_id P0SMOKENORMALR2-a1/native attempt1 because
native run_dir/OBS prefixes derive from batch, not run_id alone. Preserve all
old NORMAL01/P0SMOKENORMAL-a1 resources/evidence and record supersedes; FAULT01
retains its unregistered identity. CREATE9/22 remains cumulative.

FAULT01 clarification (verified against the original smoke-entry review): hide
one real Master CREATE response, then adopt the SAME UID without duplicate
CREATE/START. Keep attempt and generation1. This is uncertain-submit re-entry,
not failed-Master replacement or Airflow automatic recovery, and does not prove
skipping completed rules. Coordinator's generic generation-increase reminder
does not apply and is withdrawn; no extra fault scenario is added.

Before cloud CREATE owner found Step3 live identity assumes every selected owner
has recovery_context, but native initial handoff correctly does not. Scope a
single presence-aware annotation comparison and native-handoff-to-Step3 case;
platform recovery_context validation remains strict. Candidate01c43dc was pushed
but has no production consumer; final source/artifact acceptance is superseded
pending this necessary integration correction. Two smoke runs still unstarted9/22.

Follow-up design refinement: ordinary Step1/2 have no Running Master yet and
Step4–6 follow its termination. Runtime owner will therefore use the existing
same-run journal to reuse at most one live readonly helper, executing fresh
probes each time;600s deadline remains fixed and terminal TTL100. FinalStep6,
business failure or trusted-Master replacement cleans the exact helper. No
stale proof, new service or unchecked repeated CREATE. Pending deletion is
reconciled before replacement.

Diagnostic Job9 UID1f1a8683-7177-4b24-b5f2-77f99c193421 reproduced preSTART
shell line2 pipefail/CR error on the existing candidate image. Runtime owner is
preserving raw evidence and correcting packaging. Coordinator read-only
`git ls-files --eol scripts/run_cce_master_job.sh` confirms indexLF/checkoutCRLF;
no code was edited by coordinator and no image is claimed fixed yet.

The old NORMAL01-r2 is frozen to that image and already has CREATE_INTENT and
JOB_CREATED without native START/terminal evidence. Preserve its bundle,
journal, locks and failure evidence. Coordinator selects a new isolated
run/attempt/run_dir for the SAME NORMAL01 case after corrected artifact
publication, with explicit supersedes provenance; never mutate the old frozen
manifest or replay its CREATE. FAULT01 remains unregistered and may prepare
against corrected pins. Two-case scope and cumulative9/22 budget are unchanged.
Coordinator independently parsed the copied JUnit receipts: reader behavior16
PASS plus2policy PASS after correcting only private test layout/ACL inheritance;
startup observation3new cases plus2affected handoff cases PASS. Failed RED and
fixture-setup receipts remain retained, not relabeled. Files are under the
original task-artifacts/p0-native-smoke-20260927 root.
One fresh read-only reviewer found an N2 edge case: saving cleanup_pending inside
the deferred-cleanup exception handler may itself fail and mask the original
probe exception. Native94fb214 contains the correction; two injected cleanup
failure cases pass. New native receipts show9PASS in the first group,3PASS in
the affected correction group,9PASS for CAS/probe regression; fixtures/errors
and RED receipts remain available. Coordinator read the XML counts. The same
reviewer now checks only new startup/CLI/current-Master integration and that
cleanup correction. No source acceptance is claimed before its conclusion.

Owner built94fb214 via exact git archive, not CRLF working-copy tar. Version
remains0.8.7; wheel SHA73163d24bac8dfe7db4a7a3a05c6471e9cb9b3843e9c5c3fa9d326046293406c.
Build LF/bash-n and wheel sourcecommit checks reported PASS; no push/install/
profile binding yet. Coordinator is not performing image build/publication.

Goal: preserve production0.8.5 normal Step1–7 semantics while retaining necessary
P0 recovery/fencing and timely Job cleanup. Latest user approves scoped repairs,
original two-case test continuation and necessary candidate publication using
the same version/tag (0.8.7; no new suffix). TTL100 remains; the discussed return
to86400 is withdrawn. No BS96 deployment, T4, clinical workflow change or broad
data deletion. Business output remains755/644; credentials stay private.

Coordinator read source, current plan/state and boundary; updated plan N1–N5,
spec, docs08, CURRENT_STATE and TASKS. Original huawei-cloude runtime/Infra owner
is authorized to handle native probe simplification, bounded exact read-only
helper cleanup, startup-log capture/root-cause repair and matched artifacts.
No owner may guess NFS/SFS equivalence or reuse stale probes as current evidence.
Present probe checks root inode/path, not arbitrary target mv/recreation.

Test scope remains exact NORMAL01/FAULT01 roots and known owned test Jobs,
starting8/22 total CREATEs. Helper deletion uses bound UID/RV; normal terminal
Job/Pod TTL is permitted. No local/NFS project, result, FASTQ, pending or evidence
is deleted. Previously failed Master cce-master-fe030195de2da0bc5ab6 UID
b6b2aeea-dd9c-4442-90fd-f55c8580411d was already TTL-reclaimed; keep its records.
Cloud startup diagnosis must capture real failure evidence before deciding a
fix; unknown/missing evidence never grants automatic replacement or fake START.

At this checkpoint no new runtime test/deploy ran in this coordinator turn.
Source acceptance and completed smoke are pending. Rollback uses retained exact
source/artifact digests, not semantic version alone; do not reset active locks,
history or replace production settings. Scope/identity/permission uncertainty
must be reported before expanding work.

## 2026-09-27 — Step1 succeeds; separate Master startup blocker stops smoke

Original owner used only task-process WGS_REAL_OBSUTIL_BIN already configured
by existing runner; Step1 exit0, OBS200 for33B synthetic input and154B marker.
Step2 reader#7 passed, Master#8 cce-master-fe030195de2da0bc5ab6 created with UID
b6b2aeea-dd9c-4442-90fd-f55c8580411d, Pod suffix2qsdl. Events UTC:
2026-09-26T18:25:40 SuccessfulCreate;18:26:00 Started;18:26:02 BackoffLimitExceeded.
TTL100s subsequently removed exact Job/Pod; no Worker. Container failure cause
not available from events alone. Correct records are bundle/evidence/
P0SMOKENORMAL-a1/MASTER_CREATE_INTENT.json and MASTER_HANDOFF.json, sameUID and
deadline1790447735.173923, stateJOB_CREATED/noSTART. Root-directory record absence
was an incorrect early check and must not be used to infer no Master submission.
Original Step2 wait Ready exited1 naturally at its timeout; do not resubmit.
Finite static checks found required env, temporary mounts and fixture paths
generated, no obvious path mismatch. This is not proof of container root cause.
Coordinator directed only finite static/retained-evidence checks; no extra reader,
Master retry, TTL change, FAULT01 or new product repair. Ask user about separately
scoped Master-startup diagnosis with bounded startup-log capture. CREATE8/22;
cap adjustment covered only nativeStep5 log Job each of original2cases. Keep all
history; production/shared install/profile unaffected, no local data deletion.

## 2026-09-27 — real cleanup passed; task-only upload environment continuation

Owner reports reader#5 cce-evidence-8cc1433ddc4c4f00beb6a7a1 absent in precise
BS10610 query and matching private journal CLEANED. Step1 reached upload wrapper
but exited127: WGS_REAL_OBSUTIL_BIN missing from ad-hoc SSH process. This is not
missing native obsutil or broken shared runner: existing test/prod runtime.env
both define executable /bi/software/obsutil_5.8.3/obsutil; forced command exports
it and gate inherits environment. Read-only diagnosis required no shared writes.
Coordinator directed original owner to supply that verified variable only to
task process and continue original two smoke cases. No further code repair or
credentials/shared config modification. Count5/20; no Master/Worker or upload
receipt yet. Keep earlier failures and no live PASS claim until actual completion.

## 2026-09-27 — reader cleanup candidate source and regression reviewed

Native `4488d10`: cce_writer_guard.py cleanup wait30→90s and one focused regression
in test_cloud_storage_identity.py. Coordinator independently inspected diff and
copied JUnit `p0-native-smoke-20260927/junit-cloud-reader-cleanup.xml`:5 tests,
0 failures/errors/skips,13.666s. Prior16 handoff tests were not repeated.
Guard SHA2564b3ce8c5e4c02352b753b659d1c9f5faeda90ddd627686416492c337676a0119.
Default30s Pod grace overlaps old30s Foreground confirmation; a35s modeled
deletion reproduces old failure and passes correction. Live delayed absence was
observed, but first TRANSPORT failure is not proven caused by this timing.
Owner updated only task candidate/policy pins and reconciled exact reader#4 to
CLEANED via native Step1 (expected fresh-probe-required exit, noCREATE).
Shared installation and Master unchanged. NORMAL01 real upload and remaining
smoke still require actual completion evidence; no production promotion.

## 2026-09-27 — reader-cleanup repair and smoke continuation authorized

User replied "修复后继续完成" to the scoped cleanup-blocker question. Original
runtime/Infra owner huawei-cloude has been instructed to establish root cause,
fix only helper cleanup, run minimum relevant remote checks, and continue the
same NORMAL01-r2/FAULT01-r2 native smoke. Coordinator maintains docs/evidence.
Existing 16 handoff tests remain valid for unchanged source; no redundant suite.
Before new Step1, reconcile reader #4 UID385ccca8-def8-4b56-8473-956f0a81500c
DELETE_INTENT through the same node200/ctapa native entry; no journal reset.
Cumulative Job CREATE count remains 4/20. Source timeout/grace interaction is a
hypothesis, not proven root cause. No shared install/profile/assets or production
changes authorized. No execution acceptance claimed until actual receipts exist.
Rollback remains task-local candidate selection; preserve test paths and evidence.

## 2026-09-27 — live smoke failed before upload; further retry stopped

Completed authorized source slice: nativeed39d21 and16 selected remote tests,
with coordinator diff/hash/JUnit review. Two isolated bundles prepared; NORMAL01
registered through genuine pinned test producer. Source and shared deployment
must not be conflated: installed0.8.7/Master/shared release unchanged.

Actual commands/results (native Step1 through task-specific operator/bootstrap):
1. NORMAL01 Step1 exit1 in cloud_storage_identity finally: RecoveryQueryError
   `recovery query: TRANSPORT`. No upload function entry or upload receipt.
2. Same-node ctapa read-only check confirmed originalPID exited, exact helper
   absent and matching journalDELETE_INTENT. Native reconciliation call exit1
   `cloud reader cleanup reconciled; fresh probe required`, journalCLEANED, noCREATE.
3. Sole authorized Step1 retry exit1 `cloud reader cleanup pending`; new helper
   Ready then subsequently absent in BS10610 read; last node200 journal remains
   DELETE_INTENT with matching name/UID. No further cloud actions authorized here.

Total testCREATE4/20: setup#1 UID9c2889e8-2583-42e4-a24f-e849db159a84;
setup#2 UIDc34a17d7-2fb0-4b74-9141-1f7dcb102ff0; reader#3
fc61d94f-1e50-4419-93bc-7578643d3a78; reader#4
385ccca8-def8-4b56-8473-956f0a81500c. Both readers laterAbsent. No Master/Worker,
no Step2–6, no fault injection. No broad cleanup or local-data deletion.

Inspected source uses30s cleanup deadline; exact root cause of late confirmation
is not proved. EarlierPID D/wait_iff_congested is an observation, not confirmed
NFS root cause. Do not skip validation, reset journals or repeat uploads blindly.
Evidence: D:/pipeline/task-artifacts/wgs422-p0-integration-20260926/
p0-native-smoke-20260927/SMOKE_BLOCKER_RECEIPT.md (coordinator read), plus JUnit.
Next: user decision on scoped reader-cleanup diagnosis/correction; before any
resume, reconcile exact#4 journal and resource via original node200 identity.
No production/other batches changed. No production rollback needed; preserve
test paths/evidence and leave shared install unchanged. Platform docs committed
only on test branch; no main/production promotion or smokePASS claim.

## 2026-09-27 — initial CREATE fix source and focused regression verified

Native owner committed `ed39d21` on jiucheng/release/p0-validation-20260925:
only cce_batch_runtime.py and tests/test_master_handoff.py (111add/2remove).
Coordinator inspected full diff, atomic file+directory fsync/guard locking and
source hash71d7c041943607e112713b75732e4ba5ade1bf63354b5620d635c1f4dd1998a1.
Owner reproduced3 RED cases then GREEN on node200/nipttest isolated task root.
Local read-only JUnit inspection confirms16tests,0errors,0failures,0skipped.
Artifact: D:/pipeline/task-artifacts/wgs422-p0-integration-20260926/
p0-native-smoke-20260927/junit-handoff.xml. No local runtime tests performed.
Existing normal/start/deadline cases included; no full suite rerun. Native origin
remains a read-only bundle, not pushed. Unrelated dirty test_recovery_monitor.py
preserved. Original owner now prepares live tests; no cloud acceptance claim yet.
No installed package/Master/shared profile/production change. docs08 updated with
the internal intent/reconciliation contract; rollback is task-local candidate
selection, never deleting existing projects/evidence.

## 2026-09-27 — explicit confirmation resumes scoped fix and smoke

User answered "确认" to continuing smoke and allowing the original owner to
fix the first-Master CREATE lost-response gap. This resolves the preceding
install-only conflict. Dispatched to the same native/Infra owner, not a new
implementation agent. Required: durable bound intent before CREATE, original
deadline, exact manifest/identity verification before same-UID adoption, no
duplicate CREATE or fake terminal evidence. Validate only the affected contract
and original two isolated smoke cases; preserve all unrelated resources.
Coordinator owns platform state docs; native owner owns source/test deployment.
No production, WGS rules, UI/API/DB, plugin feature or shared release change.
Do not claim tests passed until fresh results/UID/output evidence is checked.

## 2026-09-27 — smoke blocked; no normal/fault PASS

Original owner reports a newer direct user install-only instruction, turn start
2026-09-27 00:22:08+08, after smoke authorization. Stop new mutations and ask the
user to resolve scope; do not treat the historical install command as authority
without time verification. Normal Step1–6 and fault injection both NOT RUN.
Initial-CREATE response-loss source defect remains unfixed; user decision pending.
Only setup Job #1 (UID9c2889e8-2583-42e4-a24f-e849db159a84), task control/evidence
roots and four new SFS directories were created, detailed in the smoke review.
Last read-only observation: setup Running0/1; manifest sleep1200s, hard deadline
1800s, no TTL configured. No automatic deletion claimed; no cleanup performed.
No production, historical batch, shared release, product source or database
changes. Local git diff --check is documentation validation only, not smoke.
Next: resolve instruction conflict, scope native fix separately, then resume
remaining tests with original owner. Preserve setup files/directories as evidence.

## 2026-09-27 — native smoke fault preflight exposes initial CREATE gap

Normal test preparation continues with the original owner. Setup Job #1 verifies
the real PVC using non-root10001:520; necessary new test-only ancestors allowed,
existing paths protected. No production or unrelated Job is modified.
Coordinator/source owner confirmed step2 persists JOB_CREATED only after CREATE
response. Lost response leaves no handoff; re-entry rejects missing schema2/UID
identity. Fault injection NOT RUN (not a test PASS or observed live failure).
No fabricated journal/FINAL or replacement-path substitution; product correction
needs scoped follow-up. Review: docs/reviews/2026-09-26-p0-smoke-entry.md.

## 2026-09-26 — user approves scoped smoke fixture and execution

2026-09-27 refinement: original owner confirms an isolated native deployment can
use unmodified0.8.7 runtime/guard with a separately pinned test producer; no WGS
API/prepare impersonation. Approved two sequential unique runs, max1Master+1Worker
concurrent, initial total Job cap8 including helpers. Normal Step1–6 followed by
one exact Master CREATE whose real success response is hidden once client-side.
Verify same UID adoption/no duplicate CREATE and genuine downstream completion.
This is native uncertain-submit reconciliation, not failed-Master replacement or
Airflow automatic recovery. No fake failure seal, no rule-output-skip claim.
Owner creates task-only profile/asset/control roots, verifying SFS mapping first;
shared profiles/ACTIVE_ASSETS and existing platform bootstrap remain unchanged.
Execution pending; details in docs/reviews/2026-09-26-p0-smoke-entry.md.

Preflight refinement before any mutation: ordinary BS10610/node200 NFS is not
the SFS PVC mapping. Owner correctly stopped instead of selecting mounted mode.
Fresh cloud-reader is required per protected stage; coordinator's initial8-Job
estimate could not cover the same two cases. Coordinator explicitly revised the
cumulative CREATE cap to20, including one exact task-subtree SFS setup Job and
all read/export/fault re-entry helpers. No extra test cases or concurrency:
max1Master+1Worker; helpers serial. Exact UID/name evidence, non-root business
755/644 and existing-state protection retained; no validation shortcut.

Pre-submit check: two unrelated active cloud Jobs preserved. The prohibition on
other-batch starts limits our actions, not all cluster users; no global-idle gate
or production scheduling change is required. Check quota before bounded starts.
BS10610 ordinary NFS write returned read-only despite mount `rw`; original owner
uses the approved ctapa/node200 writer for the verified task root, without mount
or permission changes. Cloud setup/test execution still pending at this checkpoint.

Latest user direction: "按你建议完成测试" after explicit fixture/fault/test-only
configuration proposal. Original runtime/Infra owner has the execution task;
coordinator owns state/evidence. Only isolated non-clinical test assets and needed
BS10610 test configuration are authorized, with before/after gate state recorded.
Keep production, formal WGS workflow, shared profile/assets, previous batches and
all existing local results/pending protected. No destructive cleanup authority.
Do not bypass trusted registration/identity/classification or hand-author terminal
success. Use a bounded test-process API fault only if the genuine installed
producer can record it, and label injected versus live evidence. If a real UI
submission needs a new adapter/API/product behavior, stop and explain instead of
expanding code scope. The prior readiness-only outcome remains historical evidence.

## 2026-09-26 — bounded P0 smoke requested; entry audit

Outcome: entry audit and fresh readiness complete, live smoke NOT executed.
SSH reached server10610 as chenjc. Existing inspected verify_p0_test_readiness.py
exit0: five actual service checks, flags, gateway health and catalog receipt PASS.
Allowlisted backend env inspection shows test-project=false, WGS/GATK recovery
unset (code defaultfalse), execution/runtime=true. QA and original native owner
confirm the old smoke is submit-rejection-only; no submit-ready tiny workflow or
real allowlisted fault-injection entry was found in the checked sources.
The native generic bundle alone lacks trusted platform registration; existing
platform test-project validation still requires release WGS_pipe.smk/all. Do not
bypass these with hand-authored receipts or modified frozen inputs. Missing
prerequisites: scoped test fixture/entry and test-only activation/fault plan.
No failure-injection/normal-run command was attempted because those prerequisites
are absent. No services, gates, shared assets, database or running workloads changed.
Only docs changed; no runtime rollback required. Details and next decision:
docs/reviews/2026-09-26-p0-smoke-entry.md. Earlier33/4/3 evidence retained, not rerun.

User: smoke validates P0 only; full WGS batches follow a separately authorized
production deployment. Latest instruction: complete testing. Current scope is
isolated BS10610 normal Step1–6 plus one bounded existing recovery scenario.
Original runtime/Infra owner was asked to inspect the deployed entry before
execution. No live smoke or fault has yet been started. Preserve BS96, shared
release/profile/assets, all existing batch inputs/results/pending and credentials.

Static inspection: scripts/bs10610_wgs_phase1_smoke.py writes non-FASTQ placeholder
bytes and expects submit HTTP409; it cannot validate the installed P0 runtime.
Existing selected-monitor synthetic tests already cover normal/recovery with
mocked Kubernetes/OBS transport and are not a live deployment smoke. Do not
re-run those unchanged tests or report them as a new real-cloud acceptance.
Next: establish an approved executable fixture/fault boundary without production
code or release mutation, otherwise report the precise missing prerequisite.

## 2026-09-26 — A1–A4 delivered to test; final handoff

Goal complete for this authorized slice: corrected normal registration/owner/TTL
paths and755/644 generation, matched native/platform test deployment. Not full
T1–T5, no T4/API/schema expansion, no real/synthetic business run or production
service promotion. Shared r2/assets were explicitly authorized separately.

Platform functionale358aad; native0.8.7/e2962a2; unchanged plugin0.6.4+bs8.dev2.
Master2b807004..., r2c98b13c6..., assets20260926.2-wgs422-p0 and genuine exported
receipt220c51d3... installed/published. Receipt JSON is committed under docs/releases.
Minimal remote evidence reused: native33 pass, WGS/GATK normal/recovery4 pass,
final changed GATK3 pass; one joint review closed3 Important findings. No extra
business canary/full suite. Native build and all remote operations stayed with
the original owner. Only static Git/document checks ran locally.

Original-owner final receipt:
`D:/pipeline/task-artifacts/wgs422-p0-integration-20260926/R4_DEPLOYMENT_RECEIPT.md`.
Five containers now use sourcee358aad at
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260926-p0-e358aad`.
Actual control: `candidates/p0-e358aad-control/compose.json` under that control root;
prior five-service rollback: `candidates/step7-ae416fa-control/compose.json`.
Catalog parent `candidates/p0-e358aad-catalog`, backendrw and observer/workerro.
AUTHtrue, release_managementtrue, scanfalse, auto_dispatchfalse. Existing
authenticated registration+CAS changed current4.2.1 to wgs-4.2.2-3b1dae5, and GET
readback matches. Gatewayhealth200; final actual mounts/flags/catalog checks PASS.
Other DAG pins, protected service containers and frontend image retained.

Node200 `/home/ctapa/.config/airflow-wgs-test`12-file closure installed, old3 files
in `.p0-install-20260926/backup`. Policy `paired-writers-v2.json` and platform
`cce-paired-deployment-v1.json` are private0600 in that root. Native bootstrap:
`/sg2/33.chenjiucheng/software/miniforge3/envs/nipttest/lib/python3.9/site-packages/cce_pipeline/assets/cce-paired-deployment-v1.json`.
Journal:
`/sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-ctapa/wgs-runtime/paired-writer-journal`.
Platform selected_runtime/native schema2 cloud-reader load both PASS. Private
control modes do not change the new business0755/0644 contract.

Handled operational failures: default-system Python py_compile exit1 (too old)
was rerun once with the configured Python3.9 and passed; no code/environment fix.
After service switch, gateway502 was stale Nginx upstream (.4 versus new .9), not
backend failure; nginx-t and graceful reload restored200, no frontend rebuild.
Earlier SWR auth failure resolved only after user confirmed login restored.

Remaining source delivery limitation: native branch
jiucheng/release/p0-validation-20260925 has only read-only local bundle origin,
so e2962a2 is committed but unpushed. No remote/credentials guessed; unrelated
native CRLF edit preserved. Platform test branch is pushed; no main/production merge.

Rollback requires fresh idle/no-live-v2-owner check. Never deactivate a paired
bootstrap while a new run depends on it. Restore only exact prior five-service
configuration and matched gate/runtime after that check, preserve catalog/journal/
data/evidence, and reload Nginx as needed. Shared profile rollback requires an
explicit coordinated decision; old exact bytes retained. No rollback performed.
Next: user-selected bounded business verification or deferred lifecycle work as
separately authorized; do not launch a batch merely to repeat this readiness.

## 2026-09-26 — assets complete; precise test platform switch agreed

Asset Job cce-assets-wgs-4.2.2-r2-20260926.2-wgs422-p0 Complete1/1;
live status PASS/state_verified=true, completed2026-09-26T14:43:23Z.
Native release.export canonical receipt SHA256
220c51d3499fabc0c550204bfa254d1bf993797d86d6768a5c5b10465ca0162a.
Actual test catalog has no wgs-4.2.2-3b1dae5; first registration may use that
source-derived ID. Assets ID is separately20260926.2-wgs422-p0. Original historical
JSON is retained. Unactivated r3 shared candidate file removed by original owner
after exact-hash check; its local evidence copy remains. Only r2 is selected.

Platform staged at control-root/releases/20260926-p0-e358aad. Existing mixed
mounts do not follow current. Agreed minimal service actions after active0/config
preflight: backend+observer /app to e358aad/backend; Airflow API/scheduler/worker
bio_wgs.py only to e358aad, preserving unchanged common/GATK/other DAG pins.
Frontend only if the integrated source needs a build, using existing offline SOP;
no extra full tests. Preserve DB/Redis/scanner/reference/probe/metrics containers.
Use explicit services and --no-deps --pull never. Keep current symlink historical.

Test-only release management enablement includes managed writable catalog parent
for backend and same parent readonly for consumers; do not remount all /config.
AUTH retained, scan/dispatchfalse and execution/recovery gates not silently enabled.
First register authentic receipt and CAS-select it. Node200: existing ctapa test
forced-command/key retained, no authorized_keys change; update gate/helper closure
and paired policy/bootstrap from fixed source under existing trusted deployment
roots. Repository wrapper hardcodes production root and must not replace the test
wrapper. Exact prior service mounts/configs/gate files retained for rollback.
This records planned service operations, not their completion.

## 2026-09-26 — final0.8.7 artifacts and authorized resource publication

Native commit e2962a2cfdc5c81a081fe6a6b578f22cafe2d2ca; wheel SHA256
e26b8ebfaf957ee5b6813135aaffb874b0f8fe07796d6ac33935198f4559ccc9.
Master `swr.cn-east-3.myhuaweicloud.com/biosanwgs/wgs-cce-master` digest
sha256:2b8070049c3a44319af6d6db9bb7f994af744e8b4f8aacf054071a8a4eee6394.
Installed by original owner through node005 writable entry; node005 and BS10610
confirm0.8.7/e2962a2, no WGS environment change. Existing source checks reused;
only rebuilt artifact identity/version checks performed.

Exact publication intent is recorded before mutations at
`D:/pipeline/task-artifacts/wgs422-p0-integration-20260926/R2_ASSET_RELEASE_INTENT.md`.
Asset ID20260926.2-wgs422-p0. Old r2 bytes backed up outside shared profile dir;
old asset status re-read PASS/state_verified for20260926.1-wgs422. Twelve old OBS
objects copied server-side and two new metadata objects uploaded, checksums matched.
Shared r2 atomically replaced with SHA256
c98b13c6de82470bea48d028a6df1dc78f3ce12f566920a79e4ba55bbdf35e8d.
assets validate returned PASS; one Asset Job submitted, currently PUBLISHING.
Do not resubmit or report completed until real state_verified receipt is returned.
No platform service switch or production service/batch action reported.

## 2026-09-26 — explicit shared resource/profile update authorization

After being told r2 is the same NFS file visible from test/production and replacement
invalidates old profile-bound hashes, user answered the explicit shared publication
question: "允许，更新共享资源发布". Together with "r3直接覆盖旧r2", this
authorizes exact shared profile replacement and matching assets/ACTIVE_ASSETS
publication for final native0.8.7. No production service deployment, real batch,
patient/input changes, local deletion, WGS workflow changes or arbitrary SFS writes.

Exact target:
`/mnt/biodevrwbi/33.chenjiucheng/project/cce-pipeline-profiles/wgs/wgs-4.2.2-r2.yaml`
(node200/BS96 alias `/bi/biodevrwbi/...`). Old SHA256
4a016a2d0c1006b013a1e66efc147e29275e0ce8dcd2b086f1488bed8c44d6ed.
Retain exact old-file rollback copy in approved task evidence and old ACTIVE_ASSETS
identity before replacement. Final0.8.7 Master digest, business0755/0644/0755,
same WGS source3b1dae5 and same verified resource bytes. Frozen receipts remain
historical; new asset release and registration get independent IDs/real validation.
Keep old OBS objects/receipts; no destructive cleanup.

Original Infra owner identified bounded publication: new OBS
`Project_resource/wgs-4.2.2-r1/_cce_assets/<new-release-id>/` from verified objects
(pipeline tar/files.tsv, resource files.tsv+9 payloads, new SOURCE_READY), then
existing assets validate/apply/status on declared pipeline130/resource9 SFS paths
and ACTIVE_ASSETS. No additional assets. Record exact new ID/paths before dispatch.
Completion pending; test activation requires the valid matching artifacts.

## 2026-09-26 — user revises candidate naming and profile replacement

User: "r3直接覆盖旧r2" and version0.8.6.1 or0.8.7 instead of0.8.7+p0.dev1.
Selected0.8.7. Native owner notified to stop old-candidate activation, fix version
metadata in a new commit and rebuild/push immutable artifacts; unchanged33+4+3
synthetic evidence is reused. Before replacement, native/Infra owner checks exact
r2 consumers without production DB access. If shared with production, obtain
specific authorization; do not assume test deployment allows production mutation.

Completed previous candidate, not final0.8.7: native90abacd wheel SHA256
06968907956661439a4d0ed8ec5c2e972e1d30818741ec83b3135c2a7d332da1;
SWR digest sha256:6e110ddb68bec6626cd5df4c4bb68c699cdd35f586212310b640a7588c40e757.
Installed in existing nipttest via node005 writable mount; BS10610 reads same
version/commit. WGS environment unchanged. New r3 was created/validated, not active.

Deployment contract finding: backend WgsReleaseRegistration requires matching
assets/release profile SHA/revision; native release.export_release requires real
asset status. Old registration binds r2 SHA4a016a2d..., so overwriting r2 cannot
eliminate the receipt update. Native owner must report exact new asset writes
before expanding into SFS asset publication. No fabricated PASS/receipt or disabled
verification. Platform functional e358aad is committed and pushed on test branch;
no main/production merge. No final platform activation confirmed at this point.

## 2026-09-26 — A1–A4 source accepted; paired test delivery in progress

Scope remains the normal-path correction, not all lifecycle T1–T5. No production,
real-batch action, T4 API/DB/UI, plugin rebuild or biological workflow change.
Original native/Infra owner executed all remote tests; coordinator did not install
or build artifacts. Source review closed all3 Important findings; no unresolved
Critical/Important issue. Explicit legacy schema2 requires exact frozen identity;
new schema3 registrations cannot fall back to missing legacy identity. GATK prepare
generation retry uses unchanged raw request plus exact sidecar/ended process proof.

Evidence root:
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/native-p0-20260926`.
- `native-final-focused3.log`:33 targeted native checks passed, including actual
  CLI main dispatch with simulated transport. Not a live cloud CLI full-run.
- `platform-green-2.log`:4 WGS/GATK normal/recovery cases passed,48 deselected,
  12.26s. Real registration, stable Step1 owner, native handoff/final producer and
  TTL downstream; cloud/Pod transport remains synthetic.
- `platform-gatk-gen2.log`:3 affected GATK cases passed in8.18s after review fixes;
  earlier WGS passes reused, not repeated. Includes existing prepare retry case.
- Local static `git diff --check` only; no local runtime tests or whole-suite run.

Files: paired runtime, GATK gate, selected-monitor and two existing fixture tests,
docs08 and the four progress/plan documents. Native owner committed90abacd with
independent candidate version0.8.7+p0.dev1; wheel/WGS Master build is in progress.
New r3 must bind final immutable artifact digests and version metadata, with
business755/644/755; r2 and historical trees remain untouched. Installation only
in agreed nipttest, never WGS. Platform deployment must use the forthcoming exact
source commit; scanner/dispatch stayfalse. No service switch has been reported.
Rollback retains exact previous mounts/current release/image IDs, r2 and old Master;
do not treat source acceptance as deployed or as acceptance of deferred T4.

## 2026-09-26 — P0 coordination resumed after explicit clarification

User clarified: "对，直接安装已经是过期的命令了". The earlier cross-thread
hold below is resolved. Continue the already authorized A1–A4 correction and
necessary new business-output permissions, minimal BS10610 synthetic validation,
then paired test deployment. Native owner and platform worker notified; same
file ownership, no production/real-batch/T4 scope expansion. Native interface
agreement remains the immediate dependency, not an authorization blocker.
No local runtime tests, installation or remote mutation at this resumption.

Agreed internal contract (native owner implements, platform consumes):
`initial_owner_action(*, pipeline, analysis_id, attempt, run_id)` returns bounded
`initial-` plus stable identity digest; `register_bundle(runtime, bundle, contract,
config, *, identity, control_root)` publishes schema3 frozen per-run registration
under existing trusted journal_root; identity is pipeline/analysis_id/attempt,
control_root comes from the validated gate request parent, not arbitrary payload.
`resolve_current_owner(runtime, bundle, contract, config, *, selected_bundle=None,
expected_master_uid=None, read_only=True)` returns selected_bundle,
expected_master_uid, context, platform_execution and native record. Resolution is
bounded to registered per-run journal names (4096 maximum), exact current owner
and frozen handoff hashes; no mtime/global search or new mutable selection pointer.
`_prepare_submission_view(..., owner_action=...)` propagates the same action through
both native/platform call sites. Platform retains receipt-chain validation.
Current-owner resolution must not claim or create a storage-identity probe;
writes retain fencing. Status observation does not acquire an analysis write lock.

Infra owner reports fresh read-only BS10610 preflight: server10610/chenjc,
current20260912-opt-4d3d24e6; backend /app20260923-step7-ae416fa; scheduler WGS DAG
20260915-main-359df11; active analysis/transfer counts0, scanner/dispatchfalse.
No service switch. Exact test interpreter/root remains to be returned by Infra.
Platform fixture helpers may gain an initial=True branch in the existing
resume_final/registered_recovery harness; old defaults unchanged. This creates
an initially empty state, not an in-test lock reset or future-ID policy injection.

RED evidence returned by Infra owner: BS10610 existing offline WGS candidate
image with task-root synthetic data, selector `-k
normal_registration_preserves_step1_owner_through_ttl`: 2 failed, 48 deselected,
1.58s. Both WGS/GATK entered the test body and failed at native writer_for_bundle
with `protected CLI requires an exact trusted frozen bundle binding`, before
Step1 and with static bindings empty. Log:
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/native-p0-20260926/platform-red-image5.log`.
Earlier attempts did not count as RED: nipttest Python3.9 lacked typing.Self for
the plugin; existing candidate image avoided any installation, then an indirect
fixture dependency declaration needed correction (adapter now explicitly depends
on view_inputs). No production/batch changes. Native/platform implementation
proceeds against this reproduced registration gap; GREEN not yet obtained.

Necessary gate compatibility found while implementing normal-path validation:
GATK prepare uses immutable kind=gatk-airflow-prepare, not a v2 stage request;
legacy start/worker currently emits no dispatcher sidecar, while Step6/recovery
checks require exact ended dispatcher evidence for prepare too. Approved only
within the existing gate scope: in-memory identity projection using existing
generation/execution formula, reuse worker/launch locks and dispatcher sidecar
for prepare, keep raw request/hash, prepare behavior and Step7 unchanged. Validate
the raw prepare hash plus ended process, never success/free-lock alone. Same GATK
normal case will use real prepare format and cover active rejection/ended accept;
no new API/DB/schema or independent dispatcher framework is introduced.

Read-only scope correction during integration: the earlier coordinator shorthand
"no reader CREATE" applies to pure current-owner resolution/storage validation,
not the existing Step3 evidence collector. Node200 has no SFS mount, and TTL may
remove the Pod; the existing bound read-only-volume evidence reader and local
observation mirror remain necessary. Keep that transport/cache behavior, while
explicit read_only=True skips analysis writer.enter/claim and the full write
storage probe. Do not disable evidence refresh or invent a new status collector.
Native owner also removed a proposed mandatory2770 check on existing control
roots: trusted effective ownership/ACL/access is checked, not a forced mode, and
existing directories are not chmodded. Business755/644 remains unchanged.

Infra read-only profile finding: existing wgs-4.2.2-r2 declares2775/0664/0775,
so source support alone cannot establish the new output modes. Within this test
delivery scope create a separate r3 candidate only after final artifact digests
are known, with required corrected artifact pins and755/644/755. Preserve r2,
old batches and biological workflow; no in-place profile edit or early activation.
One fresh read-only joint review is assigned across the two changed source trees;
it adds no test runs and does not replace the pending4-case remote GREEN.

First4-case GREEN attempt reported by Infra: all reached real Step1 registration
and stable Step2 owner/UID binding, then failed in the common test seal helper
reading a not-yet-produced recovery-final.json. Log `native-p0-20260926/platform-green-1.log`
under the same approved remote evidence root. Platform owner is correcting the
fixture to invoke the actual native final producer, not fabricating a snapshot.
Native owner separately reports five focused native checks passing. The combined
integration is still unaccepted; no packaging, deployment or production action.

Corrected fixture: old handoff fixture mocked worker-manifest creation. Restore
the real native producer with only Pod transport simulated; native terminal code
now creates the real snapshot instead of the test writing one. Infra reports
`4 passed, 48 deselected in12.26s`, `native-p0-20260926/platform-green-2.log`.
Native focused result advanced to7passed in1.64s (`native-green-focused2.log`).
Single joint read-only review found no Critical and three Important findings:
explicit static schema2 Step1 is rejected by new registration; GATK prepare retry
generation2 conflicts with generation1 sidecar/immutable request projection;
prepare finished+process=None is insufficient actual termination proof. Native
owner fixes explicit legacy registration no-op with full identity/frozen checks;
platform owner fixes prepare generation/process checks using existing locks.
Do not expand older stage checks or add API/schema. Actual CLI main dispatch is
not yet proved by platform's resolver-only assertion; native owner will cover it
inside existing focused checks. Recheck only affected findings/cases, not a new
full review/test chain. No artifacts or test service switch before this closes.

## 2026-09-26 — P0 normal-path correction started

Authority: user approved fixing the four audited blockers plus related new-output
permissions, then deploying test only. No production, clinical runs, pause/delete
implementation or local-data mutation is included. Baseline5165592 in the existing
isolated integration worktree; primary checkout remains untouched.

Owners: original huawei-cloude thread handles native source/artifacts and Infra
preflight; scoped platform worker handles paired runtime/gate/test changes. Root
coordinates interface, scope, documentation and final review. No cross-owned code
edits or coordinator image/Compose work. Tests remain on BS10610 only, after
fingerprint approval; no local baseline/dependency installs/full suite runs.

Pre-flight contract ledger: platform registration must consume native validated
deployment scope, not invent per-batch global policy; initial stable owner must
survive later platform execution ID; current-owner resolution must serve CLI and
platform without a second retry budget. These are shared dependencies, so native
interface agreement precedes consumer implementation. T4 control table/API is not
needed for this authorized slice and is deferred, not silently implemented.

Read-only exploration: one shared_permissions.py lookup incorrectly assumed the
assets subdirectory and returned path-not-found; no file changed. Native owner
will use the actual source tree. Latest tests/deployments: none this turn yet.
Rollback remains source reversion until a separately recorded paired test switch.

Coordination outcome: native owner explicitly reports receiving the newer user
instruction "直接安装即可，不要做其他不必要的动作" in its own thread and has
paused native design/source changes until the installation target/scope is clear.
Do not override that instruction or install old0.8.6 as the still-unbuilt fix.
User clarification required: does installation-only mean after the authorized
A1–A4 fixes and minimal tests, or does it replace source correction?
Platform worker stopped at read-only findings: WGS `_step_command` and GATK
`_step` already pass payload/gate/pipeline into `stage_command`; registration can
be wired there without DAG/API changes. Current synthetic initial-submission
test manually injects future Step2 ID into policy and cannot prove A1/A2.
No native/platform source edits, remote preflight, runtime tests, installation,
image build or deployment performed this turn. Only these progress documents
and the scoped authorization in the implementation plan are modified locally.

## 2026-09-26 — P0 lifecycle documentation delivery

Authority: user requested the revised design be written to the repository only.
Confirmed preferences: user handles local directories; cloud cleanup completion
must not leave blocking stale locks; business directories/scripts0755 and files0644,
credentials/necessary private controls excepted. No current deletion targets or
permission changes are authorized by this documentation.

Completed: original P0 spec R1–R7, aligned run-control and TTL/lock design, updated
permission boundary, new T1–T5 implementation queue and V1–V6 bounded acceptance.
Historical plan points to the new queue, preserving actual old component results.
The earlier independent audit is included as evidence, not a runtime test result.
Only Markdown documents changed; no API/schema/code implementation is claimed.

Workspace: isolated `jiucheng/test/wgs422-p0-integration-20260926`, starting b17e1b6
(functional954045a). Pre-existing changes were this task's uncommitted independent
audit plus state/task/handoff entries and were preserved. No other worktree changed.
Files: original P0 and run-control specs; TTL companion; original/new P0 plans;
docs34; independent audit; CURRENT_STATE/TASKS/HANDOFF.

Checks: local read/search, document link/task-ID checks and git diff whitespace
check only. New/changed relative links: 13 checked, 0 broken; diff whitespace
check passed. Delivery contains exactly ten Markdown files on the isolated test
branch; no main/production merge or remote push is included.
One apply_patch hunk initially failed on line wrapping in run-control;
no partial edit occurred, exact text was read and the corrected hunk applied.
No pytest/npm/compile/Compose/SSH commands: this task is documentation-only, not
runtime acceptance. Future affected tests need BS10610 preflight and implementation.
No fresh hostname, permissions, mounts or releases verified; all service/runtime,
scanner/dispatch and existing analyses remain unchanged by this task.

Next: start T1-CODE/T2 under an implementation request, not another ad hoc binding
workaround. Native wheel/Master builds stay with original owner. Test release and
production activation remain distinct. New capabilities are planned, not enabled.
Rollback: revert the documentation commit; no cloud/data/schema rollback needed.

## 2026-09-26 — independent P0 normal-analysis audit

Goal: independently check whether P0 supports normal analysis without changing
the original workflow, per latest user request. Reviewed clean integration
checkout b17e1b6 (functional954045a), native dcc1698 (functional ae90b65), plugin
4f10c27 (only documentation differs from released source5ffcb07).

Findings are recorded with source locations in
`docs/reviews/2026-09-26-p0-normal-analysis-audit.md`: missing production binding
producer; Step1 initial owner depends on a future Step2 execution ID; static CLI
owner after UID/generation transitions; new TTL combined with legacy Step4/5
still requiring a live Master. Platform selected downstream reconstruction does
exist, so do not report all downstream code as absent. Automatic recovery has
explicit evidence/category/deadline limits, not blanket failed-Master coverage.

Changed only this handoff, CURRENT_STATE, TASKS and the new audit. Source reads,
git status/revision/diff inspection and scoped ripgrep searches were used. Some
exploratory searches named nonexistent files or used PowerShell literal globs;
those returned path errors and were replaced by verified filenames or -g filters.
No SSH, runtime tests, database, deployment, analysis, lock or data mutation.
Local runtime tests remain prohibited; this code-path audit does not claim fresh
BS10610 acceptance. Prior component results were not rerun or discarded.

Next: close the existing normal-path integration, then only two affected remote
synthetic paths (normal Step1–6 with TTL; recovery/current-owner continuation).
Do not insert a manual pause or fabricate production policy rows. Native
artifacts stay with the existing owner after source correction. The staged
release and last documented unswitched services are not live-refreshed here.
Rollback: revert these documentation edits only; executable/runtime state is
unchanged. Audit findings must be resolved before declaring complete rollout.

## 2026-09-26 — R4 integration and latest production fixes

Goal/authority: user authorized the next three test-release steps and explicitly
required the latest production fixes. No production service change is included.
Fresh fetch confirms main/production43cd0c5 already ancestors of test781877e;
no duplicate cherry-pick. Isolated branch
`jiucheng/test/wgs422-p0-integration-20260926` merges P0fd9a008 as0af8367.
Only two executable conflicts required resolution (wgs_observer.py and
wgs_runtime_gate.py); independent scoped review found no Critical/Important issue.
Step7 observation and upload/download waiting behavior are preserved.

Commands/checks: git fetch, ancestor/log comparison, merge and diff whitespace
check succeeded. No local tests (repository boundary); original Infra reports
eleven named synthetic tests PASS against exact0af8367 on BS10610 (backend10,
DAG1). First backend run passed6; four cases stopped at missing/config mount,
not business assertions. Only those four were rerun after mounting same-source
config, then4/4 PASS. DAG image lackedpytest; the native task user explicitly
allowed task-scoped install; selected DAG case1pass in2.97s. No services changed.
Two new binding tests inbeba26a reproduced missing4.2.2 map and a skipped
required-handoff wait. Both passed on954045a (gate0.21s,backend1.48s,exit0;
only Starlette deprecation warning). Total13 unique selected cases; original11
not repeated. Exact source archive SHA for954045a:
`b6740abcdce74c5eef838531398401054970dffc0d99e38217db2d5eed3137c1`.
Coordinator read original Infra's local R4_SYNTHETIC_TEST_RECEIPT.md.
WGS owner statically confirmed frozen3b1dae5
supports --handoff-request and both v1 receipts; no WGS code changes required.
R1/R2/R3 artifacts remain accepted, no rebuild or republish. R4 handoffa8f9bc4
documents source pins and catalog boundary. Only test branch will be pushed.

Push completed: `git push --atomic origin` fast-forwarded the existing primary
test branch781877e→0ca80a8 and created the integration test branch at0ca80a8.
Exit0; no force, no main/production update. Functional source is954045a;
later commits are documentation only. Runtime deployment remains pending.

Target preflight: BS10610/server10610, controlroot
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`;
backend still mounts20260923-step7-ae416fa, /config20260912-opt-4d3d24e6,
WGS DAG/common20260915-main-359df11. No service changes yet.
Private catalog current34bfcbf differs from repository examplecc9bde3; preserve
private entries and use actual-current CAS rather than replacing the file.
Immutable3b1dae5 host-side source and profile were delivered; node200 source/
profile readability was confirmed from the host. User authorized the existing
ctapa SSH key for R4, and the original Infra owner confirmed ctapa identity and
write access to the ctapa-owned test gate. No forced-command key or privilege
bypass was used.

Candidate registration data is complete; no actual registration/activation yet.
R4 deployment attempt stopped after source staging. Exact receipt:
`D:/pipeline/task-artifacts/wgs422-p0-integration-20260926/R4_DEPLOYMENT_RECEIPT.md`.
BS10610 isolated candidate `releases/20260926-wgs422-p0-954045a` was staged
from the verified archive; no service mount, node200 gate, bootstrap/policy,
catalog selection, database record or real analysis was changed. Read-only
test counts were zero active AnalysisRuns and zero active TransferJobs.
Ctapa's existing kubeconfig verified `snakemake-ns/biosan-clinical` Bound to
`pv-efs-clinical` with matching claimRef; native cloud-reader requires these
exact PVC/PV identities, not invented node200 host SFS inode data.
The actual stop is the already-audited missing trusted per-bundle registration
producer: native/platform code only consumes static policy `bindings`, and
synthetic tests write them by fixture. Empty bindings fail closed for future
batches. Do not install an empty policy, fabricate a real-batch binding, or
activate partial P0. Next is a separately scoped implementation/acceptance of
the trusted producer, then paired rollout and one final API/DAG/mount smoke.
No additional synthetic tests were run in this deployment attempt.
Infra retains exact rollback mounts/config before changes;
DB/Redis/unrelated services and all analysis data remain unchanged. Global scan,
dispatch/recovery stay off. WGS4.2.2 QC/options provenance remains unaudited,
not a fabricated equivalent4.2.1 policy. Detailed receipt:
`docs/releases/2026-09-26-wgs422-p0-r4-integration.md`.


## 2026-09-23 — P0-2E batch lock documentation gap
Reviewed native _claim_batch_lock call and runtime ConfigMap/process/status locks.
Previous design stated preservation but omitted owner handoff/release acceptance.
Updated both P0 designs and state/tasks: logical-run ownership, conditional CAS,
no Master-TTL lock GC, crash reconnect, old-owner rejection and release after writers.
Scope is docs only; implementation and live lock behavior remain unverified.
Checks: diff whitespace and documentation contract consistency; no runtime tests.
Next: integrate into existing CR01, paired with TTL; no new lock/retry service.
Rollback: revert this documentation commit; no cloud, database or lock mutation.

## 2026-09-23 — P0-2 / P0 docs aligned to Huawei incident recommendations
Scope: docs only on server test branch; no production or cloud authorization inferred.
Changed original P0 spec, TTL companion, CURRENT_STATE, TASKS and this handoff.
Made automatic reclamation mandatory; proposed TTL=100 for Worker/Master/reader,
with durable evidence/consumer rollout first and UNKNOWN safety after evidence loss.
Added aggregate Pod capacity, AOM reporting, common alerts and notification gates.
Official 1000 is default Pod quota; 100 seconds is an example adopted as a project
proposal, not a vendor requirement. Removed previous 3600/86400 proposed defaults.
Validation: documentation diff/links and cross-document requirements only; no runtime
tests appropriate for this docs-only change. Actual TTL/AOM/alerts remain unverified.
Next: reuse independent CR01 code, implement generators/evidence/consumers and run
affected BS10610 mocks; real TTL check and cloud operations require separate approval.
Risk: TTL can delete evidence before collection; absent trusted evidence blocks retry.
Rollback: revert this docs commit only; no resources or analysis records changed.

## 2026-09-23 P0-2 original recovery spec revision

User asked to revise the pending-development original plan before P0-2 work.
Updated original CCE recovery spec, CURRENT_STATE, TASKS and this handoff only.
P0-1 is cluster health, P0-2 is existing P0's Master/runtime priority slice.
Documented START_CONFIRMED, immutable identity/deadline, trusted terminal writer,
missing-object fail-closed behavior, historical evidence limits and release order.
Independent CR01 e921e3a/plugin25297f9 accepted slices are reused, not merged or
declared fully complete here. Automatic policy and production remain unchanged.
Target BS10610 Git worktree only; no service/runtime/cloud/database access or
mutations needed. Validation: doc diff, links and exact four-file commit scope.
No runtime tests because no executable code changed. Preserve other worktrees.
Next: implement the priority slice on existing CR01 development, not a new retry
service. Production publication/real batch recovery require separate approval.
Rollback this documentation commit only; no task/result state is changed.

## 2026-09-23 Job TTL/cross-Master recovery documentation

User approved completing the technical design, not implementing or deploying it.
Added docs/46_JOB_TTL_CROSS_MASTER_RECOVERY_DESIGN.md and task/state entries.
Spec covers terminal evidence fields, Worker3600s/Master86400s proposed TTL,
missing-object reconciliation, exact identity/journal fencing, directory mutual
exclusion, P0 integration, query scope and minimal isolated acceptance cases.
Defaults require capacity review before production activation; historical bundles
are not rewritten and absent evidence never becomes a fabricated success.
Target: BS10610/server10610 source-only test branch. No service, database,
container mount, runtime gate, scanner, dispatch setting or cloud object changed.
Validation: documentation diff/links/scope checks only; runtime tests intentionally
not run because no executable code changed. Existing unrelated work preserved.
SSH gateway intermittently reset and first GitHub fetch failed with GnuTLS -110;
bounded reconnect/fetch used, no authentication or environment changes.
Next: implement in dependency order described in the spec after separate approval.

## 2026-09-23 Step7 primary test-branch integration

Coordinator integrated Step7 commits `ae416fa`, `08696d6` and `8697a8b` into the primary
test branch. Only the three state documents conflicted; resolution retained the
completed stale-run cancellation record, Step7 publication evidence and the
independent P0 checkpoint. Application files applied without conflict. Existing
focused BS10610 evidence was accepted without rerunning the redundant suite.
No main, production or BS96 mutation was performed. Rollback is by reverting
the resulting test-branch commits; it must not delete runtime data.

## 2026-09-22 user-authorized immediate GATK Step1 cancellation and OBS cleanup

2026-09-23 scope correction before final control-plane mutation: the user later
directed production to reuse/continue the uploaded FASTQ objects, so OBS deletion
is no longer authorized or required. The exact node200 process count is now zero;
the test DagRun is already failed and Step2 never started. The remaining mutation
is limited to marking this one test analysis/attempt, its Step1 execution,
transfer and unfinished per-file projections cancelled, releasing only
`wgs-obs-upload-01`, and adding audit/action records. Preserve all completed OBS
objects and multipart state, SFS/NFS/local inputs, sampleinfo, runtime requests,
logs/evidence, workdir, databases, services and every other analysis.

The user explicitly replaced the earlier wait-for-upload instruction: stop the
mistaken BS10610 test run `GATK_20260922_112207_23AD29` attempt 1 during
Step1 and remove only its partially uploaded OBS FASTQ objects. The exact online
target is the immutable runtime-bound `OBS_UPLOAD_PATH` for execution
`GATK_20260922_112207_23AD29-a1-step1_upload-g1`; its target SHA-256 is
`f48ae0ac292478c704136e62d90caaef75ca82eb4470cffd0ed515229b1d0fbb`.
The plaintext OBS bucket/object identity remains private and is not committed.

Authorized online actions: stop the exact DagRun before Step2, terminate/abort
the exact attempt's multipart upload, remove objects below only that frozen OBS
prefix, release only its input transfer lease, and mark the test attempt
cancelled. Protected and not authorized for deletion: source/local/NFS FASTQ,
sampleinfo, runtime requests, logs, evidence, workdir, the production WGS run,
other OBS prefixes/batches, databases, services and release candidates. Before
mutation the DagRun was running with Step1 `329296309017 / 457613089569` bytes,
59/86 files complete, 8 running and 19 accepted; Step2 had no task state or
`PipelineStageExecution`. Private preflight evidence is mode 0600 under
`candidates/cancel-gatk-20260922` on BS10610. Itemized deletion results and
recovery limitations must be appended after execution.

Final control-plane result, 2026-09-23: exact node200 process count was zero;
the DagRun was failed, `wait_step1_upload` failed and `submit_step2_master` had
no state. The business run and all 43 samples are now cancelled, the Step1
execution and transfer are canceled, 60 completed file projections remain
success, 26 unfinished projections are canceled, and `wgs-obs-upload-01` is
released. One RunAction and one AuditLog record the user cancellation with
`data_deleted=false`. No other test analysis is active. No OBS object or
multipart state, SFS/NFS/local file, sampleinfo, runtime/evidence, database,
container or service was deleted or restarted.

## 2026-09-23 Step7 final test-entry boundary result

Post-publication read-only synthetic request probe completed with expected
exit1: registered runtime request is missing. Traceback uses the isolated test
runner; no cleanup was launched. Existing request visibility wait explains the
delay. No repeat of the 40 passed cases. Commits ae416fa and 08696d6 delivered
as bundle to the primary test coordinator; its integration confirmation remains
separate from deployed BS10610 status. Production Step7 unchanged.

## 2026-09-23 Step7 BS10610 publication

User approved test wrapper correction. Completed scoped deployment from ae416fa
onto actual backend and observer baselines; independent DAG mounted into test
Airflow components. Compose/rollback under candidates/step7-ae416fa-control;
release20260923-step7-ae416fa. No production change or real cleanup submission.
Healthok; registered DAG2tasks/max_active_runs1. Runtime/test wrapper isolation
and exact backup paths recorded in Step7 document. All previous40tests reused.
Initial node patch staging lacked Git, stopped before activation; applied with
installed patch to private candidate, then syntax check. No added packages.
Read-only synthetic missing-request wrapper probe interrupted by test worker
replacement, so repeated only that boundary probe after service publication.

## 2026-09-23 Step7 accepted source, deployment safety stop

User resumed Step7; production WES checked running/normal upload-slot wait.
Focused BS10610 acceptance30+9+1 passed with mock external calls/network-none,
isolated SQLite for DAG integration. No real run submission or data deletion.
One noexec harness failure rerun alone; Airflow pytest supplied from cached
backend packages because image lacked it. Full commands/results in Step7 doc.
Fresh test active platform/Airflow runs empty, test runner process absent.
Coordinator released window but required fresh binding check: test wrapper
airflow-wgs-test/forced-command.sh actually reads production airflow-wgs env
and runner. STOPPED before deployment and asked user for test-only correction.
No backend/observer/DAG/runner deployed, no service restarted; production unchanged.
Next: obtain confirmation, validate test env/runtime roots, correct only test
wrapper, apply Step7 deltas to actual pins (not whole old tree), scoped deployment.
Do not repeat passing tests or enable real cleanup for acceptance. Rollback source
by commit revert; deployment rollback unnecessary because nothing published yet.

## 2026-09-23 Step7 acceptance resumed; transport blocked

Production GATK work is finished separately; this branch remains Step7-only.
Fresh BS10610 preflight confirmed server10610 and backend actual source still
20260917-native-ui-76915d8-r2, with stale active GATK_20260922_112207_23AD29.
Coordinator asked to reconcile deployment gate; no shared-service changes.
Prepared local source archive D:/pipeline/task-artifacts/step7-maintenance-20260923.tar.gz.
SCP to candidates and following SSH staging command both failed before remote
execution: connection reset at 172.17.61.18 SSH banner, exit1. Therefore candidate
upload/extraction and isolated pytest did not run. Do not count this as test
failure or passing evidence. Next restore the configured SSH route, stage the
archive, execute only focused tests once, and coordinate P0 before deployment.
No commit or remote acceptance yet; no production fallback.

## 2026-09-22 Step7 maintenance draft — waiting for test environment

User approved test-only independent WGS Step7 maintenance and reconnect/manual
recovery. Isolated branch `jiucheng/fix/wgs-step7-maintenance-20260922` starts at
test `eaed38e`. Read-only BS10610 preflight confirms one active GATK Step1 upload;
the environment coordinator's deployment hold remains. User permits code work
while upload finishes, not deployment or testing before release.

Draft changes: independent two-task maintenance DAG; Step7-only probe/start;
frozen-target retry; authenticated context/observation endpoints; exact identity
and stale-receipt fences; focused backend/DAG/runtime tests and documentation.
Read-only review findings addressed: registration command, stale running receipt,
v1 archive counter. Static `git diff --check` passes. Runtime tests NOT run.
No service, task, lease, data or production was changed. Code is uncommitted.
Coordinator owns upload completion/cancellation and baseline deployment; do not
start a second cancellation monitor. After explicit release, verify active tasks
and actual mounts, then perform the single focused acceptance and synthetic DAG
case. No real SFS deletion. Test-branch commit/integration and scoped deployment
follow successful acceptance. Rollback restores only test code/configuration;
do not remove results or replay requests.
See `docs/STEP7_MAINTENANCE_20260922.md` for exact findings, scope and remaining
implementation/acceptance. This is not a completed fix or deployment.

## 2026-09-26 R1 accepted: WGS4.2.2 published to SFS

Original Infra single writer ran0.8.6 assets validate/apply/status on node005,
strict task-only SSH to server10610, all exit0; final PASS/state_verified=true
at2026-09-25T17:55:38.809242Z. New release20260926.1-wgs422,manifest73bca89d...
pipeline130files/resource9files. WGS owner then checked exact SFS targets/READY,
ACTIVE_ASSETS,new source3b1dae5 and BKW VCF/index hashes in read-only inspector;
only that task-created inspector Pod was removed afterward. No dataset cleanup.

Coordinator read original CLI JSON transcriptions and command/exit record from
D:/pipeline/task-artifacts/p0-final-native-ops-20260925/R1_422_*; parsed status
against release/manifest/PASS/state_verified successfully. Status file SHA
9ac71b41782dc38bf669d8d924ba1184c3aadb6e438008484cb7a7f16f673174.
Final WGS R1_SFS_PUBLICATION_RECEIPT.md read, SHA
92daa53d5caeab5e19ea5aace9a3e21dcdc870985466e5a85f85fd3145a8da0e.
No duplicate remote tests/apply. No biological regression/canary: not required
for this asset-publication slice. Local check is static evidence parsing and
git diff --check, not local runtime testing.

Canonical record docs/releases/2026-09-26-wgs422-sfs.md lists exact paths/hashes,
branch provenance, resolved connection errors and historical-before limitation.
CURRENT_STATE/TASKS/release plan updated. No4.2.1 Git changes;4.2.2 remote dev_CJC
head not advertised, no push claimed. No Airflow/BS96 service switch, real batch,
Worker rebuild or global automatic enablement. Next is R4 when directed. Assets
and receipts retained; rollback requires supported publication, not manual pointer
edits. Runtime0.8.6/r2/SWR remain as accepted in preceding slice.

## 2026-09-26 exact whitelist replacement requirement

User explicitly requires source
/bi/BioCodeHub/WGS/WGS_V3.2.1/annotation/GRCh38_primary_assembly/whitelist.V1_BKW.V20260909.hg38.vcf.gz
in place of the former whitelist.V1.V20260909.hg38.vcf.gz in that directory.
Both owners notified before apply: confirm actual BKW payload (not filename-only),
matching.tbi source/hash, logical resource mapping and SFS target. Reuse existing
candidate if it already contains exactly these bytes; otherwise refresh immutable
candidate and dependent hashes before apply. No unrelated database/source edits.

WGS owner confirmed source branch dev_CJC_4.2.2_cloud HEAD3b1dae5 matches payload;
authenticated GitLab query shows current release_V4.2.2 upstreamca71cd6 included.
GitLab has no dev_CJC_4.2.2_cloud head: do not claim that branch was pushed.
No4.2.1 commits/pushes. BKW VCF SHA10ec6792ad3589051ca4625a6e64882e7eb99de96ce482b35cd7b0d8fc2b55c1
and index7003b1ba87f4df6ef2c15e4f795eb884e90ac1e8ce56f2fb1fd54c3ca2d815bc
match existing candidate. Logical whitelistV1 target retains ordinary name with
BKW content; no reupload required.

Infra established node005 to server10610 direct SSH using existing identity and
task-only known_hosts verified against trusted host keys. A process-only ssh
wrapper preserves strict checking/argv/exit and avoids global SSH edits. First
node005 validate failed because task operator referenced a historical absent OBS
config. WGS owner supplied the same existing configuration used by successful
copy/upload; only task operator is being corrected. No credentials copied.

## 2026-09-26 explicit WGS source branch requirement

User requires latest merged dev_CJC_4.2.2_cloud and explicitly prohibits
committing publication changes to dev_CJC_4.2.1_cloud. Both owners notified;
WGS owner must confirm current merged source/payload correspondence before apply.
Local WGS-noncoding-model is a separate dirty governance checkout without that
branch, not the authoritative WGS source. Its read-only branch query failed;
no edits/checkouts performed there. Source verification remains with WGS owner
and its existing remote WGS checkout, not an invented local branch.

## 2026-09-26 simplify R1 per latest user direction

User: "直接更新WGS 4.2.2，然后进行发布，不用管旧批次".
Both owners informed: stop old-release compatibility audits; normal shared
ACTIVE_ASSETS change is authorized for this publication. Keep tool integrity/
authentication checks and a single apply writer; do not delete unrelated old
directories, change Airflow/BS96 or start clinical runs. Use existing documented
SSH routes/task-scoped operator configuration, no copied private credentials.
WGS owner reports20260926.1-wgs422 candidate prepared:12unchanged objects copied
server-side,2metadata uploads, hashes checked,exit0. Manifest73bca89d28619fb6194233f0bea40ae5f5d8423bd6fab4fdf511a52493eaacd7;
SOURCE_READYa1c0fcd52226760374bda1c89df839458472bbeb200fdbcd3eb3810d9fce8670.
SFS has not been applied at that checkpoint; final receipt still pending.

## 2026-09-26 chronology correction: complete R1 publication

User corrected the cross-task pause as an older instruction and explicitly
reaffirmed "先完成发布". Coordinator had incorrectly treated message arrival
as instruction recency. Original WGS and native/Infra owners now notified to
resume R1 only and not replay historical pause state. Reuse accepted checks,
payloads and0.8.6/SWR/r2; continue metadata binding and safe SFS publication.
No additional scope, Airflow/BS96 switch, source changes or clinical submission.
Earlier pause entries are history of that error, not active authorization.

Authorization chronology verified from direct user message:
2026-09-25T17:33:56.145Z, task019fa8d1-0d81-7e92-abee-8154dd1cf0a7,
turn01a0d9a1-83e1-7042-bda5-466ca2a9c335,
message msg_01a0d9a1-8431-7573-91f0-c9a685dde638 (role=user).
Both owners received the exact source location, not merely a relayed summary.

## 2026-09-26 R1 paused again before completion

During resumed R1, original WGS owner relayed "先暂停" (later corrected as old).
Coordinator notified WGS and native/Infra owners to stop uploads/apply/switching/
cleanup and requested only a summary of already-performed actions, no new probes.
Owner first report had confirmed old13payload/SOURCE_READY candidate existed,
old metadata boundr1, and SFS had not yet been applied; this is not a final live
post-pause check. No coordinator remote mutations. R1 remains incomplete/paused.
Local audit identified asset_status checks sharedACTIVE_ASSETS and current
component manifests; owner was asked to trace old-release consumers before any
apply. That compatibility finding is unresolved, not authority to change code.
Resume only on explicit user direction.0.8.6/SWR/r2 completion is unchanged.

Post-pause owner summaries received: WGS performed read-only BS10610 checks of
client0.8.6, r2 SHA4a016a2d..., payload09da0287..., resource manifest67713468...
and source3b1dae5; no new remote writes/upload/apply/switch/cleanup. Infra only
read docs and parsed local ssh configuration, no remote connection or mutation.
SFS publication remains undone; no new publication receipt exists.

## 2026-09-26 R1 resumed by user

User request: "先完成1" after the four-step outline. Scope is WGS4.2.2 SFS
publication only, using accepted client0.8.6/Master/r2; no platform deployment.
Original WGS task resumed via send_message_to_thread. Owner must retain old
candidate/payloads, generate matching metadata, inspect shared ACTIVE_ASSETS
consumers and stop if old-version safety cannot be established. Existing Infra
owner may perform necessary assets apply per SOP; no duplicate build/testing.
Requested R1_SFS_PUBLICATION_RECEIPT with exact commits, SHA values, paths,
command exit results, ACTIVE_ASSETS before/after and old-version evidence.
No remote mutation performed by coordinator; publication receipt pending.
Rollback boundary: do not delete old SFS/OBS or change frozen runs; new immutable
assets are not Airflow activation. Preserve BS96 and existing4.2.1 selection.

## 2026-09-26 runtime-first slice accepted

Original owner completed0.8.6 install, WGS Master SWR push and inactive r2 profile.
Source dcc1698fb5da955d2c481a735021f0cfac2b8119 checked/clean; four changed files
are version metadata, release.py and its tests. Fixed-version restriction removed,
actual-version equality and all remaining checks unchanged. Receipt records
RED1 failure then GREEN3/3, build and pip exit0, CLI0.8.6. No extra tests run here.

Read/hashed R2_R3_086_EXECUTION_RECEIPT.md (a9e378835d1cb5c5d792e4f361b16a1f52801633b687f89130aa2bd332dd6d8e).
Read/hashed local wgs-4.2.2-r2.yaml (4a016a2d0c1006b013a1e66efc147e29275e0ce8dcd2b086f1488bed8c44d6ed).
Read-only scp downloaded exact119603-byte0.8.6 wheel from BS10610 task evidence,
exit0. Local static ZIP/metadata inspection matches wheel SHA3e77f7b4892a086b977e7ff072860f70a9344160be1949b413a12f6228b843da,
release.py a403d72a..., runtime63d3f178..., guard4009e7c5.... No local runtime test.
SWR push/inspect digestdc22c919... and profile validate exit0 documented in owner
receipt. Embedded assets unchanged, so existing accepted Master reused, not rebuilt.

Canonical record: docs/releases/2026-09-26-cce086-wgs-profile.md. Also updated
CURRENT_STATE, TASKS and release plan; git diff --check is the local docs check.
No separate old installed package backup per user's direct-install instruction;
dev3 wheel retained for explicit reinstall, not an exact environment restore.
Old profile/image remain. New r2 is inactive; no SFS apply, Airflow service change,
BS96 access, main/production merge, clinical run or automatic recovery enablement.

Next: keep WGS/SFS paused until resumed; when authorized, bind asset manifest and
SOURCE_READY to r2 SHA before publishing, then integrate API/dashboard and the
already-authorized Airflow branches. Do not use old r1 READY as proof of r2.

## 2026-09-26 user selects cce-pipeline0.8.6

User explicitly chooses0.8.6 for the approved minimal release-version fix.
Original native/Infra owner informed to use0.8.6 consistently in source metadata,
successor wheel, install receipt and profile companion release binding; no dev4,
no overwrite of accepteddev3 artifact. Continue current two-case regression work,
do not restart full verification. Master reuse still depends on unchanged embedded
asset hashes, not on making image labels cosmetically match the client version.
Installation of0.8.6 and SWR/profile completion remain pending actual receipts.

## 2026-09-25 approved release-version hardcode correction

User agreed to remove only the fixed0.8.5 restriction in native release binding.
Original native/Infra owner is assigned release.py plus focused version-match /
version-mismatch regression coverage on approved remote test infrastructure.
Retain exact catalog/actual version equality, profile/source/resource hashes,
asset PASS, schema and authentication. No installed site-packages patch, SSH or
HTTP redesign. This supersedes the prior defer-only note below.

Coordinate with active install/push/profile slice: corrected source must have
its own commit and successor artifact version/hash; never overwrite accepted
dev3 wheel with different bytes. Use the fixed artifact for the installation.
If embedded Master runtime assets remain identical, reuse accepted Master after
identity comparison rather than rebuilding for a client release.py change.
Do not claim completion until source/test/artifact/installation receipts arrive.
WGS/SFS remains paused; no Airflow/BS96 service changes or real analyses.

Owner subsequently reports dev3 installed in shared nipttest, pip exit0 and
metadata/CLI0.8.5+p02.dev3, import at the agreed site-packages path. Installed
runtime/guard hashes match63d3f178.../4009e7c5... from accepted artifacts. Owner
states a direct user instruction in its task requested direct installation and
no other unnecessary actions, so no separate old-package backup was made.
SWR/profile not changed. This is owner-reported installation evidence pending
the persisted receipt, not completion of the newly approved release.py fix.
Asked owner to continue the approved minimal fix and provide the exact successor
artifact/installation receipt, or report any explicit contradictory direct scope.

## 2026-09-25 user resolves pause scope and resumes runtime slice

User answered "确认" to continuing cce-pipeline install -> WGS Master SWR push
-> new profile binding while only WGS/SFS is paused. Redispatched the original
native/Infra owner with this exact scope, existing dev3/hash and image pins,
SOP-approved nipttest test target, minimal identity checks and rollback retention.
Do not wake paused WGS owner or apply SFS; use already frozen source/resource
contract. Candidate profile remains inactive and asset readiness is not claimed.
No Airflow/BS96 service change or branch merge during this slice. Actual owner
receipts are pending; no success inferred from redispatch.

Read-only final-build inspection found release.py:_validate_release_binding
still requires both catalog/native version equality and __version__ ==0.8.5.
With build45323e4/dev3 this rejects managed release registration/publication.
profiles.py separately accepts immutable Master RepoDigest and bound hashes;
this finding does not block installation/push/inactive profile parsing. Native
owner was informed: do not spoof version, patch installed package or rebuild in
this slice; carry the exact finding to later Airflow release-API integration.

## 2026-09-25 cross-task pause scope needs confirmation

After dispatch, WGS owner reported a newer direct user instruction in its task:
"先暂停". Native/Infra owner also paused R2/R3 after receiving that report;
it confirms only SOP reads, no installation, SWR push or profile writes.
Coordinator does not override a potentially newer user pause. Ask whether it
applies only to WGS/SFS or also to this runtime-first slice before redispatch.
WGS frozen SOP explicitly permits the nipttest cce-pipeline path for approved
tests. Its exact0.8.5 example is the previous version, not proof that the user's
explicit newdev3 installation request is invalid. No code compatibility change
is inferred solely from that documentation example. All environment state retained.

## 2026-09-25 runtime-first slice and repository audit

User directs cce-pipeline installation, new WGS Master SWR push, then new profile
binding first. Original native/Infra task019f8355-2b77-7413-9553-6670c35a1a2f
received execution request; WGS task01a09149-ad9d-7e92-b98a-16d9cae075e2 provides
SOP and frozen compatibility contract without applying SFS. The plan now removes
R1-SFS-success as a prerequisite for R2; profile remains inactive/unready until
later asset publication. Installation target follows SOP/current test scope;
do not reuse old production installation examples as implicit authority.
No actual install/push/profile receipt yet. Later Airflow main/production branch
merge is authorized, but latest turn is scoped to these three earlier steps;
BS96 services and other P0 repository main merges are not included.

Read-only Git audit: platform clean3bc77a8 includes functionalfdace86; remote
main43cd0c5 and no named P0 branch. Plugin clean4f10c27 includes5ffcb07; remote
maind5f720e and no named P0 branch. Native clean ae90b65 and build45323e4;
functional commit is ancestor of build, two version-only files differ. Native
P0 origin is local gatk-master-logger-source-20260917.bundle, not GitLab.
Server repository main/origin-main83e7adb does not include native P0.

Failed checks (no mutations): git ls-remote via GIT_SSH_COMMAND returned exit1
because Git's shell context attempted PowerShell `exec ssh` for ProxyJump.
Direct documented ssh BS10610 succeeded, hostname server10610; querying server
refs returned83e7adb. Server GitLab ls-remote with GIT_TERMINAL_PROMPT=0 returned
exit1, Username prompt unavailable. No credential workaround or blind retry;
GitLab live push state remains unverified. No runtime tests were run in this
audit; local checks were Git-only and wheel metadata/hash inspection.

Files updated: release plan, CURRENT_STATE, TASKS, HANDOFF. No application changes.
Rollback: revert this docs-only change. Next: inspect original owner's three-step
receipt and record exact installed version/hash, image RepoDigest, profile path/SHA.

## 2026-09-25 explicit SSH identity correction

User identifies `C:/Users/11217/.ssh/id_rsa_chenjiucheng` as the documented key.
The already captured local `ssh -G BS10610` selected this exact IdentityFile,
and the local hostname check succeeded. Do not read/print/copy its contents.
The coordinator's continued focus on node005 default SSH as the only entry was
an incorrect narrowing of the available management path. Both original owners
were instructed to use the existing documented local management connection,
stop redundant default-identity/hostname probes, and not require a new global
alias or private-key relocation. Preserve the private-OBS boundary; if the
existing release CLI cannot bridge these already available connections, report
the precise interface limitation, not a general claim that SSH is unavailable.
No new SSH config, host-key trust, credentials, CLI or environment change made.


## 2026-09-25 user corrects SSH prerequisite; local connection verified

User directs using documented local `ssh BS10610` or node005 direct IP, not
assuming a new managed alias must be installed. Coordinator reread AGENTS and
connection documentation. Local `ssh -G BS10610` resolves chenjc@172.17.106.10
via ProxyJump BS; `ssh -o BatchMode=yes -o ConnectTimeout=12 BS10610 hostname`
returned server10610, exit0. Do not blindly use the transposed172.61.106.10/9
from the user's shorthand or infer the .9 host has the same environment.

The previous conclusion that a global SSH alias/home edit was required was
premature. Original Infra owner is checking the existing node005 direct route
and supported operator configuration, with WGS owner avoiding duplicate probes.
No global SSH/key/routing/CLI changes; no SOURCE_READY bypass. The separate
BS10610 private-OBS read limitation is not disproved by successful local SSH.
Reuse candidate20260925.1-wgs422; SFS publication and R2–R4 remain uncompleted.


## 2026-09-25 R1 staging cleanup receipt supplement; no new remote action

WGS owner clarified its earlier cleanup: exact deleted path was
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/wgs-422-update-20260925/publication.failed-python`.
This was this turn's approximately674MiB incomplete staging copy, created when
stage_release.py used hashlib.file_digest unavailable on the server Python.
It was removed only after the corrected staging generated publication/SUMMARY.json.
It can be regenerated from frozen3b1dae5, the seven resource sources and4.2.1
baseline; it was not a clinical project, original resource or successful candidate.
Successful publication staging, OBS receipts, source databases and4.2.1 assets
are retained. No further cleanup or remote operation was performed for this
supplement. Local R1_STATUS now has SHA256
547a9fed0e5fd73aa31877c8ce3174c215bd74858af6717932c65514f9363ce3;
the remote status copy intentionally remains the previous version. SSH alias
repair and R1 apply still await user direction; R2–R4 are not deployed.

## 2026-09-25 approved four-step release: R1 execution starts

User authorization: "继续完成，开始执行" applies to the reviewed WGS4.2.2/P0
test-release plan. Existing WGS-pipeline owner executes R1; original native/Infra
owner takes R2/R3 after its contract, then paired test deployment in R4. This
supersedes prior hold-for-review entries, not the plan's consumer/rollback gates.
No production activation, GATK test, clinical submission, deletion or new service
is authorized. Coordinator does not take over wheel/Master builds.

Preflight decision: R1 manifests feed R2 compatibility and R3 profile pins; R3
is a candidate until R4's paired backend/DAG/gate deployment. Keep old assets and
frozen batches. Existing assets apply changes ACTIVE_ASSETS; unresolved consumer
impact stops publication rather than allowing a hand-edited pointer workaround.
Only local plan/state documentation changed so far; runtime results and test
commands will be appended from owner receipts. Evidence stays task-scoped under
WGS_test; no redundant full-suite tests. Local docs rollback is a Git revert.

R4 read-only preparation found a plan-input correction: ae416fa is not an
ancestor of test781877e, but255be59 contains the equivalent Step7 patch. Exact
diff across backend/dags/scripts/config/frontend is empty (exit0). Both planned
maintenance and shared-transfer test files and selected test functions exist
on781877e. Do not cherry-pick ae416fa again. This changes integration mechanics,
not scope or the need to preserve those fixes when merging P0. Initial rg in
the P0 worktree returned exit1 because those newer tests are on the test branch;
git show confirms their presence there. No runtime tests or remote writes by
coordinator. Authorization docs committed a0961d6; R1/R2 owners dispatched.

Non-mutating integration preview: `git merge-tree --write-tree --name-only
781877e fdace86` returned exit1 for expected conflicts (no checkout/ref changed).
Only two code files conflict: wgs_observer.py must retain P0 row refresh/locking
and Step7 projection; wgs_runtime_gate.py must keep Step7 request/command guards
alongside P0 publish/probe handling. Remaining conflicts are contracts/design/
state docs. main.py auto-merges but its combined API behavior still needs the
planned targeted verification. This is preparation, not R4 deployment acceptance.

Original native owner delivered R2_READY.md under task-artifacts/p0-final-native-
ops-20260925; coordinator read it and matched SHA256
179cff1cb3825205e118966183aea771f4506c9ccebfc71a177115342ae72c8e.
Owner's bounded BS10610/node200/node005/image readonly commands each exit0.
Test mount/gate state unchanged; node200 private test entry consumes shared
nipttest, current native0.8.5. No active process observed is not a complete
consumer guarantee. Exact rollback backup and final consumer check remain
before installation. Image labels are inherited old metadata; compatibility
must use R1 actual runtime contract, not require a rebuild just for a label.
No installation/push/profile/service change; R1 has not published yet.

R1 partial execution receipt: task-artifacts/wgs-422-update-20260925/R1_STATUS.md,
SHA256 f611c2c752400936130aaa690d642757097961f510eaf3bad1129275fff883bc
read and matched. New candidate20260925.1-wgs422/source3b1dae5 packages130 files,
121 resource keys,115 inherited. Asset manifest163e653b73cab11011ea97e5bdd14869eb8797955785f870e6f8c894470b4374;
upload plan510f2ea684257189cfcd42397d0076740b7480381a56b17cd804fc76493dbaa4.
Owner reports13 objects708270164 bytes and SOURCE_READY verified on node005.
This is staged/uploaded acceptance only, NOT SFS publication.

Failure: BS10610 installed0.8.5 assets validate, _validate_source_ready ->
_obsutil_cat, raises SOURCE_READY unavailable after unsuccessful OBS read;
direct same-object read with same private config timed out after25s, whereas
node005 succeeds. Original Infra owner is reviewing existing split-host support
without repeating network checks. No apply, ACTIVE_ASSETS write, route change,
credential copy or new publisher. Old4.2.1 selected by production catalog/profile;
asset_status pointer mismatch is separate status semantics, not a runtime selector.
Current support-path finding will decide continuation vs reporting external blocker.
No runtime tests requested yet; R2–R4 deployment remains pending R1.

Infra source review resolved the supported execution location:0.8.5 assets
validate only reads OBS on its caller; assets apply repeats that local read,
then uses configured hosts.cce_admin_ssh for remote kubectl. Continue on node005
for BOTH validate/apply, provided existing admin SSH resolves to BS10610 with
configured usable kubectl/kubeconfig and readable frozen profile/manifest.
Owner was dispatched to check only those prerequisites and continue R1; no
new publisher, OBS credential copy, routing change or SOURCE_READY bypass.
If the existing configuration does not satisfy them, report the exact missing
precondition rather than inventing credentials. Source references: native
docs/architecture/cce-pipeline-0.8.0-workflow-asset-release.md section13 and
docs/operations/cce-release.md. BS10610 remains the CCE executor, node005 OBS.

Final blocker confirmed by WGS owner: node005 `ssh -o BatchMode=yes BS10610
hostname` fails `Could not resolve hostname bs10610`; ssh -G leaves literal
bs10610. Existing server10610 access needs an explicit task known-hosts file,
not the current operator's default SSH invocation. The configured remote
kubectl and kubeconfig were previously proven on server10610; OBS and frozen
input readability on node005 are also proven. Do not repeat these checks.
No home SSH edit, key copy, host-key bypass, routing modification or custom
wrapper was attempted. Coordinator will request direction for original Infra
owner to repair only the managed admin alias/verified host-key prerequisite.
R1/R2 owners told to hold writes; no SFS/profile/image/environment activation.
Updated local R1_STATUS receipt read and SHA matched:
8c38daf1d04a2da823c8db3d7d3c7d7de1986e17130f67f15dbf68b3ed0b74d1.
All R2 installation/push and R3/R4 work remains pending; no remote test suite run.
Progress docs and integration preview are committed locally; no main/production
push. Once the SSH prerequisite is explicitly resolved, reuse the same staged
candidate, not a new upload/rebuild, then follow R1 through R4 in order.

## 2026-09-25 WGS4.2.2/P0 replacement plan; no implementation

User asks for four ordered steps and explicit cooperation with WGS-pipeline
(01a09149-ad9d-7e92-b98a-16d9cae075e2). Read its existing release plans and request
local-record handoffs from that owner and huawei-cloude native/Infra owner. New
plan: docs/superpowers/plans/2026-09-25-wgs422-p0-test-release.md. Coordinator
maintains docs; original owners retain release/artifact duties. No new agents.

Confirmed planning inputs: remote Git refs main/production43cd0c5, test781877e;
test contains main but not deployedStep7ae416fa. New plan preserves all three
baselines plus P0, not whole-directory replacement. WGS owner records source
ca71cd6/CCE3b1dae5 and independent4.2.2 SFS roots; execution must fresh-freeze
HEAD. September22 staging omitted later changed whitelist/index, so rebuild
manifest/resource-map/READY instead of applying stale hashes. Native dev3 Master
overlay reads WGS from SFS; base compatibility still needs owner verification.
Do not expand to five-group Worker/logger upgrades from an older WGS plan.

Important publication caveat: existingasset apply writes sharedACTIVE_ASSETS.
Publishing new roots is not the same as activating the platform/profile, but
cannot be claimed to preserve that pointer. Verify consumers and old-status
semantics before writing; unresolved impact means stop, not manual pointer edits.
Plan preserves old4.2.1 roots/profiles/batches and does not deployBS96.

Commands: local docs/source reads, git ls-remote for three named refs, ancestry
checks (test includesmain exit0; notae416fa exit1), and git diff --check. No SSH,
pytest, package install, SFS/SWR write, source integration, Docker or service
change. Tests not run because this is a plan-only request. Changed plan and three
state docs only; local docs rollback is revert, runtime remains unchanged. Next:
user review, then R1 with existing WGS owner; record published/installed/selected
statuses separately, reuse existing acceptance and only affected checks in R4.

## 2026-09-25 WGS rollout held on verified test-baseline divergence

Owner performed read-only BS10610/node200 preflight: BS10610 backend consumes
20260923-step7-ae416fa, missing compute_recovery and publish_recovery APIs;
Airflow worker/scheduler/api-server share candidates/step7-ae416fa-control/
compose.json and older20260915-main-359df11 WGS/common DAG mounts. No active
nipttest/cce-pipeline process observed and node200 runner requests empty; these
are observations, not proof of no future/shared production consumer. Three
execution gates remain false/paused. No remote install/push/restart/config write.

Coordinator independently ran local git diff ae416fa fdace86 -- backend and
git log fdace86..ae416fa on main/Step7/transfer files. Common ancestor1da45f3.
Direct replacement would remove ae416fa's independent Step7 maintenance,
frozen target/observation handling and later queued-transfer display fixes.
New DAG plus old backend is also incompatible. No additional Alembic migration
appears in the source diff; owner reports existing0025/0026 present.

Do not misclassify shared GATK backend code as forbidden by the user's GATK-test
deferral. No GATK gate/profile/image/test action is requested, but a separate
WGS-only API fork would add unnecessary work. Owner has been instructed to hold
all environment writes and record the actual evidence in task-artifacts/
p0-final-native-ops-20260925/WGS_ONLY_ROLLOUT_RECEIPT.md. Proposed next step needs
user direction: integrate already accepted P0 into the current test baseline,
preserve existing fixes, perform only affected integration checks, then deploy.

This turn edits only state/release/plan docs; git diff --check is the local
non-runtime check. No coordinator SSH, tests, build or deployment. Rollback is
not needed for the untouched environment; local documentation edits are reversible.
Owner receipt read and SHA256 matched:
03e76622c1374949da4f90c42640bd30857331dbb48880137ee01cdfbb658f3e.
No runtime tests were run because integration/deployment was held before mutation.

## 2026-09-25 WGS-only paired test rollout authorized

User explicitly defers GATK/WES testing and approves the next WGS test-entry /
candidate-runtime paired deployment and minimum recovery validation. GATK entry
discovery is no longer a prerequisite; common-runtime verification is not WES
deployment acceptance. Native/Infra remains the original artifact/deployment owner.

Scope: existing BS10610 test services and ctapa node200 WGS test entry, agreed
shared nipttest installation, accepted dev3 WGS candidate and test-only paired
configuration. Before writes, refresh actual mounts/consumers, active-use checks,
exact dependency closure and byte/permission/ACL rollback. Stop on unexpected
shared production consumers or permission/environment drift. No GATK gate/profile/
image deployment, production change, new service/Compose project, SSH authority
change, workflow-core change, biological run, broad chmod/chown or deletion.
Keep automatic scan/dispatch/recovery off; use only bounded synthetic recovery
verification, not a repeated suite or new live replacement/TTL test. Shared
outputs retain group access (2770/0660), distinct from private credentials.

Coordinator owns this repository's state documents; original owner supplies an
exact deployment and acceptance receipt without editing these shared documents.
Approval is recorded here; deployment and validation are not yet reported done.

## 2026-09-25 dev3 offline artifacts and deployment hold

Original native owner built dev3 from45323e4 (version-only child of ae90b65).
Coordinator matched nine artifact/log hashes and read original wheel3-pass/
1-skip and both Master asset/plugin/Snakemake smoke outputs. No repeated tests.
Record: docs/releases/2026-09-25-p0-validation-dev3.md. A skipped case is not
reported as passing. Source correction checkpoint remains platformfdace86.

Bounded read-only deployment preflight established ctapa@t640 and the existing
private WGS test root. Current gate is old and lacks paired modules; the assumed
Airflow release/scripts location is not the actual consumer. First path probe
failed because host Python lacks str.removeprefix; only the local probe line was
made compatible, then the same bounded check succeeded. No permission bypass,
Python upgrade, production-root read or environment write. Owner's recursive
artifact copy hit a synthetic pytest directory permission error; exact named
artifact copies subsequently succeeded, without deleting anything.

Deployment is not complete. The initial proposed eight-file list omitted paired
resume imports and did not establish the GATK test entry. Owner was asked to
correct the proposal statically only; no further SSH/tests/install. A bounded
test-service update/restart decision and rollback capture are still required
before a coherent nipttest/gate/profile/release transaction. No source feature
expansion, production rollout, new service/Compose, SSH-authority edit or clinical
operation is permitted by this handoff. Current environments remain unchanged.

## 2026-09-25 V01–V07 source correction acceptance

Goal: fix excessive/incompatible validation and then continue the blocked test
entry, without root/private shared outputs, feature expansion or production work.
Native owner froze ae90b654; platform selector base297bcee plus this follow-up
contains role-scoped trust and bounded observation/budget corrections. Source
review closed canonical-target ancestry, owner authority, legacy permission
compatibility, terminal regression and same-UID run-label conflict findings.

Changed scope: paired selector, workload/failure collector, Worker wait DAG
helper, their focused tests and the required security/runtime/deployment/state
docs. No API/schema, WGS rules, frontend or production changes. Shared outputs
are2770/0660 where created; no recursive existing-tree chmod or root chown.
Internal plugin live spool stays private and exports shared bound final evidence.

Verification: native final111 passed (ae90b65), source review only rechecked its
three findings. Platform final34 passed/two synthetic shared-parent errors;
fixture-only correction was followed by only those two passing (3.25s). DAG8
passed (3.14s). Coordinator read raw logs, matched native final hash and ran
`git diff --check`; no coordinator runtime retest. Commands and intermediate
failures are retained in docs/reviews/2026-09-25-p0-platform-corrections-result.md
and D:/pipeline/task-artifacts/p0-final-native-ops-20260925/TASK1_SOURCE_HANDOFF.md.

Remaining: affected one native wheel/two Master images, new immutable paired
test release and bootstrap/catalog/profile installation, all by original owner
after exact consumer-path/permission/rollback preflight. Plan is at
D:/pipeline/task-artifacts/p0-final-native-ops-20260925/NIPTTEST_PAIRED_PLAN_V2.md.
No build/install/switch is inferred from passing source checks. Keep recovery,
scan and dispatch disabled; no new service/Compose, TTL, biological run or BS96.
Before activation rollback is retaining current runtime; installation rollback
must preserve package/dist-info bytes, metadata and exact release/profile links.

## 2026-09-25 permission integration gate during corrections

Task2's BS10610 preflight passed, but four selected tests stopped in native/plugin
fixture setup: `SubmissionManager` rejected group-accessible internal submission
spool. No new assertion ran; this is not a valid RED or accepted correction.
See docs/reviews/2026-09-25-p0-platform-corrections-result.md for the exact log.
Native owner confirmed the private live-process claim/journal directory is read
by the current Master only; it exports shared bound `recovery-final.json` for
platform/replacement consumption. Owner restored the private/shared separation
without changing the plugin. Affected remote GREEN is pending before Task2 resumes.
No root ownership, shared-output0600, recursive permission changes or alternate
test environment workaround. Shared-root group/default-ACL preflight also needs
explicit verification before installation; setgid on a new child alone does not
prove its first inherited group is the intended collaboration group.

## 2026-09-25 validation corrections authorized; shared output requirement added

User requests fixing reviewed issues then continuing the blocked step, explicitly
forbidding root/0600 output restrictions. Plan:
docs/superpowers/plans/2026-09-25-p0-validation-corrections.md. Existing P0
worktrees retained; prior audit docs are our uncommitted changes, not discarded.
Native/Infra owner handles native plus paired trust integration and affected
artifacts. Platform owner implements independent workload/failure/DAG files;
paired entry remains native-owned until explicit handoff to avoid conflicts.
Shared output permissions are distinct from private secrets. No recursive chmod,
chown, production action, new service, unapproved Compose or new TTL Job.
Testing remains bounded remote synthetic; deployment preflight/rollback must be
explicit before the existing nipttest/paired-test blocked step can proceed.

## 2026-09-25 P0 validation code audit — review only

Goal: user requests checking code for excessive/unreasonable validation after
the non-root contract correction. Reviewed platform4a4ed3c/nativef44619d and
direct callers; independent read-only reviewers covered native guard and final
workload observations. No plugin or full-workflow review claimed.

Completed: six confirmed defects and one conditional budget risk recorded in
docs/reviews/2026-09-25-p0-validation-audit.md with source lines, triggers and
minimal correction boundaries. Known root-only/symlink entry is not fixed.
New high-priority findings: PVC/PV queries rejected by reconnect allowlist;
transient GC/completion races lose initial automatic recovery eligibility.
Also record repeated directory probes, asynchronous cleanup false refusals,
unrelated global policy changes and nested deadline mismatch.

Changed files: review note, CURRENT_STATE.md, TASKS.md, HANDOFF.md only. Commands:
local git status, source/doc reads and rg searches. `git diff --check` passed;
the review note and its linked security policy exist, and V01–V07 references
were checked. Final status contains only the four documented review/state files.
No pytest or other runtime tests: review-only request, no source change and no
need to rerun existing suites. No remote target/hostname/mount/permissions checked;
no SSH alias used. Test/production releases, services, scanner/dispatch, images,
wheels, accounts and databases remain unchanged. Worktree was clean at review
start; no commit/push/merge is requested for this review.

Next: approve/perform bounded corrections within the existing P0 paths and record
focused remote synthetic acceptance. Do not treat old fixture passes as non-root
or real cloud-reader acceptance. Risks and retained checks are in the review note.
Rollback is limited to these documentation changes; no runtime rollback needed.

## 2026-09-25 root-only requirement withdrawn after documentation audit

Goal/authority: user requests audit and cancellation of unreasonable root
requirements; Airflow deployer chenjc, workflow executor ctapa, WGS source owner
chenjx. Account names are user-provided, not a new remote UID observation.
Target: existing isolated P0 development branch, documentation only; no remote
environment fingerprint needed because no SSH/runtime/deployment was performed.

Read docs34/13/08/11, P0 requirements/progress and latest release/handoff; compare
actual platform _operator_path/selected_runtime, native _operator_file/_load_policy
and platform fixture. Both implementations hardcode UID0 and /etc; fixture changes
TRUSTED_UID and bypasses _operator_python. Prior synthetic evidence therefore does
not prove compatibility with the agreed deployment. Withdraw that requirement,
not the retained pin/path/registration/identity protections. The earlier hold
entry below is history and must not be used to demand a root-owned installation.

Changed docs: docs13 authority/affected-scope, docs34 identity boundary, docs08
runtime contract, docs11 rollout, P0 design/progress, SWR/TTL release note and
CURRENT_STATE/TASKS/HANDOFF. Existing native owner asked to align only its docs
and preflight follow-up, not to change code, install, rebuild or run remote tests.
Native owner committed f44619d (docs only); coordinator read the new trust audit
and latest HANDOFF. It agrees on role separation, retained pins, interpreter-link
scope and unmodified code. Original publication/TTL receipts are preserved.

Open: P0-NONROOT-ENTRY aligns both existing readers using deployment-managed
role-scoped authority outside the untrusted policy/project. Actual non-root
interpreter checks must not substitute its validator. Existing artifacts retain
their identities/evidence but cannot be claimed to satisfy this new correction.
No P0 retry/lock/TTL algorithm reopened. No blanket username/EUID/group allowlist.

Validation: local source/doc searches and git diff/link checks only; no pytest,
Docker/Compose, SSH, runtime tests or artifact tests (documentation-only scope).
git diff --check passed; all six links to the corrected authority and their
heading anchors resolved. Platform changed files are Markdown only.
No service/scanner/dispatch, DB, permissions, CLI, image or activation changes;
no production/main merge or Git push. Rollback is this documentation diff only;
no data deletion and no runtime rollback needed. Next: bounded selector/guard
source correction by the owners, then affected remote checks before any rollout.

## 2026-09-25 installation stopped at unclosed trust prerequisite

Coordinator read scripts/cce_paired_runtime.py:selected_runtime/_operator_path
and native cce_writer_guard:_operator_file: policy, pinned runtime/platform/guard
and selected interpreter require UID0/non-writable trusted ancestry. Shared
nipttest is chenjc-owned, so a successful pip install alone cannot activate it.
Owner confirms no approved root-owned interpreter/landing/admin entry was
established. The first installation plan omitted this prerequisite; revised
NIPTTEST_PAIRED_PREFLIGHT SHA917d4f...9bf7d and owner docs701b755 correct it.
Final explicit no-new-service hold is owner docse5a1039 and preflight
SHA5cbb2216...323729; coordinator verified the revised local record/hash.
No install, new probe or extra test was performed to work around the mismatch.

STOP before CLI mutation. User's pending general paired-upgrade question does
not itself supply a trusted entry or authorize architecture expansion. Owner's
new isolated service/container suggestion is unapproved and explicitly held;
do not add services, use sudo, chown shared paths or relax UID checks. Next decision
must reconcile the agreed nipttest deployment with the existing trust model.
SWR and scoped TTL acceptance remain valid and are not whole-P0 acceptance.
No production/runtime configuration changed. Unactivated rollback: retain old
selection; both new registry images and test evidence are preserved.

## 2026-09-25 SWR + scoped TTL final receipts

SWR publication accepted: both new tags/registry manifests map exactly to accepted
WGS/GATK image config IDs; coordinator read manifests/push receipts and verified8
evidence hashes. Full identities: docs/releases/2026-09-25-p0-swr-ttl.md.
TTL exact authorized Jobs reached Complete/exit0 and Failed/exit17. Job UIDs
d53d9507-6c81-4407-ada0-dc5f56f666e3 and4be49d60-db08-4215-bec8-91bc416a00ea
match respective Pod owners. Both Jobs/Pods automatically disappeared, no manual
cleanup. Only these data-free ephemeral test objects removed; no business data,
mounts or historical resources affected. Evidence retained, not object backups.
Coordinator checked manifest/terminal/Pod/timeline/final-absence and15 hashes.
Collector elapsed131s is its own clock, not an API-clock precise TTL measurement.
Native owner HANDOFF9d636e3, no push. Source/artifact tests not repeated.

Remaining: nipttest0.8.5 versus test catalog0.8.4; final candidate not installed.
Need exact rollback snapshot and paired test rollout plan/authorization before
shared nipttest mutation through BS. User question sent; no installation yet.
Also pending approved AOM read-only entry, all-entry capacity and alert acceptance.
No test-platform service/profile activation, BS96 access or automatic recovery.

## 2026-09-25 explicit two-Job TTL authorization

Owner pre-create receipt:2026-09-25T10:08:14Z server10610/chenjc, namespace Active,
178 Jobs/2 active/172 succeeded,2 Pending Pods. Exact authorized names:
`p0-ttl-ok-d84bace-250925-1010z`, `p0-ttl-fail-d84bace-250925-1010z`;
both absent before creation. Published WGS manifest3bd26801...0336e2f5,
SA cce-pipeline-master-v1 and pull secret default-secret; no workload data mounts.
Owner wrote its HANDOFF before creation; terminal/UID/removal results pending.

User approved the scoped question: exactly two no-business-data Jobs in
snakemake-ns after SWR publication, one success/one failure, each requests10m
CPU/64Mi memory, activeDeadlineSeconds60 and terminal TTL100. Only observe and,
if necessary, clean these exact test objects; existing batches/history untouched.
Owner must first return and record unique Job names, namespace and accepted
published image digest. No PVC/OBS/business data mounts, no workflow commands,
no Secret/ConfigMap data mounts; retain known service-account/imagePullSecret
selection only. Limit resources to prior proposal100m/128Mi. Use backoffLimit0,
restartPolicyNever, exit0/exit17. Bound observation to300s after creation;
confirm terminal state and record Job/owner Pod UIDs before automatic removal.

Deletion authorization is ONLINE Kubernetes test resources only: the two exact
named Jobs and Pods whose owner UIDs match those Jobs. No label-only bulk cleanup,
namespace delete, finalizer removal, history patch or filesystem deletion. These
ephemeral objects have no promised backup; manifests, statuses and logs are
retained in task-specific evidence. Actual names/results must be appended before
and after any cleanup. TTL canary does not authorize platform activation/AOM.

## 2026-09-25 SWR publication authorized / test-install preflight

User: "SWR 已经登录，现在继续完成后续工作" after final candidate acceptance.
Scope now includes publication of the two accepted candidate images by their
original native/Infra owner, using existing authenticated SWR access and new
distinct tags. Never overwrite historical tags or rebuild accepted artifacts.
Owner must check source image IDs and destination before push, then record
actual registry manifest digests (not local image config IDs).

In parallel with publication, owner may perform read-only nipttest installation
preflight: actual host/path/Python/dependencies/current version, active users,
paired test-platform compatibility and rollback availability. No installation
until that scope is concrete; never install into WGS or change Python/dependencies
to force compatibility. No Compose/service restart, live Master replacement,
production DB, real batches, automatic policy enablement, cloud Job creation,
cleanup or AOM notification is authorized by SWR login. Prior pending live-gate
questions remain unresolved. Coordinator maintains docs only and does not push.

## 2026-09-25 native owner documentation receipt

After platform checkpoint1557bf1, native owner committed artifact/failed-attempt
records as8c722dc (parent artifact sourced84bace), only HANDOFF and
docs/operations/p0-final-native-20260925.md. Coordinator read the record,
checked two-file diff, diff --check and clean worktree; no runtime rerun.
Added exact owner documentation pin to the candidate record. No permission,
artifact identity or operational gate change; next remains scoped OPS acceptance.

## 2026-09-25 final offline artifact acceptance / operational stop checkpoint

Goal: complete delegated items2/3 without coordinator builds or unauthorized
installation. Host Operator testing/installation is nipttest only; WGS is not an
installation target. Compatible Master/executor environment remains separate.

Plugin owner delivered5ffcb07 /0.6.4+bs8.dev2, docs4f10c27: actual-wheel4 passed,
10 source files matched. Coordinator read receipt/provenance and checked clean
Git/version-only diff. Native owner source d84bace /0.8.5+p02.dev2 likewise changes
only two version strings, clean. Full hashes/paths are recorded in
docs/releases/2026-09-25-p0-final-candidates.md.

Native harness failures, not business-code changes: attempt1 build/lib in RO
source (exit1); attempt2 nonexistent package_source_commit import after wheel
build (exit1). Original RW task scratch and real source_commit API restored.
Attempt3 verify-only reused wheel SHA0b873742..., TTL3 passed but terminal module
skipped without CCE_PLUGIN_SOURCE. Owner then built/smoked both Master images.
Supplement failed collection with ModuleNotFoundError for submission_recovery:
it imported the old base-image plugin. Coordinator had sent an execution-time
warning to use final image, exact plugin/native imports and only6 missing cases.
Ordered an immediate stop on further runs and requested timing/script/hash/log
reconciliation; no rebuild/install/extra test or cloud action is authorized by
this checkpoint. Subsequent receipt reconciliation confirms the corrected run
had already completed: final WGS candidate,6 passed/0 skipped in3.78s after the
old-base failure. The message chronology had lagged execution; exact message
receipt timestamp unavailable. Raw failure log preserved, pre-correction script
not separately hashed. Coordinator read original logs/provenance and recomputed
wheel/provenance/log/script SHA values, all matching. Native TTL3+terminal6 and
both image smokes now accepted as offline artifacts; no repeated checks needed.

OPS read-only receipt confirms namespace/storage binding and a178-Job/20-Pod
snapshot, not all-writer compatibility/provider capacity/AOM acceptance. Two TTL
canary authorization and approved cloud read-only entry questions remain unanswered.
No cloud writes, historical resource edits or deployment. Rollback: keep old
artifacts selected; new candidates unactivated. No data removed.

Coordinator modifications are documentation only: CURRENT_STATE, TASKS, HANDOFF,
runbook, both plan ledgers and the new candidate record. No SSH/Docker/Compose or
runtime test run by coordinator. Local documentation target/link check and
git diff --check passed. Remaining commands: live TTL/other gates after scoped
authorization. Already accepted source suites are not to be repeated.

## 2026-09-25 final artifact / operational owner dispatch

User re-confirmed the existing installation boundary: test Operator installation
uses nipttest, never the host WGS environment/repository. Both owners notified;
confirmation of any installation actions requested. CLOUD_DEPENDENCIES separates
Operator nipttest from Master/executor (historical Python3.9 versus executor3.11);
do not upgrade nipttest or force incompatible plugin installation. Actual package
validation must retain its approved compatible environment; ask on ambiguity.

Native owner reported and stopped on an apparent tool-version mismatch, then
withdrew it after checking the actual Task5 paths: host WGS metadata84/0.48 was
the wrong comparison, not evidence of drift in the approved build. Original
nipttest RO deps remain setuptools80.10.2/wheel0.47.0, poetry-core1.9.1 cached;
both locked base image IDs match. Owner confirms only read-only preflight,
no pip/install, run/build, environment change or evidence-directory write.
Coordinator supplied the existing script's path contract, not an alternate
privilege/entry workaround. Plugin receipt and deeper OPS evidence still pending.

Plugin owner stopped its first candidate build/check with exit1: in the cached
image plus PYTHONPATH=/poetry:/testdeps, build-check.py line17 asserted Snakemake
9.24.0+biosan1 before wheel construction. Actual version/path not printed; root
cause unconfirmed at this point. Command: ssh BS10610 'bash
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/smk-k8s-group/p0-final-plugin-20260925/build.sh'.
Log: same evidence root/build-and-check.log. No wheel or installation produced.
Reported promptly to user/native owner; requested read-only metadata/path check
against original Task5 build-only versus clean image smoke separation. No blind
retry, dependency upgrade or ignored assertion authorized.

Plugin read-only diagnosis confirmed /testdeps Snakemake7.32.4 shadowed the
cached image's9.24.0+biosan1; both metadata and import paths were checked.
Approved only the owner's harness correction within original build/verify
separation: build-tool checks remain, actual-wheel process prioritizes wheel-site
then image site-packages before RO pytest helpers; strict version/import path
assertions retained. Four artifact-focused cases and byte comparison only, not
a source-suite rerun. Original failure log retained; no dependency installation.

A second harness-only failure occurred after wheel generation: the new checker
looked for failure_summary under executor instead of logger. git ls-files
confirmed snakemake_logger_plugin_rule_status/failure_summary.py. Owner stopped,
reported exit1 and retained wheel SHA4adf2595794b3f08cc22b506173c33e99dcad795102417079f8a2d042a828b1a.
Approved two path corrections and verification-only of that exact existing wheel,
not rebuild/overwrite. It is not accepted for Master consumption until checks pass.

OPS owner reports test backend still on20260923-step7-ae416fa RO, current pointer
20260912-opt-4d3d24e6, scanner/dispatch false and recovery env unset. WGS profile
declares old cce-pipeline0.8.4, namespace/storage mappings but live PVC/PV UID
not yet verified. Heavy11/25 is not cluster capacity proof. AOM/SMN evidence
unconfirmed (not proof of absence). Requested user permission for existing
Operator read-only cluster checks plus two data-free TTL canaries and exact
failure cleanup; no answer yet, so cloud mutations remain on hold.

User now requests completion of items2/3 after documentation coordinationcbb74e7.
Coordinator sent P0-FINAL-PLUGIN to existing task WGS-cloud-plugins
019f9d79-be3f-7701-af33-3595d72bbfac: isolated plugin81132cf, distinct successor
wheel, exact provenance and minimal actual-artifact checks; no shared install.
Sent P0-FINAL-NATIVE and read-only P0-OPS-GATES preflight to huawei-cloude
019f8355-2b77-7413-9553-6670c35a1a2f, requiring ownership confirmation before
execution. Native1bc67fd; dependency on the new plugin wheel is explicit.

Both owners explicitly accepted their scopes. Plugin owner confirmed clean
81132cf and plans independent0.6.4+bs8.dev2 metadata only. Native owner confirmed
clean1bc67fd and ownership of wheel/Master plus read-only operational preflight.
Environment acceptance and artifacts are pending. Coordinator does not build
or use Docker/Compose. Owners do not edit the coordinator's platform documents.
Owners must stop/report denied permissions or drift, never ask the coordinator
to bypass the restriction or substitute another entry. BS10610 is the artifact
target; no production DB, real batches, installed CLI/service changes or push.
Operational checks start read-only; exact live TTL Job, AOM cost/enablement,
notification and activation scope must be returned before mutations.
No fresh remote fingerprint is claimed by this dispatch. Source acceptance and
old artifact hashes remain unchanged. Next: receive owner reports and record
only proven artifact/environment results; no repeated broad source tests.

## 2026-09-25 documentation and progress coordination only

User instruction: wheel/Master operations belong to corresponding repository
agents; report permission/Compose problems instead of trying workarounds. Current
request is only documentation/progress coordination. No build task dispatched.

Read AGENTS, boundary, planning/handoff skills, latest three-repo HANDOFFs,
CURRENT_STATE/TASKS, P0-2 plan/ledger, Task5 artifact receipt and deployment gates.
Reconciled the stale Task4-only ledger and runbook's unfinished source gates with
Task6 final acceptance. Preserved historical evidence; no tests re-executed or
new success inferred. Fixed duplicate unfinished PG/lifecycle/review checklist
and current native pin. Added owner cards for plugin wheel, native wheel/Master
and operational acceptance; all execution cards remain pending, not dispatched.

Changed only CURRENT_STATE.md, TASKS.md, HANDOFF.md,
docs/superpowers/plans/2026-09-22-p0-joint-recovery-progress.md,
docs/superpowers/plans/2026-09-23-p0-2-master-handoff-ttl-implementation.md,
docs/releases/2026-09-24-p02-task5-offline-artifacts.md and
docs/11_DEPLOYMENT_RUNBOOK.md. No changes to native/plugin trees or build scripts.

Local read-only git status/log: platform4c04545, native1bc67fd, plugin81132cf;
all three clean before edits. Platform runtime checkpoint remains6f03dd6.
Validation: git diff --check passed; all checked relative Markdown file links
resolved; diff contained only the seven documents listed above. Source pins and
task-status review matched the recorded acceptance. No pytest/npm/Docker/Compose/
build commands appropriate or run for this change.
No remote command, so hostname/current release/mount/permission/scanner state
were NOT freshly verified; prior BS10610 observations are historical only.
No production/BS96, DB, real workflow, cloud Job, installation, service restart,
policy activation, merge or push. Services/data/old artifacts preserved untouched.

Open: actual final artifacts and operational acceptance. Next: hand owner cards
to corresponding repository agents under confirmed environment/permission scope;
only their artifact evidence closes those gates. On denied access or drift,
report command/exit/stderr/impact and ask, without alternate-entry or privilege
workarounds. No new functionality, repeated broad tests or second source review.
This entry does not establish whether an earlier Compose permission incident
occurred; it records the user's restriction, not an unaudited incident finding.
Rollback: revert this documentation-only change; no runtime/data rollback needed.

## 2026-09-25 Task6 final source review and bounded correction

Source acceptance complete; operational acceptance still open. Fresh read-only
review covered platform9b381eb..6f03dd6, native83e7adb..fd43f88 and
plugin25297f9..81132cf, against the P0 spec, P0-2 plan, TTL companion and ledger.
No Critical or Minor finding. One Important issue: selected Step3 let verified
native RUN_COMPLETE override live Job Failed (and RUN_FAILED override Complete).
Downstream already refused conflicting success, but Step3 receipts/UI and compute
settlement could be wrong. Accepted severity by effect, not merely doc mismatch.

Correction: native1bc67fd56bed31b67ee25d4454d5179ebb60928e, five-line selected
reader guard only, plus focused tests/native handoff docs. Neither replacement
authority, legacy monitor nor biology changed. Existing paired query owner turns
the raised control error into an unconfirmed observation; it is not a verified
compute terminal. Matching states and valid TTL-absent evidence are preserved.
Platform runtime6f03dd6 and plugin81132cf unchanged in this correction.

BS10610 existing task6.ps1 Mode test, same preflight and isolated offline container:
- /task/native/tests/test_recovery_monitor.py:
  final-review-terminal-red.log, 2 failed/4 passed4.35s; both opposite states
  emitted authoritative JSON before the fix (behavioral RED, not fixture errors).
- /task/native/tests/test_recovery_monitor.py plus test_recovery_downstream.py:
  final-review-terminal-green.log, 13 passed8.11s. No broad/redundant rerun.
Evidence remains /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.
Earlier this turn: PG10, full automatic/manual lifecycle4, deadline/owner denial4
passed; full commands and transport limits are in the next entry. No second review.
git diff --check passed. Initial native commit was blocked by absent Git author
configuration; reused the verified existing project identity with command-local
-c settings, not a global configuration change, then committed successfully.

Final review rulings for items the reviewer declined to judge:
1. Real TTL/capacity/AOM/notification: keep operational gate closed. Synthetic
   tests cannot establish live behavior; cost is delayed release until authorized.
2. Installed CLI/platform writers and storage mappings: retain operator-owned
   paired activation/identity checks, no inferred live compatibility. Cost is
   blocked activation where exact writer pins/mount mapping are unavailable.
3. Task6 release artifacts: immutable Task5 pins are historical acceptance, not
   current candidates. Rebuild/verify new pinned candidates in the release step;
   no overwrite or install now. Cost is an outstanding artifact acceptance gate.
4. Unrelated on-prem/intake/base-range changes: excluded from recovery review
   and untouched here. This is not a verdict on unrelated features; cost is that
   any future combined promotion still needs its own scope check.
5. Production/historical batch feasibility: no live records inspected, no old
   evidence fabricated, no rerun authorized. Missing identity remains fail-closed;
   cost is manual case-specific reconciliation for historical runs.
No deferred minors. Preserve worktrees, accepted artifacts and evidence; do not
delete the plan workspace. Rollback remains source revert, never data cleanup.

Updated platform CURRENT_STATE, TASKS, plan, docs08 and docs46 with the source/
operational distinction. No local runtime tests, BS96, real cloud writes,
workflow launch, service restart, image/CLI install, automatic-policy enablement,
merge or push. Next requires separate release/operational authorization, not
another round of unchanged source tests or new functionality.

## 2026-09-25 Task6 PostgreSQL and automatic lifecycle acceptance

Goal: continue Task6 from platform7963428; nativefd43f88/plugin81132cf unchanged.
Production code change is confined to scripts/cce_paired_runtime.py: an exact
started direct-Step3 action uses the existing selected-Master reader on re-entry;
that reader now compares compute_deadline from the registered producer too.
No replacement/takeover shortcut, budget reset or workflow change.

Added backend/tests/test_cce_recovery_postgres.py and
scripts/tests/test_p02_automatic_flow.py. Extended the existing manual/native
test harness and DAG HTTP transport to exchange actual backend responses, so
opted-in Step4 begin/check/finish and normal finalize are exercised. Config/cloud
transport is synthetic; no forged post-seal failure proof or fake stage body.

BS10610 runner: .superpowers/sdd/2026-09-23-p0-2-master-handoff-ttl-implementation/task6.ps1
- Mode pg, backend/tests/test_cce_recovery_postgres.py:
  pg-contention-final.log, 10 passed7.42s.
- Mode integrated, scripts/tests/test_p02_automatic_flow.py and
  scripts/tests/test_p02_manual_flow.py: automatic-manual-lifecycle-final.log,
  4 passed94.49s. Actual services/DAG callables/native gates, SQLite lifecycle DB;
  PostgreSQL contention is separately tested above.
- Mode integrated, selected-monitor journal_deadline/lock_owner × WGS/GATK:
  automatic-final-fences.log, 4 passed8.11s; changed deadline and foreign owner
  remain rejected. git diff --check passed.
- Initial PG run failed before tests because the original cached Python image
  could not import psycopg2._psycopg. Switched to already-cached compatible
  Airflow image58195672 (psycopg2 2.9.9); no dependency installation/service update.
- Intermediate lifecycle fixture errors: missing producer platform identity,
  wrong DNS label/control workdir, read-only Airflow HOME, missing normal launch
  archival/query transport, missing synthetic finalization catalog. Fixed only
  fixture boundaries; no weakened native checks. These are NOT behavioral RED.
- Behavioral RED: automatic-lifecycle-context.log (confirmed replacement Job
  absent on same-action re-entry); automatic-lifecycle-reentry.log (reader did
  not account for producer compute_deadline). Both now covered by final4 GREEN.

Preflight each call: server10610 uid6708; control airflow-WGS/current points to
20260912-opt-4d3d24e6; backend36ff21f87356 /app RO20260923-step7-ae416fa and /config
RO20260912-opt-4d3d24e6; scanner/auto-dispatch false. Evidence is retained under
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.
No local runtime tests, broad test rerun, real workflow, BS96 access, image build,
CLI/runtime installation, source merge/push or deployment. Rollback is source
revert only. Remaining: final whole-plan fresh review; separate cloud TTL,
Pod capacity and AOM/alert evidence must not be inferred from synthetic tests.

### Disposable PostgreSQL cleanup authorization and results

User requested continuation; scope is isolated synthetic validation only.
Plan: use cached postgres image9943612906a8 in one uniquely named task container,
network none/no published ports, localhost only, tmpfs database and Unix socket.
Test container joins only that container's network namespace. No shared service
database/network/volume or host data is used. Runner records exact generated
container name/ID and stops only that owned labeled container in finally;
auto-removal discards its temporary synthetic database (intentionally no backup).
Evidence stays under the existing BS10610 p02-task6-20260925 task root.

Only these task-created online temporary containers/tmpfs databases were removed:
- p02-task6-pg-5028356e8ab2 (f07fef93d07e): failed driver preparation; removed.
- p02-task6-pg-577164160828 (3e40294d8ca7): passing PG contention; removed.
- p02-task6-pg-6ec4ea5d0a4b (e47dd670e5db): initial lifecycle fixture run; removed.
Each deletion verified generated name/owner label/full ID first. No backup; this
synthetic temporary DB data is not recoverable. No host directory, real input,
pending, results, service volume/database or retained evidence was deleted.

## 2026-09-25 Task6 continuation / explicit monitor handoff

Goal: continue approved automatic/manual interaction from platform728f098,
nativefd43f88/plugin81132cf. Same isolated platform branch; native/plugin unchanged.
No production access, rerun, service change, push/merge/deploy or artifact rebuild.

Completed: poll query-unconfirmed guard prevents a failed observer becoming
compute_terminal=failed. Existing manual Step3 service may retire an exact ended
query observer only after blocked/exhausted scope validation, current confirmed
action/DagRun/generation, frozen request checks and the existing run lock. The
prior action becomes canceled with monitor_handoff_to, not compute-failed.
Successor identity and retirement commit together; existing runtime must check
original execution liveness. Pending/uncertain/active/foreign/stopped actions
remain fenced. Same key/new concurrent click reuse the active operation; later
explicit monitor recovery can have a new generation without resetting attempt,
compute count or deadline. GATK manual registration now retains the deadline.
Existing ResumeStagePanel is reused for WGS/GATK query attention and labels it
恢复监控; adapter resume capability and operator confirmation still apply.

Files: backend cce_recovery_poll/budget, cce_resume_dispatch, wgs_resume_service,
gatk_runtime_service; new test_cce_manual_monitor_reconnect and poll regression;
frontend ResumeStagePanel/test and RunDetailPage; docs04/05/06/08, plan and state
docs. No migration, DAG/native/plugin/workflow changes or new public endpoint.

Environment verified by each existing task6.ps1 call before task writes:
ssh BS10610 -> server10610, uid6708; control
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/current resolves to
releases/20260912-opt-4d3d24e6. Backend36ff21f87356 /app RO remains
20260923-step7-ae416fa/backend/backend; /config RO remains current release/config.
Scanner/auto-dispatch false. Cached test containers a0112f0b8ef0 / 25e83a56052d,
network-none, read-only root, task-scoped scratch; no runtime services altered.
Evidence: /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.

Commands/results (runner: ignored .superpowers/sdd/2026-09-23-p0-2-master-handoff-ttl-implementation/task6.ps1):
- Mode test, poll::test_monitor_query_failure_does_not_settle_compute_or_reserve_another_slot:
  query-action-red.log, exit1/6 expected failures, false compute_terminal persisted.
- Mode test, manual monitor positive test: manual-reconnect-red.log, exit1/2
  expected failures, old automatic queued action permanently blocked manual Resume.
- Mode test, poll + manual files: monitor-handoff-green.log, exit1/29 pass/1 fail;
  GATK dropped cce_recovery_deadline. Repair scoped inheritance, not a new deadline.
- Mode test, test_cce_manual_monitor_reconnect.py + test_cce_recovery_poll.py +
  test_wgs_resume_stage.py + test_gatk_resume_stage.py + test_cce_recovery_manual_fence.py:
  monitor-handoff-final.log, exit0, 82 pass15.32s; existing Starlette deprecation only.
- Mode ui, src/features/run-detail/ResumeStagePanel.test.tsx:
  monitor-ui-red.log exit1/1 expected missing helper; monitor-ui-green.log exit0,
  2 pass3.15s. Existing uncertain-reply key and new explicit monitor control tested.
- Mode ui-build: monitor-ui-build.log exit0, tsc -b and Vite build successful.
No local runtime tests, broad suites, real biological/cloud tasks or production DB.

Open: Task6/CR-04 not closed. Next focused PostgreSQL concurrent-action checks,
full automatic lifecycle integration, then one fresh whole-plan review. These
were not run in this bounded interaction checkpoint; SQLite tests do NOT prove
PostgreSQL lock contention. Operational TTL/capacity/AOM/alerts remain separately
authorized gates. No change to default-off policy or accepted Task5 artifacts.
Rollback: revert this isolated source checkpoint before any release; no production
rollback required. Preserve history/evidence and do not roll an enabled controller
back across an in-flight handoff without reconciliation. Tracked changes are this
checkpoint only; commit after final diff/whitespace check, no remote branch update.

## 2026-09-25 Task6 continuation / finite reconnect wired

Goal: continue approved query-only CR-04 integration from platform400bf77 and
native90cae30, same isolated branches. Native source now fd43f88; plugin81132cf
unchanged. No production, main/production merge, push, deploy or real workflow.

Completed: selected WGS/GATK monitor GET-only retry owner, durable existing
status JSON reservations/identity and original deadline, missing/foreign/terminal
status fence; full observation clears only query budget. Private hook reaches
strict and legacy native readers without wrapping mutations. Runtime outer
failure keeps marker. Backend real ingestion preserves confirmed analysis and
stage projections; existing view shows checking/needs_attention limit6. Shared
callback and periodic DagRun failure fence prevents false analysis failure.
Selected identity/control errors stop without retry or terminal inference.

Files: scripts/cce_paired_runtime.py, cce_query_reconnect.py, WGS/GATK gate status
writers and their selected/status tests; backend cce_monitor_observation,
cce_recovery_budget/projection, wgs_observer, gatk_runtime_service,
diagnostics_service/gatk_airflow_sync and producer-ingestion test; docs04/05/08,
plan, CURRENT_STATE/TASKS/HANDOFF. No frontend/schema/workflow changes.

Validation via existing ignored task6.ps1 only on ssh BS10610 / server10610:
control /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/current remains
releases/20260912-opt-4d3d24e6; backend36ff21f87356 /app RO points to
20260923-step7-ae416fa/backend/backend, /config RO to current release/config;
scanner/auto-dispatch false, evidence uid6708. Cached a0112f0b8ef0 container,
network-none/read-only root and task-scoped scratch. No services changed.
Evidence root: /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.
- query-periodic-red: WGS entered analysis failure diagnostics; GATK became failed.
  Shared current-monitor fence -> query-periodic-green2 pass2.14s.
- query-selected-integration:2 failed ProtectedWriter config mismatch. A bound
  method was deep-copied; stable closure retains one owner without weakening
  comparisons. query-selected-final: actual protected new/legacy WGS/GATK4
  pass6.43s; no second CREATE/START, source config not mutated.
- query-control-red2 missing blocked marker -> query-control-green2 pass0.27s.
- query-status-fence-red2 missing status silently accepted; fail closed before
  any GET -> query-status-fence-green producer/consumer16 pass3.63s.
- query-wiring-final: native query24, core17, status8, ingestion4, projection,
  callback fences, GATK and observer periodic sync regression total113 pass8.29s.
  Final fence changed only paired owner/status fixture; affected16 + selected4
  rerun above. git diff --check passes (native only normal LF/CRLF warnings).

Not run: broad suites, local runtime tests, frontend build (no frontend change),
PG contention/full automatic lifecycle, live cluster TTL/AOM, image builds.
These remain separate planned gates, not inferred passed from synthetic SQLite.
Task6/CR-04 OPEN: next final automatic/manual reconnect interaction (including
pending automatic-action mutual exclusion and existing manual entry), focused PG,
then whole-plan fresh review. No new manual control/status invented here.
Task5 frozen artifacts do NOT contain this paired source; installed CLI/policy
unchanged. Rollback before activation is source revert of these paired commits;
no data or service rollback needed. Do not clean other worktrees or evidence.

## 2026-09-25 Task6 continuation / finite query-budget prerequisite

Goal: continue original Task6/CR-04, BASE04a1a04 platform and BASEd7bd741 native,
same isolated branches. Scope is query-only budget and strict native read ABI,
not new recovery policy/state machine for compute, public endpoints or controls.
Paired native source committed90cae30; plugin remains81132cf, artifacts unchanged.

Completed: scripts/cce_query_reconnect.py consumes caller-owned current scope and
original deadline, one typed read-only GET at a time. Max6 retries with delays
30/60/120/240/300/300, capped request30s/original deadline, persist before retry,
crash consumes in-flight slot, failed persistence cannot authorize another call.
Partial GET success retains outage count; explicit authoritative observation is
needed to clear it. Exhausted/blocked/foreign/corrupt state fails closed. Tests
use actual strict native GET + fake subprocess transport and synthetic JSON;
the runtime persistence callback itself is NOT wired to real monitor status yet.

Native prerequisite: platform selected observer calls _recovery_query(configmap)
but native only accepted Job, so real directory-lock read failed INVALID_QUERY.
Added exact ConfigMap under same identity envelope. Missing/denied command and
auth/certificate failures no longer map to transport; generic unable-to-connect
is unknown, not auto-retryable. Positive caller timeout may shorten existing30s.
No legacy _kubectl_json, Snakemake workflow/plugin, CREATE/START or installed CLI
changes. Files: platform helper/test + docs08/plan/state/tasks/handoff; native
cce_batch_runtime.py/test_recovery_query.py/HANDOFF. Native source commit is paired,
not contained in accepted Task5 wheels/images. Do not rebuild/activate implicitly.

Validation: task6.ps1 preflight verified ssh BS10610 -> server10610; control
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/current remains
releases/20260912-opt-4d3d24e6, backend36ff21f87356 expected /app and /config RO
mounts, scanner/auto-dispatch false, uid6708; no services changed. Same cached
backend a0112f0b8ef0 with network-none/read-only root and scoped scratch.
Evidence root: /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.
Command: task6.ps1 -Mode test -Test '/task/native/tests/test_recovery_query.py
/task/platform/scripts/tests/test_cce_query_reconnect.py' -Log query-reconnect-final.
Initial RED: collection missing new module (exit1), query-reconnect-red.log.
Budget-corruption RED: three expected failures (a waiting count6 could exceed its
limit; healthy nonzero count and bool attempt accepted), one passed;
query-reconnect-fence-red.log. Fixed input-state validation, no runtime workaround.
Final41 passed0.79s (native24 + platform17), exit0, query-reconnect-final.log.
No local runtime tests, broad suites, frontend/DAG reruns or real K8s operations.

Remaining/next: wire this owner only to paired selected monitor GETs, with current
worker identity and existing status JSON atomic persistence; preserve reconnect
fields through outer handlers. GATK currently can mark query error as analysis
failed; that consumer and DagRun callback/periodic failure projection need the
same explicit unconfirmed marker before UI integration acceptance. No retries
around prepare_monitor_registered, Resume mutation or whole stage. No authority
from cached progress. Then focused PG/final automatic lifecycle + whole-plan
review. Task6 and CR-04 remain OPEN; no production/push/main merge/deployment.
Rollback: revert paired source commits; no installed state to restore.

## 2026-09-25 Task6 continuation / existing recovery UI

Goal: CR-04 existing Tracker/RunDetail projection, BASE5257b77 on isolated
jiucheng/runtime/CR01-cce-recovery-20260922. No new pages, controls, retry policy,
native/plugin changes, production access, merge/push or artifact rebuild.

Completed: shared read-only recovery_views bulk-reads current-attempt actions and
latest stage generation. It projects waiting/checking/recovering/needs_attention/
stale/completed_degraded with allowlisted messages, due time and last healthy
observation time; no raw path/error/action conf exposed. Queued/running controller
alone cannot imply started Master; schema2 platform identity, native Job/Pod UID
and action match are required. Old attempt/generation/manual-action/user-stop
fences apply. The successful run can retain a Step3 log-health warning after
finalize. Historical workflow/action status and budgets are never changed by GET.

Real-consumer check found running binding/health were not retained. Added a small
UI-only cce_monitor_observation in existing execution JSON after existing identity
gates; no terminal receipt/hash is invented. WGS/GATK preserve newer observations
against old healthy replays. Snapshot contains only time/health and reduced binding.
CurrentProgressPanel/RunTracker reuse existing bars, retain measured values and
disable estimated advancement/live speed/ETA for uncertain or stopped recovery.
Healthy reattachment removes the overlay; actual started recovery uses normal
progress. The old failure remains history, not rewritten to success/running.

Files: new backend cce_recovery_projection/cce_monitor_observation and projection
tests; existing dashboard_service/run_service and WGS/GATK status ingestion;
frontend API types, shared RecoveryNotice, RunTracker/CurrentProgressPanel and
their tests; docs04/05/06 and state/plan/handoff. No runtime producer or DAG edits.

Validation: BS10610 preflight server10610; control
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/current -> releases/20260912-opt-4d3d24e6;
backend36ff21f87356 /app and /config RO mounts unchanged, scan/dispatch disabled.
Task-specific evidence under
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.
Cached backend image a0112f0b8ef0 and frontend builder25e83a56052d; network-none,
read-only root, uid6708, isolated scratch only; no service changes/dependency download.
RED: projection16 failures before implementation; UI3 expected failures; actual
ingestion2 failures after correcting fixture's required v2 envelope. GREEN:
pytest test_cce_recovery_projection.py test_cce_recovery_receipt_projection.py
26 passed3.03s (ui-projection-final2.log); vitest RunTracker/CurrentProgressPanel
13 passed6.17s (ui-components-final.log); npm run build (tsc -b + vite) exit0
(ui-build-final.log). One intermediate frontend test failed because a loose text
selector matched label and explanation; narrowed selector, no product workaround.
No local runtime tests/full-suite repetition/browser or live synthetic run.

Remaining: CR-04 finite-reconnect versus exhausted producer-to-UI distinction
must be verified in final integration. This checkpoint only projects actual
persisted health/actions; degraded alone does not prove an active reconnect loop.
Next focused PG contention and full automatic lifecycle integration, then one
fresh whole-plan review. Separately authorized live TTL/capacity/AOM/alerts gates
remain closed; Task6/P0 are NOT fully complete or production-ready.
Rollback: revert this source checkpoint; optional response/snapshot fields are
additive with no migration. Original native d7bd741/plugin81132cf unchanged.

## 2026-09-25 Task6 continuation / Step4 actual caller

Goal: connect the accepted Step4 probe/budget to existing WGS/GATK registration,
runner and sensor. BASE29aae91, isolated jiucheng/runtime/CR01-cce-recovery-20260922.
User requested continuation with no scope expansion or redundant tests. No BS96,
production DB, analysis submission, shared installation, image rebuild or push.

Completed: first opted-in Step4 freezes hashed marker1/original stage deadline;
both adapters preserve execution identity on lost registration replies, including
terminal failures. Existing authenticated stage route accepts begin/poll/check/
finish and commits intent/challenge before SSH. Actual DagRun/recovery identity,
pending control/maintenance, latest generation/hash and frozen request are checked.
Manual Resume cannot race an unresolved publish action; stop paths remain allowed.
Existing Airflow Step4 runner sends once via fixed --publish-dispatch, capped by
120s/original deadline, and acknowledges only that exact local process exit.
Timeout/nonzero enters existing sensor reconciliation. A crashed caller retains
in-flight ambiguity. Sensor makes at most one probe per poke and sends only the
backend-authorized same identity; success still requires normal stage receipt.
Default-off policy, DAG graph/pools/task retries and compute budget unchanged.

Files: backend cce_publish_recovery/cce_recovery_budget, main existing schemas/
routes, WGS registration and GATK runtime service; dags cce_publish_dispatch and
both existing DAG modules; scripts cce_publish_recovery and both runtime gates;
two new caller test files plus original Step4 probe tests. Docs04/05/07/08,
Task6 plan and state/task/handoff/ignored ledger aligned. No frontend/native/plugin
changes. Needed ancillary fix: main.py used Any in the previous Worker observation
schema without importing it; actual route import reproduced NameError, now fixed.

Validation: only ignored task6.ps1 runner, BS10610 synthetic/cached containers.
- step4-caller-red12 failures: absent registration marker / missing control caller.
- step4-airflow-red10 failed4 passed: absent actual DagRun field/automatic stop
  handling. Strengthened probe test to assert it actually made both control calls.
- step4-registration-check6 failed8 passed: GATK filename suffix mismatch in new
  caller plus not-yet-implemented exact send; use actual .request.json convention.
- step4-send-deadline-red2 failures reproduced sends after expired deadline.
- step4-caller-fences-red8 failed12 passed: absent manual/stale-caller fences,
  repeated terminal registration generatedg2, and prior Any import failure.
- step4-caller-boundary-green1 failed88 passed: package import of WGS release
  selector failed; corrected package/standalone import as existing gates require.
- FINAL -Mode test -Test '/task/platform/backend/tests/test_cce_publish_caller.py
  /task/platform/scripts/tests/test_cce_publish_probe.py
  /task/platform/backend/tests/test_cce_publish_recovery.py
  /task/platform/scripts/tests/test_gatk_dispatcher_fence.py::test_ambiguous_spawn_does_not_launch_again'
  -Log step4-caller-final:90 passed7.11s, exit0.
- FINAL -Mode dag -Test /task/platform/dags/tests/test_cce_publish_caller.py
  -Log step4-airflow-final:20 passed3.04s, exit0; actual Airflow DAG imports/callables,
  only external HTTP/SSH substituted. No local runtime tests or broad suite rerun.
- Tests use real SQLAlchemy temporary SQLite transactions/files/locks/request
  registration, not production DB. PG contention and whole automatic integration
  remain planned; this is not a PostgreSQL or cloud-operation acceptance claim.

Each invocation verified test BS10610/server10610, control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS, current
releases/20260912-opt-4d3d24e6 and backend36ff21f87356 actual RO mounts:
/app from20260923-step7-ae416fa/backend/backend, /config from current. Scanner/
auto-dispatch false; UID6708 evidence under
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.
Cached network-none RO1CPU/1GiB containers with task scratch RW. Existing kernel
swap-limit warning only. All services/current/rollback pointers preserved.

Task6 OPEN. Next existing UI projections, focused PG contention/final automatic
integration, then whole-plan review. Separately authorized live TTL/capacity/AOM/
alerts still required; no production readiness claim. Rollback is source revert
only; preserve state/receipts/history and accepted artifact pins. No cleanup.

## 2026-09-25 Task6 continuation / Step4 original operation and durable budget

Goal: next approved Step4 slice, source development only, minimal targeted tests.
BASE platform a53aabd; branch jiucheng/runtime/CR01-cce-recovery-20260922 in the
existing isolated worktree. Native d7bd741/plugin81132cf unchanged. No production
access, push/merge, new artifact build, install, automatic enablement or real run.

Completed: scripts/cce_publish_recovery.py validates the original registered
Step4 operation and lock/process/receipt evidence; both restricted gates expose
fixed --publish-probe. New hashed request marker publish_dispatch_version=1 is
mandatory, never inferred for legacy requests. WGS opted-in async launch refuses
repeat Popen after uncertain intent; GATK's existing intent fence is unchanged.
Only absence of records under free launch/worker locks yields not_started;
unknown/foreign/malformed evidence cannot authorize replay. Existing terminal
receipts are read, not synthesized; no native publish record reconstruction or
output scanning. No automatic caller or new registered marker is enabled yet.

backend/app/cce_publish_recovery.py uses existing RunAction and refreshed run/
latest execution locks: one initial sequence0, max2 same-operation redispatches
60/180; original stage deadline, identity, release and workdir retained. Separate
from compute budget. Initial intent must commit before SSH; exact local SSH exit
acknowledges its sequence, process death leaves in_flight unresolved. Negative
proof cannot override in-flight; dispatch requires a challenge issued at/after
due time. Consumed duplicates/stale identity cannot spend another slot. Started
once never returns to not-started eligibility, and success survives later expiry.
Stop/expiry blocks unsent work. Service does not commit or perform external I/O.

Changed files: two new cce_publish_recovery.py modules, both existing runtime
gates, backend/tests/test_cce_publish_recovery.py and scripts/tests/test_cce_publish_probe.py.
Docs04/05/08, plan Task6, CURRENT_STATE/TASKS/HANDOFF updated. No schema migration,
public route, DAG node, frontend, native or biological workflow changes.

Tests via ignored .superpowers/sdd/2026-09-23-p0-2-master-handoff-ttl-implementation/task6.ps1:
- step4-probe-red:27 failed/1 passed (missing probe and WGS ambiguous launch fence;
  removed the irrelevant GATK no-op parameter before GREEN), then27 GREEN1.30s.
- step4-budget-red:22 failed (missing budget service). Initial budget/command
  boundary32 GREEN2.22s. Additional freshness/started-once/terminal boundary6 RED.
- Final -Mode test -Test '/task/platform/backend/tests/test_cce_publish_recovery.py
  /task/platform/scripts/tests/test_cce_publish_probe.py
  /task/platform/scripts/tests/test_gatk_dispatcher_fence.py::test_ambiguous_spawn_does_not_launch_again'
  -Log step4-contract-final:64 passed3.73s, exit0. Real locks, request files,
  SQLAlchemy transactions and gate loaders; only external Popen replaced.
- git diff --check: clean. No full suite, local runtime tests, PG contention,
  Airflow integration or live publish: deferred until the actual caller is wired.
  Docker reports existing kernel swap-limit warning; no test failure.

Every invocation verified BS10610/server10610, control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS, current release
releases/20260912-opt-4d3d24e6 and backend36ff21f87356 actual RO mounts:
/app from20260923-step7-ae416fa/backend/backend, /config from current. Scanner/
auto-dispatch false. UID6708 task evidence path:
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.
Cached network-none/read-only1CPU/1GiB container, source RO/task scratch RW.
Services and current/rollback pointers preserved, no deployment/cleanup.

Next: existing stage registration freezes this marker/deadline, and existing
Step4 runner/reschedule sensor uses begin/finish/poll plus restricted probe. Send
only original hash-pinned identity, commit/recheck controls before SSH; confirm
normal authoritative stage receipt before downstream, do not fabricate success
from the budget alone. Wire recovery-action/control fencing there. No retries=2
on the whole side-effectful task, no new DAG nodes. PG contention/full automatic
integration, existing UI and separately authorized cloud gates still OPEN.
Risk: source contracts alone cannot repair a production SSH timeout. Ambiguous
caller crash deliberately needs reconciliation, not guessed re-dispatch. Rollback
by reverting this source checkpoint; no running service rollback needed.

## 2026-09-25 Task6 continuation / exact CREATE failure classes

Goal: continue the approved next slice without widening retries or redundant
tests. BASE platform898db80/plugin c0b266b/native d7bd741. Plugin checkpoint now
81132cf on jiucheng/runtime/p02-worker-terminal-20260923. Platform changes stay
on jiucheng/runtime/CR01-cce-recovery-20260922; native clean/unchanged. No production,
push, main/production merge, build, install, activation, real rerun or service change.

Completed: plugin recognizes exact CREATE Status500 RPC Unavailable/peer-reset;
reconciles deterministic original Job first (PRESENT adopts, UNKNOWN blocks,
ABSENT uses existing bounded submission retries). New category carries only four
fixed typed fields, independently checked by inventory and backend before existing
ABSENT/exhaustion/fatal-cause/terminal gates. mutation.gatekeeper.sh exact500
context-deadline now recognized; policy denial/generic500/missing Status rejected.
Legacy Gatekeeper classes, budgets and default-off policy unchanged. Task5 frozen
wheel/images are not rebuilt and do not include this successor source checkpoint.

Files: backend/app/cce_recovery_evidence.py, scripts/cce_recovery_inventory.py;
new backend/tests/test_cce_rpc_evidence.py; existing scripts/tests/test_p02_failure_evidence.py
uses actual plugin/logger/native FINAL and normal platform receipt/reservation.
Plugin submission_recovery.py, new test_storage_rpc_submission.py and HANDOFF.
Docs08/10, design section3.1, Task6 plan, CURRENT_STATE/TASKS/HANDOFF synchronized.
No public API, DB schema, DAG, frontend or biological workflow change.

Validation via ignored .superpowers/sdd/2026-09-23-p0-2-master-handoff-ttl-implementation/task6.ps1:
initial exact-create-red4 failed/20 passed (missing classes/validator), then24 GREEN.
Mutation strict-boundary4 RED caught legacy over-broad recognition; narrowed new
mutation path, preserving old validation/check-ignore-label rules. Final commands:

- -Mode test -Test '/task/plugin/tests/test_storage_rpc_submission.py
  /task/platform/backend/tests/test_cce_rpc_evidence.py
  /task/plugin/tests/test_submission_recovery.py::test_admission_timeout_has_three_requests_with_30_60_backoff
  /task/plugin/tests/test_submission_recovery.py::test_lost_response_is_adopted_by_exact_name_without_second_post'
  -Log exact-create-final:30 passed2.34s, exit0.
- -Mode test -Test '/task/platform/scripts/tests/test_p02_failure_evidence.py::test_schema2_evidence_through_normal_receipt_and_reservation
  -k storage_rpc' -Log storage-rpc-chain:2 passed/4 deselected3.00s, exit0.

Both WGS/GATK chains accepted one idempotent reservation with distinct native/
platform identity. No full suite or repeated accepted Task1–5 tests. Local runtime,
real cluster, PG contention and deployment tests not run: outside this source slice.
One documentation read used a nonexistent docs/10_ERROR_LOGGING.md filename;
resolved with rg to docs/10_QC_LOGGING_REPORTING.md, no runtime side effect.

Each remote invocation verified BS10610/server10610, control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS and current release
releases/20260912-opt-4d3d24e6. Backend36ff21f87356 RO/app from
20260923-step7-ae416fa/backend/backend; RO/config from current; scanner/dispatch false.
Evidence uid6708 confined to /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.
Cached network-none/read-only synthetic container, source RO/scratch RW,1CPU/1GiB.
Live services and current/rollback release pointers untouched. This does not
replay archived production failures or authorize activation of new artifacts.

Task6 OPEN. Next Step4 ambiguous SSH dispatch: reconcile original operation,
at most two same-operation redispatches60/180 only with proven not-started and no
in-flight process; separate budget. Then existing UI/PG/final integration and
separately authorized operational gates. Rollback: revert this paired source
checkpoint before any future artifact build; no live rollback currently needed.

## 2026-09-25 Task6 continuation / bounded natural Worker wait

User: continue the next approved Task6 step, preserve scope and avoid redundant
tests. BASE platform7d9f1f8/native d7bd741/plugin c0b266b. Only the existing platform
branch jiucheng/runtime/CR01-cce-recovery-20260922 changed. Native/plugin trees
remain clean; Task5 artifacts unchanged. No push, merge, build, installed policy,
production access, real rerun, deployment or service/scan/dispatch changes.

Completed within this slice: existing automatic RunAction persists worker_wait
start/deadline/state and one nonce-bound monitor probe. It consumes one existing
compute slot and caps wait at min600s/original deadline. Duplicate consumed replies
cannot clear the next challenge. Direct due-dispatch cannot bypass waiting;
stop/expiry/changed proof rejects an untransmitted action. Failed monitor receipts
and FINAL are immutable. Existing Step3 sensors call one fixed read-only restricted
probe per poke; timeout/nonzero/malformed response only reschedules. The restricted
reader rechecks registered request, exact failed receipt, selected native producer,
operator writer/directory owner, retained lineage and complete live inventories.
Only active counts may change. Normal native replacement remains strict and does
its own fresh quiescence check before side effects. No automatic kill.

Files: backend cce_recovery_{evidence,service,poll}, cce_compute_dispatch, existing
main.py internal request/route; dags/cce_worker_wait.py plus existing bio_wgs/gatk;
scripts/cce_recovery_workloads/failure, cce_paired_runtime and both restricted
gate entries. New backend waiting test and focused existing runtime/DAG fixtures.
Docs04/05/07/08, implementation plan, CURRENT_STATE/TASKS and this handoff updated.
No new DB table/migration, public route, scheduler, DAG node, frontend or native code.

Validation: backend new10 RED (missing worker_observation) ->10 GREEN3.17s.
One attempted runtime selection ran ZERO tests because the runner splits arguments
and the quoted '-k A or B' expression was split; no source defect or side effect.
Corrected to exact node IDs/single-token filter, not a broad rerun. Runtime strict
Master/active-worker checks7 GREEN5.09s; actual failed-monitor/probe2 GREEN5.43s;
real Airflow six scoped cases GREEN3.05s. After the final nonce replay/direct
dispatch/entry guards, final commands via ignored task6.ps1 were:

- -Mode test -Test '/task/platform/backend/tests/test_cce_worker_wait.py
  /task/platform/backend/tests/test_cce_recovery_dispatch.py::test_due_action_keeps_single_budget_and_uses_existing_resume_generation
  /task/platform/backend/tests/test_cce_recovery_dispatch.py::test_uncertain_post_is_get_only_even_after_deadline_and_stop
  /task/platform/scripts/tests/test_p02_failure_evidence.py::test_final_active_worker_is_wait_only_then_fresh_terminal_proof'
  -Log worker-wait-backend-final:17 passed5.52s.
- -Mode test -Test '/task/platform/scripts/tests/test_p02_selected_monitor.py
  -k recoverable_failure' -Log worker-wait-entry-final:2 passed5.27s.
- -Mode dag -Test '/task/platform/dags/tests/test_cce_recovery_poll.py::test_existing_sensor_runs_one_bounded_read_only_probe'
  -Log worker-wait-airflow-final:4 passed3.03s.

Every remote invocation verified BS10610/server10610 and existing control/current
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260912-opt-4d3d24e6;
backend36ff21f87356 RO/app from20260923-step7-ae416fa/backend/backend, RO/config from
current, scanner/automatic dispatch false. Evidence uid6708 confined to
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925. Containers
cached only, network none, source RO, task scratch RW,1CPU/1GiB. Live services and
release/rollback pointers untouched. No local runtime tests, full suite, real
Kubernetes/SSH probe execution against a run, PostgreSQL contention or TTL test;
those require the remaining Task6/separate activation gates, not this checkpoint.

Known boundary: a reclaimed Worker without exact persisted terminal proof remains
ineligible, even if it might have completed. Query/unknown evidence never authorizes
replacement; persisted wait eventually exhausts to manual review. No claims of
whole Task6/P0 completion or end-to-end production readiness. Next: exact remaining
failure classifications then Step4 uncertain-SSH same-operation reconciliation,
CR04 existing UI and PG/final integration per plan. Rollback source checkpoint by
reviewed revert before activation; no data/service rollback needed for this turn.

## 2026-09-25 Task6 continuation / original controller deadline

User: next approved Task6 step, no expanded scope/redundant tests. BASE platform
72809ac / nativeffe51d4; original isolated branches retained. No production,
real rerun, main merge, push, installed policy, image/wheel build or activation.
Native source committed as d7bd741; plugin remains c0b266b. First native commit
failed because user identity was unset; command-local git -c used the existing
verified platform/history identity, without changing global Git configuration.

Changes: scripts/cce_recovery_deadline.py parses authenticated absolute deadline
and bounds poll sleeps; cce_paired_runtime validates before active-Master handoff
and passes the epoch via RecoveryCapability. Both Resume adapters pass the new
native keyword only when tagged, preserving the accepted Task5 manual ABI.
Native cce_batch_runtime._advance_recovery_view binds compute_deadline in its
existing journal and gates replacement entry/DELETE/CREATE/handoff, capping
handoff by the original budget. WGS/GATK Step3 loops no longer grant a fresh
budget after process restart. Focused new test file plus docs08/plan/state/task.

RED:11 tests exposed unconsumed deadline/absent helper, then11 GREEN6.33s.
Boundary/real-monitor checks18 GREEN12.91s. Active-Master entry2 RED showed the
deadline check must precede the reuse/handoff path (not just replacement).
Fixed that ordering;20 GREEN14.22s. Review retained old native call signature
for untagged manual Resume. Final exact selection22 passed16.25s:
task6.ps1 -Mode test -Test '/task/platform/scripts/tests/test_p02_compute_deadline.py
/task/platform/scripts/tests/test_p02_selected_monitor.py::test_direct_step3_replacement_and_observation'
-Log compute-deadline-final. These are scoped remote synthetic cases, no full
suite/local runtime tests. Duplicate final log name contains latest22 result.

Each remote run verified ssh BS10610 -> server10610; control/current still
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260912-opt-4d3d24e6;
backend36ff21f87356 RO/app from20260923-step7-ae416fa/backend/backend and RO/config
from current release, scanner/auto-dispatch false. UID6708 evidence confined to
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.
Cached imagea0112f0b, network none/read-only/nonroot/1CPU/1GiB. No service changes.

Deadline is controller/monitor budget: no Master/Worker kill or Job native
activeDeadlineSeconds change. Existing bounded query may return after deadline;
no subsequent recovery operation/poll receives a renewed budget. Timeout may
retain an existing intent/Job and must go to reconciliation, not auto-cleanup.
Tagged recovery requires the paired updated native source; old/default-off
manual paths remain compatible. Revert these two source commits together to
rollback development; no runtime rollback needed. Task5 artifacts/plugin remain
unchanged. Task6 OPEN: next implement max600s/original-deadline natural Worker
wait via existing Airflow persistent actions, not a gate-owned retry engine;
then exact remaining classes, Step4, UI, PG/final integration and authorized
live cloud gates. No repeated Task1–5 validation.

## 2026-09-25 Task6 continuation / frozen policy and sensor handoff

User: continue the approved P0 Task6, narrow scope and minimal tests. BASEf5c82e0
on jiucheng/runtime/CR01-cce-recovery-20260922; nativeffe51d4 and pluginc0b266b
unchanged. No production/real rerun/installation/build/main merge/push authorization
used. Original workspace and Task5 offline artifacts preserved.

Added cce_recovery_policy.py and cce_recovery_poll.py. New-run creation freezes
default-off per-adapter policy/budget; first monitor fixes the absolute deadline.
WGS duplicate registration carries that same deadline into its hash. Historical
missing policy or legacy manual next-attempt state is not backfilled; it cannot
receive automatic quota but does not block the manual registration path.
Existing internal stage POST authenticates actual DagRun/action and reuses the
due dispatcher. Existing Step3 sensors reschedule waiting/uncertain and skip old
chains after delegation, including lost-response replay when GET sees the new
monitor. Current exact monitor generation alone sets compute_terminal; preserve
queued authorization for downstream, but end the active compute fence. Second
failure uses the same two-slot journal. GATK cleanup forwards its action identity.

Changed scope: backend policy/poll/config, creation and registration services,
shared budget lifecycle and existing main routes; existing WGS/GATK DAG sensors;
focused tests and docs02/04/05/07/08/11 plus plan/state/task/handoff.
No DB migration/public endpoint/new DAG node/independent retry daemon.

RED: policy3 and poll4 initially missing modules; internal route2 and real sensor2
then exposed missing caller wiring. Second-failure2 reproduced completed-history
cleanup incorrectly blocked as pending. Fixed that shared fence. First monitor
hash replay, duplicate creation, actual GATK creation/registration, old manual
attempt compatibility and current/old cleanup identity covered by final selection.
BS10610 final backend19 passed4.70s (policy-poll-final.log), real-Airflow5
passed3.00s (policy-poll-dag-final.log). Commands: task6.ps1 -Mode test with new
policy/poll files, affected GATK confirm and two budget cases; -Mode dag with new
sensor file, WGS transport classifier and two GATK default-off sensor cases.
No redundant full suite. git diff --check passed. Preliminary RED/missing-path
discovery outputs are not acceptance; tests ran only remotely.

Fresh preflight each run: server10610; control
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/current ->
releases/20260912-opt-4d3d24e6; backend36ff21f87356 has RO/app from
20260923-step7-ae416fa/backend/backend and RO/config from current release;
scan/auto-dispatch false. Evidence/task files confined to uid6708-owned
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.
Offline cached containers, network none, read-only source, nonroot,1CPU/1GiB.
Master test image a0112f0b8ef003dd488c6c6ee2f13ca760c116d703e9ff7a83083e2857ce143e;
Airflow test image58195672af685cfa6551cfc44b37b6218bd2039c44b717163a6e8072f78dfd2b.
Existing kernel swap-limit warning does not remove the1GiB memory limit.

Ruling: only existing sensor rescheduling/control POST owns automatic waiting;
stage-status GET stays read-only. An old sensor must reconcile even when the
latest monitor looks running, or a lost response could advance the wrong chain.
compute_terminal is separate from dispatch result_status because downstream still
needs the same action's authority. No manual Resume call is nested into auto.

OPEN/NEXT: native consumption/enforcement of original cce_recovery_deadline,
bounded natural Worker wait, exact CREATE transport/storage classification,
Step4 uncertain operation reconciliation, CR04 projection, PG contention and
final automatic integration. No complete Task6/P0 or whole-plan review claim.
Both new env switches stay false; do not activate while these gates are open.
Rollback: revert this isolated platform checkpoint; no live service/data rollback
needed. No failed biological runs were restarted.

## 2026-09-25 Task6 continuation / internal due dispatch

Same user authorization and three isolated branches as the entry below. Completed
prerequisite commits: platform abdba43/native ffe51d4/plugin c0b266b. Preserved
Task5 artifacts, installed CLI/images and unrelated original workspace edits.

Added backend/app/cce_compute_dispatch.py and focused test. Reuses existing
cce_compute_recovery RunAction, budget validator, adapter-specific registration
and cce_resume_dispatch; shared stage authorization now recognizes that same
automatic action. No new table/public route/loop/manual action. Deadline field
is preserved in WGS/GATK recovery requests. Prepared identity commits before
request writes; replay rechecks current source proof and current action under
run/action locks. Missing/changed evidence, stopped state and expiry block first
dispatch. Once POST intent exists, reconcile by GET only even after expiry/stop;
late replies do not reset the user's state. Runtime live quiescence/owner guards
remain Task4's responsibility and are not replaced by a client-provided flag.

Tests: same BS10610 offline/non-root/read-only environment and exact fresh
fingerprint below. task6.ps1 test_cce_recovery_dispatch.py:12 RED (missing service)
then12 GREEN3.50s. Two prepared-crash cases RED (proof not rechecked), fixed by
reloading action under run lock and validating original failed receipt again.
Final explicit changed-boundary selection:23 passed4.68s, log dispatch-final.log
under p02-task6-20260925 (14 new +9 affected manual Resume cases). git diff --check
passed. No full unrelated suite, local runtime tests or production database.
The kernel swap-limit warning is unchanged; container memory limit remains1GiB.

Ruling: split durable preparation from external dispatch using the same action,
not a new scheduler or a nested manual Resume call (which correctly fences a
pending automatic action). Cost if interrupted between filesystem and database
writes: adapter mismatch remains fail-closed, never an invented new generation.

OPEN: automatic Airflow polling entry point, default-off new-attempt policy/
budget freeze, native original-deadline enforcement, terminal action lifecycle,
bounded natural Worker wait, exact CREATE transport/storage classes, Step4,
UI/PG/final integration. No task-wide/final reviewer claim. This checkpoint does
not activate recovery or complete Task6/P0. Next work stays within Task6; real
TTL/capacity/AOM/alerts, installation and production require separate gates.
Rollback: revert this platform source checkpoint; no live service/data rollback
needed. Native/plugin have no changes after their prerequisite commits.

## 2026-09-25 Task6 approved prerequisite / source acceptance

Authorization: user “补齐，然后继续” approves the prior bounded Master wrapper/
logger and schema2 bridge prerequisite. No repeat approval needed. BASE platform
da6626b/native770934c/pluginb6d1fb8; existing three isolated branches unchanged.

Completed: privacy-safe complete Master error accounting and real Snakemake
lifecycle validation; handoff-v2 preflight logger; optional native FINAL phase
summary binding; restricted current-Master native FINAL + retained/live Worker
reconciliation; immutable normal receipt evidence; schema2 backend reservation
with distinct platform/native identities. Later observer generations may retain
an older verified producer, not spend another budget or relabel its native hash.
Missing/unfinished/mixed evidence and active/unknown work stay ineligible. Normal
manual monitoring still reports failures even when automatic proof is unavailable.

Files: plugin failure_summary.py, logger __init__, two focused tests; native
run_cce_master_job.sh, cce_batch_runtime.py and two existing fixture/test files;
platform cce_recovery_failure.py, cce_paired_runtime.py, cce_recovery_inventory.py,
backend cce_recovery_evidence/service.py, source/monitor tests and state/runtime docs.
No public API, table, UI, biological rule or installed configuration changed.

Test environment only: ssh BS10610 -> server10610, uid6708/gid520. Each remote
runner rechecked control `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`,
current releases/20260912-opt-4d3d24e6, backend36ff21f87356 /app read-only at
20260923-step7-ae416fa/backend/backend and /config read-only at current/config;
WGS_INTAKE_SCAN_ENABLED=false, WGS_AUTO_DISPATCH_ENABLED=false. All preserved.
New owned evidence root (no /tmp):
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925`.
Offline non-root read-only cached Master container a0112f0b, network none,
one CPU/1GiB, own writable scratch; actual Snakemake9.24.0+biosan1. Existing
Task4 backend dependency cache read-only; temporary synthetic SQLite only.

Commands: ignored task6.ps1 uploads scoped source and runs `python -m pytest -q
-p no:cacheprovider --tb=short` on the explicit selected files/nodes recorded in
prerequisite-final.log. RED/GREEN: logger4 RED/1 existing pass ->5 GREEN; native
summary3 RED->3 GREEN; preflight logger2 RED; actual Snakemake control lifecycle1
RED (two redundant shutdown ERRORs) with submission/rule2 already GREEN;
source classifier6 RED->6 GREEN; schema2 receipt/reservation2 RED->2 GREEN;
older Step3 producer observer2 RED->2 GREEN; genuine fresh monitor2 RED->2 GREEN.
Final changed-boundary suite **28 passed35.59s**, including normal receipt2 and
three real Snakemake lifecycle cases. No full Task1–5 suite or local runtime tests.

Diagnostic failures (not acceptance): initial real lifecycle fixture hit read-only
cache and missing passwd UID; fixed only synthetic XDG_CACHE_HOME/USER/LOGNAME.
Probe initially imported old testdeps Snakemake, then corrected image site-packages
precedence; two probe syntax/import mistakes corrected without production effect.
An incorrect -k selected zero tests (exit5); replaced with exact nodes. Some local
rg wildcard/nonexistent path guesses were replaced with scoped file discovery.
No unresolved test failures. git diff --check is the local non-runtime check.

Ruling: use existing verified normal status receipts for schema2 evidence instead
of adding a backend cloud reader/service or flattening native IDs. The restricted
reader already owns authenticated source/lock mapping and cloud queries. This
keeps the original plan's single budget owner; failure cost is fail-closed/manual,
never automatic authorization from arbitrary receipt JSON.

Next: continue Task6 actual due dispatch through the shared Resume dispatcher,
frozen new-attempt policy/budget, bounded worker wait, Step4 uncertain dispatch,
existing UI projection and focused PG/final acceptance. This prerequisite is not
whole Task6/P0 completion. Exact CREATE transport/storage eligibility must be
checked against the existing producer contract; no new broad retry classes.
No merge/push, production, real rerun, CLI/image installation or live cloud
TTL/capacity/AOM/alerts acceptance. Task5 accepted artifacts remain immutable;
new source needs distinct version/pins/artifacts before activation. Rollback is
source revert only; no data/evidence cleanup and no services to roll back.

## 2026-09-24 Task6 preflight / failure-summary scope confirmation

Goal: continue the approved Task6 after Task5, without repeating accepted tests
or expanding operational scope. Inspected platform83528cf/native770934c/plugin
b6d1fb8 source. Only planning/state documents changed in this checkpoint.

Verified interface gaps:

1. `backend/app/cce_recovery_service.py:reserve_monitored_recovery` expects
   `{workdir, context, evidence_scope}` and equates the candidate context to the
   platform submit execution. Actual Task4 `cce_master_binding` is schema2 with
   `platform_execution`, `native`, `source_bundle`, `selected_bundle`.
   `scripts/cce_paired_runtime.py:_exported_master` and
   `scripts/cce_recovery_inventory.py:RecoveryCapability.export_result` are the
   actual producers. Native phase execution IDs/hashes/generations must remain
   distinct from platform submit and monitor identities.
2. `cce_recovery_reader.py` consumes `master-terminal.json`; the validator demands
   authoritative fatal_source and cumulative rule/other failure counts. Scoped
   source search found no current runtime producer of that terminal contract.
   Native `_bind_master_terminal` binds RUN_FAILED/RUN_COMPLETE to a final
   submission snapshot, sets evidence_complete=false and records stage/exit code;
   `_submission_final_snapshot` explicitly does not grant automatic recovery.
   `_recovery_phase_finished` captures context and exit code, not a cumulative
   classifier proving a whitelist failure is the sole fatal cause. Worker
   inventory completeness does not prove absence of mixed local rule/other errors.
3. The existing automatic service remains an internal reservation bridge, not a
   caller/dispatcher. Policy/budget freeze, due dispatch, Step4 reconciliation,
   UI projection and PostgreSQL contention remain pending as already planned.

Ruling: preserve fail-closed behavior. Do not manufacture a terminal seal,
infer zero failures from absent events, relabel native identity, or wire generic
manual Resume as automatic authorization. Cost: automatic dispatch remains off
until the producer/consumer contract is complete; manual Task4 acceptance stands.

Proposed necessary addition, awaiting user scope confirmation: in the existing
isolated Master wrapper/logger path, capture a complete bound fatal-cause summary
that distinguishes allowlisted executor faults from mixed rule/other failures;
consume it through the existing trusted reader/monitor/reservation path. No new
service/table, biological rule change or broader retry category. Missing/incomplete
or conflicting evidence stays ineligible. New source changes would require new
artifact pins; do not overwrite or reuse Task5 accepted artifact evidence.

Checks: git status/log and scoped rg/Get-Content inspection only. No pytest,
Docker/build, SSH or remote runtime commands executed in this checkpoint, hence
no fresh hostname/current/mount/permission validation or remote test claim.
Target for eventual minimal RED/GREEN verification remains BS10610 test only;
fresh environment gate first. No local runtime substitute. No services, production,
CLI/operator policy, frozen bundles, samples or recovery budgets changed.

Files: CURRENT_STATE.md, TASKS.md, HANDOFF.md and the existing P0-2 implementation
plan; ignored plan ledger records the same finding. No unresolved command/test
failure: PowerShell rg wildcard arguments were rejected locally and replaced by
directory searches with -g; no remote retry attempted. Next: obtain bounded
producer-scope confirmation, then add targeted real-producer/consumer tests before
implementation. Rollback is a docs-only revert; preserve all source/evidence.

## 2026-09-24 Task5 closed / Task6 next

Source commits platform074dc55/native7232f57/pluginfdf1520 on the existing three
isolated branches. Details, exact wheel hashes, local image IDs, commands/results,
scope review, failure records and rollback:
docs/releases/2026-09-24-p02-task5-offline-artifacts.md.
Task5 only: generators6 RED->GREEN, affected matrix15 GREEN, packaging1 RED->GREEN;
distinct offline wheels2 and Master images2 built, actual-wheel acceptance13 GREEN
14.57s and image smokes2 passed. Snakemake9.24.0+biosan1 unchanged in both images.
Retained original evidence and accepted bs7 bytes; no old bundle/template rewrite.
All service/current/mount and scan/dispatch gates unchanged. No production, real
Jobs/data/rerun, install, push/merge, new framework or Task6 implementation.
Final current requirement/scope review found no further Important Task5 defect;
full Task4/budget/callback tests deliberately not repeated. Author scope review
does not replace the eventual whole-plan review. Next Task6 automatic recovery,
still using existing reservations/budgets/receipts. Live TTL/AOM/alerts/capacity
are separately authorized operational gates, not claimed from synthetic tests.

## 2026-09-24 Task5 source checkpoint / offline artifacts next

Existing isolated baselines platformde3b5a5/nativebd41f87/plugin5b5d7ee.
New Worker/Master/evidence readers TTL100, no Pod TTL, frozen-bundle, deadline,
restart/resource, cleanup, Step7/maintenance changes. Native test0.8.5+p02.dev1;
Master Dockerfile now includes existing sibling guard, after packaging RED.

BS10610 server10610 current20260912-opt-4d3d24e6; backend36ff21f87356 /app
20260923-step7-ae416fa/backend/backend RO, /config20260912-opt-4d3d24e6/config RO;
intake/auto_dispatch=false, uid6708. Evidence WGS_test/cce-evidence/p02-task5-20260924.
Ignored task5.ps1 uses cached network-none/read-only containers and own scratch.
Generators6 RED then6 GREEN; affected matrix15 GREEN19.76s; packaging1 RED then
1 GREEN0.22s. No unaffected budget/callback/full suite or local runtime tests.
Slow read-only cache listing stopped by exact own-process match; targeted bs7
build directory supplied cached poetry-core1.9.1, read-only. No chmod/removal.
Both cached Master bases have Snakemake9.24.0+biosan1, verified without testdeps
metadata shadowing. Distinct wheels/images and provenance remain next.
No real Jobs, service/CLI/policy install, main/production merge/push, database,
automatic recovery or real rerun. Pre-deploy rollback source revert only.

## 2026-09-24 Task4 manual closure accepted / latest requirements checked

Goal and scope: inspect existing code, finish only P0-2 Task4, then compare with
the latest approved spec and Task4 plan. No Task5 TTL/artifact or Task6 automatic
work, no production deployment, real batches, database/data edits, new API/table
or second retry engine. Existing isolated platform branch
jiucheng/runtime/CR01-cce-recovery-20260922, baseline42edd35; Task4 basef93ba00.
Native counterpart bd41f87 on jiucheng/runtime/p02-master-handoff-20260923;
plugin5b5d7ee unchanged. Commit containing this entry is the platform closure.

Completed:
- cce_paired_runtime.py: initial registered submission and interrupted original
  handoff reconciliation; active reconnect, direct Step3 replacement and post-CAS
  crash replay; authenticated producer/archive selection; actual child-process
  Step4–6 command/receipt reconstruction and final directory release.
- cce_recovery_inventory.py + existing WGS/GATK Resume: separate immutable origin
  and selected source, preserve registered lineage and original producer identity;
  sealed ancestor Worker snapshots participate in complete live reconciliation.
- Existing runtime gates: selected initial/monitor/downstream routing and WGS
  actual reattach revalidation before receipt archival. Generic JSON cannot mint
  VerifiedMasterResult. GATK approved materialization target is unchanged.
- Native cce_batch_runtime.py: generation-local final manifest projection and
  shared-history digest; no shared manifest or original bundle rewrite.
- tests/test_p02_selected_monitor.py plus new test_p02_manual_flow.py and
  p02_dag_transport.py: existing authenticated API/service, actual DAG methods in
  a separate Airflow subprocess, restricted native source, normal receipts and
  downstream success. Same attempt/action/config/workdir; one lost-response POST;
  no prepare/upload rerun. This is synthetic transport, not live scheduling.
- CURRENT_STATE/TASKS/docs08/Task4 implementation plan/P0 progress consolidated;
  old checkpoint OPEN text is historical, not current unfinished work.

Final independent code review: no Critical, three Important findings (initial
interrupted handoff, retained old Workers at release, WGS reattach receipt fields).
Five behavioral cases RED; fixed with the existing journal/evidence contracts.
First fix run3 passed/1 skipped/2 failed: remaining failure was a synthetic test
label mismatch (display label overwrote native inventory identity), corrected in
fixture without relaxing production checks; retained-Worker2 then passed7.32s.
No repeated reviewer or broad test suite. Earlier recorded service/DAG/lock tests
are reused, not rerun. Requirement-by-requirement result is in Task4's plan table.

Environment checked before each remote action: ssh BS10610, hostname server10610;
control root /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS, current points to
releases/20260912-opt-4d3d24e6; backend36ff21f87356 /app mounted read-only from
releases/20260923-step7-ae416fa/backend/backend, /config read-only from
releases/20260912-opt-4d3d24e6/config. scan=false/auto_dispatch=false unchanged.
Cached containers --network none --read-only --cpus1 --memory1g; candidate/native/
plugin mounts read-only, only task synthetic scratch writable. No services changed.

Final commands (PowerShell runner under ignored
.superpowers/sdd/2026-09-23-p0-2-master-handoff-ttl-implementation/selected-test.ps1):
- -Log task4-selected-final: test_p02_selected_monitor.py **41 passed,1 skipped
  in76.91s**. Skip = GATK has no separate WGS reattach-worker entry; its own actual
  recovery path is tested. Includes real forked selected monitor/downstream.
- -Integration -Test scripts/tests/test_p02_manual_flow.py -Log task4-manual-final:
  **2 passed41.32s**, dependency-only AnyIO/Starlette deprecation warning.
- Local git diff --check only (non-runtime); no local pytest or compile substitute.

Evidence root /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/
p02-task4-20260924/: task4-selected-final.log, task4-manual-final.log,
review-boundaries-red.log, review-boundaries-green.log,
review-retained-workers-green.log. Earlier implementation RED/GREEN logs retained,
including replay-chain-{red,green}, reattach-chain-red and initial-resume-green4.
Initial manual fixture/environment failures were not acceptance: missing cached
dependencies/permissions, incomplete registry fixtures, global mock sleep and
missing normal gate receipt. Corrected only isolated runner/fixtures; no install.

Test provenance: native image a0112f0b8ef003dd488c6c6ee2f13ca760c116d703e9ff7a83083e2857ce143e,
integration Airflow58195672af685cfa6551cfc44b37b6218bd2039c44b717163a6e8072f78dfd2b.
Integration uses offline selected dependencies exported from cached backend
8491604ee01d9b3a84d74e7edf233a9d5dd20ddbf14f8a646c25c05f8729efed and native image;
export hashes/image IDs in downstream-scratch/backend-deps/{provenance,native-provenance}.json.
Airflow subprocess retains its SQLAlchemy1.4 environment; backend uses temporary
SQLite/SQLAlchemy2, no live PostgreSQL or credentials. No wheel/image built.

Not run / remaining gates: full suites (user explicitly asked minimal affected
tests), live scheduler/SSH/native cloud operations, PostgreSQL contention, actual
TTL/AOM/capacity/notifications (Tasks5/6 and separately authorized operational work).
Task4 is manual source accepted, NOT all P0, artifact release or production-ready.
No open Task4 Important/Critical finding; unknown/legacy evidence remains blocked
by design. Production five old failed batches are not migrated or restarted.

Next: Task5 existing TTL generators and pinned artifact acceptance, then Task6;
do not enable installed GATK resume capability or operator policy automatically.
Branches/worktrees retained, no merge/push. Native commit initially failed because
its repo lacked author config; retried with per-command identity matching existing
commits, no global configuration change. Before deployment rollback is paired
source revert only; preserve records, bindings and data. After future TTL activation,
never revert to a reader requiring already-reclaimed objects.

## 2026-09-24 Task4 selected Master -> actual Step3 monitor checkpoint

BS10610 SSH restored; hostname server10610. Each isolated run rechecked current
20260912-opt-4d3d24e6, backend36ff21f87356 /app20260923-step7-ae416fa/backend/backend
RO and /config20260912-opt-4d3d24e6 RO; scanner/auto dispatch false. Same offline
image a0112f0b8ef0, user6708:520, network none, source/producer RO, task scratch
only. No service, DB, real workload, credential, policy or production change.

Scope: finish the interrupted cross-process selected-monitor slice, not all
Task4. Native903e1af adds UID/Pod/generation/platform-bound Step3 evidence from
the selected view. Platform cce_paired_runtime.py reconstructs authority from
registered producer/current request, receipt digest, native journal/handoff and
current directory lock under writer serialization. Actual WGS/GATK gate loops
use it; rule bridge gets a copied selected bundle binding. wgs_resume routes
paired Step3 into that monitor instead of the Step2-only replacement factory.
Original bundle bytes remain unchanged; no extra CREATE/START on observation.

Remote tests (scripts/tests/test_p02_selected_monitor.py; genuine os.fork):
- Prior missing-entry2 RED. Resumed draft10 cases:2 failed/8 passed. Diagnostic
  isolated missing START_CONFIRMED because the test Pod omitted Ready=True;
  corrected the transport fixture, normal2 GREEN4.13s, no relaxed identity gate.
- Actual WGS/GATK gate entry2 RED (Step2-only factory); connected monitoring.
  Fixture used invalid display run label and caught its own stop sentinel as
  workflow failure; corrected those test boundaries, gate2 GREEN4.27s.
- Old ANALYSIS_COMPLETE wrongly yielded success; reclaimed failure was routed
  to success-only reader. New terminal matrix4 RED/2 GREEN, then6 GREEN11.96s.
  Native monitor ignores run-id-only completion absent a verified new terminal,
  uses sealed final failure after Job reclaim and refuses unproven completion.
- Final focused18 GREEN30.04s. Affected registered Step2 replay2 GREEN3.99s;
  legacy worker disconnect1 GREEN1.99s; unactivated entry2 GREEN0.26s. No broad
  suites or local runtime tests. Docker swap-limit warning only.

Evidence: /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/
p02-task4-20260924/{selected-monitor-final,selected-gates-red,selected-gates-green,
selected-terminal-red,selected-terminal-green,selected-registered-affected,
selected-disconnect-affected,selected-legacy-affected}.log.
Reusable scoped runner is in the ignored plan workspace selected-test.ps1.
Changed platform: cce_paired_runtime.py, wgs_runtime_gate.py, gatk_runtime_gate.py,
wgs_resume.py, new test_p02_selected_monitor.py and state/contract/plan docs.
Native changes only cce_batch_runtime.py. git diff --check passed.

Remaining Task4: direct Step3 replacement and initial-submit view selection,
selected Step4-6 execution across processes, final protected release and actual
authenticated service/DAG/native manual synthetic closure. Current monitor
requires its successful registered Step2 predecessor, otherwise fails closed.
GATK registry capability/policy not activated; no Tasks5/6 advancement. Rollback
is source revert only; there is no deployed service or data rollback to perform.

## 2026-09-24 Task4 fresh-process monitor — unverified working-tree draft

Goal: continue the existing Task4 cross-process selected-Master handoff, not TTL
or automatic activation. Last accepted platform caf87e4, native1c8fca7.
Changed scripts/cce_paired_runtime.py, added scripts/tests/test_p02_selected_monitor.py;
native p02-master-handoff-20260923/src/cce_pipeline/assets/cce_batch_runtime.py.
State/task/runtime docs and ignored progress ledger updated. All remain
uncommitted; no branch push, merge or production changes.

First BS10610 offline pytest test_p02_selected_monitor.py -k None --tb=short:
2 RED/8 deselected4.56s, missing monitor_registered. Genuine os.fork means only
registered JSON crosses the process boundary. Evidence: WGS_test/cce-evidence/
p02-task4-20260924/selected-monitor-red.log. Successful preflight: server10610,
current20260912-opt-4d3d24e6, backend36ff21f87356 /app20260923-step7-ae416fa/
backend/backend RO, /config20260912-opt-4d3d24e6 RO, scan/dispatch false.
Cached image a0112f0b8ef0, network none, user6708:520, source/producer RO and
task-specific synthetic scratch only. No runtime services changed.

Draft implementation: shared registered-request check; Step3 reads successful
Step2's registered producer, verifies raw WGS or canonical GATK receipt hash;
derives recovery journal/view rather than trusting a supplied path. Checks
journal context/platform identity, frozen hashes, native handoff and current
directory owner under writer serialization. Native Step3 optional selected-view
arguments fence Job UID/recovery context, Pod UID and startup/terminal identity,
and write only the selected mirror. No gate loop wired yet. Direct Step3 Resume,
missing-Job failure/success acceptance, downstream execution and final release
still require work; do not claim this draft is a complete consumer.

GREEN command attempted same isolated runner with this one test file (10 cases),
but SSH exit1: kex_exchange_identification read Connection reset by
172.17.61.18 port22, then UNKNOWN port65535. No preflight, source sync or test ran.
Diagnostic ssh -G BS10610 confirms host172.17.106.10/userchenjc/ProxyJumpBS;
ssh -o BatchMode=yes -o ConnectTimeout=15 BS hostname also exit1, same jump
handshake reset. No blind retries, local tests or BS96 substitution. The earlier
preflight above is not a current availability claim. git diff --check passed
both source worktrees (only CRLF warnings).

Next: after access returns, rerun only this focused file with both platform and
native runtime source synchronized; fix any real failures before actual gate
wiring, then cover the existing service/DAG path. Do not rerun accepted suites.
Rollback: only uncommitted task-owned draft hunks if necessary, preserving other
work; no data, frozen bundle, service or operator policy rollback is required.
Task4 remains OPEN. No Task5/6 advancement or production authority inferred.

## 2026-09-24 Task4 registered Step2 recovery — source checkpoint

Network restored. BS returned node005; BS10610 preflight returned server10610,
current20260912-opt-4d3d24e6, backend36ff21f87356 /app from
20260923-step7-ae416fa/backend/backend RO and /config20260912-opt-4d3d24e6 RO.
Scanner and automatic dispatch remain false. No service restart/config write.

Goal: connect registered request to the existing verified Resume capability.
Implemented in scripts/cce_paired_runtime.py, wgs_resume.py and
gatk_runtime_gate.py. Native cce_writer_guard.py validate now returns the
already-validated physical mapping (no new probe/activation mechanism).
The existing authenticated spool is the trust boundary; canonical hashes detect
changes, not authentication. Recheck request bytes before native actions/export.
Use the fixed pinned runtime and operator-approved per-run frozen registration;
do not synthesize a binding from batch name. Hold shared writer serialization,
all stage launch locks and other worker locks. The invoking restricted gate
already holds its own worker lock. Free/dead dispatcher alone does not prove
quiescence: existing state must have a matching terminal receipt. Match the old
native owner before takeover; blank new-owner binding and live replacement UID
are fenced. Missing/foreign/legacy-only lock cannot authorize this new path.
Repeated action goes through existing one-CREATE/START journal, not a new retry
engine. Original frozen files unchanged. Normal receipt carries verified result.

Validation, only BS10610 offline cached Docker image a0112f0b8ef0, network none,
read-only candidate/producer, synthetic scratch and fake Kubernetes transport:
- Initial draft6 failed/4 passed exposed GATK fixture import error as well as
  missing routing. Fixed test import path/alias, then actual entry2 RED2.87s.
- Factory/routing first10 GREEN10.76s. Real backend request review found GATK
  does not have WGS control_workdir: corrected fixture, reproduced1 RED1.90s,
  then limited that field check to WGS. No backend request schema change.
- Final pytest scripts/tests/test_p02_registered_recovery.py:14 GREEN13.78s,
  includes repeat, changed request, occupied/uncertain dispatcher, foreign or
  missing lock and absent operator registration for both pipelines.
- Existing test_unactivated_entries_preserve_old_bundle (2 cases) and
  test_wgs_resume_worker_retains_binding_when_monitor_disconnects:3 GREEN2.17s.
Evidence root /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/
p02-task4-20260924: registered-entry-red.log, registered-gatk-shape-red.log,
registered-recovery-green.log, registered-recovery-affected.log.
One green-run SSH command exited1 during jump handshake (Connection aborted),
before preflight/test. Direct BS hostname then succeeded; bounded retry ran the
test. No blind repeated launch or environment substitution.

Docs: CURRENT_STATE/TASKS/HANDOFF, docs08, Task4 plan and ignored SDD ledger.
No new public API/table; no BS96, DB, image/CLI upgrade, live workload, operator
policy installation, actual batch rerun, main/production merge or push.
Task4 OPEN: current slice is Step2 only; paired Step3 replacement explicitly
refuses until verified selected-view cross-process continuation is connected.
Still need native Step3-6 use of selected view, final protected lock release,
full authenticated service/DAG/native manual flow. Then Tasks5/6 in order.
Rollback: revert this isolated source checkpoint with its native guard return;
no deployed state or original project needs restoration. Do not enable policy
or GATK resume registry before the remaining Task4 gates pass.

## 2026-09-24 Task4 registered-entry continuation blocked before RED

Latest user-reported network restoration recheck: the same BS10610 test runner
still failed at SSH banner exchange (exit1); a single direct BS hostname probe
failed TCP connect172.17.61.18:22 (exit1). Read-only Find-NetRoute selects local
Ethernet192.168.1.144 via default gateway192.168.1.1. This locates the currently
unavailable hop, not a proven server/VPN root cause. Target health remains
unknown. No remote preflight or test ran, and no network settings were changed.

Goal: existing Task4 registered request -> verified capability -> own adapter
Resume; no extra feature, new retry mechanism, Task5/6 or production change.
Prepared WIP scripts/tests/test_p02_registered_recovery.py using existing native
adapter fixtures and real physical mapping/lock CAS, with external transport
substituted. This test draft is unverified; do not treat it as accepted coverage.
No production implementation file changed. Last accepted commit685c5b2.

Attempted command: existing gated BS10610 offline runner selecting
pytest -q -p no:cacheprovider scripts/tests/test_p02_registered_recovery.py.
Transport: ssh -o BatchMode=yes -o ConnectTimeout=15 BS10610 with the existing
base64 command/data transfer. Two attempts, both exit1 at banner exchange:
Connection timed out during banner exchange; Connection to UNKNOWN port65535
timed out. Neither reached remote preflight, sync, container or test execution.
Likely SSH transport/jump availability; no evidence of a test/code failure.
Local read-only ssh -G confirmed BS10610=172.17.106.10 via BS=172.17.61.18.
One diagnostic ssh -o BatchMode=yes -o ConnectTimeout=10 BS hostname also failed
before remote execution: connect to host172.17.61.18 port22: Connection timed
out (exit1). Thus the jump is currently unreachable; target health is unknown.
No alternate environment, credential, production host, mount or service change.

Changed only test draft and CURRENT_STATE/TASKS/HANDOFF plus ignored SDD ledger.
No source checkpoint committed while RED cannot run. Next: restore test SSH,
rerun this single draft selection, correct fixture issues if any, implement only
planned registered entry, then minimal affected checks. Do not reuse the earlier
receipt tests as proof of this new capability. Task4 remains OPEN.

## 2026-09-24 Task4 normal-receipt identity checkpoint

Goal: continue the existing Task4 route only; no new functionality, automatic
recovery, UI, public API, database table or production changes.

Completed: RecoveryCapability returns a JSON-compatible internal verified result
with an independent receipt snapshot. Both normal status writers preserve its
Master binding and submit execution ID; GATK signs them in its existing receipt
hash. Generic progress JSON cannot inject those fields. WGS Resume attaches the
result to the in-memory worker payload so terminal failure/success cannot drop
the binding. GATK return wrapping no longer discards the verified result type.
Package/standalone imports work through the same module convention. An older
successful Master's submit identity is not replaced by a new observer identity.

Changed source: scripts/cce_recovery_inventory.py, wgs_resume.py, gatk_resume.py,
wgs_runtime_gate.py, gatk_runtime_gate.py, tests/test_p02_resume_final.py.
Updated runtime contract, plan, current state, tasks and SDD ledger.

Validation: BS10610/server10610, existing control/current and actual RO app/config
mounts checked before each call; intake scan and auto dispatch remain false.
Offline read-only source containers, network none; no local runtime tests.
pytest test_p02_resume_final.py::test_verified_master_binding_survives_normal_stage_receipts:
two RED (missing field). First GREEN attempt exposed GATK result type lost in its
dict wrapper (one failure); repaired wrapper, two GREEN. Affected selection:
that pair + WGS disconnect worker + prior binding-export pair + existing WGS
status monotonicity/retry preservation = seven GREEN7.62s. Inspection then caught
observer vs submit identity distinction; refined it and reran only receipt pair,
two GREEN3.51s. git diff --check passed. No redundant whole-suite run.
Logs: /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task4-20260924/
normal-receipts-{red,green,affected,observer-green}.log.

Remaining/next: trusted per-run registration/capability factory, actual GATK
Resume routing, cross-process selected-view reconstruction and native Step3-6
entry, verified final lock release, full authenticated service/DAG/native mock.
This commit only closes the in-process normal-receipt seam, not all Task4.
Tasks5/6 remain unstarted. No capability policy installed or branch merged.
Rollback: revert this source checkpoint before activation; nothing deployed.

## 2026-09-24 Task4 cloud identity and actual entry selection checkpoint

Committed source: native7026528 and platformc3cf3c2. Post-checkpoint scope check
found activated Resume could still fall through to the legacy two-argument lock
when no RecoveryCapability was constructed. Both adapter entries now reject that
path before runtime effects; the operator loader tags its validated module only
internally (not a payload field). Two adapter cases RED, final12 paired cases +3
existing result-root cases GREEN0.99s, paired-resume-denied-{red,green}.log. This
is a fail-closed checkpoint, not a completed capability factory or full Task4.

Goal: implement the approved read-only cloud directory identity source and wire
paired runtime selection without changing frozen projects or production.
Native guard/source checkpoint: readonly PVC-only reader from existing generator,
bound PVC/PV/Job/Pod UIDs, cloud symlink resolution, persisted one-CREATE intent,
uncertain-response reconciliation and conditional cleanup. Replayed foreign UID
cannot be deleted; completed cleanup does not reuse stale directory evidence.
Factory rejects bad frozen registration before any probe. Cloud10 + writer13
GREEN2.23s; details and source commit in native HANDOFF/history.

Platform adds scripts/cce_paired_runtime.py and its focused tests; actual WGS/GATK
stage command builders and Resume loaders select the operator-pinned external
runtime, preserving --bundle. Fixed policy, source hashes and root ownership;
guard sibling is pinned before importing native code. No payload/env runtime
selector and no invalid-policy fallback. GATK's direct materialization now enters
the protected writer while retaining its original approved result-root validation.
Existing prepare/Step7/maintenance mechanisms stay outside this source change.

Validation: BS10610/server10610, current20260912-opt-4d3d24e6,
backend36ff21f87356 mounts backend20260923-step7-ae416fa and config20260912-opt;
both RO, scanner/auto dispatch false. Cached imagea0112f0b8ef0 offline readonly
candidate/producer/plugin/dependencies; only synthetic scratch RW. New loader7
RED missing module -> GREEN, unactivated compatibility2 GREEN, custom GATK guard
1 RED -> GREEN; final10 new +3 existing result-root cases GREEN0.82s. Evidence:
WGS_test/cce-evidence/p02-task4-20260924/paired-{loader,materialize,entry}-*.log.
Two individual SSH jump handshake failures had bounded successful retries.
No local runtime tests/full-suite reruns; no real cloud/DB/analysis/deployment.

Task4 OPEN: this is selection/entry fencing, not automatic registration or full
Resume capability construction. Normal selected-view receipts/backend binding,
final Step6 release and real service->DAG->native synthetic closure still pending.
GATK resume registry remains disabled. Tasks5/6 not started; no TTL/capacity claim.
Next continue those existing Task4 seams, not another storage choice. Rollback:
revert isolated source commits; no deployed release/policy or data to roll back.
Docs08/02/11 and plan/ledger updated; no API/schema change in this checkpoint.

## 2026-09-24 Task4 cloud-reader identity authorization

User agreed to reuse the existing cloud read-only reader for actual SFS directory
identity, with no new host mount. Continue isolated source + BS10610 offline
synthetic verification only. This supersedes the pending mapping-choice question,
not the production rollout gates. No real reader Job, production query, CLI/image
upgrade, frozen bundle edit or deployment is authorized by this confirmation.

## 2026-09-24 Task4 CLI compatibility authorization

Latest: protected stage actual arguments now bind to original bundle/contract/
config; wrong Step6 output root rejects before side effects. New targeted RED,
final13 writer cases GREEN0.51s, protected-target-{red,green}.log. Native source
has a follow-up commit after8ec5415; no production artifacts were built/installed.

Asked user for the one remaining mapping choice before actual gate activation:
reuse existing cloud read-only reader to obtain canonical SFS identity (preferred,
no new mount), or provide an existing actual SFS mount on CLI nodes. Current host
mapping code requires that mount; BS/NFS paths are NOT proof of cloud SFS access.
No mount, new cloud probe, operator policy or real production query was performed.
Execution-plan boundary: do not silently add storage infrastructure or treat a
local NFS path as cloud evidence. Task4 OPEN; Task5/6 must not start prematurely.

User confirmed extending isolated cce-pipeline CLI Step1–Step6 protected entries,
trusted storage mapping and paired CLI/platform version checks. Authorization is
source development and BS10610 synthetic validation only. No production CLI,
image, configuration, old frozen bundle, real Job or data changes are authorized.
Task4 remains open until actual restricted gates and normal receipts are wired.

Native checkpoint8ec5415 implements the protected-entry capability and fixed
operator-owned activation reader. Source checks pins/namespace, actual mounted
symlinks+root inode/filesystem identity, frozen bundle/config hashes; shared
journal flock and existing CAS enforce entry/early-release fences. Explicit old
binding required; missing proof fails closed. No policy or mount created. This
does not prove the production all-writer inventory or complete gate wiring.
BS10610 first jump handshake reset, bounded retry passed. New9 RED -> GREEN;
actual CLI bypass1 RED -> GREEN; programmatic sibling import1 RED -> GREEN.
Final new12 GREEN0.53s, affected35 GREEN5.78s, oldStep4/5 threeGREEN0.17s.
Evidence p02-task4-20260924/protected-*.log under WGS_test/cce-evidence. Runtime
imagea0112f0b8ef0 offline/RO source; existing swap-limit warning only. No full
suite rerun, no local tests or production activity. Pending exact normal platform
registration/entry, final release, selected-view receipts and manual closure.

## 2026-09-24 Task4 selected downstream and validated binding export

Native08c6cda adds optional selected-Master bundle/UID to Step4/5/log export.
Real native completion readers validate immutable inputs and selected UID even
when TTL removed the Job; conflicting active/foreign Job blocks. All result/log
paths stay under the ORIGINAL bundle, not the independently derived Master view.
Step6 path semantics/default CLI unchanged. Native tests: five RED, then10 focused
GREEN in5.09s. Scope/details in native HANDOFF; no new templates/TTL enabled.

Platform RecoveryCapability.export_result validates native handoff and exact
platform execution before returning cce_master_binding (schema_version2) and
cce_master_submit_execution_id. Native hash/generation/UIDs and platform hash/
generation are separate fields. WGS/GATK actual Resume functions call this writer.
Dry-run readiness and unbound historical results gain no fabricated binding.
This is NOT yet connected to backend reservation or the normal restricted gate;
the older draft automatic reader still expects a different terminal schema.

BS10610 preflight unchanged server10610/current20260912-opt-4d3d24e6/backend36ff21f87356,
scan/auto disabled. Cached imagea0112f0b8ef0 offline, sources/plugin/testdeps RO,
synthetic scratch only. Binding export2 behavioral RED, then6 affected GREEN
in7.11s (24 unrelated parameter cases deselected). Initial import collection error
used an incomplete fresh source root; corrected to existing p02-resume-20260923
source, not a runtime/code fix. Evidence in WGS_test/cce-evidence/p02-task4-20260924/
binding-export-{red,affected}.log and downstream-{red,affected}.log.

Remaining Task4 boundary: actual CLI Step1/2 still call old two-argument batch lock;
Step4–6 lack v2 entry protection. Trusted actual-storage alias mapping/all-writer
version enforcement plus selected-view/receipt forwarding are required, not a
boolean from an API request. Asked user to confirm extending those CLI protected
entry points in isolated source. Do NOT activate recovery/TTL or advance Task5/6
on the strength of helper tests alone. No production data/services touched.
Rollback source commits only; preserve all original bundles and evidence.

## 2026-09-24 Task4 GATK dispatcher fence

Continue remaining Tasks4→5→6 without production changes. Added launch and worker
flocks, durable launch intent/process identity, full receipt identity and late-write
guard in scripts/gatk_runtime_gate.py. Step1–6 only; no Prepare/Step7 rewrite.
Unknown launch outcome, dead parent without terminal evidence and identity-incomplete
legacy status fail closed. A completed generation permits a registered successor;
same-generation terminal receipts never execute again.

BS10610 fingerprint: server10610 uid6708; control current remains20260912-opt-4d3d24e6,
backend36ff21f87356 mounts20260923-step7-ae416fa/backend/backend read-only, scan/auto
dispatch false. Cached image8491604ee01d, network none/read-only, synthetic scratch.
New test_dispatcher cases first failed5; then15 focused checks passed in2.77s.
Evidence: WGS_test/cce-evidence/p02-task4-20260924/gatk-dispatcher-{red,affected}.log.
One intermediate fork test hung because its fake spawn inherited the launch FD;
fixed fixture to match real Popen(close_fds=True), after inspecting/stopping only
our test container ec2f88a8e757. No data removed; live service containers untouched.
Initial SSH preflight reset once; subsequent verified connection succeeded.

Files: gate, scripts/tests/test_gatk_dispatcher_fence.py, existing terminal fixture,
runtime contract and progress documents. No full suite/local tests/production calls.
Still open: trusted native binding writer, canonical storage/paired all-writer
activation and selected-view downstream before Task4 acceptance; then Tasks5/6.
Rollback by reverting source checkpoint only; no deployment to undo.

## 2026-09-24 Task4 authorized initial Master binding source checkpoint

User explicitly confirmed adding initial Master platform execution binding, without
old bundle edits or production CLI/image changes. Native isolated worktree provides
generation-one submission view and optional internal Step2 arguments; existing
native locking/START confirmation remains. Platform and native hashes/generations
are distinct. Startup and terminal evidence bind platform identity; a bound-source
replacement requires a fresh identity, and the existing action journal pins it.

Platform changes: cce_recovery_inventory.py capability plus wgs_resume.py and
gatk_resume.py forward the new identity; test_p02_resume_final.py covers both actual
adapters/native producer, lost CREATE and unchanged one-START replay. Runtime
contract, state/task/plan/ledger notes updated. No public interface or gate enabled.

Preflight BS10610 server10610 uid6708, current20260912-opt-4d3d24e6, backend36ff21f87356
RO app20260923-step7-ae416fa/backend/backend, scan/dispatch false. No live services,
database, CCE calls or production operations. Tests in --network none/read-only
cached8491604 backend and a0112f0b Master images, synthetic scratch only.
Native new10 RED missing function and Step2 case RED missing argument; final
affected native41 passed20.59s. Two setup issues (scratch/import path) corrected
before behavioral RED. Adapter new2 RED missing propagated identity, GREEN2 in3.40s.
Evidence approved WGS_test/cce-evidence/p02-master-handoff-20260923/submission-native-final.log
and p02-resume-20260923/resume-platform-green.log. No redundant full suites/local tests.

Remaining Task4: trusted writer/canonical storage and paired-all-writer proof,
dispatcher quiescence and selected-view normal downstream receipts. Do not claim
full Task4/TTL/automatic recovery acceptance. Rollback isolated source commits only;
frozen projects, successful outputs, histories and evidence remain protected.

## 2026-09-24 Task4 GATK own service/DAG/HTTP source checkpoint

Goal: sequential remaining Tasks4–6 with minimum affected tests. Same isolated
platform worktree/branch, base373da98. Producer32aa7fb and Worker5b5d7ee unchanged.

Implemented GATK own same-attempt Resume registration, exact canonical frozen
request validation, history and PipelineStageExecution generation. Extracted
existing durable RunAction dispatch/action authorization without changing WGS
execution guard. Existing operator/CSRF endpoint routes registered adapters.
GATK stage API requires actual DagRun/action/scope and rejects old registrations;
acquire rechecks after committed lease; finalize rechecks after evidence ingestion.
GATK DAG skips prepare/upload/completed stages. No registry capability enabled.

Files: cce_resume_dispatch.py, gatk_runtime_service.py, wgs_resume_service.py,
pipeline_registry.py/pipeline_registry_service.py, main.py, bio_gatk.py, two focused
GATK tests, API/DAG contracts, plan/CURRENT_STATE/TASKS/HANDOFF. No runtime producer,
frontend, normal workflow or frozen project files changed.

Remote preflight: BS10610 server10610 uid6708; current still20260912-opt-4d3d24e6;
backend36ff21f87356 /app RO20260923-step7-ae416fa/backend/backend, /config RO current.
WGS_INTAKE_SCAN_ENABLED=false and WGS_AUTO_DISPATCH_ENABLED=false. Used only isolated
offline read-only cached-image containers, synthetic in-memory SQLite, source RO,
scratch RW; no live DB/service or cloud access. Evidence under
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task4-20260924.

Tests: new service5 RED missing entry; DAG RED missing skip result, then GREEN.
Initial service GREEN found SQLAlchemy mutable JSON alias omitted conf; copy before
assignment fixed. pytest test_gatk_resume_stage.py test_wgs_resume_stage.py
test_gatk_runtime_service.py:39 passed in5.90s (gatk-dispatch-regression.log).
Actual HTTP adapter/scope test RED WGS-only gate, then GREEN (gatk-route-green.log);
the paired WGS HTTP check passed before GATK fixture-thread correction. New finalize
control race RED then GREEN (gatk-finalize-red/green.log). Real Airflow unittest
test_gatk_resume_stage:1 passed (gatk-dag-green.log). Setup-only failures (missing
registry fixture/SQLite thread pool and initial DAG mock return) were corrected;
not counted as behavioral RED. No full-suite repetition or local runtime tests.

Open/blocking decision: initial native Master lacks recovery_context whereas the
replacement view has one. Native handoff request_hash is a bundle/manifest digest,
not the platform stage request_hash. Asked user to allow necessary isolated
cce-pipeline initial-submission platform identity binding; not yet implemented.
Do not fabricate binding metadata from arbitrary receipts. Continue Task4 trusted
writer/canonical mapping, paired all-writer+old dispatcher proof and selected-view
normal downstream receipt after that confirmation. Task5/6 not started. Existing
historical batches without evidence remain manual; no rerun authorization implied.

Risk/rollback: source-only staged capability; revert this checkpoint if needed.
No deployment/push/main merge/image/CLI changes, no data cleanup. Task4 is not
complete and this does not authorize TTL or automatic recovery activation.

## 2026-09-24 Task4 checkpoint: authenticated WGS Resume/DagRun dispatch

Goal: continue approved P0-2 Task4, starting with actual WGS service/DAG dispatch
identity, not another recovery engine. Worktree cce-recovery-impl-20260922,
branch jiucheng/runtime/CR01-cce-recovery-20260922, base f93ba00. Producer32aa7fb
and Worker5b5d7ee unchanged. Original dirty worktree/frozen projects untouched.

Completed: RunAction not_started/post_intent/confirmed journal, commit before
POST; uncertain transmitted POST or legacy missing journal uses GET only even
after404. Exact DagRun ID AND conf confirmation. Fresh run/action lock checks;
late responses cannot erase running/stop state or current-DAG failure audit.
Recovery stage/acquire/finalize calls carry actual DagRun ID and require current
action/attempt/scope/control. Slot helper commits, so handler re-locks/rechecks
before projecting acquired; already committed lease remains on refusal. Finalize
may reuse successful Step6 and retains existing receipt validation. Auth/CSRF/
role checks tested through actual FastAPI middleware with synthetic session auth.

Changed: backend/app/wgs_resume_service.py, main.py; dags/bio_wgs.py; their two
test_wgs_resume_stage.py files; docs04/05/07, implementation plan and state docs.
No new public API, DB migration, runtime capability writer or activation flag.

Environment: fresh BS10610 server10610 uid6708. Control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS, current symlink remains
releases/20260912-opt-4d3d24e6. backend36ff21f87356 running; /app RO from
release20260923-step7-ae416fa/backend/backend, /config RO current/config;
scan=false/auto_dispatch=false. No service mounts/data/credentials used for tests.
Test sources/results only under
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task4-20260924.
HEAD tracked backend/config/dags archived, extracted to own source, changed files
overlaid byte-for-byte. Docker --rm --pull never --network none --read-only,
1CPU/1GiB, user6708, source RO and own scratch RW. No /tmp task writes.

Commands/results, all in that evidence root (counts overlap; no full suite):
- backend cached8491604ee01d: python -m pytest -q -p no:cacheprovider --tb=short
  backend/tests/test_wgs_resume_stage.py. Initial dispatch-red.log:16 failed,
  8 passed. Five failures reached missing catalog fixture rather than the
  expected rejection; do not count those as clean product RED evidence.
- dispatch-green-attempt1.log:19 passed,7 failed only because tests expected409
  instead of existing internal400. Corrected assertions, no API workaround.
- same file -k 'old_dag or stage_handler': stage-fence-green.log,7 passed,
  19 deselected. All original26 cases thereby passed across affected groups.
- Scoped review found newer DAG failure erased, post-commit acquire race,
  reused-Step6 finalization rejection. Added5 cases before fixes; same file
  -k 'reconciliation_preserves or slot_commit or finalize_reused':
  review-boundaries-red.log,5 failed/26 deselected, then implemented fixes.
- -k 'reconciliation_preserves or slot_commit or finalize_reused or
  same_attempt_action or lost_airflow_post': review-boundaries-green.log,
  7 passed/24 deselected in2.05s. Includes5 new plus2 affected existing cases.
- Real cached Airflow58195672af68: /usr/local/bin/python -m unittest -q
  test_wgs_resume_stage. Final dag-identity-green-deps.log:3 passed; same new
  method against baseline f93ba00: dag-identity-red-deps.log,1 expected failure
  (actual DagRun ID missing). Covers actual DAG registration and existing skip
  preparation/upload behavior. No Airflow service or metadata connection.
- Initial DAG commands failed import (not application RED): image PATH picks
  Snakemake venv; /usr/local/bin/python also needs explicit
  /home/airflow/.local/lib/python3.11/site-packages in PYTHONPATH under uid6708
  and isolated HOME=/scratch. Read-only image inspection confirmed dependency
  path. Corrected test environment only; failure logs retained.

SSH intermittently reset at jump172.17.61.18:22 (mkdir/scp exit1 before action);
one initial PowerShell quote error also did not execute source sync. Switched
to literal script/base64 JSON stdin for bounded sync+test; recovered. Kernel
swap-limit warning and existing anyio deprecation only. No local runtime tests,
full regression suite, actual PostgreSQL contention, service restart, production
access, real analysis, image build, CLI installation, automatic/TTL enablement,
main/production merge or push. Scoped reviewer rechecked3 fixes with no open
Important/Critical. git diff --check passed before documentation closure.

Task4 remains OPEN: GATK own authenticated service/DAG path; trusted native
binding writer/canonical mapping and all-writer/dispatcher exclusion; propagation
of selected recovery view into monitor/downstream receipts. Do not reuse mocked
proof callbacks as a production capability or advance Task5 TTL. Next continue
these integration items under the existing plan. PostgreSQL contention remains
later acceptance; SQLite checks are deterministic boundary tests, not lock proof.

Rollback: revert this source checkpoint only. No deployed release changed, no
data/history/evidence deleted. Existing running recovery DAG code omitting ID
would be rejected after future backend rollout; backend+DAG must be paired and
old dispatchers quiesced under Task4 activation gates, not deployed separately.

## 2026-09-24 Task3 source acceptance: existing Resume + native view/lock

Native handoff/Resume primitive committed32aa7fb on its isolated source branch;
use that source together with this platform checkpoint (not installed CLI).

Verified dependency commits: platform321b0a1, producerfa1ac44, Worker5b5d7ee.
Existing WGS/GATK Resume now consumes verified final inventory, trusted lock
capability, native generation view and original adapter journals. BS10610:
capability6 GREEN; initial composition10 RED; expanded composition29 GREEN;
5 affected legacy checks GREEN. Scoped review: no open Important/Critical.
SSH recovered; latest source synced and validated, see HANDOFF for evidence.
Task3 source complete; Task4 authenticated service/DAG/all-writer construction
and selected-view propagation remain next. No automatic/TTL activation, images,
CLI install, production changes, real reruns, main/production merge or push.

Files: scripts/cce_recovery_inventory.py, wgs_resume.py, gatk_resume.py;
tests/test_p02_final_inventory.py and new test_p02_resume_final.py; runtime
contract, implementation/progress plan and state/handoff docs. Producer changes:
cce_batch_runtime.py and test_recovery_view.py, native HANDOFF. Original dirty
worktree and frozen project bundles/config/history unchanged.

BS10610 handshake initially reset at jump172.17.61.18:22 (ssh/scp exit1, no
remote action); later hostname succeeded. Fresh preflight server10610 uid6708,
control current releases/20260912-opt-4d3d24e6, backend36ff21f87356 /app RO
release20260923-step7-ae416fa, /config RO current/config, both scan/dispatch false.
Latest selected source synchronized into existing isolated cce-evidence sources.
Pinned no-network/read-only cached Docker image a0112f0b8ef0, actual producer
and plugin source, synthetic temporary files only. No service or real-data mounts.

Evidence root /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-resume-20260923:
- recovery-capability-green.log:6 passed (earlier RED6).
- recovery-resume-final-red.log: initial10 failed before implementation.
- recovery-resume-composition-attempt1.log: expanded29 passed in28.30s.
- resume-final-affected-green.log:5 passed,47 deselected in0.66s.
No full-suite or repeated GREEN run. Review-found cases authored before fixes;
SSH outage prevented their separate RED execution, disclosed rather than claimed.
Final scoped reviewer found no open Important/Critical. Static diff check passed.

Coverage includes both adapters' failed/reclaimed Master, native success create0,
unknown404 no newCREATE, foreignUID, survivingPod, unknownWorker, partialpage,
missingterminal, lostCREATE replay exactlyoneCREATE/START, actual directory CAS,
frozenbytes unchanged, missing/regressed handoff, ambiguousComplete, GATK replay
maintenance. Started journal stays monotonic and cannot reconstruct confirmation.
No production/default CLI capability construction; authenticated callbacks,
all-writer exclusion and downstream selected-view routing belong to Task4.
Rollback: revert this isolated source commit only; no runtime rollback needed.
Next: Task4 under the existing plan; Task5 TTL and real five-batch reruns remain
gated and unauthorized by this development acceptance.

## 2026-09-24 Task3 native dependency acceptance; side-effect closure still open

User approved final Worker snapshot and independent replacement-generation view
in isolated cce-pipeline, only BS10610 synthetic. Platform branch base707533b,
producer branch base7926496, pinned Worker source5b5d7ee. Original dirty worktree
untouched. Query/confirmation/native-success guards connected to current Resume;
v2 failed/missing replacement still safely blocks until verified view/lock wiring.
New final submission content validator consumes actual plugin bytes, including
empty completed phases, exact terminals and candidates; full run-label + exact
Job/Pod probe rejects unknown/active/reclaimed-without-proof/partial inventories.
Native producer captures final phase snapshot, independent hash-checked view and
current-bound reader. No public API, DB, DAG, installation, image or service changes.

Fresh BS10610 preflight same as previous entry: server10610 uid6708, control
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS,current releases/20260912-opt-4d3d24e6;
backend36ff21f87356 /app RO releases/20260923-step7-ae416fa/backend/backend,
/config RO current/config, scanner=false,auto_dispatch=false; candidate writable.
Intermittent jump172.17.61.18 SSH handshake failures ran no remote commands;
bounded later retries succeeded. No BS96/production, DB or real reruns.

Evidence WGS_test/cce-evidence/p02-resume-20260923 under /mnt/biodevrwsg2/33.chenjiucheng.
Docker --rm --pull=never --network none --read-only --user6708:520 --cpus1 --memory1g,
source mounts RO, synthetic evidence/tmp RW, no secrets/live data. Cached image
8491604ee01d9b3a84d74e7edf233a9d5dd20ddbf14f8a646c25c05f8729efed for lightweight checks;
a0112f0b8ef003dd488c6c6ee2f13ca760c116d703e9ff7a83083e2857ce143e for actual plugin source
composition with existing pytest pure deps RO. CCE_PIPELINE_SOURCE=/producer,
CCE_PLUGIN_SOURCE=/plugin; PYTHONDONTWRITEBYTECODE=1; pytest -q -p no:cacheprovider.

Accepted targeted evidence (not full-suite):
- resume-confirmation-red/green:15 new; resume-native-success-red/green:9 new;
  resume-ambiguous-terminal-red/green:3 new. Combined affected run31 passed.
- resume-v2-replay-red:2 failed; resume-review-red:2 failed. Replay guards,
  GATK ownership-before-START and malformed RUN_FAILED presence fixed;
  resume-review-green:5 passed including1 affected positive.
- recovery-view-red/green:6 new.
- recovery-final-red-implementation:5 missing helper errors; final producer GREEN5
  after correcting fixture namespace. Initial fixture-only failures not acceptance.
- recovery-final-consumer-red:10 new failures; missing decode field found during
  first attempted green; recovery-final-consumer-shell-green:17 passed including
  original5 +reader/content10 +shipped shell2. Shell uses actual plugin manager,
  not a full real Snakemake CLI no-op acceptance. Cached source read establishes
  Executor initialization before no-op return (snakemake-noop-*-source.log).
- recovery-live-inventory-red/green:10 new.
- review empty candidate RED1, fixed presence-based validation; review-affected
  GREEN6 =1 new +5 affected (legacy inventory/control +native shell success/failure).
Focused same reviewer found only that Important for new dependency code; fixed.
Changed files: wgs_resume/gatk_resume and tests, cce_recovery_inventory/workloads,
new p02_resume_handoff/p02_final_inventory tests, current/task/runtime/plan/handoff docs.
No full suite/local runtime test, artifact build, real cluster or deployment.

Remaining Task3: verified internal canonical-storage/dispatcher/lock capability,
existing Resume next-view/submit/START journal integration and WGS/GATK matrix.
Task4 authenticated all-writer entry points remain separate; Task5 TTL disabled.
Do not turn process-only evidence or caller-provided JSON into launch authority.
Rollback isolated commits only; nothing deployed, no data rollback needed.

## 2026-09-23 Task3 Resume guard checkpoint; consumer closure still pending

Goal: continue P0 after Task2 without operating the five failed production runs.
Existing isolated branch jiucheng/runtime/CR01-cce-recovery-20260922, base bfff46c;
original dirty D:/pipeline/airflow-demo and both producer worktrees untouched.

Implemented in scripts/wgs_resume.py, scripts/gatk_resume.py and their existing
test files: WGS unknown CREATE outcome followed by404 never issues a second
CREATE; acknowledged replacement disappearance blocks instead of recreating;
recheck exact UID/resourceVersion and frozen manifest immediately before DELETE;
owner-only O_EXCL/O_NOFOLLOW journal, file+directory fsync, preserve prior fields;
bounded delete timeout. Both adapters request unchunked Master Pod lists and
reject incomplete pages/malformed lists. GATK archived Worker NOT_FOUND no
longer grants replacement permission; compatible persisted terminal consumption
is still required later. No new API, DB, DAG, service or producer source change.

Remote validation only. Initial ssh BS10610 full preflight exit1:
kex_exchange_identification reset at jump172.17.61.18; no remote command ran.
After local test authoring, hostname retry succeeded. Fresh full preflight:
server10610 uid6708, control /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS,
current releases/20260912-opt-4d3d24e6; backend36ff21f87356 image8491604ee01d,
actual /app releases/20260923-step7-ae416fa/backend/backend ro, /config current
config ro; scanner=false/auto_dispatch=false; candidate writable. Intermittent
later test/scp SSH invocations also failed at handshake before remote execution;
bounded retries succeeded. Required source sync succeeded before each test.
No repeated cloud side effects, production fallback or local tests.

Evidence /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-resume-20260923.
Archived HEAD scripts to new source directory then copied only this task's
modified files. Docker --rm --pull=never --network none --read-only --user
6708:520 --cpus1 --memory1g, source ro, evidence/tmp rw, no credentials or live
data mounts. Cached sha256:8491604ee01d9b3a84d74e7edf233a9d5dd20ddbf14f8a646c25c05f8729efed.
Command python -m pytest -q -p no:cacheprovider scripts/tests/test_wgs_resume.py
scripts/tests/test_gatk_resume.py -k 'lost_create or missing_started or
resource_version_change_during or paginated_empty or reclaimed_historical'
--tb=short: RED6 failed/1 passed, then GREEN7 passed/13 deselected0.70s.
Same two modules with negated selection:13 passed/7 deselected1.53s. Logs:
resume-guards-red.log, resume-guards-green.log, resume-guards-compat.log.
Focused reviewer found delayed-visible Failed replacement could reopen a
submitting journal. Added test RED1 then block before archival/delete. Regression
plus normal replacement/replay path GREEN2/19 deselected0.28s in
resume-delayed-red.log / resume-delayed-green.log. Total8 new +13 affected cases
accepted across these runs. Reviewer rechecked fix: no remaining important
findings for checkpoint, not Task3/production acceptance. Minor journal crash
fault injection not added; no such fault-injection acceptance claimed. Remaining
full inventory/hand-off/lock/adapter work deliberately remains open below.
No full suite or other accepted Task1/2 tests rerun. Local git diff --check only.

Remaining / next: Task3 not complete. Connect trusted START_CONFIRMED/native
terminal success, exact persisted terminals with complete submission/live
Job+Pod inventories, safe unknown-CREATE adoption, and canonical directory/legacy
lock callbacks. Task4 then covers authenticated WGS/GATK adapter/DAG/all-writer
closure. Keep frozen bundles intact. Task1 v2 writer intentionally rejects a
different Job UID in an existing handoff record: the recovery wrapper must
preserve old evidence and bind the next owner explicitly, not overwrite the
record or silently reuse old generation/digests. TTL/automatic gates stay off.

Separately recorded prior user question: Step7+local project deletion alone does
not implement platform same-batch recreation; existing project/batch dispatch and
snapshot uniqueness/reuse are still a blocker. Do not mutate DB/history or add
that lifecycle feature silently to Task3. User has not asked to execute deletion.

Risk: reclaimed Workers with no exact terminal evidence now explicitly block,
by design; no extra acceptance implied for current production. Rollback is source
revert of this checkpoint, not lock/evidence/data deletion. No push, merge main/
production, BS96 access, cloud writes, deployment or real analysis performed.

## 2026-09-23 Task2 source acceptance; five reruns are compatibility only

User corrected the previous detour: discuss how new locks support five frozen
reruns, do NOT rerun/inspect production now; continue approved P0 development.
This supersedes the prior checkpoint's request for an operational choice.
No BS96, DB, cloud Job/lock, frozen project, main/production or service mutation.

Source commits (local isolated branches, not pushed):
- Plugin5b5d7ee631cb45bf4e14877e483ec24adedd6de4,
  jiucheng/runtime/p02-worker-terminal-20260923 at canonical plugin/.worktrees/
  p02-worker-terminal-20260923. Distinct successor0.6.4+bs8.dev1, no built artifact.
- cce-pipeline7926496ea80dab9371885215bdaca81b8ccaddc2,
  jiucheng/runtime/p02-master-handoff-20260923 in its existing isolated worktree.

Worker: journal-derived exact UID/context terminal publication before callbacks;
explicit Job conditions only, unknown404 preserved; exact replay skips status
queries. Single validated journal view per poll. Cached callbacks precede quota
reads; claims remain for existing conservative reconciliation, not fake release.
Lock: optional internal extension of existing helpers, directory/logical identity,
generation/action/Master owner, journal intent before UID/RV CAS, response-loss
reconciliation, pending UID bind, conditional RELEASED record, stale-generation
fence, positively mapped legacy-key snapshot/guard before directory acquisition.
Frozen/v1 callers remain unchanged; no consumer currently opts into new locks.

Compatibility answer: keep old analysis_id/attempt/config/workdir/history and
success outputs. Future upgraded recovery entry verifies old mapping and full
quiescence then performs audited conditional handoff, not lock deletion/prepare.
Unknown mapping stops for verification. All writers for the directory must
upgrade together, including downstream stages; a legacy guard is not enough
against an old CLI using a different batch key. Actual canonical storage alias
validation, evidence verifier, existing durable journal callbacks and compatible
frozen-runtime wrappers remain Tasks3/4. No operational eligibility of any of
the five runs was determined this turn; no recent production snapshot relied on.

Preflight ssh BS10610 confirmed server10610 uid6708/gid520, control
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS current
releases/20260912-opt-4d3d24e6, backend36ff21f87356 image8491604ee01d,
actual /app releases/20260923-step7-ae416fa/backend/backend ro; /config
current/config ro; scanner=false/auto_dispatch=false. Candidate and evidence
writable. No services changed, current/rollback release untouched.

Remote synthetic tests only, task source mounted ro, evidence rw, user6708:520,
--pull=never --network none --read-only --cpus1 --memory1g, no /tmp evidence:
- Plugin evidence /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/
  smk-k8s-group/p02-worker-terminal-20260923; cached imagea0112f0b8ef0,
  Python3.11 and existing pytest deps ro. `pytest -q -p no:cacheprovider
  tests/test_worker_terminal.py --tb=short`:15 passed2.20s worker-final-green.log.
  `tests/test_heavy_io_quota.py tests/test_heavy_submission_recovery.py -k
  'real_status_coroutine or container_exit_before_job_terminal or completed_p0_worker_preserves or repeated_adoption'`:
  5 passed/25 deselected1.09s worker-compat-green.log.
- Runtime evidence same WGS_test/cce-evidence/p02-master-handoff-20260923,
  cached backend image8491604ee01d. `pytest -q -p no:cacheprovider
  tests/test_directory_lock.py --tb=short`:17 passed0.29s lock-final-green.log.
  `tests/test_batch_runtime_boundaries.py -k 'batch_lock or release_lock_requires_matching'`:
  3 passed/38 deselected0.14s lock-compat-green.log.
Initial13 Worker and13 lock RED; review regressions1 Worker +2 lock RED then
GREEN. Initial namespace error was an incomplete synthetic API object, fixed
fixture without relaxing real identity. SSH/scp twice failed handshake exit1 at
jump172.17.61.18 before remote execution; after local work bounded retry succeeded,
source synced before GREEN. No local test fallback. One focused read-only reviewer
confirmed corrected cached quota callback, uncertain-write journal retention and
retired-generation fence; no remaining important findings in this bounded scope.

Changed Airflow docs only: CURRENT_STATE, TASKS, HANDOFF, docs08, docs46,
P0-2 implementation plan and existing progress ledger. No API/DB/DAG change.
Not run: full suites, minikube/live CCE, build/install, real batch reruns. These
are outside source-level Task2; artifact/TTL acceptance remains Task5. State and
runtime documents updated with source IDs and remaining activation gates.
Next Task3 trusted runtime Resume/inventory/legacy mapping, then Task4 all manual
adapter paths. Task2 SOURCE PRIMITIVES complete, not P0/production-ready rerun.
Rollback: revert isolated commits only; no service rollback or data restore.

## 2026-09-23 Task2 RED checkpoint; five legacy failed-run question

User requested next step. Read current plan/spec/runtime and canonical plugin
AGENTS/skill; isolated source edits, synthetic BS10610 only. Fresh preflight:
server10610 uid6708, current releases/20260912-opt-4d3d24e6, backend36ff21f87356
image8491604ee01d and /app releases/20260923-step7-ae416fa/backend/backend ro;
/config current/config ro; scanner=false and auto_dispatch=false. Candidate
writable. No services changed; no production/cloud/DB/real-data action.

Remote plugin worktree snakemake-kubernetes-bs6-heavy-p0-20260923 is clean
25297f971dd463176d5fdc07908a60095ade50ea, branch bs7-control-reconnect.
Read source HANDOFF (no AGENTS there); exported exact HEAD bundle, fetched into
canonical D:/pipeline/snakemake-executor-plugin-kubernetes without checkout changes,
then created its .worktrees/p02-worker-terminal-20260923 on independent
jiucheng/runtime/p02-worker-terminal-20260923. Native worktree tool cannot target
the other repository, so Git fallback used after ignored-directory check.
Original canonical detached8a6187d and other worktrees remain untouched.

New tests/test_worker_terminal.py only,13 tests exercising real submission journal
and status coroutine with synthetic Kubernetes transport. BS10610 command:
python -m pytest -q -p no:cacheprovider tests/test_worker_terminal.py --tb=short,
inside cached Master a0112f0b8ef003dd488c6c6ee2f13ca760c116d703e9ff7a83083e2857ce143e,
--rm --pull=never --network none --read-only --user6708:520 --cpus1 --memory1g,
read-only source and existing pytest deps mounts, TMPDIR task evidence.
Result13 expected behavioral failures2.53s (worker-red.log); missing durable
terminal before callbacks, false success without final Job condition,404 failure
instead of unknown, no restart reuse/identity/conflict/write-failure safeguards.
No implementation or GREEN yet; do not mark Worker half or Task2 complete.
Evidence /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/smk-k8s-group/p02-worker-terminal-20260923.
No full suite, wheel/image build/install or live CCE tests (plan forbids them now).

Asked user: enable new directory/generation-aware locks only with CLI/platform
co-upgrade and keep unknown legacy locks, versus retain legacy same-name mutex.
User replied with five failed runs requiring rerun, not a choice or authorization
to modify them. Read original workspace HANDOFF/OPS_P0_1_PREFLIGHT_20260923.md
and OPS_RECOVERY_AUDIT_20260923.md without editing their dirty files. Thread
read tool returned empty items, so it supplied no current operational facts.
Latest documented snapshot12:04UTC: WGS0921D Master Complete, four others absent;
B/E journal/handoff mismatch; C/WES no current final evidence; native manifests
empty. This is historical, not this turn's live cloud state or rerun approval.
Advice: prioritize D final-result/downstream reconciliation, then resolve exact
legacy identity/Worker evidence for B/E/C/WES; keep attempts/inputs/successful
stages, no forceall/frozen-bundle rewriting/fabricated evidence. New lock rollout
must not be a prerequisite or silent migration of these historical tasks.

Next: answer user's legacy-run question and obtain the needed operational/lock
choice; continue from the13 RED tests, do not redo Task1/bs7 suites. Runtime
lock source unchanged. Rollback draft: remove only own test through normal Git
editing if abandoned; no live rollback needed. No main/production merge or push.

## 2026-09-23 P0-2 Task1 Master producer completed, source only

Goal: user said complete Task1 first and briefly explain completion/method.
Used existing implementation plan, runtime/planning, TDD, focused code review,
verification and handoff skills. No automatic-policy/Task2 scope expansion.

Producer: cce-pipeline c33740dea3a94e8ee3633592aba1b111948171b3, base83e7adbff9e94b99da34f687903cb4ee9df9f996,
branch jiucheng/runtime/p02-master-handoff-20260923,
worktree D:/pipeline/cce-pipeline-worktrees/p02-master-handoff-20260923.
Remote original source was verified tracked-clean; its two untracked audit
files preserved, independent branch created and operations owner informed.
Changes: existing runtime handoff/reader; master manifest identities; Master
entrypoint confirmation/terminal trap/process claim; Dockerfile helper copy;
targeted tests, two downward-env fixture assertions and producer contract doc.
Airflow changes this turn are six documentation files only: STATE/TASKS/HANDOFF,
docs08, existing P0 progress ledger and P0-2 implementation plan. No API/DB/DAG.

Handoff schema2 binds frozen run/attempt/generation, exact Job/Pod UID and
request/config/metadata/manifest digests. START_SENT persists before send;
Master verifies inputs and confirms before Snakemake. No ack means structured
handoff_timeout, not rule failure or permission to restart. Lost-response replay
does not resend; original timely ack is usable after controller restart/deadline.
Completed Pod reads use existing persistent reader. Same-Pod O_EXCL claim runs
before setup/failure trap. Native success checks preserved; trusted catchable
setup/analysis failures recorded, pre-trust/hard-kill cases remain unknown.
Terminal process evidence_complete=false; it is not a Worker-finality seal.

Environment: ssh BS10610, hostname server10610, uid6708/gid520. Control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS; current release
releases/20260912-opt-4d3d24e6. Actual backend36ff21f87356 /app read-only mount
releases/20260923-step7-ae416fa/backend/backend; /config current/config read-only.
Scanner=false, auto_dispatch=false. Task candidate and evidence writable.
No services changed; no release switch, rollback release change or DB access.
Cached image sha256:8491604ee01d9b3a84d74e7edf233a9d5dd20ddbf14f8a646c25c05f8729efed
ran isolated --network=none --read-only, uid6708:520, source/candidate read-only,
task tmp as /evidence with TMPDIR there,1CPU/1GiB, no image pull.

Evidence root /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-master-handoff-20260923.
Final commands/results (full invocation also in producer HANDOFF):
- pytest -q -p no:cacheprovider tests/test_master_handoff.py --tb=short:
  24 passed16.76s, task1-final-green.log.
- Targeted test_batch_runtime_boundaries, test_analysis_complete_contract and
  test_prepare_bundle schema3 case, -k step2/handoff/wait_pod/AnalysisComplete/
  schema_three/reader_job/pod_evidence/mirror/evidence_is_persisted:
  18 passed32 deselected0.92s, task1-compat-final-green.log.
Behavioral RED captured before each narrow implementation; fixture CRLF issue
corrected before counting Master behavior RED. Focused review's3 findings got
RED/GREEN: expired control restart, terminal-Pod reader and atomic process claim.
Later intermittent scp/SSH attempts failed exit1 at jump172.17.61.18 handshake
(reset/aborted), no remote execution; after static/doc work bounded attempts
succeeded, final exact sources recopied and tested. No local-test substitution.

Not run: full suites, image/wheel build/install, real Kubernetes or biology,
shared test service deployment, production. These remain future compatibility/
artifact/authorized operational gates, not required Task1 source tests.
Next planned Task2 verifies plugin25297f9 ownership, implements Worker terminal
and logical-run lock handoff. Tasks3–4 adapters/manual recovery, Task5 artifacts/
TTL and Task6 automatic remainder stay open. Old bundles untouched, TTL unchanged.
Risks: source requires paired controller/new Master image before promotion;
unknown CREATE/missing Job still fail closed. Rollback isolated commits only;
no live resources/data need rollback. Both branches committed locally, no push.

## 2026-09-23 P0-2 plan and lock-contract integration; blocked before code

Goal: user requested development steps and execution of latest P0 changes.
Used writing-plans/executing-plans and runtime/planning/handoff skills. Existing
CR01 worktree at e921e3a retained; original dirty operations worktree untouched.
Integrated design revisions a1af96a/729564c/781877e selectively, preserving this
branch's existing quota/RPC coverage. Added docs46 TTL companion and P0-2 plan;
updated original spec, STATE/TASKS and existing progress ledger (seven docs).
Plan explicitly requires producer-first manual closure, P0-2E conditional lock
handoff and compatible consumers before TTL; automatic P0 remains subsequent.

Target test only, ssh BS10610. Both bounded read-only preflights failed exit1:
first Python stdin preflight and later `ssh -o BatchMode=yes -o
ConnectionAttempts=1 -o ConnectTimeout=10 BS10610 hostname` returned
`kex_exchange_identification: read: Connection reset`, jump172.17.61.18:22.
No remote command executed; no fresh hostname/current/mount/permission evidence.
Do not reuse earlier successful fingerprints as this turn's verification.
Operations task supplied prior runtime path
/mnt/biodevrwbi/33.chenjiucheng/project/worktrees/huawei-cloud-runtime-master-errors-20260923,
HEAD83e7adb with uncommitted prototype, and plugin25297f9 path. These snapshots
are not current ownership/provenance acceptance. Preserve all existing work.

No product code or new tests written/run. Task1 targeted runtime tests and all
later implementation checks NOT RUN: remote gate unavailable and producer
baseline unverified. No local runtime fallback, production connection, real data,
cloud resource mutation, service change, image install or policy activation.
Planning/static document checks do not establish functional acceptance.
Static checks: `git diff --check` passed; relative Markdown links in the new
plan, updated spec and docs46 resolved; changed-path review contains only the
seven intended Markdown documents. No implementation acceptance claimed.
Next: restore BS10610 access, inspect exact source status/remotes/HANDOFF and
prototype ownership, pin source, run Task1 RED then implement in that scope.
Risk: short TTL before evidence/lock consumers would destroy recovery inputs;
do not activate it. Rollback: revert this documentation commit only; no runtime
rollback/data recovery required. Independent branch commit only, no shared push.

## 2026-09-23 next step: current-attempt stage receipt projection

Goal: continue existing CR-03 observer/receipt fences fromfdef310. Used backend,
runtime, executing-plans/TDD/verification and handoff skills. No scope expansion,
local runtime testing, deployment, shared service/DB access or production action.
Changed backend/app/{wgs_observer,gatk_runtime_service}.py and new
backend/tests/test_cce_recovery_receipt_projection.py. Updated STATE/TASKS,
runtime contract and existing P0 ledger. API/DB schema unchanged.

Both stage-status paths now hold refreshed AnalysisRun lock through validation
and projection, refresh execution state and reject old attempt/generation.
GATK obtains lock after its separate evidence sessions to avoid nesting those
sessions under this new lock. Existing current terminal transitions preserved.
Scope is receipt projection only: rule/workload/transfer paths, trusted terminal
writers, binding/dispatch/adapters, Step4 and real concurrency remain pending.

Fresh test preflight: ssh BS10610 ->server10610 uid6708; control
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS; current20260912-opt-4d3d24e6;
backend36ff21f87356 image8491604ee01d; actual /app readonly
releases/20260923-step7-ae416fa/backend/backend and /config readonlycurrent/config.
scan=false/auto_dispatch=false; own candidate writable, no permission changes.
C=control/candidates/p0-airflow-recovery-20260922. Only exact changed source/test
files copied. Tests run cached backend image network-none/read-only1CPU1GiB
with64MiB tmpfs and C/backend plus stage YAML readonly. All services preserved.

Commands/results (python -m pytest -q -p no:cacheprovider ... --tb=short):
- backend/tests/test_cce_recovery_receipt_projection.py: first fixture attempt
  failed setup because required synthetic workdir was omitted; fixed fixture.
  Behavioral RED4 failed/4 passed0.70s; C/receipt-projection-red.log.
  GREEN8 passed0.79s; C/receipt-projection-green.log.
- backend/tests/test_gatk_runtime_service.py plus
  test_wgs_observer.py::test_step3_terminal_execution_freezes_dry_run_master_identity
  and ::test_step3_retry_generation_replaces_prior_failed_projection:
  GREEN5 passed0.73s; C/receipt-projection-compat.log.
- git diff --check passed. Only expected kernel swap-limit warning.

No full suite (user requests targeted tests); no PostgreSQL concurrency test or
end-to-end recovery claimed. This does not enable recovery or complete P0.
Next: existing trusted runtime terminal/binding and automatic dispatch/adapter
integration; retain remaining evidence-projection/Step4 checks. Independent
CR01 branch only, no push/main/production merge. Rollback is source revert;
no runtime rollback, data restore or service restart needed.

## 2026-09-23 next step completed: control inventory + bs7 actual fixtures

User requested next step; resumed26d62dd and the10 drafted inventory cases,
no scope expansion. Used runtime, executing-plans/TDD/verification and handoff
skills. Original ops workspace untouched. No local runtime tests or production
commands. Existing independent CR01 branch retained; no merge/push/deployment.

Changed scripts/cce_recovery_inventory.py and its test: recognize agreed control
candidate separately; all referenced Workers must already be CREATED/ADOPTED
under bound context, UID from journal matches complete schema2 manifest. A null
control UID retains the known journal UID; foreign UID or missing Worker cannot
be inferred away. Reject any mixed FAILED submission and unresolved inventory.
No fake INTENT/FAILED entries or control-based release. Count cumulative control
faults as executor_failure_count. Inventory remains snapshot-only, not finality.
Added backend/tests/test_cce_recovery_bs7_contract.py with immutable hashes for
four real-wheel-generated fixture scopes; terminal positives synthetic only.
Updated runtime contract, STATE/TASKS and P0 ledger; design scope unchanged.

Fresh preflight ssh BS10610: server10610 uid6708; control
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS, current20260912-opt-4d3d24e6;
backend36ff21f87356 image8491604ee01d, /app readonly20260923-step7-ae416fa/backend/backend,
/config readonlycurrent/config. scan=false/dispatch=false. Own C writable,
C=control-root/candidates/p0-airflow-recovery-20260922; no permissions changed.
Only exact source/tests copied to C; isolated cached containers network-none,
readonly root/mounts,1CPU/1GiB, tmpfs. Shared services/data unchanged.

Test commands use cached backend image python -m pytest -q -p no:cacheprovider,
PYTHONPATH=/candidate/backend:/candidate, C/backend and C/scripts readonly:
- scripts/tests/test_cce_recovery_inventory.py -k control_candidate --maxfail=1
  --tb=short: RED1 failed/26 deselected0.05s, unsupported schema as expected;
  C/control-inventory-red.log.
- Same file -k 'not actual_bs5' --tb=short: GREEN34 passed/2 deselected0.05s;
  C/control-inventory-green.log. Covers10 new plus24 affected existing cases.
- backend/tests/test_cce_recovery_bs7_contract.py --tb=short with bs7 wheel and
  fixture root readonly mounted: GREEN4 passed0.08s, no skips;
  C/bs7-contract-green.log. No redundant plugin full suite or DB tests.
- git diff --check passed. Expected container kernel swap warning only.

Plugin owner requested help executing its already-reviewed guarded finish/build
because its SSH handshake failed while ours worked. Read local finish-candidate.sh
and remote build-candidate.sh completely; executed once after hostname/uid/base/
branch/dirty whitelist guards. No source edits by this task in plugin repo.
Finish source: D:/pipeline/task-artifacts/plugin-bs7-control-reconnect-20260923/finish-candidate.sh.
Remote worktree: /mnt/biodevrwbi/33.chenjiucheng/project/worktrees/snakemake-kubernetes-bs6-heavy-p0-20260923.
New commit25297f971dd463176d5fdc07908a60095ade50ea (11files); clean
jiucheng/plugin-bs7-control-reconnect-20260923. bs6 ref remains
0b19bb605cdff619a7f09b34a6fe774e4b43d357. Owner owns final producer handoff.
Build ran offline with fixed cached image;52 affected actual-wheel tests passed
5.60s (test_control_recovery.py,test_heavy_io_quota.py,test_heavy_submission_recovery.py).
No runtime install, image replacement, registry push, live cluster or bs6 overwrite.

E=/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/plugin-bs7-control-reconnect-20260923.
Artifact E/build-25297f971dd463176d5fdc07908a60095ade50ea/wheel/snakemake_executor_plugin_kubernetes-0.6.4+bs7-py3-none-any.whl
SHA256=2ad4aa737e6f34930b6832e3ce69edd9ee64867cc9c7ce0c1bcb4c455cdbae86.
Fixtures E/consumer-fixtures-v1: wgs-get-lease,wgs-list-pod,gatk-get-lease,gatk-list-pod;
20 fixture files checksum OK. SHA256SUMS hash
de1b3ab20d888f9660c38b8dce037333ce3ce3b0b81b66fbf79563832b780296;
fixture-provenance.json hash74102da1e10cab3728bed6f1caf31eb4bf1a0d08ed42c6002b01d1048041f83f.
E/build.log, build-<commit>/wheel-tests.log and consumer-fixtures-generation.log
retain provenance. CREATE/ADOPT fixtures use real plugin paths with synthetic
external API, no clinical data. No terminal seal generated.

Remaining: D RPC500 source-call confirmation, structured query failure (generic
kubectl still unknown), complete trusted terminal closure, binding/dispatch,
observer generation, Step4 and PostgreSQL/end-to-end acceptance. No new audit
track or weakened proof. Automatic recovery stays disabled; P0 NOT complete.
Rollback: revert this source slice; no service/data rollback needed. Plugin
artifact is isolated and uninstalled; keep bs6 unchanged. Next task resumes the
existing P0 integration from these pinned contracts, not another fixture rebuild.

## 2026-09-23 next control-inventory slice: remote preflight/transfer blocked

Completed first slice is commit26d62dd. Continued existing P0 control-inventory
integration while owner builds bs7; added10 synthetic cases to
scripts/tests/test_cce_recovery_inventory.py (known/null candidate UID retains
admitted journal UID; foreign/missing/unresolved/mixed inventory and broad/write
query rejection). This next slice has NOT run RED/GREEN and no inventory product
code changed. Test draft retained in worktree, not counted as accepted.

SCP of this single test to the same isolated BS10610 C/scripts/tests failed at
jump172.17.61.18:22: kex_exchange_identification/banner Connection aborted,
exit1. The following already-composed isolated RED command also failed before
remote execution at the same handshake, exit1; no pytest result or new remote
log. Stopped further attempts, no local/BS96 substitute or SSH config edits.
No evidence that source was copied or remote environment changed. Resume with
fresh BS10610 preflight, copy test then observe RED before inventory implementation.
Plugin owner reports108 source tests passed (86baseline+22new), but actual bs7
wheel/fixture handoff remains pending and those results are not our acceptance.
No change to26d62dd verified claims, no production/service actions or deployment.

## 2026-09-23 current disconnect types: first bounded implementation slice

User requested adding today's WGS B/C/D/E and WES disconnect gaps, then
continuing P0. Base670b50e, independent CR01 worktree/branch. Runtime, scoped
planning, TDD/verification and handoff practices used; no production authority
inferred. Original airflow-demo dirty ops workspace preserved.

Completed: bio_gatk input/result slot sensors retry only the existing transient
backend classifications, six retries30s exponential capped5m. Original48h
timeout and exact analysis/attempt/transfer request retained. The existing
backend acquisition primitive is already idempotent; no primitive change.
Other stage POST/SSH/upload/CREATE/publish/release/finalize retries unchanged.
Tests cover actual DAG settings/request bytes/permanent401/403/409 rejection,
and same-identity lost-response reacquire/no other-owner slot takeover.

Added separate agreed executor-control-failure.v1 validation in existing
cce_recovery_evidence.py and fixed-path reader. HEAVY_SLOT_API_UNAVAILABLE
accepts only exact Lease GET or Worker Pod LIST, phase heavy_slot_refresh,
typed CONNECTION_REFUSED enum, integer1..3 original-operation attempts,
retry_scope same_operation, retryable/exhausted true, creation_state UNKNOWN.
UNKNOWN never means absent. Existing complete terminal/UID/zero-active-work
requirements remain; control fatal_source is executor_control. Mixed candidate
files, filename/schema mismatch and directory changes during read reject.
No route, binding, dispatcher or automatic enablement added. New test file
backend/tests/test_cce_recovery_control_evidence.py uses explicitly synthetic
terminal scaffolding, not evidence of an actual producer terminal.

Failure evidence clarification from existing authorized ops owners only (no
production queries by this task): B/C were quota GET Lease errno111; one E
failure was quota release -> _finished -> exact Worker Pod LIST errno111.
Other E generations had old-active-Worker guard, Ready wait and unclassified
kubectl failures; C later generation and WES also have swallowed query reasons.
D archived HTTP500 Status.message is a string containing RPC Unavailable and
peer reset; exact CREATE source chain still needs verification. Do not convert
all failures in one batch or generic500 into one automatic category.

Plugin owner WGS-cloud-plugins task019f9d79-be3f-7701-af33-3595d72bbfac received
confirmed control schema and is implementing a distinct bs7 source/artifact.
bs6/wheel/86-test results remain immutable. Requested actual producer-generated
GET/LIST fixtures with admitted Worker journal/checkpoint/manifest. No fake
control INTENT/FAILED submission events. Existing inventory helper STILL rejects
control schema; actual artifact and inventory integration are the next slice.
WES gate generic kubectl error still cannot classify transient vs permanent;
cce-pipeline structured-query producer ownership/baseline remains to be resolved.
No extra Master audit framework, no frozen runtime edits or relaxed quota.

Test environment: fresh ssh BS10610 hostname server10610 uid6708; control
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS, current release
20260912-opt-4d3d24e6. Backend36ff21f87356 image8491604ee01d mounts readonly
/app from20260923-step7-ae416fa/backend/backend and /config from current/config;
scan=false, auto_dispatch=false. Own candidate writable; unchanged permissions.
C=control-root/candidates/p0-airflow-recovery-20260922. Only changed source/tests
copied there; Docker network=none, readonly mounts/rootfs,1CPU/1GiB, tmpfs.
No shared DB/service/restart, production access or live analysis mutation.

Commands/results (logs in C; counts overlap, not an aggregate unique total):
- Cached Airflow58195672af68 image, /usr/local/bin/python
  /candidate/dags/tests/test_gatk_network_retry.py: RED7 methods/1failure0.878s
  (gate retries0), GREEN7 passed0.869s; gatk-slot-{red,green}.log.
- Cached backend8491604ee01d, python -m pytest -q -p no:cacheprovider
  backend/tests/test_cce_recovery_control_evidence.py --tb=short --maxfail=1:
  RED1 failed0.07s (unsupported schema), control-evidence-red.log.
- Control file plus test_cce_recovery_reader.py and test_wgs_transfer_lease.py,
  -k 'control or fixed_bound_pair or lost_acquire_response or cannot_replace_directional':
  GREEN26 passed/31 deselected0.58s; control-evidence-green.log.
- New -k masquerade --maxfail=1: RED1 failed/22 deselected0.12s,
  control-schema-red.log; filename/schema mismatch was not rejected.
- After fix, control + reader files -k 'masquerade or single_stable or symlink
  or nonregular or traversal': GREEN26 passed/24 deselected0.07s,
  control-reader-green.log. Expected container kernel swap-limit warning only.
- git diff --check passed. No local runtime tests, full regression, real cluster
  canary, PostgreSQL concurrency or actual new-plugin acceptance run: excluded
  to keep scope bounded; new artifact is not yet delivered.

Docs changed: design, DAG/runtime contracts, P0 ledger, STATE/TASKS/HANDOFF.
Next: actual bs7 evidence+inventory integration; existing query/dispatch/adapter/
observer-generation/Step4 work and focused remote acceptance. P0 NOT complete.
Automatic policy stays disabled until complete trusted runtime proof and wiring.
Rollback: revert this isolated source commit; no deployed release or data rollback
needed. No main/production merge/push/deploy in this slice.

## 2026-09-23 CR-03 old DagRun cleanup protection

User next step; base3b3e142, independent jiucheng/runtime/CR01-cce-recovery-20260922.
Coordinator confirmed no overlapping ownership and approved isolated synthetic
validation only. Used existing execution plan, backend/runtime/DAG and handoff
skills. Changed cce_recovery_budget.py, main.py cleanup request/handlers only,
bio_wgs.py and bio_gatk.py cleanup payloads; added backend cleanup fence tests,
actual DAG identity tests, updated four affected legacy WGS DAG tests. Updated
API/DAG/runtime docs plus CURRENT_STATE/TASKS/this HANDOFF/P0 progress ledger.

Current pipeline/attempt + refreshed AnalysisRun FOR UPDATE precedes external
cleanup. Shared failure-fence predicate rejects superseded ID, missing identity
with current recovery history, ambiguous/reserved/unbound action. Queued or
uncertain exact current target may clean up; WGS manual resume_action_id is
also required. No new table, policy or graph changes. Transfer must still be
terminal; current ID does not grant early release. Runtime receipt ingestion,
lease primitive, activation and Local/SGE launchers unchanged.

Found partial release primitive commits before retained-slot projection. A
focused forced-interleaving test reproduced stale current_stage overwrite;
WGS now re-locks/rechecks after that partial commit before further mutation.
Earlier valid terminal-slot release is not rolled back if later identity
changed. Separate observer request checks identity again. These tests are not
PostgreSQL serialization proof. No full-scope completion claim.

Fresh test preflight: ssh BS10610 -> server10610 uid6708, control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS; current20260912-opt-4d3d24e6.
Backend36ff21f87356 image8491604ee01d actual /app readonly from
releases/20260923-step7-ae416fa/backend/backend; /config current/config readonly.
scan=false/dispatch=false. Own candidate writable; no permission changes.
No shared services, databases, live runtime or BS96 accessed/mutated. No active
run query needed for network-none isolated containers, no shared deployment.
Candidate C=control-root/candidates/p0-airflow-recovery-20260922.

Backend command: docker run --rm --pull=never --network=none --read-only
--cpus=1 --memory=1g --tmpfs /tmp:rw,size=64m, readonly C/backend and stage YAML,
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/candidate/backend; cached backend image,
python -m pytest -q -p no:cacheprovider <selection> --tb=short.
- test_cce_recovery_cleanup_fence.py --maxfail=1 initial setup ERROR1: synthetic
  fixture omitted required workdir, corrected fixture only; cleanup-fence-red.log.
- Same selection RED1 failed1.22s: stale cleanup not rejected;
  cleanup-fence-red1.log. GREEN23 passed1.67s; cleanup-fence-green.log.
- Added only test_partial_release_rechecks_identity_before_changing_run_projection:
  RED1 failed1.27s, GREEN1 passed1.26s; cleanup-partial-{red,green}.log.
  Only affected case rerun for that fix, not the whole 23-case matrix.
- Extended the existing manual-identity test for an unbound target: both request
  and current dag_run_id absent must not compare equal and authorize drain.
  RED1 failed1.48s; added explicit nonempty ID requirement. Only this case and
  legacy-no-recovery compatibility rerun: GREEN2 passed,22 deselected0.98s;
  cleanup-manual-unbound-{red,green}.log. No additional callback semantics changed.
- test_wgs_only_platform.py -k 'test_internal_runtime_uses_4_1_1_stages_and_releases_transfer_lease
  or test_final_lease_cleanup_does_not_release_another_active_run
  or test_internal_step3_observer_activation_and_drain_are_exposed_in_run_detail'
  GREEN3 passed,62 deselected2.28s; cleanup-legacy-green.log. Existing anyio
  BlockingPortal deprecation warning; all docker runs show kernel swap warning.

DAG command: same isolated limits, tmpfs128MiB, C/dags readonly, AIRFLOW_HOME
and SQLite metadata in tmpfs; cached58195672af68 image entrypoint
/usr/local/bin/python /candidate/dags/tests/<file>. No live credentials/DB.
- test_cleanup_dag_identity.py initial ERROR: candidate missing bio_wgs.py;
  copied unchanged source. Next run incomplete synthetic conf lacked resume_stages
  (3errors+3failures); corrected fixture, no product workaround. Clean RED:6
  subcase failures across2 methods,3 methods total2.798s (missing actual run_id).
  Logs cleanup-dag-red.log, cleanup-dag-red1.log, cleanup-dag-red2.log.
- GREEN3 methods2.952s, then final lease payload coverage added: GREEN3 methods
  2.812s (cleanup-dag-green.log / cleanup-dag-green-final.log).
- test_bio_wgs_dag.py BioWgsDagTests.test_step3_terminal_status_requests_observer_drain
  BioWgsDagTests.test_release_leases_always_requests_final_observer_drain
  BioWgsDagTests.test_release_leases_fails_closed_when_backend_retains_a_lease
  BioWgsDagTests.test_directional_release_task_fails_closed_when_evidence_is_not_terminal:
  GREEN4 passed (cleanup-dag-legacy-green.log). Fixtures now have actual run_id;
  old release-before-drain ordering assertion aligned to existing safe ordering.

Unique24 new backend+3 legacy endpoint+7 DAG tests. No full suite, local runtime,
PostgreSQL concurrency, plugin suite or live recovery: user requests scoped
minimum verification. No push/merge/deployment. Future approved release must put
backend API before DAGs. Rollback source commit only; no data/service rollback.
Next: dispatcher/adapter continuation and observer generation projection under
existing CR-03, trusted terminal closure/Step4/concurrency/end-to-end still open.
Automatic recovery stays off. No extra Master audit track added.

## 2026-09-23 CR-03 old DagRun failure callback protection

User next step; base04a2530, independent CR01 branch. Used executing-plans,
backend/DAG and handoff skills for the already approved callback fence. Coordinator
confirmed these narrow files unowned and Step7 test window released; no shared
service change requested/performed. Changes: cce_recovery_budget shared guard,
wgs_submission_service and gatk_runtime_service terminal entries; main.py only
GATK request field/forwarding; bio_gatk only callback run_id. Two test files plus
API/DB/DAG and progress/state docs. No Step7/observer/lease/runtime/clinical code.

Callback takes refreshed AnalysisRun FOR UPDATE. Superseded DagRun, ambiguous
action attempt, identity-less recovery callback or pending unbound action returns
ignored without state/history/timestamp mutation. reserved never authorizes a
new failure; queued/uncertain with exact action target and current DagRun retains
prior terminal behavior. Completed recovery history still requires callback ID;
unrelated attempts and legacy callbacks retain behavior. WGS manual recovery
action check unchanged. This does not classify generic monitor failure or complete
automatic dispatch. Future dispatcher must freeze target dag_run_id before POST.

Focused review reproduced a related WGS bug: same-attempt/task failure in a new
DagRun deduplicated against old failure and reused old end time. Added DagRun to
the existing failure payload/dedup; historical actions stay intact, no backfill.

Fresh BS10610/server10610 uid6708; control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS; current20260912-opt-4d3d24e6.
Backend36ff21f87356 image8491604ee01d, actual /app readonly from
releases/20260923-step7-ae416fa/backend/backend, /config current/config readonly;
scan/dispatch=false. Own candidate writable. No active-run query: only isolated
network-none synthetic tests, no shared DB/config/runtime mounted or mutated.
Candidate C=control-root/candidates/p0-airflow-recovery-20260922. Backend test
container --rm --pull=never --network=none --read-only,1CPU/1GiB,/tmp64MiB;
C/backend and exact stage YAML readonly. No permissions changes or BS96 access.

Commands/evidence (PYTHONPATH=/candidate/backend, python -m pytest -q -p no:cacheprovider):
- test_cce_recovery_callback_fence.py --maxfail=1 --tb=short:
  RED1 failed1.04s, missing ignored and real WGS state overwrite; callback-fence-red.log.
- Same file without maxfail: GREEN21 passed1.64s, callback-fence-green.log.
- test_wgs_submission_service.py test_gatk_terminal_reconciliation.py
  test_wgs_resume_stage.py -k dag_failure --tb=short:
  GREEN5 passed,23 deselected0.87s; callback-fence-regression.log.
- Added exact test_new_dag_failure_is_not_deduplicated_against_old_dag_end_time:
  RED1 failed0.60s (old2020 end time reused), GREEN1 passed0.48s;
  callback-history-red.log / callback-history-green.log.
- After small dedup fix, only three affected legacy WGS dag_failure cases rerun
  =>3 passed,14 deselected0.60s (callback-history-regression.log); no full previous
  matrix/budget/plugin suite. Initial SSH invocation aborted before remote execution
  at BS172.17.61.18:22 handshake, exit1. Diagnostic ssh BS hostname succeeded
  (node005); one bounded retry reached BS10610 and produced that GREEN result.

Actual Airflow image58195672af685cfa6551cfc44b37b6218bd2039c44b717163a6e8072f78dfd2b
from worker641409cf1cf9; standalone network-none/read-only1CPU/1GiB container,
tmpfs128MiB, own C/dags readonly, isolated AIRFLOW_HOME and SQLite path in /tmp,
no live service credentials, network or database. First --entrypoint python failed
ModuleNotFoundError airflow (callback-dag-identity.log), not application RED.
Read-only worker env showed PATH starts /opt/airflow/snakemake-venv/bin: wrong
interpreter selected. Changed only test invocation to /usr/local/bin/python;
actual DAG import/callback test passed1/1 in2.764s (callback-dag-identity-green.log).
No source workaround or dependency install; kernel swap-limit warning unchanged.

Unique tested cases22 new backend+5 affected legacy+1 real DAG. SQLite does not
prove PostgreSQL concurrency. No full suite, local runtime tests, deployment,
push or main/production/shared-test merge. Next remains dispatcher/adapter/lease
and observer fences plus trusted terminal closure and end-to-end acceptance;
automatic policy stays off. Rollback this source commit only; no data/runtime
rollback needed. Any future deploy: backend API before new GATK callback/DAG.

## 2026-09-23 WGS legacy manual retry fence

User next step; basedddda74e, same isolated P0 branch. Found action_wgs_run legacy
Resume/Rerun failed could increase attempt/dispatch while automatic reservation
pending, unlike resume_stage. Added shared require_no_pending_compute_recovery
in existing cce_recovery_budget; both service entries use it after refreshed
AnalysisRun FOR UPDATE. Guard before release lookup/attempt mutations. Keeps
completed history, treats missing/ill-typed attempt as ambiguous. Cancel bypasses
retry guard but retains prior CCE cancellation restriction. No main.py/Step7/
observer/DAG/runtime changes, no new routes/DB schema/recovery permission.

Fresh preflight: BS10610/server10610 uid6708; current20260912-opt-4d3d24e6;
backend36ff21f87356 image8491604ee01d, /app readonly20260923-step7-ae416fa/backend/backend;
/config current/config readonly; test,scan=false,dispatch=false; own candidate
writable. No fresh active-run DB query needed for network-none synthetic-only
tests and no shared mutation; prior [] is not presented as current evidence.
First scp and subsequent test SSH each aborted at BS172.17.61.18:22 handshake,
exit1; no remote test executed. Diagnostic ssh -v BS exit confirmed public-key
login/exit0, then bounded copy/test retry succeeded. No SSH config change.

New test_cce_recovery_manual_fence.py substitutes external release catalog and
uses existing synthetic Airflow fixture; real SQLite service/dispatch/action
paths. Covers reserved/queued/uncertain, ambiguous attempt identity, finished
history, cancel priority and stale-session attempt refresh. Tests do not prove
PostgreSQL locking/concurrency. Unchanged automatic budget suite not rerun.
Candidate C=control-root/candidates/p0-airflow-recovery-20260922. Cached image
8491604ee01d, --pull=never --network=none --read-only,1CPU/1GiB,/tmp64MiB.
Own backend and exact wgs_stage_contract.yaml mounted readonly; no DB, real
runtime, credentials or kubeconfig. Only C test/module/config files changed.
RED: PYTHONPATH=/candidate/backend python -m pytest -q -p no:cacheprovider
backend/tests/test_cce_recovery_manual_fence.py --tb=short --maxfail=1
=>1 failed0.65s exit1: DID NOT RAISE ValueError, legacy pending reservation bypass.
GREEN: same command without --maxfail=1, plus backend/tests/test_wgs_resume_stage.py
=>22 passed1.23s exit0 (14 new+8 affected), no skips. Logs manual-fence-red.log,
manual-fence-green.log. Kernel swap-capability warning unchanged. git diff --check.
No redundant full suite/local runtime tests/shared service change/deploy/BS96.

Updated API/DB documentation for service guard semantics, TASKS/CURRENT_STATE
and P0 ledger. Remaining: dispatch/callback/lease/adapter integration and terminal
evidence gaps, GATK path, PostgreSQL concurrency. Automatic policy remains off.
Do not count these WGS entries as every resubmission path. Rollback source commit
only; no runtime data/schema/production rollback needed.

## 2026-09-23 bs6 actual producer-to-consumer acceptance

User requested next step; sourceb5d8718 on existing isolated P0 branch. Prior SSH
blocker cleared on the first user-requested fresh attempt. Used runtime/backend
and handoff skills for remote-only scoped acceptance, not shared deployment.
Only two test files and related state/runtime/progress docs changed; no production
implementation or recovery policy change. Existing guard negative matrix extended
by one parameter (WGS/GATK); new opt-in actual bs6 contract file adds12 checks.
This is compatibility validation of existing behavior, not a RED/GREEN claim for
a new production implementation. No broad suite or plugin86-test rerun.

Fresh BS10610/server10610 uid6708; current resolves20260912-opt-4d3d24e6.
Backend36ff21f87356 /app readonly from
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260923-step7-ae416fa/backend/backend;
/config readonly from current release; image8491604ee01d. EnvironmentBS10610-Test,
scan/dispatch=false. Own candidate writable, no permission changes. A bounded
readonly test DB transaction (5s statement timeout) returned nonterminal_runs=[];
rolled back, no clinical fields queried. No shared service restart/changes or
BS96 access. Existing Step7 services and all runtime inputs/results preserved.

Producer fixture root E:
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/plugin-bs6-heavy-p0-20260923/consumer-fixtures-v1
Four scopes: wgs-admission/gatk-admission/wgs-guard/gatk-guard. Each contains actual
context.json, submit-events.ndjson, journal-state.json, executor-failure.json and
explicit empty jobs.ndjson. No admitted Workers or producer terminal seal.
Owner uses real bs6 SubmissionManager and Executor quota guard with synthetic
external API/quota responses/clock. Independently read/verified provenance and
checksum pins, then test checked all20 raw-file hashes and actual wheel bytes.
SHA256SUMS SHA a22a6d55de4947f0884c16c21d102222cd41c9c3f6a59159a4a9bd6c392fb038;
fixture-provenance.json SHA b36fab5298a58bc8e749a82a35ccc37816ebda485a3757f91ead68afbf73ce9d;
wheel SHA f9671d22ed02ec5a3edf0af861e116c0ea7dc9de816de6e07926fa869e2bb546.
Generator SHA in pinned provenance4e5fd7e63bcc6e715ef757f30b634e4a2e6c861cd6e7d4a812c52bb46a811783.
No old fixture relabeling or producer-byte rewriting.

Candidate C: control-root/candidates/p0-airflow-recovery-20260922. Copied only
current consumer/probe modules and selected tests into C. Ran cached image
8491604ee01d with --pull=never --network=none --read-only,1CPU/1GiB,/tmp64MiB;
only C/backend,C/scripts,E,wheel mounted readonly, no DB/env credentials/kubeconfig.
PYTHONPATH=/candidate:/candidate/backend CCE_BS6_FIXTURE_ROOT=/producer:
`python -m pytest -q -p no:cacheprovider backend/tests/test_cce_recovery_bs6_contract.py backend/tests/test_cce_recovery_evidence.py -k 'bs6 or WORKER_SUBMIT_GUARD_FAILED' --tb=short`
Result14 passed,62 deselected0.32s exit0, no skips. Log C/bs6-consumer-contract.log.
Kernel swap-limit warning unchanged; tests otherwise clean. git diff --check.

Scope of result: admission candidate/inventory format compatible; guard unknown
rejects; all candidate-only inputs reject. Synthetic terminal scaffolding cannot
prove a live complete Master terminal or enable recovery. Remaining existing
control/dispatch/callback/adapter and terminal-evidence gaps stay open. No actual
analysis, automatic enablement, publish/install/merge/production mutation.
Rollback source test/docs commit only; no runtime data rollback needed.

## 2026-09-23 next slice: bs6 consumer acceptance blocked before remote access

Source930348c, same isolated branch. User requested next step. Scope is actual
bs6 admission/guard-failure contract acceptance using readonly producer fixtures,
not a new terminal producer or shared-service integration. Requested existing
or minimal actual-wheel synthetic fixtures from plugin owner (WGS/GATK); no
rerun of its86-test suite. Fixture delivery/byte hashes remain pending.

Failed command: a readonly Python fingerprint script piped to
`ssh -o BatchMode=yes -o ConnectTimeout=12 BS10610 'python3 -'`.
Wrapper exit1; stderr `kex_exchange_identification: read: Connection reset`,
`Connection reset by 172.17.61.18 port 22`, then proxy connection closed.
Local `ssh -G` confirms BS10610 is chenjc@172.17.106.10 via BS, and BS is
chenjc@172.17.61.18. Failure is at the jump-host handshake, not evidence of a
backend, fixture or test failure. One attempt only; no blind retries or bypass.
No verified new hostname/mount/gates/active-runs; no remote writes or services
changed, no local runtime/production fallback. Coordinator and owner notified.

Prepared one extra parameter in backend/tests/test_cce_recovery_evidence.py:
WORKER_SUBMIT_GUARD_FAILED with otherwise qualifying synthetic values must still
be refused solely because its category is not allowlisted. Existing UNKNOWN/
retryable=false checks remain. Test is unrun, not GREEN; production code unchanged.
Planned remote command after preflight: selected guard parameter in that test
plus actual bs6 producer contract tests once hash-pinned fixtures are received,
inside the existing isolated cached-image network-none candidate only.
Do not count old-bs5 fixtures as bs6 acceptance. git diff --check passes locally;
runtime validation waits for approved test connectivity. Test edit remains
uncommitted pending validation; docs-only blocker record committed separately.
Rollback: remove that own one-line test addition or revert docs commit; no data
or runtime rollback required. Next condition is restored BS10610 access.

## 2026-09-23 bs6 producer handoff received

Owner: WGS-cloud-plugins task019f9d79-be3f-7701-af33-3595d72bbfac.
Branch jiucheng/plugin-bs6-heavy-p0-20260923; commit
0b19bb605cdff619a7f09b34a6fe774e4b43d357, reported clean. Combines full biosan5
5dd176a baseline with P0 0d606489. Wheel version0.6.4+bs6, SHA256
f9671d22ed02ec5a3edf0af861e116c0ea7dc9de816de6e07926fa869e2bb546.
Evidence root:
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/plugin-bs6-heavy-p0-20260923
Report HANDOFF_BS6.md; wheel below build-0b19bb605cdff619a7f09b34a6fe774e4b43d357/wheel/.
Owner reports baseline24 passed, source86 passed7.38s, actual wheel86 passed7.01s;
not independently rerun here. Duplicate adoption now emits one manifest entry
and permits actual quota receipt release in success/lost-response tests.

Static consumer inspection: cce_recovery_evidence.CATEGORIES remains the two
approved transport/admission categories; WORKER_SUBMIT_GUARD_FAILED with UNKNOWN
and retryable=false cannot pass it. No code or allowlist change. No new complete
Master terminal producer/seal; no automatic recovery enablement. Candidate was
not installed, deployed or promoted. Future consumer acceptance must use actual
bs6 fixtures, not relabel previous wheel evidence. Coordinator reports BS10610
test branch ab8695d/Step7 deployed; P0 not deployed. Revalidate live mounts and
active runs before remote work. This update only records owner handoff; local
git diff --check, no redundant runtime tests. Revert docs to roll back this note.

## 2026-09-23 user scope correction and producer alignment

User: MasterPod failure example requests a completeness check; continue original
P0 plan. WGS owner confirmed its latest authorization: biosan5 plus existing P0
into bs6, all HeavySlotQuota behavior preserved, no additional Master audit.
Plugin owner stopped its separate uncommitted audit candidate. This task stopped
the dependent terminal draft; no source hooks/launcher/RUN_FAILED extension or
producer fixture is considered delivered. Original CR-01–05 scope remains.

Preserved only our uncommitted scripts/cce_master_terminal.py, its test, and the
additional worker_pods probe projection in Git stash
3c617cbd86a4b3d27309689ecdfd7fc820f73c57. No user changes discarded or data removed.
The existing committed Master diagnostic increment ce9e296 remains unchanged.
Draft RED on BS10610 was one ModuleNotFoundError, exit1, master-terminal-red.log;
GREEN intentionally not run after scope correction. Do not count draft coverage.
No new remote actions, shared-service changes, installs, BS96 access or deployment
in this scope correction. Production and automatic policy remain untouched/off.

Changed state/task/spec/progress documents only after shelving draft code.
Verify with git diff --check and explicit diff/status review; no runtime regression
for these documentation edits. Next: existing consumer/control/callback work,
actual bs6 contract handoff and adapter integration. Missing trusted complete
Master/Worker terminal evidence still rejects automatic recovery; do not weaken
that gate or restore the extra audit draft without explicit scope approval.
Rollback: revert this documentation commit; stash retains unverified draft only.

## 2026-09-23 Master BackoffLimitExceeded coverage increment

User requested next step and whether reported20260921D Master BackoffLimitExceeded
is covered. Source8439f55; same isolated P0 branch. Design section3.1 already
explicitly denies recovery based on this symptom alone. Existing P0 probe dropped
reason detail: now retains master_job_condition and all observed Master Pod
main/init/ephemeral exits/reasons/signals/restarts/last termination. Keeps fixed
safe reason codes, omits messages, retains missing values as null, rejects invalid
history/ambiguous failure condition. No new recovery category, seal or permission.
Only scripts/cce_recovery_workloads.py, new focused tests and related state/spec/docs
files changed. No live caller/API/DB projection or production workflow changed.

Fresh test fingerprint: BS10610/server10610 uid6708; control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS; current20260912-opt-4d3d24e6;
actual backend/app20260917-native-ui-76915d8-r2/backend and config from current,
read-only; image8491604ee01d; PLATFORM_ENVIRONMENT=BS10610-Test, scan/dispatch=false.
Own candidate writable, no permission changes. No active-run query needed for this
network-none synthetic check; no shared-service change (window still not acquired).

Under candidates/p0-airflow-recovery-20260922, cached image with --pull=never,
--network=none --read-only,1CPU/1GiB, only own scripts mounted read-only; no DB,
kubeconfig/live runtime or credentials. PYTHONPATH=/candidate:
`python -m pytest -q -p no:cacheprovider scripts/tests/test_cce_master_failure_observation.py --tb=short --maxfail=1`
RED1 failed0.04s exit1: KeyError master_job_condition, expected missing feature.
GREEN command removed --maxfail=1 and additionally selected affected
scripts/tests/test_cce_recovery_workloads.py and
scripts/tests/test_cce_recovery_inventory.py::test_validated_inventory_drives_every_exact_worker_query.
Result34 passed0.06s exit0 (7 new,25 affected probe,2 composition), no skips.
Logs master-observation-red.log/master-observation-green.log. Swap-limit warning
unchanged. No unrelated suites/local runtime tests. git diff --check required.

No BS96/real cluster query;20260921D root cause and current production DB evidence
NOT confirmed. User report is not classified as eligible. Kubernetes official Job
docs confirm backoff terminal semantics; implementation coverage checked from repo.
Remaining: full trusted Master audit/final footer and complete Worker historical
outcomes, then adapter/dispatch/fences. lastState is not complete restart history.
No shared deploy, bs5 replacement, automatic enablement, cleanup or resume.
Rollback this source commit only; no runtime data/state changed.

## 2026-09-23 next step: submission inventory to UID probe

User: 继续下一步. Source22d47cb, isolated P0 branch/worktree unchanged. Added
scripts/cce_recovery_inventory.py and its new test file only; no existing runtime
entry changed. Joined complete bound journal/checkpoint/candidate/admitted-manifest
snapshot validation to prior read-only UID probe. All intents feed probe queries;
missing/extra/partial/conflicting evidence rejects. No terminal seal or automatic
authorization; internally consistent stale snapshots are not finality proof.
Updated docs08, CURRENT_STATE, TASKS and existing P0 progress ledger. Runtime and
handoff skills kept this slice test-only; no new plan or unrelated feature added.

Fresh gate: ssh BS10610 -> server10610; control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS; current -> releases/20260912-opt-4d3d24e6;
actual backend/app -> releases/20260917-native-ui-76915d8-r2/backend, config from
current release, image8491604ee01d; test environment, scan/dispatch=false.
Bounded read-only test DB transaction active_runs=[]. Existing candidate/evidence
access used; no permission change. Shared backend/frontend window belongs to WES
UI task. All shared services, workflows, inputs/results, bs5 artifact and BS96
preserved; no install/deploy/deletion/analysis submission/database write.

Candidate C: control-root/candidates/p0-airflow-recovery-20260922.
Fixture E: /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/plugin-p0-submit-20260922/fixtures.
Command (scripts mounted at /candidate/scripts:ro, E at /producer:ro):
`PYTHONPATH=/candidate CCE_PRODUCER_FIXTURE_ROOT=/producer python -m pytest -q -p no:cacheprovider scripts/tests/test_cce_recovery_inventory.py --tb=short`
RED with --maxfail=1: ModuleNotFoundError scripts.cce_recovery_inventory,
1 failed0.04s, exit1, C/inventory-red.log. Expected missing implementation, not
an environment problem; implemented then GREEN26 passed0.08s, exit0,
C/inventory-green.log. All tests ran, including both actual producer fixtures.
Cached image8491604ee01d, --pull=never --network=none --read-only,1CPU/1GiB,
ephemeral /tmp scratch only, no DB/kubeconfig/live runtime mounts. Kernel swap
limit warning unchanged. Two composition tests use prior synthetic subprocess
fixture, not repeated prior test cases. No old suites or local runtime tests run.

Plugin-owner read-only source report inspected locally at
D:/pipeline/task-artifacts/plugin-p0-submit-20260922/MASTER_ERROR_PRODUCER_READONLY_REVIEW.md;
remote same basename under E parent. Frozen cached Master490153a56b64,
Snakemake9.24.0+biosan1: SubmissionFailure reaches CLI ERROR without mandatory
JOB_ERROR; rule-status excludes ERROR; cancellation/monitor callback races and
swallowed logger flush errors prevent completeness inference. Need typed origin
binding, cumulative mixed/unknown error accounting and explicit healthy final
footer. Admitted Worker historical outcomes must also be accounted for; no-active
observations and404 are not proof of zero historical rule failure. Report is source
review, not producer implementation/acceptance. bs5 remains unchanged.

Next: trusted Master audit/terminal producer plus final snapshot and Worker
history binding, then adapter writer, dispatch/callback/control fences. CR-01–05
not complete. Live cluster/PostgreSQL concurrency/full integration not run because
not implemented in this slice and shared-service window is unavailable; obtain
fresh gate and coordinated window before service acceptance. No runtime rollback
needed; reverting this source-only commit removes helpers with no data effect.

## 2026-09-23 next step: bound workload observation prerequisite

User: 下一步. Source branch unchanged fromd9bd2a7. Used runtime/planning and inline
execution skills, preserved existing scope/ledger; no per-slice agent dispatch.
Added scripts/cce_recovery_workloads.py and scripts/tests/test_cce_recovery_workloads.py.
No existing runtime/Resume entry or workflow changed. Probe binds exact Master/
Worker UIDs, namespace and Pod controller ownership; rejects active/terminating,
missing/paged Pod inventories or incomplete main/init/ephemeral container exits.
Missing Job still queries residual Pods. Bounded read-only kubectl commands only.
It cannot prove input-list completeness or classify errors; deliberately no seal,
automatic permission, backend caller or deployment. Updated docs08/state/tasks/ledger.

Fresh BS10610 preflight: server10610, control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS, current20260912-opt-4d3d24e6;
actual backend/app20260917-native-ui-76915d8-r2/backend, cached image8491604ee01d,
scanner/dispatch false. Bounded read-only test DB transaction returned active_runs=[].
Coordinator then assigned shared-service window to WES UI task: no backend/frontend
mutation or deploy. Only own candidates/p0-airflow-recovery-20260922 used here.

Synthetic command (PYTHONPATH=/candidate; own scripts mounted read-only there):
`python -m pytest -q -p no:cacheprovider scripts/tests/test_cce_recovery_workloads.py --tb=short`
RED with --maxfail=1: missing module,1 failed0.04s,exit1. GREEN25 passed0.06s,exit0.
Logs workloads-red.log/workloads-green.log in own candidate. Cached backend image,
network none/read-only/1CPU/1GiB, no DB/kubeconfig/live runtime mounts. Tests replace
only subprocess boundary, exercising actual object/UID/state validation. No prior
helper, plugin suite, unrelated test, local runtime or actual cluster check rerun.
Initial scp failed exit1 because candidate scripts/tests did not exist; created
only that exact candidate subdirectory and copied successfully. No files deleted.
Kernel swap-limit warning unchanged. No permissions broadened or shared install.

Read-only source findings: huawei-cloud-runtime source83e7adb (untracked historical
asset backup left untouched). Native no-active-worker guard only checks states
from manifest, not exact UID/residual Pods. Master RUN_FAILED is generic and current
rule-status logger filters events/no complete classified error footer. These cannot
authorize recovery. Next: complete submit journal/admitted-manifest reader + trusted
Master error summary/writer, then adapter binding/dispatch/callback fences. Do not
write a positive terminal seal from zero observed rule errors alone.

Plugin version update verified: f1d3fa58a5075387500dd72620c03affe49b48e7 is metadata/
version only, recovery.py bytes identical to0d606489 and worktree clean. New
0.6.4+bs5 wheel SHA256 independently checked:
8ab618cb46d9e8d06ed0063096b30d9ffad3c3c41c7ba25f101ad6903165a26b.
Path: plugin-p0-submit-20260922/build-f1d3fa58a5075387500dd72620c03affe49b48e7/wheel/
snakemake_executor_plugin_kubernetes-0.6.4+bs5-py3-none-any.whl under the same evidence
root in preceding entry. No install or producer-suite rerun; old hash-pinned fixtures
retain old wheel provenance. No BS96/production/data mutation. Rollback source
commit only; no runtime data state to undo. CR-01–05 not complete.

## 2026-09-23 actual candidate producer/consumer contract check

After f73e284, plugin owner delivered commit
0d60648922b27aee25eda3ea7900f50467fbe0d9, version0.6.4+biosan4.p0.1.
Verified clean source worktree at
/mnt/biodevrwbi/33.chenjiucheng/project/worktrees/snakemake-kubernetes-p0-submit-20260922.
Evidence root E:
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/plugin-p0-submit-20260922.
Actual wheel SHA256 independently verified:
520914e26ced796b70805f2daf35e027c00fa1e985aadb855d72807c6aef844b.
Wheel: E/build-0d60648922b27aee25eda3ea7900f50467fbe0d9/wheel/
snakemake_executor_plugin_kubernetes-0.6.4+biosan4.p0.1-py3-none-any.whl.
Owner's source/wheel56-test results were read in E/HANDOFF.md, not rerun here.

Original admission fixture uses pipeline=synthetic, correctly outside consumer
allowlist. Requested regeneration, not edited JSON or a permissive production
change. Owner generated E/fixtures/wgs-admission and gatk-admission through that
wheel and synthetic API; generation1, explicit Master-submit execution identities.
Raw context/candidate SHA256 pins are in the new opt-in test file. Generator and
provenance: E/generate-pipeline-fixtures.py and E/pipeline-fixtures.log.

Added backend/tests/test_cce_recovery_producer_contract.py only; no production
code changed in this follow-up. With E/fixtures mounted read-only at /producer:
`CCE_PRODUCER_FIXTURE_ROOT=/producer python -m pytest -q -p no:cacheprovider tests/test_cce_recovery_producer_contract.py --tb=short`
Result4 passed0.08s, exit0; own candidate producer-contract.log. Same cached
backend image8491604ee01d, network none/read-only/1CPU/1GiB, no live DB mount.
Candidate-alone rejection plus synthetic-terminal compatibility tested for both
adapters. The terminal is test scaffolding, NOT real runtime evidence or a seal.
No extra RED/implementation cycle: this is contract acceptance of existing code.
Missing external fixture env explicitly skips opt-in tests, never counts as pass.

Fresh preflight: server10610; current and actual backend mounts unchanged from
preceding entry; scan/dispatch false. Read-only bounded test DB transaction found
GATK_20260922_112207_23AD29 attempt1 running/step1_upload; coordinator notified.
No shared service, that run, BS96, database write, install, image deploy or cleanup.
Updated state/tasks/runtime/prerequisite/ledger docs. Working branch unchanged.
Next: trusted Master terminal/Worker quiescence writer and adapter binding,
then dispatch/callback/control fences. CR-01–05 incomplete, policy unwired/off.
Rollback this test/docs commit only; source evidence and real data untouched.

## 2026-09-23 P0 evidence-to-action bridge and manual resume fence

Goal: user requested next step of existing P0, not P1 pause/delete. Continued in
isolated jiucheng/runtime/CR01-cce-recovery-20260922 from7bfa967. Original dirty
ops workspace and Step7-owned main.py/wgs_step7_service.py/wgs_observer.py untouched.

Added backend/app/cce_recovery_service.py and its synthetic test file: current
failed Step3 monitor explicitly binds to actual Master-submit execution; frozen
release/workdir/hash/generation and controlled evidence validated before reserve.
RunAction stores both identities and sealed-content binding; replay cannot replace
evidence. No status mutation, external dispatch, public endpoint or auto enablement.
Updated wgs_resume_service.py and test_wgs_resume_stage.py: unfinished same-attempt
automatic recovery blocks manual Resume before frozen files or Airflow change;
terminal automatic history stays intact. Updated docs04/05/08, state/tasks/ledger.

BS10610 read-only fingerprint in this turn: server10610, control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS, current20260912-opt-4d3d24e6,
actual backend mount releases/20260917-native-ui-76915d8-r2/backend; cached image
8491604ee01d. Test environment and scan/dispatch false. Only own candidate files
changed: candidates/p0-airflow-recovery-20260922. No service or deployment change,
so no rollback release selected. Shared database/runtime paths were not mounted.

Commands in cached image, network none/read-only/1CPU/1GiB, synthetic SQLite:
- python -m pytest -q -p no:cacheprovider tests/test_cce_recovery_service.py
  RED missing module; GREEN22 passed1.04s, service-red.log/service-green.log.
- python -m pytest -q -p no:cacheprovider tests/test_wgs_resume_stage.py
  RED selected pending guard failed DID NOT RAISE, exit1; GREEN whole affected
  file8 passed1.17s, exit0; resume-fence-red.log/resume-fence-green.log.
  Only tracked wgs_stage_contract.yaml additionally mounted read-only at /config.
Kernel swap-limit warning unchanged. No unchanged helper suite/local runtime
tests, live Postgres, Kubernetes or browser checks were run: none needed for this
internal slice; concurrency/actual producer integration remain required later.

Producer worktree now has submission_recovery.py plus plugin/init/tests changes;
owner still active, no final commit/producer fixture accepted. Proposed binding
writer and terminal wrapper remain missing. Do not deploy or enable automatic
recovery from these synthetic results. Before future shared-service work, recheck
active runs and mounts and coordinate Step7. Next: actual producer/wrapper-bound
adapter handoff, dispatch and remaining control/callback fences. Rollback this
source commit; no production/data state to undo. P0 remains incomplete.

## P0 next step: controlled evidence reader (test only)

User: continue next step. Worktree/branch unchanged from73f8d4e, original dirty
ops worktree untouched. Applied runtime/planning/execution skills; no expanded
pause/delete scope. Read-only BS10610 probe confirmed server10610, current
20260912-opt-4d3d24e6, actual backend20260917-native-ui-76915d8-r2/backend,
image8491604ee01d, test environment with scanner/dispatch disabled. Coordinator
subsequently released upload gate, but this slice did not deploy or mutate any
shared service/run/lease/database. Step7-owned shared files remain untouched.

Changed backend/app/cce_recovery_reader.py and tests/test_cce_recovery_reader.py;
updated docs08, CURRENT_STATE, TASKS and P0 ledger. Reader uses controlled fixed
file names, no-follow descriptor traversal, size/type/link and JSON guards,
pair stability checks, then existing bound validator. No public request accepts
root/scope/context. Actual adapter binding and trusted writer remain prerequisites.
Master Step2 creation identity is not interchangeable with Step3 monitor identity.

Remote candidate candidates/p0-airflow-recovery-20260922; cached backend image,
network none, read-only,1CPU/1GiB, no live mounts. Command:
`python -m pytest -q -p no:cacheprovider tests/test_cce_recovery_reader.py`.
RED: missing module (exit1). GREEN:26 passed0.09s (exit0), recorded as
reader-red.log/reader-green.log. Kernel no-swap-limit warning unchanged.
No repeat of unchanged budget/evidence suites, no local runtime tests.

Pending: plugin real producer fixture, authoritative terminal wrapper, current
Master/monitor lineage binding, reservation-to-dispatch/control fences, DAG/UI
and PostgreSQL concurrency. These tests are not real Master integration or P0
completion. Continue from plugin owner's final artifact; no additional authority
is implied. Rollback: revert unreferenced reader/tests; no data state to undo.

## 2026-09-22 P0 draft evidence validator checkpoint

Added backend/app/cce_recovery_evidence.py and its synthetic test file. Existing
candidate/image/limits used; RED missing module, GREEN62 passed0.13s. Logs are
evidence-red.log/evidence-green.log in the same P0 test candidate. Only this test
file ran; budget was not rerun after unrelated pure validator additions.
Plugin owner confirmed no completed producer fixture yet. Terminal seal is a
proposed trusted-wrapper contract, documented in docs08 and code, not a browser
API or authenticated signature. Exact identities, digest, complete cumulative
failure summary and all-intent/all-manifest quiescence are mandatory. Unknown
creation outcome stays rejected even after GET404. No producer/runtime integration,
new endpoint, image release or automatic policy enablement is claimed.
Continue with real producer fixture and authoritative wrapper support before
connecting reservation or dispatch; CR-01/02 remain partial. Scope and rollback
unchanged: unreferenced helpers only, no shared or production data changes.

## 2026-09-22 P0 continued under isolated-test release

Authority: user requested code and partial tests during remaining upload;
coordinator explicitly released only separate candidate/network-none containers.
SSH BS10610 succeeded (server10610). Current symlink remains 20260912-opt-4d3d24e6;
actual backend mount is 20260917-native-ui-76915d8-r2/backend, image8491604ee01d,
PLATFORM_ENVIRONMENT=BS10610-Test, intake scan and auto dispatch false.

Implemented backend/app/cce_recovery_budget.py with focused synthetic tests:
same-attempt max2, 60/180s, deadline/journal consistency, replay without double
spend, stop/control/Step7 fences, no commit inside helper. Missing initialized
budget rejects rather than assuming historical count0. No API or runtime caller,
no dispatch, policy enablement or default changes. Existing state retained.

Remote candidate: candidates/p0-airflow-recovery-20260922 under test control root.
Cached backend image; docker run --rm --pull=never --network=none --read-only,
1 CPU/1GiB, candidate /app read-only; synthetic SQLite only, no live mounts/DB.
`python -m pytest -q -p no:cacheprovider tests/test_cce_recovery_budget.py`:
RED missing module (exit1); GREEN54 passed1.89s (exit0), budget-red/green.log.
Kernel warns no swap limit support; memory limit applied, no swap-limit claim.

Changed code/test above, P0 ledger, prerequisite/status/task/handoff docs. No
service restart, upload/monitor/lease/task mutation, production access or deploy.
PostgreSQL concurrency and endpoint/DAG/runtime integration NOT tested. Shared
control locking at dispatch is still required; reservation is not authorization
to launch. Step7 owner is editing main.py/wgs_step7_service.py/wgs_observer.py;
leave these paths untouched until coordinated. Plugin owner preparing candidate
evidence schema. Next: validated consumer then adapter/fence integration; do not
claim entire P0 complete. Rollback: remove unreferenced module, no data rollback.

## 2026-09-22 P0 approved — remote acceptance blocked by baseline decision

User approved full joint implementation restricted to BS10610 testing. Agreed
versioned plugin context/failure interface with the user-selected plugin task;
wrote `backend/tests/test_cce_recovery_budget.py` and the P0 progress ledger.
Tests are not run and application code is not implemented. No completion claim.
Coordinator `01a0b254-07b5-7352-99aa-871b117459ad` explicitly paused all BS10610
deployment/acceptance while user chooses selective versus full test baseline;
the plugin owner was informed. No deployment/restart, real analysis, production
access or shared package installation occurred. Local `git diff --check` passed.
Next: resolve baseline through coordinator, receive actual fingerprint, run RED
then implement and verify the focused two-stage plan. Preserve these uncommitted
preparations and the separate original worktree's operational records.

## 2026-09-22 P0 prerequisite review — awaiting external scope confirmation

User requested P0 implementation. Isolated branch
`jiucheng/runtime/CR01-cce-recovery-20260922` starts from test `1da45f3`.
Reviewed GATK monitor/resume and read-only BS10610 executor source (`1ca1e88`);
the inspected producer lacks the required bound Worker-create fatal evidence.
Exact frozen Master artifact binding is not yet verified. No application edits,
runtime tests, real analysis, production access or deployment occurred.

Changed only this entry, CURRENT_STATE, TASKS and
`docs/P0_RECOVERY_PREREQUISITE_20260922.md`; the latter records exact paths,
commands/failures, evidence, risk and next decision. `git diff --check` is the
documentation check. Next: obtain scoped external producer/artifact confirmation,
then CR-01–05 and focused synthetic BS10610 acceptance. No tests are claimed.
Rollback is document-only; no task state or analysis data was changed. Existing
dirty operational documents in the original worktree were left untouched.

## 2026-09-22 remove redundant blanket validation gate

The user determined that `TEST-VALIDATION-01` would duplicate testing already
completed before production publication. The queue now accepts existing release
evidence for completed work and requires focused tests only for newly authorized
changes. No standalone missing-`S1` rerun or branch-wide validation matrix is a
prerequisite.

The next priority is P0 `CCE-RECOVERY-01`: review the proposed bounded recovery
policy for the known 0918A/0919B failure causes, then implement `CR-01`–`CR-05`
under a separate development instruction. P1 remains two-step WGS submission
followed by run control. This update changes only `CURRENT_STATE.md`, `TASKS.md`
and `HANDOFF.md`; it performs no application test, SSH, runtime, database,
analysis, deployment or data action. Rollback is a documentation-only revert.

## 2026-09-22 completed production commits synchronized into test

### Goal and authorization

The user clarified that `9ff67d3` and `9b381eb` should be included directly in
the primary test branch. Both are already completed and deployed production work;
they must not be represented as future development.

### Result and scope

- Target: local Git primary test worktree/branch
  `jiucheng/test/wgs-local-main-sync-20260917`.
- Verified `origin/main` and `origin/jiucheng/release/production` both at
  `9b381eb`; pre-merge divergence was `2 35`.
- Merged `origin/main` normally, preserving the complete `9ff67d3` application
  fix and `9b381eb` BS96 release record plus all test-only history.
- Resolved documentation conflicts by retaining the compact test backlog and
  adding the production feature, server, release and rollback facts. No
  application behavior was rewritten during conflict resolution.
- `TEST-LINEAGE-SYNC-01` is complete. These commits add no development card.
  The later priority correction above closes redundant `TEST-VALIDATION-01`.

### Checks, environment and rollback

This repository synchronization performs no SSH, Docker, database, runtime,
analysis, gate or data operation. The production release's existing acceptance
evidence is retained in `docs/releases/2026-09-18-sampleinfo-bs96.md`; local
runtime tests are not used as a substitute for BS10610. Checks are limited to
merge ancestry, exact file scope, conflict-marker/link/task consistency and
`git diff --check`. Rollback, if explicitly requested before further work, is a
normal Git revert of the merge; it must not alter BS96, BS10610 or analysis data.

## 2026-09-22 development backlog refresh and priority decision

### Goal

Refresh the authoritative test-branch planning state after new CCE recovery,
WGS submission and display designs were added, then assign a dependency- and
risk-based implementation order. This is planning only.

### Current source and lineage evidence

- Fast-forwarded the clean primary test worktree from `cd7771b` to remote
  `e44dc3e`; no local change was overwritten.
- Current `origin/main` and production both equal `9b381eb` and are not ancestors
  of test. Before this planning commit,
  `git rev-list --left-right --count origin/main...HEAD` was `2 33`; the
  documentation commit only increases the test-only side.
- The two absent main commits are `9ff67d3` (same-batch import and saved-review
  fix) and `9b381eb` (its BS96 release record). They are already released work,
  not new development, but must be reviewed into the test baseline before coding.
- The separate `D:/pipeline/airflow-demo` operations worktree has three user-
  owned dirty state documents for the completed 0919B manual rollback. They were
  inspected as operational evidence and left untouched.

### Reorganized priority

1. P0 — restore main/production ancestry in test and finish
   `TEST-VALIDATION-01`, including a fresh classification of missing `S1` after
   the submission-page main fix is present.
2. P1 — `CCE-RECOVERY-01`: review the two-recovery/60–180 second policy, then
   implement `CR-01` through `CR-05`. This addresses known 0918A/0919B failure
   modes and defines the identity/fencing contract required by run control.
3. P2 — `WGS-SUBMIT2-20260922`, then `RUN-CONTROL-20260918`. Submission work
   first reduces pre-analysis side effects; run control must reuse CCE recovery
   rather than introduce a competing recovery path.
4. P3 — `WGS-QC-TWO-SOURCE-20260918`; it adds source-qualified supplemental
   evidence while preserving ordinary QC authority.
5. P4 — `WGS-CNVPLOT-20260918`; it is a bounded read-only viewer.
6. P5 — operator acceptance, combined BS10610 evidence, promotion manifest and
   protected worktree hygiene after the selected feature scope stabilizes.

No two tracks may edit the same Backend/Airflow contracts concurrently. QC/CNV
can use independent owner worktrees only after the P0 baseline is fixed.

### Modified files and checks

- `TASKS.md`: added the priority table, dependency rule, current lineage refresh
  items and missing-`S1` reclassification gate.
- `CURRENT_STATE.md`: recorded current commits/divergence, new designs and the
  priority rationale.
- `HANDOFF.md`: this entry.

Validation is limited to branch/ref inventory, task/spec link and ID checks,
the three-file Markdown whitelist and `git diff --check`. No application tests,
SSH, Docker, database, runtime, real analysis or deployment action belongs to
this planning pass.

The target of this pass is local Git documentation at source `e44dc3e`; future
runtime acceptance remains BS10610. No SSH alias/hostname fingerprint, current
or rollback release path, mount/permission check, service state, scanner gate or
dispatch setting was inspected or changed because no remote action was in scope.

### Next action, risk and rollback

Next action is the P0 reviewed main-to-test refresh, not feature implementation.
Do not assume the production runner binding for editable sampleinfo until its
future preflight. Do not enable automatic CCE recovery before policy review and
focused BS10610 synthetic evidence. Rollback of this pass is a documentation-
only revert; it does not alter runtime or data.

Open questions are whether the revised two-recovery policy is accepted, whether
missing `S1` remains after the main refresh, and which exact production runner
SHA will be the future two-step-submission release target.

## 2026-09-22 submit recovery documents to the pending-development branch

User now authorizes submitting the documentation to primary test branch
`jiucheng/test/wgs-local-main-sync-20260917`. Remote advanced from9333160 to
cd7771b with QC presentation and CNV viewer designs; preserve both unchanged.
Integrate6540982 with that tip; resolve only competing TASKS/HANDOFF insertions,
retaining both sets of entries. Delta against remote is limited to the same
four recovery documentation files. No application, main/production or runtime
changes; application tests remain inapplicable.

GitHub port22 timed out;443 worked with StrictHostKeyChecking=yes and existing
github.com HostKeyAlias after the separate443 host alias was unknown. No host
key checks disabled, credentials exposed or persistent SSH config changed.
Verify exact file scope, whitespace, no conflict markers and preserved remote
designs before a normal fast-forward push; do not force-push on remote races.

## 2026-09-22 CCE recovery redesign — documentation only

### Goal and authority

User requests a revised development design covering0918A Worker-create transport
disconnect and0919B Gatekeeper admission timeout. Missing-input repair (0919C)
is deferred. This authorizes document changes, not application implementation,
real recovery, remote validation, production deployment or branch promotion.

Native isolated worktree is based on local test tracking ref9333160; branch
`jiucheng/docs/cce-recovery-design-20260922`. Existing dirty operations worktrees
remain untouched. No dependency installation or application baseline tests:
this is Markdown-only work under the project's local-editing boundary.

### Revised scope and files

- `docs/superpowers/specs/2026-09-17-wgs-gatk-cce-connection-recovery-design.md`:
  replace blanket automatic-Master exclusion with two source-bound allowlisted
  failure classes; keep ordinary500, unknown causes, real rule errors and
  input defects excluded. Add persistent two-recovery budget,60/180s proposed
  waits, original deadline, old Worker quiescence, exact UID lineage, safe
  replay/reconciliation, user-stop priority, adapter gates and state display.
  Include0918A Step4 uncertain dispatch without blind publish replay.
- `TASKS.md`: CR-01–05 future delivery/acceptance cards; implementation unchecked.
- `CURRENT_STATE.md`: revised scope, proposal/review status and exact branch base.
- `HANDOFF.md`: this scope, evidence and handoff record.

Two/60/180 values are design defaults proposed for review, not previously
approved operational settings. Query retries remain separate from compute
recovery; both must be bounded and cannot reset silently. Resume reuses frozen
inputs/attempt/workdir and existing outputs; incomplete rules may execute again.

### Checks and intentionally unrun work

Read the current test-ref spec/task queue and bounded local resume source;
checked the design link, CR-01–05 in spec and task queue, contradictory exclusions
and exact four-file whitelist with Git diff/status. `git diff --check` passed;
`git diff --exit-code -- backend frontend dags scripts config` returned0 with
no output. These are document checks, not application validation. No
SSH/API/DB/Docker/workflow command was run.
Do not run pytest/npm/DAG import checks for this document-only delta. Future
application tests require development authorization and BS10610 isolation.

### Remaining work, risks and rollback

Written-spec review precedes a detailed execution plan and coding. Runtime
error evidence availability, existing Worker quiescence primitives, GATK
capability and atomic control fences must be demonstrated in CR-01–03; fail
closed if an old bundle cannot support them. Necessary external source/release,
image/schema/permission changes need explicit scope review, not implicit uplift.
No automatic kill of Workers, data cleanup, inputs/receipts repair or prepare.
No test/main/production merge or push is part of this document revision.
Rollback is a documentation revert only; no runtime or data state changed.

## 2026-09-18 WGS CNV plot viewer design

Documented a narrow WGS-only `CNV plot` Run Detail tab. It resolves only
selected-sample native PNGs from the frozen bound `03_CNV` directory, lists
sample IDs at left and lazily streams one image at right. The observed V4.2.1
plots are 4800x1200 PNGs at about 0.4 MiB each, so PNG is retained; HTML/SVG
redraw and eager batch preload are excluded. No code, synthetic fixture,
runtime/data operation, workflow change or deployment occurred. Future work is
`CNV-01` through `CNV-03` in the new design document.

## 2026-09-18 QC two-source presentation simplification

The approved presentation direction supersedes the prior expandable
supplemental-row idea: Run Detail QC uses default **常规临检** for batch
`QCstat.tsv` and conditional **罕见病** for batch `multi.QCstat.tsv`. The latter
is hidden when no `F57J`/`UPC` sample applies and contains only applicable
samples. This keeps identically named metrics apart without a wide table or
ordinary-row placeholders. Documentation/task cards only; no code, test,
runtime, data or deployment change.

## 2026-09-22 submission design queued for development

User authorized completing the combined development document and committing it
to the pending-development test branch. Incorporated WGS owner source evidence,
two-step final-submit boundary, editable input/revision/hash contract, automatic
intake deduplication and narrow cancellation semantics. Only four documentation
files are included. Preserve newer test-branch CCE recovery design updates;
main/production and existing operations-worktree changes are excluded.
Validation: document links, task identifiers and git diff --check only; no
application tests, server operations or deployment are necessary for this change.


## 2026-09-22 WGS two-step submission and editable sampleinfo proposal

User requested combined assessment and updated design only. New isolated docs
worktree wgs-submission-design-20260922 branches from local test9333160; main
inspection baseline9b381eb. No remote production command, source implementation,
test execution, merge or push performed. Existing0919B operational changes stay
in their original worktree. New design and CURRENT_STATE/TASKS/HANDOFF only.

Confirmed current approval2 starts analysis and can mutate pending; cancellation
works at config_review before approval, not after. Proposed final submission
defers analysis side effects until one explicit decision. Editing uses a private
working copy, revision and hash frozen before analysis, rather than modifying
an existing frozen source/receipt. Runtime already handles existing sampleinfo
with valid receipt reuse or missing-receipt archive/regeneration. Auto-dispatch
may instead be blocked by a retained manual task: narrowly release explicitly
cancelled uncommitted drafts, never all terminal tasks.

WGS-pipeline thread01a09149-ad9d-7e92-b98a-16d9cae075e2 was explicitly asked
to confirm current native source/commit, file-exists behavior and --sampleinfo
handoff effects. Its returned server-source audit is incorporated: server10610
wgs-4.2.0 HEAD ebf1f4b, prepare script last change9f4f359. Native sampleinfo/all
refuse existing files; analysis accepts valid edited copy, with updated source
hash/request for handoff. Source is not rewritten; final sampleinfo is derived.
Pending mutation precedes final directory rename, including zero-selected cases.
Actual production runner binding remains unverified; check once before rollout.
No native source edit or overwrite switch is proposed.
Document links and scope checked locally; no runtime test is appropriate for
this proposal. Rollback removes this proposal only, without service/data effects.


## 2026-09-18 consolidate new development documents into the primary test branch

### Goal and source selection

Make the primary test branch the single authoritative place for current planned
development. The two Git common repositories and their worktrees/refs were
inventoried after a remote fetch. Only two commits newer than test tip `2d899e5`
were documentation-only development proposals:

- `1c631b7` on `jiucheng/feature/run-control-20260918`;
- `53fc860` on `jiucheng/docs/wgs-qc-two-source-20260918`.

Older feature, fix, release and operations branches were not treated as new
development merely because they contain Markdown. Their historical deployment
or handoff notes remain evidence, not active queue entries.

### Consolidated content

- Added `docs/superpowers/specs/2026-09-18-run-control.md` unchanged in meaning:
  proposed CCE pause, same-attempt checkpoint recovery, exact cloud/Airflow/
  biodemo deletion, residual handling, tombstone, scanner fence and permissions.
- Added `docs/2026-09-18-wgs-qc-two-source-contract.md` unchanged in meaning:
  ordinary batch QC remains authoritative while applicable `F57J`/`UPC` samples
  receive separately labelled WgsMetrics supplemental evidence.
- Rewrote the source branches' task snippets into the current compact
  `TASKS.md`: `RC-01` through `RC-05` and `QC2-01` through `QC2-03`, with owner,
  sequence, dependency, scope and authorization boundaries.
- Updated `CURRENT_STATE.md` so both designs are visible beside the existing
  `CCE-RECOVERY-01` track without claiming any implementation or validation.

The source branches had different bases: run control was based directly on
`2d899e5`, while the QC document was based on main `1255a06`. Their full commits
and inherited state files were therefore not merged or cherry-picked. Only the
two specs and reconciled current-branch state were retained.

### Scope and validation

This was documentation and Git inventory only. No backend, frontend, DAG,
runtime, migration, application test, SSH, Docker, database, analysis, service
or production operation was performed. The designs do not register APIs, change
QC policy at runtime or authorize pause/resume/delete of a real task.

Validation covers the exact five-file documentation delta, local Markdown link
resolution, task-ID/spec consistency, source-spec comparison, `git diff --check`,
and proof that `backend`, `dags`, `scripts`, `frontend`, migrations and runtime
configuration did not change. No application test is applicable to this
documentation-only consolidation.

### Next action and rollback

Review `TEST-VALIDATION-01`, then select a documented development track under a
new implementation instruction. Coordinate run control with CCE recovery before
coding; the two-source QC work is independent. Production activation, test-to-
main promotion and live task/data actions remain separately authorized.

Rollback is a single documentation revert. The two source branches remain
available as provenance until repository hygiene separately classifies them;
this consolidation does not authorize deleting their worktrees or branches.

## 2026-09-18 test-branch backlog consolidation and synchronization hold

### Goal

Maintain one authoritative test development branch, preserve historical state
and make unfinished testing visible without synchronizing with `main`.

### Completed

- Confirmed the primary test worktree is
  `D:/pipeline/airflow-demo-worktrees/wgs-local-main-sync-20260917` on
  `jiucheng/test/wgs-local-main-sync-20260917` at `f0b07c4`.
- Refreshed origin and confirmed this is the only remote
  `origin/jiucheng/test/*` branch.
- Recorded, for inventory only, `origin/main=1e512e1`, main-only 13, test-only 23
  and merge base `c6ac6ce66df7f1636cc82376f5b2c113ecd457ed`.
- After user correction, replaced the proposed main-delta integration queue
  with `docs/TEST_BRANCH_SYNC_HOLD_20260918.md`. All main-only and legacy-branch
  changes are held while testing is incomplete.
- Replaced historical narrative in `CURRENT_STATE.md`, `TASKS.md` and this file
  with a compact snapshot, unfinished-test workflow and authorization gates.
- No merge, rebase, cherry-pick, code port, commit, push, source-code change,
  runtime action, analysis, database change or production action was performed.

### Preserved history

Original pre-consolidation files were copied to
`D:/pipeline/task-artifacts/airflow-test-branch-state-20260918`:

- `CURRENT_STATE.md`: 356710 bytes,
  SHA-256 `13C1EE3C6D5CB0D7323111FBAD9E58E6F88DB0C5D08FE2CD360BA64DE99BF60E`.
- `TASKS.md`: 204039 bytes,
  SHA-256 `C5FBA92467D1D692CFE5DBB6240D36FCFB2790023D74E3A1F3A3621FD59B049C`.
- `HANDOFF.md`: 857955 bytes,
  SHA-256 `80470E265EC9AB9CF2F1F3807AD0F433FC7190817CE713D29AE60954CCA39817`.

Git history and detailed release/design records remain available. Archived
historical instructions are evidence, not current authority.

### Modified files

- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `docs/TEST_BRANCH_SYNC_HOLD_20260918.md`

### Commands and validation

- `git fetch --prune origin`: passed; refreshed the branch inventory.
- `git rev-list --left-right --count origin/main...HEAD`: `13 23`.
- Per-worktree ancestry and unique-commit inspection: completed for inventory;
  no integration performed.
- Documentation reference checks passed for the environment boundary, CCE
  recovery spec and synchronization-hold record.
- `git diff --check`: passed with exit code 0.
- Archive SHA-256 values were recomputed and match the recorded originals.
- Stale instructions to integrate/port main into the test branch were searched
  across all four changed documents and were absent.
- The compact queue has 17 intentionally open validation, implementation,
  acceptance, future-promotion and hygiene items.

No backend, frontend, DAG or workflow test is claimed by this documentation-
only consolidation. No BS10610 live preflight was run because no runtime action
was requested.

### Next action

Execute `TEST-VALIDATION-01`: reconcile archived unchecked items with current
source and evidence, then produce the unfinished-test matrix. Do not synchronize
with `main` while building or executing that matrix.

### Risks and rollback

- The test branch is not promotion-ready merely because prior focused tests or
  deployments exist; evidence must match the final candidate source.
- Counts are tied to the recorded commits and may change after future fetches,
  but divergence is not itself a defect to repair.
- Restore the three archived state files or revert this documentation change to
  undo the consolidation. No runtime/data rollback is needed.

## 2026-09-18 selective main-fix port to the test branch

### Goal

Apply only the three fixes explicitly approved by the user—`e7f0373`,
`cb1c3fe` and `347e4ed`—without synchronizing the rest of main or overwriting
test-branch Native/Local/SGE work.

### Completed

- Registered the audited `wgs-4.2.1-ebf1f4b` rule-to-phase inventory while
  retaining Unknown behavior for unreviewed releases.
- Made file-ledger reconciliation wait for an unpublished receipt and ignore a
  self-consistent foreign project root without deleting imported history.
- Added authenticated run-detail sample fields only for participating Sample
  IDs; global sample/QC/workspace projections remain privacy-safe.
- Added whole-attempt exact Rule filter options and full phase choices. The
  test-branch adaptation combines summary/filter/attempt rows into one SQL
  query so the existing `<=8` query budget remains satisfied.
- Simplified WGS Overview/Samples/Ledger presentation, added searchable exact
  Sample/Family selection and removed the Files tab request. Existing Native
  execution views were preserved.
- Updated API/frontend contracts and the synchronization-hold record. Main-side
  release documents and state files were not copied.

### Validation

- Local: Python compile passed; phase policy JSON parsed; `git diff --check`
  passed.
- BS10610 isolated candidate:
  `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/three-fix-sync-20260918`.
- Backend focused tests: 28 passed, 1 dependency warning.
- Frontend changed-scope tests: 17 passed.
- Frontend `npm run build`: passed; generated
  `index-D2PoeP0p.js` and `index-D4g5ndFq.css` in the isolated build image.
- Full frontend suite: 133 passed, 1 failed. The same failure reproduces on the
  pre-port `f0b07c4` baseline in the same image: `starts stage one without
  accepting runtime configuration` times out finding `S1`. It is therefore a
  pre-existing test-branch blocker, not accepted as green.

### Runtime impact and rollback

No BS10610 service, database, workflow, gate or running analysis was changed;
BS96 was not contacted. Roll back by reverting this selective local port. The
isolated candidate directory and build image contain no runtime authorization.

## 2026-09-18 local repository hygiene pass

### Goal

Remove provably stale local worktree/branch clutter while preserving the
primary test branch and every uncommitted or unique change set.

### Completed

- Refreshed both local Git common repositories and fast-forwarded only their
  clean `main` checkouts to `1255a06`; the test branch remained at `f0b07c4`.
- Reduced registered worktrees from 20 to 10. Removed five clean merged
  worktrees with their branches and three clean unique worktrees while retaining
  those branches and creating recovery bundles.
- Deleted nine additional unattached local branches proven to be ancestors of
  `origin/main`. No remote branch was deleted.
- Patch-preserved and removed two state-doc-only dirty worktrees. The merged
  GATK logger branch was deleted; the unique T242 branch and bundle were kept.
- Moved six nonregistered legacy directories and nineteen loose packages from
  the worktree root to
  `D:/pipeline/task-artifacts/airflow-repo-hygiene-20260918`.
- Preserved all eight source/test-bearing dirty worktrees. The primary test worktree retained its
  original 27 modified/untracked paths before this documentation update.

### Validation

- Both `D:/pipeline/airflow-demo` and
  `D:/pipeline/airflow-demo-production` are clean on `main` at `1255a06`.
- The remaining worktree root contains only ten registered dirty worktrees and
  no loose archive files or nonregistered legacy directories.
- Recovery bundles were created for the three removed unique worktrees and
  hashed; see `docs/REPOSITORY_HYGIENE_20260918.md` and the archive manifest.
- T197's historical bundle passed `git bundle verify` as complete before its
  broken-link disk remnants were archived.
- No source test was run because this pass changed repository organization and
  documentation only. No runtime host was contacted.

### Remaining work

Content-triage the eight retained dirty worktrees. Compare each change set with
current main and the primary test branch, preserve a patch or bundle, and obtain
an explicit keep/archive/discard disposition before removing any dirty
worktree. Then resume `TEST-VALIDATION-01`.

### Recovery

The three unique branches remain local and have standalone bundles. Moved disk
remnants and packages can be restored from the task-artifact archive. Deleted
local merged branches are recoverable from `origin/main` or reflogs. No runtime
or data rollback is required.

## 2026-09-18 main/production lineage merge into test

### Goal

Establish the user-requested relationship in which current main and production
are ancestors of the primary test branch, while preserving all test-only
commits and Native/Local/SGE adaptations.

### Completed before merge verification

- Committed the three approved fix ports as `8f062f9`.
- Committed compact state and repository hygiene records as `91060d0`.
- Confirmed live remote refs `main` and `jiucheng/release/production` both point
  to `1255a06`; no second production merge is required.
- Merged `origin/main` with explicit conflict review. Duplicate three-fix
  conflicts retain the test SQL budget, Native status choices and CCE log
  archive UI. WGS prepare-recovery source/tests from `1255a06` are included.
- Combined test and production environment/runbook observations; compact test
  state remains the current queue.

### Verification and publication

- Merge commit: `e8ce35a`; pushed to
  `origin/jiucheng/test/wgs-local-main-sync-20260917`.
- `origin/main` and `origin/jiucheng/release/production` are both ancestors;
  each reports `0` commits absent from test and test reports `26` additional
  commits at the merge tip.
- BS10610 isolated source candidate:
  `candidates/lineage-sync-e8ce35a`; no service deployment or restart.
- Existing backend Docker image, network disabled and source mounted read-only:
  the exact three-fix plus prepare-recovery set passed `36` tests.
- A broader backend set passed `94` and failed `6`. All six failing node IDs
  fail identically on first-parent baseline `91060d0` in the same image, so
  they remain pre-existing test-branch contract drift rather than merge
  regressions.
- Existing frontend build image, network disabled and candidate copied to
  tmpfs: selected tests passed `32` and failed the already recorded
  `starts stage one...`/missing `S1` case. Production build passed and emitted
  `index-D2PoeP0p.js` plus `index-D4g5ndFq.css`.
- Local checks were limited to Python compilation, policy JSON parsing and
  `git diff --check`; no local dependency environment was created.

No runtime host, analysis, database or production deployment is authorized by
this Git-only merge.
