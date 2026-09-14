# REL-01 WGS SSH reconnect (not deployed)

## Scope

WGS node200 dispatch only: a single registration retains its attempt, execution
and generation while allowlisted pre-session SSH failures reconnect at5s/10s.
Request-visibility retries retain their own budget and cannot reset the two
reconnect allowance. No blanket255 retry or automatic Airflow task retry.
Nonempty stdout or unknown stderr fails closed. Ambiguous outcomes use the
existing bounded exact-generation terminal-status query, then fail without
replaying the remote command, even if a process may still be running.
This does not implement general reconnect-to-running-workflow recovery.

No prepare_wgs_batch.py, local96/97 execution, GATK, pending, API/schema or
node gate modifications. Local timezone is separate REL-02 work.

## Verification

Target test BS10610, hostname server10610, userchenjc. Verified actual worker
mounts under releases/20260912-gatk-81587fcb and historical current opt4d3d24e6.
Isolated candidate (not active service source):
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/rel01-20260915.
Real cached Airflow image airflow-demo/airflow:bs-control-841eb55;
docker run --rm --network none --pull never, candidate read-only, entrypoint
/usr/local/bin/python, PYTHONDONTWRITEBYTECODE=1.

RED: test_wgs_ssh_retry.py ran4 tests,3 expected failures: single invocation
instead of reconnect/success/bounded combined budget. GREEN final:
`python -m unittest discover -s /work/dags/tests -p 'test*py'` ran36 tests, OK.
Includes existing31 WGS DAG tests and5 new retry tests, real Airflow import.
Existing negative-path tests log expected backend-unavailable warnings;
network-none prevents external calls. No new dependency or full analysis tests.
Final uploaded DAG SHA256 matches local:
18365194d5d1724ab5e3e8a3d2318c51632d750d9664e2f4ea4eff9a5175e8d7.

Initial SSH preflight failed with jump-host reset; later final file uploads
failed with pre-session abort. No workflow ran. Reconnected, resent exact files,
verified hash and reran final suite. Unknown SSH diagnostic variants intentionally
fail closed; this patch does not claim every SSH255 is recoverable.

## Publication gate and rollback

No production deployment or active service restart performed. Current user
request authorizes implementation; explicit production rollout approval and a
fresh active-task/mount check are required. Another task reports cloud0911A and
0912D running; do not restart/clear their tasks to load this fix. No analysis or
pending mutation is part of the rollout. Future deployment must update the
actual WGS DAG mounts in all Airflow services and verify imported code, not just
change a current symlink. Preserve original DAG/task retry counts.

Rollback the code commit or restore the recorded prior DAG source using a safe
service-specific rollout. Never delete outputs, reset generations or clear
successful work as a rollback. Planning/cleanup working notes are excluded from
the narrowly staged implementation commit.
