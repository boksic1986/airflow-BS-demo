# Current state

Updated 2026-09-18 after the user authorized a complete Git lineage sync from
current main/production into the primary test branch. Test-only development
remains on the test branch; main and production are now required ancestors.

## Repository role

- Primary test development worktree:
  `D:/pipeline/airflow-demo-worktrees/wgs-local-main-sync-20260917`.
- Primary test development branch:
  `jiucheng/test/wgs-local-main-sync-20260917`.
- Pre-sync test tip: `f0b07c4`. The approved three-fix integration is committed
  as `8f062f9`; repository-state consolidation is `91060d0`.
- This is the only remote branch under `origin/jiucheng/test/*`.

## Branch relationship rule

Current `origin/main` and `origin/jiucheng/release/production` both point to
`1255a06`. The user explicitly authorized merging that complete history into
the primary test branch after committing the three reviewed fix ports. The
resulting invariant is:

- main and production must be ancestors of the test branch;
- test may retain additional test-only implementation and evidence;
- test-to-main promotion remains a separate reviewed and authorized action;
- old worktree/patch branches are not merge sources unless separately selected.

The historical `14` main-only / `23` test-only divergence is closed by a merge,
not by rebasing or discarding test commits. See
`docs/TEST_BRANCH_SYNC_HOLD_20260918.md` for the decision transition.

## Consolidated development designs

The primary test branch now owns the current documentation-only development
queue. Two new design branches were reviewed and consolidated without merging
their branch histories or any application code:

- Run control from `jiucheng/feature/run-control-20260918` commit `1c631b7`:
  controlled CCE pause, same-attempt checkpoint recovery and exact online
  project deletion. See
  `docs/superpowers/specs/2026-09-18-run-control.md` and `RC-01` through `RC-05`.
- WGS two-source QC from `jiucheng/docs/wgs-qc-two-source-20260918` commit
  `53fc860`: required ordinary `QCstat.tsv` plus conditional source-qualified
  `multi.QCstat.tsv` evidence for `F57J`/`UPC` samples. See
  `docs/2026-09-18-wgs-qc-two-source-contract.md` and `QC2-01` through `QC2-03`.
- WGS CNV plot viewer design: a WGS-only Run Detail tab lists selected sample
  IDs and streams one native bound `03_CNV/<sample_id>.CNV_genome.png` at a
  time. It is not implemented; no generic artifact reader, image conversion,
  workflow/QC change, test run or deployment is authorized. See
  `docs/2026-09-18-wgs-cnv-plot-viewer-design.md` and `CNV-01` through `CNV-03`.

Both designs are complete and their implementation has not started. They are
proposals, not available APIs or runtime capabilities. This consolidation did
not authorize code, schema, application tests, remote validation, deployment or
real task/data operations. Existing `CCE-RECOVERY-01` remains a separate but
prerequisite-aligned implementation track; run control must reuse its execution
versus monitoring-state contract instead of creating a competing path.

## Test environment and readiness

The target is BS10610/server10610 test. Runtime roots, gates and release
fingerprints remain governed by
`docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md`. Selective-sync validation used an
isolated candidate under the BS10610 control root; no service was deployed or
restarted, no analysis was submitted and no execution gate changed.

The branch contains recorded Local/SGE integration, native execution views,
CCE log-package download, native labels, GATK phase projection and worker-child
timing work. It is not declared fully tested or ready for main. Remaining work
includes reconciling the archived open checklist against current code/evidence,
the deferred CCE recovery implementation, the newly documented run-control and
two-source QC work, operator-facing visual acceptance and one final combined
BS10610 acceptance after the branch scope stabilizes.

## Repository hygiene

The user reprioritized repository cleanup before the validation matrix. The
2026-09-18 safe pass removed ten worktrees and fifteen local branches. Unique
branches or state-only dirty documents were bundle/patch-preserved before their
worktrees were removed.
Six nonregistered legacy directories and nineteen loose packages were moved to
`D:/pipeline/task-artifacts/airflow-repo-hygiene-20260918` rather than deleted.

Eight dirty worktrees remain registered and protected, including the primary
test worktree. Their content must be triaged before any further removal. See
`docs/REPOSITORY_HYGIENE_20260918.md`.

## Open work

`TASKS.md` is the authoritative compact queue. Continue the remaining dirty-
worktree triage and test validation matrix; begin any documented development
track only after a separate implementation instruction. No production
deployment or live data operation is authorized.

## Historical evidence

The complete pre-consolidation files are preserved with SHA-256 hashes at
`D:/pipeline/task-artifacts/airflow-test-branch-state-20260918`. Git history and
the existing release/design documents remain evidence; they are not reusable
runtime authorization or proof that every test is complete.
