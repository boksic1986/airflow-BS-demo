# Multi-repository development, release, and data governance design

## Status

This design records the user-approved direction for the airflow-demo control
plane, the independent WGS, cce-pipeline, and GATK repositories, and the two
currently test-oriented BS environments. It is a design contract only. It does
not authorize a deployment, workflow run, data deletion, or production gate
change.

The implementation is intentionally split into two governance domains:

1. Git, version, worktree, pull-request, test, and release governance.
2. Data classification, retention, and operator-authorized batch cleanup.

The domains may share environment and release identity, but they use separate
skills because source integration and destructive data operations have
different failure modes.

## Problem statement

The control plane, WGS workflow, cce-pipeline runtime, and GATK workflow are
developed and tested independently. Re-running each repository's internal test
suite from airflow-demo creates duplicated work without proving additional
compatibility. At the same time, the repositories do not yet share one
machine-readable record of the exact versions and contracts accepted together.

The current safety documents also protect selected paths and operations, but do
not define a complete data classification or a practical rule for removing old
test data. Step7 remains failure-prone. Until it is stable, the user needs to be
able to authorize cleanup of one exact batch without a second approval ceremony.

## Goals

- Keep each repository independently versioned and independently tested.
- Make airflow-demo the integration and release-coordination repository.
- Pin accepted component commits and contract versions in one release BOM.
- Use short-lived task branches and isolated worktrees from current `main`.
- Replace blanket repeated testing with change-impact and contract testing.
- Keep source, original, reference, and final project data non-deletable.
- Permit user-authorized cleanup of one exact test batch while Step7 is unstable.
- Remove old, proven test data without treating unknown data as disposable.
- Keep all cleanup bounded to the named environment and batch.

## Non-goals

- Combining the four repositories into a monorepo.
- Giving all repositories one shared version number.
- Adding a permanent `develop` or `test` branch.
- Making cce-pipeline version metadata an Airflow runtime gate.
- Enabling automatic age-based deletion in the first implementation.
- Treating a test-purpose environment as permission to delete source data.
- Replacing workflow-owned biological validation with control-plane tests.

## Authority and environment model

The authority order remains:

1. The user's explicit instruction for the current task.
2. Live read-only target-host preflight.
3. Stable repository contracts.
4. Dated state and handoff evidence.

BS10610 is the integration-test environment. BS96 is currently a
production-shaped test environment. The names and paths remain distinct even
while both are used for testing. A future declaration that BS96 carries formal
production service must be a separate policy change; it must not be inferred
from the hostname, release directory, or an old dated document.

Data sensitivity is independent from environment role. Original FASTQ,
references, workflow source, and final project results remain protected even
when they are mounted into a test environment.

## Repository ownership

| Repository | Owns | Does not delegate to airflow-demo |
| --- | --- | --- |
| airflow-demo | Control plane, registry/adapters, Airflow orchestration, API/UI, integration BOM and release coordination | Internal WGS/GATK biological behavior or cce-pipeline internals |
| WGS | Workflow rules, configuration, biological outputs and workflow-side evidence production | Control-plane API/UI behavior |
| cce-pipeline | CCE execution, transfers, runtime receipts and execution evidence | Workflow correctness or control-plane projection |
| GATK | GATK workflow, configuration and result contracts | Generic platform behavior |

Every repository proves its own implementation. Cross-repository acceptance
proves only the versioned interface between producer and consumer.

## Git branch and worktree contract

`main` is the only long-lived integration branch. There is no long-lived test
branch. A task begins from freshly fetched `origin/main` and uses one branch and
one worktree:

```text
jiucheng/<owner>/T<task-id>-<short-slug>
```

Examples:

```text
jiucheng/platform/T250-release-bom
jiucheng/workflow/T251-wgs-contract-v3
jiucheng/runtime/T252-cce-receipt-v3
jiucheng/docs/T253-data-cleanup-policy
```

An existing task fix may append `-fix2` or a descriptive suffix. Do not create
parallel branches that claim the same task ID and contract files without an
explicit coordinator split.

