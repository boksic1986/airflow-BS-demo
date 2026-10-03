# WES 20260927B Step4 TTL failure: independent review

Reviewed 2026-09-29 11:45-11:57 UTC. This is a production read-only review,
not a repair, release approval or completed recovery.

## Scope and ownership

User assigned repair to thread `01a09e7e-a0c5-7c30-a06f-e002662b0289`
and asked the coordinator to compare its diagnosis and approach independently.
Run: `GATK_20260929_024231_F246CD-a1`, attempt1,43 samples, profile r4.
No changes to WGS batches, requests, receipts, code, Jobs, locks or databases
were made by this review. UE-03 development remains with its original owners.

## Independently observed evidence

- BS96 is server96/chenjc. Backend7ac6a8e6b412 and observer80f6d137f9ef still
  use `/data/airflow-WGS/downstream-stage-20260929-control/compose.json` and
  the recorded base/overlays, not the stale `current` symlink alone.
- node200 is t640/ctapa using id_rsa_ctapa. Its actual
  `/home/ctapa/.config/airflow-gatk/gatk_runtime_gate.py` is ctapa:bioinfo0700.
  `_step()` invokes the frozen shell entry directly; it does not select the
  paired downstream path present in newer source. No permission change needed.
- Native Step3 receipt is success at11:18:53Z,561/561 rules, and its receipt
  hash `e49656a9410e7f60049c55162f69c77c655e7cd99f7efe650c29106569afad00`
  is the actual Step4 predecessor hash. This is not a foreign predecessor.
- Airflow wait_step3_analysis succeeded11:19:11Z; start_step4_publish
  succeeded11:20:01Z. Native Step4 failed11:20:50Z, and wait_step4_publish
  failed11:21:07Z. Airflow final state failed11:21:16Z; downstream was not run.
- Exact error: `RuntimeError: Step4 requires a successful Master Job`.
  The Airflow task log and frozen native status agree.
- Original handoff binds Job `cce-master-f0db57be1ca1a60a6628`, UID
  `faecf4ae-562d-42f9-a449-18bf50b90c9c`, Pod UID
  `e9b7dddc-f75c-4208-8d17-b86499f6dbd1`, with START_CONFIRMED and matching
  input/config/manifest hashes. Frozen Master template TTL is100 seconds.

## Source-level cause and comparison with repair owner

Frozen source is beneath
`/sg2/50.ctapa/project/HWcloud/airflow-gatk/runtime/runs/GATK_20260929_024231_F246CD/attempt-1/cce/`.

`cce_batch_runtime.py:3047-3050` ordinary Step4 reads the live Job and requires
its Complete condition. `_kubectl_json` returns None for a successful empty
ignore-not-found GET; `_job_flags(None)` returns complete=false. Thus successful
TTL reclamation is indistinguishable from missing success at this boundary.
The repair owner separately observed the Job absent. Its TTL diagnosis agrees
with this independently inspected call chain and timing; the exact deletion
instant was not reconstructed by the coordinator.

This is a real lifecycle defect in the deployed generic path, not a display
bug or evidence that the biological analysis must be rerun. It is also not
fixed merely by changing Airflow task state or increasing retries.

## Two necessary conditions before approving the repair

1. **Refresh genuine terminal evidence, do not infer it.** The current mirror
   was sealed11:15:53Z and contains START_CONFIRMED, workflow-completion,
   analysis.log, an empty jobs.ndjson and an active1 Master snapshot. It has
   no RUN_COMPLETE.json. MIRROR_COMPLETE means snapshot completeness, not
   execution finality. `_recovery_native_success:1713-1755` already requires
   the exact handoff UID/attempt/hashes, valid START, RUN_COMPLETE and native
   preflight/analysis/final_dryrun exits. Simply passing the original UID into
   `_bound_downstream_master` will still fail without genuine terminal data.
   Repair must first collect the original run's persisted terminal, if present;
   neither the successful platform receipt,561/561 nor Job404 substitutes for it.
2. **Cover Step5's same dependency.** `step5:3251-3256` calls log download;
   ordinary `download_snakemake_logs:3185-3188` also requires a live terminal
   Master and rechecks it at3221-3223. The actual deployed GATK gate invokes
   that frozen script. Fixing Step4 alone would leave another TTL failure in
   Step5. Both should share the existing identity-validated downstream reader,
   retaining log/export verification. Native Step6 has no analogous direct
   live-Master gate in its inspected entry; this is not blanket Step6 acceptance.

