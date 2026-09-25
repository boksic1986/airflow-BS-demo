# P0 validation dev3 candidates — not installed

## Current execution authority

User has approved the replacement four-step sequence in
`../superpowers/plans/2026-09-25-wgs422-p0-test-release.md` and asked to start.
R1 publishes refreshed WGS4.2.2 assets; R2 then installs the compatible wheel
in nipttest and pushes the WGS Master; R3 installs a candidate profile; R4
integrates and activates the paired test consumers. Thus the older "integrate
first / writes held" notes below describe previous preflight, not a renewed
approval requirement. Paired recovery remains inactive until R4. GATK remains
deferred. Read R2_READY.md for current readonly preparation; no install/push
receipt has been delivered yet. Test781877e already has ae416fa-equivalent
Step7 source via255be59, so it must be preserved, not cherry-picked twice.

## WGS-only continuation approved (subsequent user decision)

Latest preflight outcome: no writes. Existing test backendae416fa lacks the
P0 recovery APIs, while a direct replacement byfdace86 would regress current
Step7 maintenance and transfer-queue fixes (verified source diff, common
ancestor1da45f3). Existing WGS DAG mounts are also pre-P0. Resolve the test-release
integration first; neither wheel-only installation nor whole-source rollback
is accepted. GATK testing remains deferred, not a prerequisite. A shared backend
containing dormant GATK code does not by itself constitute a GATK rollout.

User defers GATK/WES testing and approves the WGS test-entry/candidate-runtime
paired deployment and minimum recovery verification. This supersedes the
GATK-consumer prerequisite and pending-scope approval below for WGS only; it
does not assert installation success. Original native/Infra owner is dispatched
to refresh WGS consumer/mount/active-use/rollback facts and execute within the
existing test scope. No GATK rollout, production, new service/Compose project,
biological run, live replacement/TTL retest or automatic enablement. Necessary
GATK helper imports in a shared module are code dependencies, not GATK activation.
Common-runtime verification must not be reported as WES deployment acceptance.
Actual results are pending the owner's WGS_ONLY_ROLLOUT_RECEIPT.md.

Corrected platform source: `fdace86db2f25a2c3bf25ecef2c6947d5fba7d27`.
Native functional source: `ae90b654b0fa297c5102b2f696990ed75b0b4d74`.
Build source: `45323e4e956728bd2f4117e00e978c344b9f1bec`, a version-only child
on `jiucheng/release/p0-validation-20260925`, version `0.8.5+p02.dev3`.
Unchanged plugin source/version: `5ffcb07`, `0.6.4+bs8.dev2`.

## Verified offline evidence

Original native/Infra owner built one wheel and two Master candidates offline.
Coordinator read the actual logs/provenance and matched nine delivered file
hashes, without rebuilding or rerunning tests.

- Wheel SHA256: `004348233d18815ac8763eb38e07e67e22f5b7a0281ec65dbe36c8310cb4ec45`.
- WGS local image ID: `sha256:05888c3ac82e1a9b149c2bbd42788d227269787d5042c1af3287daa6d16be367`.
- GATK local image ID: `sha256:b5b3c38536d12f66cdcac3eb6a5b9e006de73b9a2331976136fe99a4cfbe8758`.
- Both smoke logs match the exact changed runtime/guard asset hashes, unchanged
  plugin and Snakemake `9.24.0+biosan1`.
- Actual-wheel log says **3 passed, 1 skipped**, not four passed. The skipped
  monitor module imports the plugin-backed final fixture, which skips when its
  pinned Worker producer source is absent from that wheel-only environment.
  This is not counted as artifact verification; source acceptance separately
  records111 affected tests plus packaged asset identity. No repeat TTL/whole-
  workflow test was performed.

These image IDs are local config digests, not published SWR manifest digests.
Raw local evidence:
`D:/pipeline/task-artifacts/p0-final-native-ops-20260925/p0-validation-dev3`.
Build log hash: `913592d4f75ad6ec2f1e8df6ae87dff070a9b648f52f715ef6b0e21233318224`.

## Actual test entry and remaining deployment gate

Node200 is `t640`, execution identity ctapa6801:520. Its existing private WGS
test root is `/home/ctapa/.config/airflow-wgs-test` (0700); private runtime.env
is0600. These are private configuration/code, not shared output directories.
The current WGS gate does not import paired runtime and no paired module is
present. WGS_PYTHON selects the agreed shared nipttest Python3.9. A test request
root under `/sg2/biodevrwsg2/33.chenjiucheng/WGS_test` was confirmed present.
The earlier assumption that Airflow release/scripts is the actual gate was wrong.

One read-only probe failed on the host's old Python `str.removeprefix`; only
that local probe was made compatible and the same bounded check completed.
No remote Python upgrade, permission workaround or production-root inspection.

Installation cannot be represented as only a wheel replacement. Before writes:

1. Freeze the actual test gate/module dependency closure, including the
   `wgs_resume` and `gatk_resume` imports of paired recovery. The initial proposed
   eight-file list is not sufficient proof of a complete runtime deployment.
2. Confirm which existing WGS/GATK test entry and service release consumes each
   pin. WGS-root inspection alone does not prove a GATK test entry. Do not point
   any bootstrap to a guessed common mount or production private root.
3. Confirm the bounded test-service update/restart scope with the user, capture
   exact package/config/release rollback and keep automatic recovery/dispatch off.

Owner has statically corrected the proposal to include both resume modules and
the release-runtime dependency. GATK must not be installed into the WGS private
root merely because its own consumer is unconfirmed. Existing Airflow service
mount/release targets are still unconfirmed; no container recreation is approved
by this proposal. Earlier PLAN_V2 execution paths are superseded historical notes.

No wheel installation, SWR push, service switch/restart, test/production gate
write, authorized_keys/forced-command change, database or clinical-data mutation
has occurred. Owner is preparing only the proposed deployment list; it is not
an authorization to execute a broader rollout. No new environment exploration
or runtime tests are requested for this handoff.
