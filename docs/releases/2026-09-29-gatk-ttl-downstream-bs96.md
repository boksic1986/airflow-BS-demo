# GATK terminal-Master TTL downstream repair — 2026-09-29

This is the scoped production record for WES/GATK batch `20260927B`,
analysis `GATK_20260929_024231_F246CD`, attempt 1. It records the
isolated test, node release and same-DagRun recovery evidence.

## Cause and source

Step3 completed, then Step4 failed with
`Step4 requires a successful Master Job`. The frozen Master manifest specified
`ttlSecondsAfterFinished: 100`.
The original Master UID was `faecf4ae-562d-42f9-a449-18bf50b90c9c`;
its exact Job/Pod were absent at preflight. The TTL deletion event was not
observed, so absence is not treated as proof of success. Native SFS evidence
for this UID existed, but the old local mirror had not imported it.

The source for mainline integration is `5945f26` plus `22e5535` on
`jiucheng/fix/gatk-ttl-downstream-main`, based on main `613b095`. The installed
node200 private gate was patched from its existing version by `4870e2b` plus
`eb1b8aa`; the installed helper has the same hash as the mainline candidate.
The update preserves
paired `stage_command` precedence; only unpaired Step4/5 uses the bounded
helper, which verifies the frozen request/UID, both run-label inventories,
batch-lock ownership and native terminal evidence before the original stage.
No Master replacement, biological analysis rerun, TTL change or generic GATK
resume activation is included.

## Verification and production boundary

- BS10610 `server10610`: the old gate's two-file synthetic check passed 45
  cases; the current-main TTL subset passed 21. The final kubectl complete
  JSON bytes regression yielded 2 expected RED failures, then 5 GREEN cases
  with 17 deselected. No test was rerun for the documentation update.
- `ssh BS96` is `server96`, control root `/data/airflow-WGS`; node200 is
  `t640`, and the private GATK gate runs under `ctapa`. Production release
  affected only files in `/home/ctapa/.config/airflow-gatk`. Server96's
  actual control remained `/data/airflow-WGS/downstream-stage-20260929-control/compose.json`;
  backend `7ac6a8e6b412`, observer `80f6d137f9ef` and worker mounts were
  unchanged. No service restarted or new server96 release directory was
  installed; the historical `current` symlink is not used as release proof.
- Prior gate SHA-256 began `b3230de8`; its backup is
  `/home/ctapa/.config/airflow-gatk/gatk_runtime_gate.py.pre-ttl-downstream-20260929`
  (mode 0700). Installed `gatk_runtime_gate.py` SHA-256 is
  `cb0903e262b3b80a2b56f43a883906bf95ce0ca4e4c9b463ef63d261a81edd9c`;
  adjacent `gatk_ttl_downstream.py` SHA-256 is
  `cfe0a5266342ca5275f46aa62cd9a33a73aea294687f8eef625780a7f51f96a4`.
  Both installed files are mode 0700. No directory permissions were changed.
- Scanner and auto-dispatch settings were preserved by this file-only release.
  The last documented 2026-09-28 observation was scanner enabled, dispatch
  disabled; this release did not recheck those settings.

## Exact attempt continuation

Both run-label Job/Pod inventories were zero, and the batch lock belonged to
the original run. The historical run has no `publish_deadline`; generic GATK
resume capability is disabled in production. Airflow 2.9.3 API dry-run for
the exact original `dag_run_id` selected 10 Step4-and-downstream task
instances. The exact clear returned HTTP 200. Step1–3 were not selected or
rerun; no new analysis, attempt or Master was created.

The temporary read-only reader verified native `RUN_COMPLETE` as `SUCCEEDED`
for the original UID, three exit codes 0, a matching `START_CONFIRMED` UID,
present `workflow-completion`, and absent `RUN_FAILED`. The temporary reader
left no Job/Pod. Step4 generation 2 succeeded at
2026-09-29T14:39:35Z; its receipt hash is
`c72a693c827bc66a51eb01998acd2cb3e69148b65d71dca08c712482fd4ea5a3`.
`wait_step4_publish` succeeded. At this checkpoint Step5 awaited the result
transfer slot and Step6 had not started. Final delivery and whole-batch
success remain unverified.

## Limits, next check and rollback

The documentation check used `git diff --check` and verified both release-note
links, task ID and receipt references. No runtime test or deployment was
repeated solely for documentation. Observe the original DagRun's Step5/6,
terminal receipt and delivered artifacts before marking the task complete.
If a downstream stage fails, collect its exact receipt/log and preserve the
original identity; do not restart Step1–3 or enable generic resume.

Rollback is only after confirming no active downstream stage. Restore the
exact backed-up private gate and remove only this added helper. Do not reset
the Airflow task history or delete local project, runtime evidence, SFS,
OBS or cloud resources. No broader data snapshot or recovery guarantee is
asserted by this file-level backup.
