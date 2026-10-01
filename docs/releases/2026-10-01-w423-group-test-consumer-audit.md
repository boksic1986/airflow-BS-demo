# W423 Group TEST candidate and native consumer audit

## Scope and status

The direct user instruction in coordinator turn
`01a0f647-a247-7201-8388-afd5f65d7902` supersedes the earlier W42303/04 plan:
publish the already merged WGS4.2.3, native0.8.9 and two Master candidates for
TEST Group rule display. Prepare/FQ synthesis, QC2, delivery actions, new CRAM
layout and production release are deferred. No previous batch is resumed,
resubmitted or deleted by this task.

Airflow source branch: `jiucheng/airflow/W423-test-group-release-20261001`.
Its source integration base is
`827dc56004ddf7857644499c85835ded8ae93a85`, containing the accepted UE merge,
exact WGS/GATK phase registrations and the late Step4 receipt fence. Main's
GATK TTL helper is retained. The one prepare test added before scope changed
is preserved on `jiucheng/airflow/W423-prepare-deferred-20261001`, commit
`08e4cbc`; it was neither uploaded nor run in this release candidate.

This record is a candidate handoff, **not installation or TEST activation**.
The coordinator has asked the user to choose whether the explicitly requested
shared nipttest installation can instead use a TEST private prefix. No answer
is inferred from elapsed time. Airflow has not installed either option.

## Source delta and consumer checks

`RunWorkflowTab.tsx` displays the existing `execution_group` beside each real
rule instance. The cell shows the group suffix and exposes the full origin
identity in its title. Existing per-rule status/start/end remain authoritative.
A planned/accepted member with group-only timing and no recorded start says
`Awaiting rule start`. Group inventory does not manufacture rule rows or member
timestamps. No backend projection, API schema or producer protocol is added.

Two synthetic WGS/GATK tests append events to a task-only JSONL stream, ingest
through the existing bound pipeline observer, persist rule state, and read the
authenticated Rules API. They check group-only waiting, early unnamed starts
joined to their own later stream/job declaration, duplicate event idempotence,
separate success/failure times and failure messages. SQLite's naive UTC
serialization is normalized only in the assertion; the API is unchanged.

## Fresh environment observations

BS10610 was verified as `server10610`, `chenjc` UID/GID `6708:520`.
Control root is `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`;
`current` remains `releases/20260912-opt-4d3d24e6`. Actual backend mounts use
`20260926-p0-e358aad/backend`, with image
`sha256:8491604ee01d9b3a84d74e7edf233a9d5dd20ddbf14f8a646c25c05f8729efed`.
Current symlink identity does not replace inspection of actual mounts.
Scanner and automatic submission are false. TEST business run/transfer and
Airflow DagRun/TaskInstance active counts were zero at preflight; this does not
prove that the shared NFS environment has no production consumers.

Approved node200 route was verified as literal IP `172.17.61.200`, hostname
`t640`, account `ctapa` UID/GID `6801:520`, through NGS with the ctapa key.
NGS itself is node005. The unresolved alias `node200` was not repeatedly retried.
No BS96 connection or production business action was performed.

## Actual 0.8.8 to 0.8.9 impact

Native owner evidence `package-upgrade-impact.json`, SHA-256
`08d9394d86177c5f2ad76821ac784a5d59bf874166dac284b6f6ab7a07d0ff80`, compares
rollback0.8.8/417de59 to final0.8.9/1f5e1e0: four modified files
(`__init__.py`, `_build_commit.py`, `assets/cce_batch_runtime.py`,
`assets/cce_writer_guard.py`), one added `stage_execution.py`, 25 unchanged and
zero removed. The earlier 29 unchanged comparison was accepted717 to final1f5,
not 0.8.8 to 0.8.9. An unchanged console name does not establish isolation.

### Production WGS: traced paths use private package and assets

Effective `/home/ctapa/.config/airflow-wgs/runtime.env` selects private0.8.8
`PYTHONPATH` and console below
`/sg2/50.ctapa/project/HWcloud/airflow-wgs/runtime/tools/cce-pipeline/0.8.8`.
Its active paired bootstrap SHA-256
`0c57ea26f94f80209c33fa2ec5385662df7a338a52dd158b129e23971e46ffc7` selects
the separate `0.8.8-step3-57483541a968/site-packages/cce_pipeline/assets`
runtime and guard, SHA-256 respectively:

- `88aedf570b1ceadbe92dc838c707493f41eb16415109ecfb3ea6f750767b81c4`;
- `106297299d7316060c120dad2ec8673793bb5eadfc8a3bafb8432930a68c677c`.

