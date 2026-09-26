# P0 normal-analysis integration audit — 2026-09-26

## Scope and verdict

User requested an independent code audit, preserving the original analysis
workflow. This review did not activate P0, run a batch, alter a database, deploy
services, or change workflow code. Local work was read-only source inspection
and documentation editing; no local runtime tests were run.

Reviewed sources:

- Platform test integration `b17e1b6` (functional source `954045a`).
- Native cce-pipeline `dcc1698` / 0.8.6 (functional source `ae90b65`).
- Kubernetes plugin `5ffcb07` / `0.6.4+bs8.dev2`; inspected checkout `4f10c27`
  differs from that source only in two documentation files.

**Not ready to enable as a complete normal-analysis/recovery integration.**
Artifact publication and isolated component tests do not establish a usable
new-batch Step1–6 path. The current source has a deterministic initial-binding
gap. This verdict supersedes any interpretation of historical Task4/Task6 source
acceptance as end-to-end rollout acceptance; it does not invalidate the tests
that actually passed.

## A1 — Missing production registration before Step1 (blocking)

`cce_writer_guard.py:527–552` consumes a unique trusted binding for the exact
bundle and contract/input hashes. With activation present and no row, it raises
`protected CLI requires an exact trusted frozen bundle binding`.
`cce_batch_runtime.py:3341–3344` invokes this consumer before Step1 upload.

The inspected production platform/native sources contain consumers, not a
producer for this policy row. The similarly named WGS evidence bindings and
`cce_master_binding` receipt are different contracts; neither writes the policy
registration. `scripts/tests/test_p02_registered_recovery.py:64–65` supplies it
as a fixture. Installing a policy with an empty `bindings` list is not a working
new-batch integration.

Required correction: register the frozen attempt through the existing trusted
prepare/launch path before its first protected operation. No human pause or
manual per-batch policy editing may be added to normal submission.

## A2 — Initial lock action depends on a future Step2 ID (blocking)

The temporal dependency is inconsistent:

1. Step1 enters `ProtectedWriter.enter`, claims the directory lock, then uploads
   (`cce_writer_guard.py:495–520`; native Step1 decorator at 2215).
2. Airflow registers a stage when that stage executes
   (`dags/bio_wgs.py:231–273`). The backend first validates its successful
   predecessor, then generates a new random execution ID
   (`backend/app/wgs_stage_execution_service.py:67–73`).
3. Initial Step2 requires the pre-existing policy context to have generation 1
   and `action == Step2.execution_id`
   (`scripts/cce_paired_runtime.py:366–375`). The native derived view also sets
   that same action (`cce_batch_runtime.py:979–988`).
4. Merely changing policy action after Step1 cannot transfer the existing lock:
   same-generation different-action ownership is rejected by the directory CAS
   (`cce_batch_runtime.py:357–368`).

Therefore a producer inserted only immediately before Step2 is insufficient.
The initial lifecycle owner must be available before Step1, independently of the
later Step2 request ID. Keep the authenticated Step2 request identity separately
for handoff/receipt verification. Do not pre-register an executable Step2 before
its predecessor succeeds or introduce a manual stop after upload.

## A3 — Ordinary CLI does not resolve the platform's current owner (compatibility gap)

Even assuming an initial fixture-like registration is supplied, platform
`submit_registered` binds the Master UID to the directory owner
(`scripts/cce_paired_runtime.py:428–439`). Recovery later advances generation.
Platform monitor/downstream code reconstructs that owner from its selected
native journal (`:651–659`, `:1217–1224`).

Ordinary native CLI Step3/4/5/6 instead reloads the static policy context
(`cce_batch_runtime.py:3341–3361`; `cce_writer_guard.py:546–550`). It does not
reconstruct the selected Master/current owner. An initial row with empty UID
then disagrees with the bound owner, so its protected claim is rejected; after
replacement its generation is stale as well. A read-only `step3-status` is also
wrapped in a claim. Its log-only variant is a different path.