The owner's latest stated approach agrees: do not blindly retry, obtain durable
original-Master proof, and continue only publish/download/materialization.
That direction is reasonable. Concrete implementation and genuine SFS terminal
availability are still pending; they are not approved/verified by this note.
Do not rebuild a Master, repeat prepare/upload/analysis, edit old hashes, relax
identity/locks, add unverified bypasses or extend TTL to hide this dependency.
Do not enable the new P0 for a historical attempt by fabricating registrations.

## Coordination and verification scope

The coordinator sent both findings and exact deployed code paths to the repair
owner; that owner explicitly confirmed the Step4/Step5 dependency in its latest
progress. Source/policy/deployment changes remain its scoped responsibility.
The unified executor plan already preserves durable TTL-safe downstream evidence;
this incident is an actual consumer-wiring example, not permission to expand
UE-03 or to claim source acceptance has upgraded this frozen GATK bundle.

Only existing authenticated GET APIs, frozen files and deployed gate source were
read. No synthetic tests, full-batch validation or clinical data reads were run.
One diagnostic log request returned HTTP200 text/plain; an initial JSON decoder
failed locally, then the same read was handled as text. This was not an Airflow
or pipeline fault. No service restart, deployment or rollback was necessary.

## Follow-up: current patch and permanent plan placement

User subsequently authorized a current-project patch. The same repair owner
reports SFS RUN_COMPLETE bound to original UID faecf4ae-562d-42f9-a449-18bf50b90c9c,
with preflight/analysis/final_dryrun exit0. This supersedes the earlier pending
SFS-proof status; the coordinator has not independently re-read that new proof
or accepted a finished patch/downstream outcome. The old mirror remains an
example of insufficient evidence, not a reason to recompute successful analysis.

The [shared plan](../superpowers/plans/2026-09-28-unified-stage-execution.md)
now assigns TTL-DOWNSTREAM to UE-04 (native verifier/ordinary consumers plus
actual gate binding), UE-05 (reuse for downstream-only recovery) and UE-06
(installed entry/patch replacement mapping). Current F246CD recovery remains
separate and scoped to attempt1/43samples; no new Master, upload or reanalysis.
UE-02 is not reopened; UE-03 inventory/probe continues without this extra scope.

## 2026-09-29 12:51Z in-progress implementation/scope review

User requested a check for drift and excessive development/testing. Inspected
the repair thread's current turn and its isolated worktree
`C:/Users/11217/.codex/worktrees/gatk-ttl-downstream/airflow-demo`, branch
`jiucheng/fix/gatk-ttl-downstream-20260929`, base9b381eb. This is a moving source
snapshot, not final implementation or production acceptance.

Observed progress: documentation plus a13-line gate routing change and29-line
gate assertion; new downstream test fixture is present, helper implementation
was not yet present. No completed GREEN or deployment/recovery was established
by the inspected snapshot. The main direction still preserves the frozen
attempt and successful computation, covering Step4 and Step5 rather than only
the first visible failure. No new API, DAG, schema or UE executor implementation
was found in this candidate.

Review feedback sent to owner:

1. **Test evidence must match its claim.** The new fixture writes a simplified
   fake `cce_batch_runtime.py`; its `_recovery_native_success` only reads JSON,
   and Step4/5 only record a call. A GREEN there establishes wrapper routing,
   not the real frozen native UID/hash/terminal validator or downstream logic.
   Reuse pinned real native code with mocked cloud I/O or clearly cite prior
   unchanged-validator acceptance; do not rebuild a second validator to satisfy
   the fake. No request to rerun the complete native suite.
2. **Trim duplicate scope, not required safety.** Four common error conditions
   are multiplied by both downstream stages. Shared negative validation can be
   proved once; both stages still need their positive wiring assertions. This
   is modest duplicate fixture scope, not evidence of a large redundant test
   campaign. One inspected command named a nonexistent test node, then the
   corrected command failed because the helper is absent. Those invocations do
   not prove a fixed defect. Do not repeat missing-helper RED after it is known.
3. **Preserve the real deployed baseline.** The chosen9b381eb gate differs from
   the local production ref by284 insertions/11 deletions, including paired
   integration. That alone does not prove an incorrect base: the live private
   GATK gate may intentionally be older. Requested the actual deployed hash and
   matching source, plus minimal-diff integration instead of replacing an
   unrelated newer gate wholesale. No production regression asserted yet.

Helper separation is reasonable only as a thin trusted bridge into the existing
frozen native verifier/functions, with a scoped evidence refresh when genuinely
missing. It must not become a new dispatcher, general recovery framework or
repeated reader-Job loop. Asked owner to explain exact reuse and expected file
scope while continuing the urgent repair; this review adds no extra approval
cycle or test matrix. Permanent shared repair remains UE-04.

Coordinator performed no tests, remote commands or production mutations during
this scope review. Runtime/doc ownership remains with the original repair agent.