The paired operator interpreter is still nipttest. Read-only import resolution
using that interpreter plus the effective private `PYTHONPATH` resolves
`cce_pipeline` and `shared_permissions` to private0.8.8. The traced WGS
gate/prepare/paired imports and version checks therefore do not consume the
shared changed package files. This is a bounded path conclusion, not a claim
that every production/NFS consumer is isolated.

### Production GATK: frozen assets retain a shared transitive import

Current `/home/ctapa/.config/airflow-gatk/gatk_runtime_gate.py` SHA-256 is
`cb0903e262b3b80a2b56f43a883906bf95ce0ca4e4c9b463ef63d261a81edd9c`;
TTL helper SHA-256 is
`cfe0a5266342ca5275f46aa62cd9a33a73aea294687f8eef625780a7f51f96a4`.
Its declared interpreter is nipttest with no `PYTHONPATH` override.

The latest inspected frozen bundle is
`/sg2/50.ctapa/project/HWcloud/airflow-gatk/runtime/runs/GATK_20260929_024231_F246CD/attempt-1/cce`.
Its copied runtime/guard retain SHA-256 `e46744a6...`/`10629729...` regardless
of a shared pip replacement. However, `cce_delivery.py`, SHA-256
`da3dbbfff9c9382a92e4c78abf17679bb960920b55a3fa15ae7d2a326337c72c`,
line24 first imports `cce_pipeline.shared_permissions`; line29 uses the sibling
`cce_shared_permissions` only on `ModuleNotFoundError`.

Actual resolution under this declared interpreter/environment reaches
`/sg2/33.chenjiucheng/software/miniforge3/envs/nipttest/lib/python3.9/site-packages/cce_pipeline/__init__.py`
(SHA-256 `bf7ad320df5d639f11574d121e45988bf5e0fde360dfcbdfa578f046225cf827`)
and `shared_permissions.py` (SHA-256
`942d3da7bfa794dff6d5c566873a5bd164a1b7615f75f7bad20608cab1769755`).
The former contains `__version__ = "0.8.8"`; permissions is unchanged in the
approved upgrade. Thus a subsequent frozen process would import modified
package metadata0.8.9. An already imported process does not automatically
refresh Python modules. There is no evidence that this frozen path imports
new `stage_execution` or replaces its runtime/guard. This is **not evidence
that GATK would fail**, nor evidence of full isolation.

The latest actual prepare request SHA-256
`6a7917c0a40938e330157d923aafae98fd22d6859a18ce03906888344694db66`
instead binds `/bi/software/mamba/envs/WGS/bin/cce-pipeline`. Its console
SHA-256 `42520fbef3f5f8b98205b6424e59f38f442250ce3559ceb44c9e66cd47eb5bac`
uses WGS Python and resolves package0.8.8/source
`095f1e937d8cb5815c62435f4875a88921d7afe3` under WGS Python3.11. That prepare
binding does not select nipttest. Its seven recorded stage statuses were
success; no conclusion about all production active consumers follows.

### TEST: existing package, version and writer pins must be paired

WGS TEST bootstrap `/home/ctapa/.config/airflow-wgs-test/cce-paired-deployment-v1.json`
SHA-256 `a16ecf15e92155e7d881dbf656b04d8df2da52e8f28816ea3840eb1ab7317eff`
selects nipttest runtime/guard, console and Python. Current shared runtime is
`e46744a61176610a2ee13147a0a777f89f1e0a1c3d5868c511e8d6e050e28fe9` and
guard is `10629729...`; old policy pins `f45c50ab...`/`63a704e7...` already
differ. Restoring old configuration bytes alone is not a proven working pairing.

GATK TEST prepare request SHA-256
`4e3b1a8bb2f9159f6604536882ffd6040e3a6403b94f223ac0ab3990ce32c99f`
selects nipttest console. Existing prepare helper SHA-256
`d71c45854b61abac84185a7410fc9209324c52c5f6765196646a41f543a745f4`
executes that console's `--version` (accepting0.8.x) and `prepare`.
The console imports `.cli`, which reads changed `__init__`; later prepare
would render the new runtime/guard assets. Existing frozen bundle bytes remain
unchanged. No inspected existing entry imports newly added `stage_execution`.

Minimal proposal, awaiting the user's choice: native owner installs the complete
approved0.8.9 package at one TEST private prefix using existing nipttest Python;
Airflow then explicitly pairs both TEST consumers, console/import environment,
runtime/guard trust paths, bootstrap/policy and release/profile bindings.
Shared0.8.8 and production remain untouched. A shared overwrite instead needs
an explicit decision about the proven production GATK metadata exposure and
TEST pairing; no production migration is performed to manufacture isolation.

## Verification and evidence limits