The standard local sequence is:

1. Fetch and prune remote refs.
2. Verify the proposed task branch and worktree path are absent.
3. Create the worktree directly from `origin/main`.
4. Record baseline commit, branch, repository remote, and dirty state.
5. Work only in the task worktree.
6. Remove the worktree only after merge and after proving it is clean.

Dirty, stale, or unrelated worktrees are never reset to make room for a new
task. They are preserved and reconciled separately.

## Pull-request and merge contract

All changes enter `main` through a pull request. Direct feature commits to
`main`, force pushes, and retagging accepted releases are prohibited.

A pull request records:

- task ID and scope;
- baseline and head commits;
- repository or repositories affected;
- contract/schema versions changed or explicitly unchanged;
- exact tests selected by the impact matrix;
- tests intentionally not repeated and the upstream evidence reused;
- target environment, if any;
- data and execution effects;
- rollback or forward-fix path.

Task pull requests use squash merge so the PR title becomes the durable mainline
change. The branch is deleted after merge. Release coordination does not require
a merge commit; the immutable tag and BOM identify the accepted source.

## Version and release contract

Components keep independent versions:

- airflow-demo platform: CalVer, for example `platform-v2026.09.0`;
- WGS: workflow SemVer, for example `wgs-v4.2.0`;
- cce-pipeline: package SemVer, for example `v0.8.3`;
- GATK integration: its own release identifier tied to the accepted source.

Release candidates use immutable annotated tags such as
`platform-v2026.09.0-rc.1`. A failed candidate is followed by `rc.2`; an old tag
is never moved. The final `platform-v2026.09.0` tag points to the exact commit
accepted in the final candidate. `main` alone does not mean deployed.

The release directory includes date, platform version, and source prefix:

```text
20260910-platform-v2026.09.0-<sha7>
```

BS10610 validates the candidate source using its approved preloaded bases.
BS96 builds from the same exact source commit using its own approved local bases.
Environment-specific image IDs and digests are recorded separately; no
source-specific image needs to transit through fengxian.

## Integration BOM

airflow-demo owns a machine-readable `config/integration_release.yaml`. The BOM
records, at minimum:

```yaml
schema_version: 1
platform:
  version: platform-v2026.09.0-rc.1
  source_commit: <40-hex>
components:
  wgs:
    version: 4.2.0
    source_commit: <40-hex>
    request_schema: wgs-runtime.request.v3
    rule_event_schema: "1"
  cce_pipeline:
    version: 0.8.3
    source_commit: <40-hex>
    receipt_schema: <versioned-schema>
    enforcement: audit-only
  gatk:
    version: 7.6.0
    source_commit: <40-hex>
    enabled_environments: [BS10610]
validation:
  environment: BS10610
  evidence_key: <privacy-safe-key>
```

The BOM does not contain credentials, unrestricted paths, patient identifiers,
or clinical payloads. cce-pipeline version and resolved image/profile data may
be recorded for provenance without becoming a duplicate Airflow compatibility
gate. Workflow prepare remains responsible for runtime compatibility.

## Contract and information sharing

Each producer repository publishes versioned, privacy-safe fixtures for the
interfaces it owns. Consumers test against those frozen fixtures:

- WGS publishes request, rule-event, QC, result, and terminal-evidence fixtures.
- cce-pipeline publishes request, receipt, transfer-progress, and failure fixtures.
- GATK publishes submission and result/evidence fixtures.
- airflow-demo publishes generic adapter, API, projection, and UI contracts.

Breaking a schema requires a new schema version and coordinated consumer PR.
Internal code changes that leave the published fixture unchanged do not trigger
another repository's full suite.

## Test impact model

Testing is selected by ownership and changed contract rather than by habit.

