# Pod-exit evidence race: production private-script release

User explicitly approved committing only the Pod-exit race fix, syncing main and
production, pushing, then deploying. Code commit: `17708001a7080e6879221bddf01338a4728bb4f5`.
Both remote main and `jiucheng/release/production` were atomically pushed to that
commit before installation. Prior uncommitted `gatk_resume.py` compatibility and
its tests/operational notes were excluded, not discarded or deployed.

## Exact scope and actual invocation

Production server96 control root remains `/data/airflow-WGS`; historical current
still resolves to `releases/20260912-panel-opt-4d3d24e6`. Actual backend/observer
mount `releases/20260915-ui-93069eb/backend`; WGS DAG remains platform-f69c577 and
GATK DAG remains recovery-0436dce. These services were not upgraded in this release.

The restricted runtime invoked by this deployment executes as ctapa on node200
(`t640`), reached through NGS/node005 as a jump only. Private forced-command
wrappers select their adjacent runtime gates; both gates select adjacent
`wgs_evidence_bridge.py`. Three files replaced atomically at 2026-09-16T02:48:40Z:

| Installed path under `/home/ctapa/.config/` | Mode | SHA-256 |
| --- | --- | --- |
| airflow-gatk/gatk_runtime_gate.py | 0700 | e67f461c721344005205477929e62969ade064f054231d033596cd63de8d9f29 |
| airflow-gatk/wgs_evidence_bridge.py | 0644 | 9bf5ad6a47074caab187eedca1137fa8b81f32df525dca83cb082774b5f362ac |
| airflow-wgs/wgs_evidence_bridge.py | 0600 | e69fb62d55f4b669be5f70749bad5bf1dff5cee901162dbcbc3ad9fe6086a42f |

Owner/group ctapa:bioinfo and private directory modes0700 preserved. GATK files
exactly match the commit. The older WGS bridge (blob61fcbfa) lacks generic GATK
label support; only the two race-fix hunks were applied to it, retaining all other
production behavior. Its patched blob is ba4c8bb68cd39a7aa56ddb5723c7e50f58427da0.
WGS runtime gate, wrapper/environment files, CCE, images and workflow were untouched.

## Verification and continuity

- BS10610 prior targeted RED:10 failed/6 passed; GREEN:48 passed in1.30s.
- Production staging: patch applicability and one AST syntax check for3 scripts
  using the configured nipttest Python. No workflow execution or regression suite.
- Guarded all3 original hashes before replacement; installed files matched their
  staged candidates with cmp. Original permissions preserved.
- All12 server96 Airflow project container IDs unchanged before/after; gateway
  `/api/health` returned200. No service, Master or monitoring-process restart.
- No task-state/attempt/generation edits, 0914A rerun, data deletion, DB access,
  latency-wait180 change or unrelated UI rollout. Existing Python processes are
  not hot-reloaded; gate changes apply on their next normal invocation. New bridge
  subprocesses consume the installed fix.

## Rollback

Node200 private release root:
`/home/ctapa/.config/airflow-monitor-pod-exit-1770800`.
Original files are under `rollback/gatk/{gatk_runtime_gate.py,wgs_evidence_bridge.py}`
and `rollback/wgs/wgs_evidence_bridge.py`. Restore these exact files via adjacent
temporary files and atomic rename, preserving original modes. Do not restart or
reset tasks, delete outputs, change release symlinks or roll back application DBs.
Source archive, exact bridge patch and staged files remain in this private root.

Only the release record is added after deployment; no additional code change.