This is not a finding that the platform downstream path has the same defect;
that path explicitly reconstructs the owner. It is a limit on the claimed
CLI/platform compatibility. Correct the existing owner-resolution path; do not
allow blind lock replacement or rewrite frozen analysis inputs. If concurrent
CLI writes are disallowed, retain that exclusion, but do not label stale static
ownership as a usable sequential CLI continuation mechanism.

## A4 — New TTL plus legacy downstream is not transparent compatibility

The new native Master template sets `ttlSecondsAfterFinished: 100`
(`assets/05-master-job.yaml:13`); the plugin's generated Worker Job also has TTL
100 (`snakemake_executor_plugin_kubernetes/__init__.py:767`).

With no paired bootstrap, `selected_runtime()` and `stage_command()` return
None (`scripts/cce_paired_runtime.py:172–205`) and use the legacy path. Native
Step4 without a selected Master still requires a live successful Job
(`cce_batch_runtime.py:2843–2846`); Step5 log collection likewise requires a
live terminal Job (`:2979–2984`). Once TTL removes the Master, those calls reject
even if the analysis succeeded and durable evidence exists.

Thus absent activation preserves legacy *routing*, not necessarily compatibility
with newly generated TTL-enabled bundles. This is a conditional code-path risk,
not a claim that a current production batch has suffered it. The paired selected
downstream path already supports a missing Job when bound native success exists
(`:2796–2817`). Do not enable the new profile alone as a workaround. Either finish
the paired normal path or provide equivalent validated evidence resolution in
the existing native path, within the original release design.

## What exists and should be retained

- The DAG still starts Master execution at Step2, monitors at Step3, then
  publishes/downloads/materializes. No normal manual pause after Step2 is needed.
- Derived Master views retain the frozen config and payload bytes; their changes
  concern execution identity/manifest metadata, not biological rule selection
  (`cce_batch_runtime.py:1016–1057`). This is not proof that an analysis was run.
- Registered monitoring/downstream propagate the exact selected Master; missing
  Jobs can be accepted with matching durable native success. Step6 performs
  existing materialization and then conditional lifecycle release
  (`scripts/cce_paired_runtime.py:1007–1074`). These paths exist, but this review
  did not execute them end-to-end.
- Automatic recovery remains bounded by a frozen original deadline and two
  reservations (`backend/app/cce_recovery_budget.py:20`, `reserve_compute_recovery`).
  Pure executor submission/control failures require complete bound evidence;
  mixed rule errors and missing evidence do not authorize automatic replacement
  (`scripts/cce_recovery_failure.py:31–81`). `BackoffLimitExceeded` alone is not
  a sufficient recovery reason. This is an intentional boundary, not blanket
  coverage for every failed Master.

## Verification gap and smallest next acceptance

`scripts/tests/test_p02_selected_monitor.py:38–69` creates the initial policy row
with the already-known Step2 ID and clears the locks before testing submission.
It does not exercise the preceding real Step1 owner and backend-generated Step2
identity. Those successful component tests cannot refute A1/A2. The documented
13 R4 tests concern integration/version binding, not a normal cloud run.

After scoped source fixes, extend the existing synthetic harness, without a new
test framework or a full-suite repeat:

1. One normal new-attempt path using the real registration boundary: prepare
   registration -> Step1 lock -> generated Step2 ID -> confirmed Master ->
   Step3 -> Step4/5/6. Include Master TTL disappearance before downstream, no
   hand-written policy adjustment between stages.
2. One recovery path preserving the same attempt/config/output directory:
   interrupted observation -> approved replacement/current-owner reconstruction
   -> downstream completion. Include a stale CLI/owner refusal and a legitimate
   current-owner read/continuation assertion in the same fixture.

Run only the affected cases on BS10610 after its required preflight. No tests
were run during this static audit; no fresh deployment status is claimed.
Native wheel/Master packaging remains with its existing owner after the exact
source correction is accepted, not a coordinator-side ad hoc rebuild.
