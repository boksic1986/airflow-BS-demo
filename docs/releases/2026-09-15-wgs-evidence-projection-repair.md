# WGS evidence projection repair (source only; not deployed)

## Authority and scope

Latest user instruction authorizes Git synchronization of prior repairs into
main and production, superseding the earlier commit wait for0911A/0912D.
Production deployment still needs separate approval. No service/analysis restart,
Airflow clear, prepare/pending
change, Master/CCE image change, or direct production DB operation is included.

Independent worktree: `D:/pipeline/airflow-demo-worktrees/wgs-evidence-repair-20260915`,
branch `jiucheng/fix/wgs-evidence-20260915`, base `0860412`. Earlier unpublished
changes already in that base are separately documented and included by the latest
Git synchronization request. This record is not authority to deploy the branch.

## Targeted changes

- Legacy Step1/5 status ingestion validates the exact registered request and
  worker analysis/attempt/stage, request SHA256, PID/boot/process-start identity
  and timezone-aware launch timestamp. A launch strictly after the old failed
  stage, with a subsequent status heartbeat, can reopen the same attempt even
  when the retained legacy gate reports retry_no=0. This reads recorded launch
  evidence; it does not claim that a process is still alive.
- Reopening resets stage/transfer start to that launch time and clears old end
  fields, including when the transfer heartbeat was already imported. A completed
  restart can reconcile without a running poll. Success stays monotonic; old
  heartbeat/cross-attempt/invalid worker evidence cannot authorize recovery.
  Progress alone cannot bypass terminal stage state. No runtime receipt is edited.
- Explicitly register `wgs-4.2.1-34bfcbf` against the existing phase policy.
  Fixed server Git 2.49.0 on BS/node005 resolves it to
  `34bfcbf82238af684d005314360c9c9739377351`. `git diff cc9bde3 34bfcbf -- rule
  WGS_pipe.smk WGS_cloud.smk` is empty; `git ls-tree -r` gives the same 14 blob
  IDs as the packaged policy sources. This is audited equivalence, not a latest
  release or prefix fallback. Other unknown releases/rules remain Unknown.
- RunWorkflowTab reuses RuleInstanceTable for a full-width expanded group
  inventory, with unknown status/time when the inventory provides names/job IDs
  only. No sibling sample or timing inference, extra API call, or CSS overlay.
  Main Job column omits opaque master origin; closed diagnostic details retain it.

## Current-run evidence boundary

One read-only BS96 check confirmed server96, backend container8388a8e8b600 and
backend mount `/data/airflow-WGS/releases/20260914-gatk-recovery-0436dce/backend`;
current remains the historical panel-opt4d3d24e6 symlink. Scan=true/auto=false.
0911A attempt2 was running. `/rules?attempt=2&limit=50&offset=0` returned total44
and44 items:23 group-marked rows, zero nonempty execution_group_members arrays.
Mapping/Dedup showed group_only timing. This covers the response's complete set
at that instant, not future events. It proves the current API lacks inventory;
it does not independently prove every producer/raw stream lacks that evidence.
The UI fix cannot create missing inventory or child start times. No Master restart
or producer rollout is authorized to populate it.

## Verification

BS10610/server10610 uid6708 bioinfo+docker; existing current opt4d3d24e6,
backend mount panel1fb971b; scan=false/auto=false. Active service mounts were
inspected, not changed. Test-only candidate root:
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/wgs-evidence-20260915`.
All test containers use `--network none --pull never`, no service credentials or
runtime/result mounts. Backend image `airflow-demo/backend:t235-232154f`, candidate
backend read-only at /work, explicit workdir/PYTHONPATH. Frontend uses cached
`airflow-demo/frontend-build-test:node22-lock-35420d5e3ec0`, its existing node_modules.

RED: restart suite14 failed against unchanged source; phase suite1 failed/4passed;
UI2 failed/9passed for missing common inventory table and exposed origin.
Initial GREEN: restart14 + existing observer58 =72 passed; phase/monitor/timing/shared
transfer/transfer projection/estimate suite42 passed; RunWorkflowTab11 passed.
Independent review then caught a regression: stage timestamp gating incorrectly
blocked older matching-terminal file enrichment/lease release. Strengthened the
existing regression with a real RunStageState and observed failure; restored only
the matching-terminal progress path, retaining its aggregate checks. Added one
malformed-worker JSON negative case (RED before dict validation). Final combined
backend suite115 passed in14.82s, including these changes. Reviewer rechecked the
diff read-only and reported no remaining P1/P2. UI code unchanged after11pass/build.
TypeScript/Vite production build passed1852modules, JS index-CJCGiVTD.js and
unchanged CSS index-CdK5PwQa.css. Existing Starlette/AnyIO deprecation warning is
not introduced by this diff. Local git diff --check passed (not runtime testing).

Commands: `python -m pytest -q -p no:cacheprovider` with the named test files;
`npm test -- --run src/features/run-detail/RunWorkflowTab.test.tsx`; `npm run build`.
Backend combined green tests used unique `/evidence` basetemp directories in
the isolated candidate; initial RED tests used ephemeral container pytest tmp.
One scp pre-session reset left old source on the test host, so that test invocation
was a second RED run, not a failed candidate. Re-upload succeeded and local/remote
SHA256 matched before GREEN. Tar source-clock warnings (~14 seconds) do not form
runtime timestamp evidence. No Docker Hub access or biological workflow test.
The final remote hash read also hit a pre-session SSH reset; retried read-only.

## Remaining / rollback

Independent code review and its targeted correction are complete. No live browser visual
acceptance or production acceptance claimed. Missing current group inventory is
explicitly unresolved; do not backfill made-up members/statuses. Git integration
is now explicitly authorized. Before separately approved production deployment,
recheck exact mounts and publish only reviewed changes; backend/
observer source and frontend are separate services. Rollback source only, retain
all receipts, history, pending, leases and analysis data.
