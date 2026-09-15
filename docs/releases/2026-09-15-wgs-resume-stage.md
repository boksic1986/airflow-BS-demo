# WGS resume_stage source implementation — 2026-09-15

## Scope and result

Base f241149 in the independent wgs-resume-stage-20260915 worktree/branch.
Implemented the operator API, durable same-attempt RunAction, frozen request
generation registration, bio_wgs recovery path, restricted runtime helper and
Run Detail action. ETA modules are separately owned and were not edited.
No push, main merge, deployment, production probe or real0911A recovery.

Frozen analysis/attempt/release/configuration/image/workdir are retained. Only
an actual stage retry reserves a new execution generation; downstream stages
register when dispatched. Repeated/uncertain actions reconcile their deterministic
DagRun before submission. Non-transient HTTP rejection is explicit and retained.
The original DagRun is retained in RunAction and cannot close/deactivate recovery
through its callback or lease cleanup. Current recovery failures remain visible.

Existing transfer checkpoints, materialization journals and successful outputs
are reused. Active executors are followed through their original lock/receipt.
Failed Master replacement uses exact UID/resourceVersion deletion and original
manifest low-level creation, followed by native payload/START handoff. No Step0,
prepare, forceall, OBS-empty prerequisite, workflow-core/pending edit or CCE upgrade.

## Test environment

Test only: BS10610 / server10610. Parent preflight confirmed control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS; current release
releases/20260912-opt-4d3d24e6; actual backend mount20260913-panel-1fb971b/backend:/app.
Scanner=false, auto dispatch=false, execution=true. No running service was changed.

Disposable source mount:
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/wgs-resume-stage-20260915/source`.
Baseline arrived by git archive f241149; only task delta was overlaid. All test
containers used --rm --pull=never --network none and candidate-only source mounts.
Images: backend:t235-232154f, airflow:bs-control-841eb55 and
frontend-builder:node22-lock-35420d5e3ec0, all under airflow-demo/.
No local runtime tests, downloads, full suite, test matrix or biological canary.

## Bounded RED/GREEN evidence

Exactly four backend, four runtime, two real-Airflow unittest cases and one UI
case; production build as compile check. Fixes reran only covering files.

RED baseline: backend4 failed for absent resume service after correcting the
fixture's required RunStageState.progress_source; runtime4 failed for absent
wgs_resume.py; real-Airflow2 failed for absent skip/retry behavior; UI import
failed for absent ResumeStagePanel. Setup failures below are not counted as RED.

Final covering commands (inside the above isolated containers):

```text
backend image, workdir /candidate/backend, PYTHONPATH=/candidate/backend:
python -m pytest -q --tb=short tests/test_wgs_resume_stage.py /candidate/scripts/tests/test_wgs_resume.py
8 passed in 1.08s

Airflow image, entrypoint /usr/local/bin/python, HOME=/home/airflow:
/candidate/tests/test_wgs_resume_stage.py
2 tests, OK

frontend builder, copy candidate frontend into disposable /app (cached node_modules):
npm test -- --run src/features/run-detail/ResumeStagePanel.test.tsx
1 passed (144ms)
npm run build
tsc -b and vite build passed;1851 modules; JS420.46kB / gzip122.58kB
```

Runtime dispatch case invokes the real gate.run_stage entry, with synthetic
transfer/step boundaries. Backend cases cover persistence/idempotency, uncertain
POST reconciliation, invalid/conflicting actions, old receipt/DagRun fencing and
actual recovery failure propagation. Native CCE/OBS are mocked; no real Job,
transfer or data mutation occurred. UI case covers explicit confirmation,
same-key retry and insecure-HTTP-compatible random key generation.

## Failures encountered and corrected

- Initial inferred candidate path lacked source directories; scp failed, Docker
  reported no tests. Parent created the explicit /source child and extracted the
  baseline. Empty automatically-created top-level directory was left untouched.
- SSH pre-session banner exchange through172.17.61.18 returned Connection aborted
  (exit255); parent reconnected. No task side effect occurred on failed sessions.
- Backend baseline fixture omitted required progress_source (4 setup errors).
  Corrected fixture, then observed the four intended missing-service failures.
- Plain python in cached Airflow selected the Snakemake venv and lacked Airflow.
  Used existing /usr/local/bin/python with HOME=/home/airflow; no installation.
- Initial GREEN persisted RunAction before mutating its JSON in place; three
  replay cases exposed missing generation. Replaced JSON object before assignment.
- UI fixture needed explicit jest-dom/vitest; build exposed that current stage
  belongs to RunProgressResponse.stage_code, not RunDetail. Corrected both.
- One tar overlay emitted a small host-clock skew warning; source extraction and
  validation succeeded. No environment clock or container configuration changed.

## Compatibility, limitations and handoff

Native source inspected:
`D:/pipeline/task-artifacts/wgs421-consistency/generated-cce/cce_batch_runtime.py`,
SHA2562371c52d675b675a70702a05104bdc923b4e60bcc995e03ca5b41118718fc3fa;
retained candidate profile0.8.4/source8f1db532. This is not evidence of the actual
0911A frozen bundle. The gate checks required native primitives before deletion.
Production compatibility, real worker-lock attachment, interrupted Kubernetes
handoff and actual resumed biology were not exercised; they require separately
approved environment validation. Unknown worker state or unverified replacement
identity blocks rather than deleting another workload.

Parent owns the combined static review and ETA integration. Deployment packaging
must install wgs_resume.py beside wgs_runtime_gate.py and include backend/DAG/UI
changes. Rollback source by reverting this task commit; future runtime rollback
uses recorded previous gate/release. Never delete retained evidence/output or
restart an active executor merely to roll back source.