| Change | Required evidence | Explicitly not repeated |
| --- | --- | --- |
| Documentation only | links, task IDs, manifest, secret scan, diff check | backend/frontend/workflow suites |
| airflow-demo backend | focused backend tests and affected adapter contracts | WGS rules and cce-pipeline internals |
| airflow-demo frontend | affected Vitest, TypeScript, production build | workflow and CCE execution suites |
| Airflow DAG | DAG unit/import/contract checks | biological output validation |
| WGS internal rule | WGS-owned tests, dry-run, output contract | full airflow-demo suite |
| cce-pipeline internal change | package tests and bounded runtime canary | WGS biological tests and frontend suite |
| GATK internal change | GATK-owned tests and result contract | WGS and cce-pipeline suites |
| Cross-repository schema change | producer and consumer contract tests | unrelated repository suites |
| Release candidate | one BOM-pinned BS10610 integration smoke | repeating every component's development TDD |
| BS96 activation | environment fingerprint, migration/config, health and bounded smoke | development-time full suites |

TDD remains appropriate for new logic and bug reproduction in the owning
repository. It is not required for documentation-only changes, version/BOM
updates, deployment evidence, or choreography that adds no logic. Full suites
run at repository merge or selected release gates, not at every intermediate
task checkpoint.

## Data classification

| Class | Examples | Default action |
| --- | --- | --- |
| P0 protected source | Original FASTQ, reference data, workflow source, shared databases, credentials | Never delete through an agent cleanup task |
| P1 retained project data | Final project results, approved reports/QC, business history, retained evidence | Preserve unless a separate explicit scope names the exact class and target |
| P2 batch-owned generated data | SFS analysis/linkage, run intermediates, checkpoints, terminal CCE resources | Eligible for exact batch cleanup after user instruction and active-work checks |
| P3 disposable test data | Synthetic workdirs, canary objects, test DB rows, test releases and test images | Eligible for task- or batch-scoped cleanup |
| P4 unknown | Data without trustworthy owner, batch, environment, or source classification | Treat as protected until classified |

A path being located on BS10610 or BS96 does not make it disposable. A real
FASTQ used by a test remains P0. A test cleanup may unlink a generated symlink,
but must never follow it to its source.

## Operator-authorized batch cleanup

Until Step7 is stable, the user may authorize cleanup with a direct instruction
that identifies an environment and a batch, analysis, or run. That instruction
is sufficient authorization for the default batch scope; no second confirmation,
manifest hash, quarantine delay, or retention wait is required.

The default meaning of `delete batch X` is:

- delete the Step7-defined SFS analysis/linkage scope for batch X;
- delete batch-owned runtime intermediates, checkpoints, and failed residue;
- delete terminal CCE resources owned only by that batch when applicable;
- preserve OBS objects, database rows, Airflow history, retained evidence, and
  final project results unless the instruction names those classes explicitly.

An instruction that explicitly includes OBS may delete only exact batch-owned
test/canary objects. It never authorizes bucket deletion, a shared prefix, raw
FASTQ backup, or another batch. Database and Airflow-history cleanup likewise
requires those classes to be named in the instruction.

Manual cleanup may bypass Step7's run-success and Step5/Step6 business gates
when the target is test data and Step7 itself is broken. It may not bypass the
identity, path, ownership, or active-work checks below.

## Minimum pre-delete checks

These checks are execution safeguards, not another approval round:

1. The live hostname matches the named environment.
2. The batch/run identity resolves uniquely.
3. No matching Airflow task, Snakemake Master, CCE Job/Pod, transfer process, or
   lease is active.
4. Every path is absolute and below the configured generated/test/runtime root.
5. No target is a mountpoint, source root, reference root, workflow source,
   final project result, database volume, or another batch.
6. Symlinks are inspected with link metadata and only the link itself is
   eligible; cleanup never follows its target.
7. OBS cleanup uses exact object keys owned by the batch, never a bucket or
   unconstrained prefix.

If these checks pass, the authorized cleanup proceeds in the same task. If an
identity is ambiguous, a workload is active, or a target escapes its approved
root, the operation stops and reports the conflict.

