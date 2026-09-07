# T206 WGS Step2/Step3 Dry-Run and Heavy Slot Design

## Goal

Validate the disabled WGS contract-v2 control plane through Step2 Master and
Step3 monitoring without executing a real WGS analysis or allowing Step4-6 to
start. Independently validate the fixed 25 Worker Pod Heavy Slot quota with
no-compute Lease contenders.

## Scope and safety boundary

- BS10610 test control plane only; production `.96` is out of scope.
- One synthetic trio: three samples and six small paired FASTQ files.
- `bio_wgs`, scanner, auto-dispatch and all runtime gates remain disabled by
  default. Test gates are enabled only for the bounded validation window.
- The dry-run path must not create analysis Worker Pods, publish results,
  download results or materialize results.
- Evidence is written under the task-specific WGS evidence root, never `/tmp`.
- OBS objects, Kubernetes Jobs and test files are cleaned only by exact ID or
  exact prefix after terminal evidence is captured.

## Contracts

### Airflow validation scope

`params.validation_scope=step3_dryrun` is an admin-only hidden scope. It is
accepted only when contract v2 and `WGS_STEP3_DRYRUN_CANARY_ENABLED` are both
true. It follows the normal path through Step1, Step2 and Step3. A branch after
`wait_step3_analysis` sends it to `finalize_step3_dryrun`; all Step4-6 tasks are
skipped.

The finalizer succeeds only when the current Step3 generation has an exact
successful receipt and terminal evidence identifies the bound Master Job,
namespace, UID/resourceVersion and dry-run execution mode.

### CCE workflow execution mode

The generic batch workflow gains `execution_mode: analysis|dry_run`, defaulting
to `analysis` for backwards compatibility. In `dry_run` mode the Master:

1. materializes the run-local config;
2. invokes the analysis target with Snakemake `--dry-run --nolock`;
3. does not run the normal analysis command and does not require production
   completion artifacts;
4. writes logger-compatible dry-run evidence and a terminal marker containing
   `execution_mode=dry_run`.

The mode is frozen into `BATCH_RUNTIME.yaml`; it cannot be supplied by the
browser or changed after Step2 submission.

### Heavy Slot probe

The quota remains 25 named `wgs-heavy-io-NN` Kubernetes Lease objects in
`snakemake-ns`. A repo-owned validation command creates 26 unique no-compute
holders using the same compare-and-swap Lease semantics as the executor. The
acceptance result is exactly 25 acquired and one waiting. Cleanup releases only
the holders created by the validation run and never deletes the Lease objects.

## User-visible result

The run is terminal success with `validation_result=step3_dryrun_complete`.
Run Detail shows Step1, Step2 and Step3 as successful and Step4-6 as skipped.
It also shows the bound Master and the captured dry-run evidence. This path is
not exposed in the ordinary Submit UI.