All runtime tests used isolated BS10610 containers with task-only scratch and
existing cached dependencies; no package manager or dependency installation.
Evidence root:
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/w423-platform-827dc56-20261001`.
Local mirror is this worktree's `.codex-artifacts/w423-integration-20261001`.

| Check | Observed result |
| --- | --- |
| New Group UI case against old component | expected missing-Group RED; `group-ui-red-v3.log` |
| New Group UI case against changed component | 1 passed, 8 skipped; `group-ui-green-v2.log` |
| WGS/GATK synthetic ingest to Rules API | 2 passed; `group-api-green.log` |
| Affected `RunWorkflowTab.test.tsx` file | 9 passed; `group-ui-final.log` |
| TypeScript `tsc -p ... --noEmit --incremental false` | exit0 before build; same log |
| Actual application Vite build | exit0; `group-build-browser.log` |
| Browser actual component with exported API frames | 6 states, 2 real rows each, independent start/end/status/message; no console errors |

Browser DOM evidence: `group-browser-frames.json`. Key screenshots:
`group-browser-wgs-waiting.jpg` and `group-browser-gatk-terminal.jpg`.
The fixture uses epoch seconds1–5 deliberately; these are synthetic timestamps
and do not measure real CCE duration. Browser harness is separate from deployed
services and was closed/stopped after evidence capture.

Reuse accepted producer reports `master-rule-status-20260929/ACCEPTANCE_REPORT.md`
and `wgs422-group-logger-smoke-20260930/REPORT.md`. The available files named
canary-worker/master-events were Kubernetes EventLists, not the full accepted
Snakemake JSONL stream. This run proves synthetic persisted consumption/API/UI;
it does not prove a replay of complete real producer events, GATK real CCE Group
acceptance or the new paired deployment. No UE/P0/Worker suite or CCE canary
was repeated.

Harness failures were diagnosed before correction: missing jsdom environment,
read-only Vite temporary directory, wrong shell positional argument, SQLite UTC
fixture assertion, missing builder `index.html` mount, node200 Python3.6 ASCII
read/capture_output incompatibility, and PowerShell interpolation in the first
temporary-server stop command. Those failures are not product RED evidence.
The stop command was rerun as literal stdin Bash. No production or data deletion
resulted. Raw failure logs remain in task evidence.

## TEST pairing inventory, stop gates and rollback

Owner/approver separation is unchanged: WGS owner builds both Master images and
new WGS/GATK profiles/resources; native owner installs the one complete package;
Airflow owns TEST catalog/consumer/bootstrap/policy/gate/platform pairing after
coordinator review and the required user choice.

- Native: source `1f5e1e0d7d7095ab43b14f514aafe623f4f89ca3`, wheel
  `f843cfa7766169bb7e5485b2af99ffbe933aac9ae7e667056aa3223da62c098d`.
- Coordinator-confirmed pushed WGS Master:
  `swr.cn-east-3.myhuaweicloud.com/biosanwgs/wgs-cce-master@sha256:e48125333a8a4343921eed4a63dd3346d80a981b33ba7e5090136ef3da94f941`.
- Coordinator-confirmed pushed GATK Master:
  `swr.cn-east-3.myhuaweicloud.com/biosanwgs/wgs-cce-master@sha256:a4f8d15e728b9e9c4f56d4b7cea320cef57998b32ae59875d286b9d975f6be1d`.
- Actual old WGS TEST catalog SHA-256 is `6801b8a8...`; selected release
  `wgs-4.2.2-3b1dae5`, profile `wgs-4.2.2-r2.yaml`, old Master `3d180a9f...`.
  Catalog profile digest `c98b13c6...` differs from actual file `cccb04c5...`.
  Create and verify an independent new candidate binding; do not rewrite the
  old profile/catalog to hide drift.
- Actual old GATK TEST profile is the9/17 repository's `profiles/cce-pipeline/gatk.yaml`,
  SHA-256 `62265f84...`, selected Master `ee93eaf2...`.
  New GATK Master uses accepted direct base `1a923...`; its dependency difference
  from old active `ee93` is an existing P0 pairing delta, not byte-identical base.
- Pending: approved install target and console/import route; final new profiles,
  resource digest and exact WGS4.2.3 release identity/rule inventory; final Airflow
  source commit; matching new writer/platform hashes and required release pins.

Before any future switch, capture each actual TEST Compose/config/mount and
private gate/env/bootstrap/policy byte set, verify old/current pins honestly,
and refresh active-use counts. A private TEST installation can be reverted by
restoring those exact TEST selectors/mounts without overwriting shared0.8.8;
preserve the new candidate and all evidence. No rollback is asserted GREEN
until the restored pairing is verified. The already retained rollback0.8.8
wheel alone does not establish compatibility of historically drifted TEST pins.