Broad destructive commands remain prohibited, including unbounded `rm -rf`,
`find ... -delete`, `rsync --delete`, recursive OBS removal, bucket deletion,
`kubectl delete namespace`, `kubectl delete all`, Docker volume/system prune,
and `docker compose down -v`.

## Old test data

Old test data is cleaned in batches rather than by an unreviewed age glob:

1. Inventory recognizable test batches and report privacy-safe batch IDs,
   environment, size, terminal state, and last update.
2. The user selects all or a subset for deletion.
3. Apply the minimum pre-delete checks and delete the selected batches without
   a second approval.
4. Record deleted item counts, released bytes, and intentionally retained data.

Unknown or mixed-ownership directories remain P4 until classified. A future
retention mode may use configurable defaults such as 7 days for successful
synthetic data, 30 days for failed diagnostics, and 90 days for release evidence,
but automatic retention deletion is outside the first implementation.

## Cleanup records

Cleanup writes a concise post-operation receipt to a location outside the
deleted target. It includes environment, hostname, user instruction summary,
batch/run identity, target classes, deleted counts/bytes, retained classes,
active-work checks, command result, and timestamp. It excludes credentials,
patient fields, raw object URIs, and unrestricted source paths.

The corresponding `HANDOFF.md` entry records the receipt key and whether OBS,
database, Airflow history, and final project results were preserved or
explicitly included.

## Skills

Two repository-owned skills are required.

### `ngs-release-governance`

Triggers on branch, worktree, PR, merge, version, release, promotion, and
cross-repository integration work. It:

- identifies repository ownership and changed contracts;
- creates or validates the task worktree;
- selects tests from the impact matrix;
- validates the BOM and immutable versions;
- prepares the PR/release checklist;
- stops before BS96 activation without explicit task authority.

### `ngs-data-lifecycle-safety`

Triggers on delete, cleanup, prune, retention, reset, Step7, SFS, OBS, database
history, or old test data. It supports:

- `operator-batch-cleanup`: direct user instruction authorizes one exact batch;
- `retention-cleanup`: future policy-driven cleanup, disabled initially;
- read-only inventory when the user has not authorized deletion.

The skill applies the minimum checks without adding another confirmation round.
It reads environment roots from stable contracts and never hard-codes a current
release, credential, or patient-bearing value.

## Planned repository changes

After this design is reviewed, implementation should be split into small PRs:

1. Add `docs/35_MULTI_REPO_DEVELOPMENT_AND_RELEASE.md`, the integration BOM
   schema/example, PR template, and `ngs-release-governance` skill.
2. Add `docs/36_DATA_CLASSIFICATION_RETENTION_AND_DELETION.md`, update
   `AGENTS.md` and environment/security contracts, and add the
   `ngs-data-lifecycle-safety` skill.
3. Add a read-only inventory/cleanup-plan utility and tests. It must not delete.
4. Use the inventory against old test data, then perform separately requested
   exact-batch cleanup with the approved operator mode.

No implementation PR may combine a feature release with unrelated data cleanup.

## Acceptance criteria

- A new agent can identify the correct repository, branch, worktree, tests, RC,
  and release evidence without reading historical task narratives.
- The BOM rejects missing commits, mutable versions, unknown schema versions,
  and secret/path-bearing fields.
- Each repository runs its own internal tests once; airflow-demo runs only
  affected consumer contracts and one candidate integration smoke.
- Direct user instruction can authorize one exact batch cleanup without a
  second confirmation.
- Batch cleanup cannot delete original FASTQ, references, workflow source,
  final project results, shared OBS prefixes, database volumes, or another batch.
- Old test data can be inventoried and selectively removed with a durable,
  privacy-safe receipt.
- BS10610 and BS96 remain path-, credential-, database-, and release-isolated.

## Rollback

The design and future policy documents roll back through Git. Skills and
read-only validators may be removed without runtime effects. A completed data
deletion is not recoverable through Git, so the cleanup receipt must state the
scope and preserved classes truthfully; the design never claims otherwise.
