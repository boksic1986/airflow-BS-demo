# OPT20260912 — BS10610 deployment and acceptance ledger

Status: preparation only; candidate not deployed. Production is out of scope.

## Baseline

- Local development worktree: `D:/pipeline/airflow-demo-worktrees/development`, `jiucheng/development/next`, base `e107f3b22044034c329899efc94bb3fbe64e208d`.
- SSH `BS10610`, verified hostname `server10610`.
- Control root `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`.
- Current release `releases/20260912-gatk-81587fcb`.
- Compose contract: `docker-compose.wgs.yaml` plus `docker-compose.gatk.yaml`; retain both external test env files `env/bs10610.wgs.env` and `env/gatk-81587fcb.env`. Never print env values or rendered secret-bearing configuration.
- Gateway binds **172.17.106.10:12959**, not loopback. Read-only health request on this interface returned `{"status":"ok"}`. Loopback curl exit7 was the expected consequence of the interface-specific bind, not an outage.
- WGS scanner and automatic dispatch both disabled; no active test Airflow runs. Three existing GATK test records remain. These switches and records must be preserved.
- External CCE read-only observation found one active Master and 11 reserved Heavy leases in a complete inventory of25. Do not restart or alter this workload for a UI release.

Protected service IDs confirmed again before candidate deployment: Airflow worker `fdaf00067050`, scheduler `ba14b9433b2f`, API `9ba5b54ce74c`, Postgres `6cf33066b97a`, Redis `ae5b4e30caf0`, node probe `d77affe7a22d`. Affected candidates currently backend `8eca1592b509`, observer `add051b157d5`, frontend `e90c834e3fa6`, metrics collector `5629edc808c8` (only replace if resource collector code requires it).

The live `/data/airflow-demo` shared bind currently resolves into the predecessor release's `shared` directory. A new immutable source release must explicitly preserve this existing shared target; do not let relative Compose `./shared` silently create an empty independent runtime root. Unchanged Airflow services remain pinned to their existing source mounts.

## Planned activation boundary

After task reviews and pinned candidate acceptance, stage an immutable test source release; record commit, checksums, image provenance and predecessor. Render Compose quietly before changes. Recreate only affected backend, observer and frontend; preserve Airflow worker/scheduler/API, Postgres, Redis and unrelated collectors unless the final reviewed change demonstrably requires an affected collector replacement. No Master, work Pod, DAG submission or scan/dispatch change.

Node-owned test preparation and Heavy collection use `/home/ctapa/.config/airflow-wgs-test`, not the production private directory. Existing test runtime references its private operator config in place. Do not copy operator credentials into source, logs, Git or build context. Test-only project output is `/sg2/50.ctapa/project/HWcloud/WGS_test`; backend mount remains read-only, actual preparation is performed by ctapa on t640. Record prior gate hash and owner-only rollback sibling before atomic replacement.

Task1 requires explicit backend and restricted-gate test feature flags. Keep defaults disabled and never set these in production. Task3 requires an explicit test output location for Heavy snapshot. Billing remains `not_configured` until a dedicated BSS read-only identity is available; no reuse of regional Cloud Eye credentials.

Targeted read-only installed-source check on t640: nipttest distribution reports cce-pipeline0.8.4; `_batch_lock_name` hashes `identity.project/identity.batch` (SHA256 prefix20), not batch alone. Owner prepare likewise derives SFS/OBS suffix from project/batch. A distinct frozen test project namespace can isolate the lock without rewriting source batch columns; verify the final generated bundle scope before acceptance. This was source inspection only, not pipeline revalidation or execution.

### Pending exact permission approval

Task1 independent review found a shared-parent replacement race for owner preparation. Fresh `namei -l` on t640: `/sg2` root755; `/sg2/50.ctapa`, `project`, `HWcloud` ctapa755; only `WGS_test` ctapa:bioinfo2770. User has been asked whether to add sticky bit **only to this directory** (2770→3770), with no recursive operation or access expansion. No permission change has been performed. Implementation must fail closed on unsafe writable parents, and preserve private0700 descendants/no-follow/inode ownership. Synthetic tests can validate that mechanism; actual custom test entry remains disabled until this prerequisite and code review pass. Other panel features do not depend on this permission.

Additional read-only target probe: t640 nipttest uses glibc2.17 and `ctypes.CDLL(None)` does **not** export renameat2. Task1 must not rely solely on a newer libc symbol that passed in the cached backend container. Implementer notified to retain no-overwrite safety using a target-compatible mechanism; no system library or file was changed by the probe.

Task1 d5a4e1d resolves this with portable mkdir/flock and passed scoped review. Further read-only source check found shared WGS owner repository HEAD68f5dccee5ea6d7d8104d998118a69a5cb5ac4da, plus modified prepare/config.yaml. Both live prepare/config.yaml and cfg/config.template.yaml differ from the audited cc9bde3 pins. This is source/release drift, not authority to reset or rewrite the shared WGS repo. Custom test execution stays gated pending aligned owner release selection; independent panel monitoring updates may still be deployed. No owner source/config was changed.

## Browser access

Desktop direct gateway access timed out; server-side health succeeded. A temporary SSH tunnel bound only to `127.0.0.1:22959` forwards to the existing gateway through BS10610. Browser reached the normal sign-in page; existing-account login requested from the user. No firewall or published port changed. Close the temporary tunnel at task completion unless still needed for the user's acceptance.

## Acceptance still required

- Task1/2/3 scoped reviews and integration review.
- Exact candidate targeted backend, gate and UI tests plus cached frontend production build.
- Feature environment rejection, synthetic isolated project preparation, API contracts and no source/pending changes.
- Fresh preflight container IDs/mounts, filesystem authority, gate hashes and active workload inventory.
- Post-deploy health, observed API/UI version, submit rail/options, rule filters, QC provenance, estimated progress and partial Heavy metrics.
- Browser desktop/narrow layout and refresh state; do not submit real analysis from the browser.
- Compare protected container IDs and scan/dispatch switches with baseline.
- Record rollback commands and final known limitations without deleting data.
