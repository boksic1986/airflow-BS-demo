# Development ownership boundaries

Every agent reads `docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md` before remote
work and records whether its target is test or production.

- Coordinator: scope, sequencing, integration, and state documents.
- Backend: registry, adapters, APIs, business database, evidence projection.
- Airflow: DAG structure, target dispatch, task terminal projection.
- Workflow: Snakemake, CCE/local runners, execution profiles, receipts and rule evidence.
- Frontend: registry-driven pages and API consumption.
- Infrastructure: offline images, Compose, remote paths, permissions, image retention and release validation.
- QA: isolated tests, migration checks, and acceptance evidence.

Workflow-specific code belongs to its adapter/runtime owner. Shared platform code must not acquire pipeline-name branches during integration.

## Current cross-repository routing snapshot (2026-10-03)

The canonical priority/status index is [`docs/36_CROSS_REPO_DEVELOPMENT_BACKLOG.md`](36_CROSS_REPO_DEVELOPMENT_BACKLOG.md). Its rankings are advisory; they do not assign work, authorize remote access, or authorize release. This routing update supersedes the 2026-10-02 A468E9 monitoring assignment: 323D3F/a1 Step1–6 is complete and automatic monitoring is stopped.

| Owner area | Known thread | Scope and handoff boundary |
|---|---|---|
| Coordinator | `019fa8d1-0d81-7e92-abee-8154dd1cf0a7` | Sets order/scope, assigns one owner per card, resolves cross-repo dependencies and reviews integration; no implied production write authority. |
| Backlog/status documentation | `01a0b254-07b5-7352-99aa-871b117459ad` | Maintains the authorized status snapshot and task routing only; source repositories remain authoritative for technical contracts. |
| Airflow | `01a0e728-4c99-71d0-87e9-987b311022c9` | Platform backend/frontend/DAG integration owner and the sole product Git writer for the completed `GIT-AF-3TARGET-20261003`. Its verified scope was ordinary main/production/test Git synchronization and bounded worktree/branch cleanup; exact results are in the latest state/ledger. It is not monitoring an active run; no new development, runtime recovery or deployment is part of this Git task. |
| WGS pipeline | `01a09149-ad9d-7e92-b98a-16d9cae075e2` | WGS pipeline source work and candidate design; confirm each task's authorization before implementation. |
| WGS cloud/native runtime | `019f9d79-be3f-7701-af33-3595d72bbfac` | CCE/native source and convergence evidence; owner reports normal main push/readback at `96278362dae9fc412a87906f267efd13ec2c80c1`, without a runtime install/deployment. Verify current installed receipts before making runtime drift claims. |
| Frontend, QA, Infrastructure | No fixed thread verified in this snapshot | Coordinator assigns a single owner for each accepted task; do not infer ownership from role labels alone. |

### Status reporting and recovery

- A status snapshot records observation date, source HEAD, evidence links and explicit unknowns. A planning-document commit is not a source-repository or runtime update.
- Report only material progress, failure, drift, a required user decision, or completion; remain quiet for unchanged healthy state when the relevant monitor asks for quiet operation.
- After compaction or handoff, read the latest `CURRENT_STATE.md`, `TASKS.md`, `HANDOFF.md`, this routing document, backlog index and release-boundary document before acting. Re-establish the active task, exact run/attempt, environment and permissions from evidence; do not replay completed actions.
- Historical unchecked items remain unverified until their current owner checks the relevant source/version. Do not create parallel cards or treat a priority suggestion as authorization.
- Preserve historical records. When evidence establishes that an old card is superseded, mark it `superseded` and link the current card; if evidence conflicts or is insufficient, ask the coordinator and original owner to adjudicate. Never reopen work based only on age or an unchecked checkbox.

### Minimal material-status report

For a material change, blocker, drift, user decision or completion, the technical owner sends a concise update to both the authorized documentation owner (`01a0b254-07b5-7352-99aa-871b117459ad`) and coordinator (`019fa8d1-0d81-7e92-abee-8154dd1cf0a7`):

1. Task/card ID and accountable technical owner.
2. Repository, worktree, branch and exact source commit (or runtime release identity).
3. Implementation, acceptance and deployment states separately.
4. Material delta since the prior report.
5. Exact evidence/links and remaining unverified checks.
6. Blocker, next step, and the person/role whose decision is needed.
7. Observation timestamp/time zone and whether the status is a snapshot or live read.

The documentation owner updates/routes status only; it does not approve code, acceptance, remote operations or deployment. Source owners retain technical contracts and release evidence in their authoritative repositories. Revalidate host, branch/release, mounts, active-run identity and gates immediately before remote/runtime operations; documentation-only work requires no remote preflight.
