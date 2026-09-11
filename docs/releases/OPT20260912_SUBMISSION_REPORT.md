# OPT20260912 Task1 submission report

## Final integration review P1 activation fix

On f08d6b3 the candidate advertised audited caller/configuration options while
the retained private node gate did not forward/validate that contract. Custom
test-mode gating was insufficient. Added independent default-off backend
`WGS_CONFIG_OPTIONS_ENABLED` and empty-default
`WGS_CONFIG_OPTIONS_RUNTIME_CONTRACT`; activation requires true plus the exact
reviewed declaration `wgs-submission-options.v1` and an audited release. The
declaration is configured compatibility, not a claimed runtime observation.
Current deployment must remain false/empty; owner HEAD drift and old gate are
not modified, deployed or silently accepted by this change.

Release API exposes activation/reason separately from informative audited
enums/defaults. Inactive explicit algo/reference overrides reject in the
submission service before catalog resolution/record creation/DAG trigger.
Inactive UI controls are read-only, explain that defaults are informational,
and omit both override fields on a legacy catalog request. Existing stored run
recovery, approvals and no-override submission behavior remain intact.

BS10610 cached offline containers only; no local runtime test or real analysis:

```text
pytest -q tests/test_submission_options.py -k 'unactivated or activation'
 --basetemp=/src/test-activation-red --tb=short
# Before implementation: 9 failed (missing guard/API activation status).
pytest -q tests/test_submission_options.py tests/test_wgs_submission_service.py
 --basetemp=/src/test-activation-final --tb=short
# After implementation: 29 passed; one third-party anyio deprecation.
vitest run src/SubmissionOptions.test.tsx src/IncompleteSubmission.test.tsx
tsc --noEmit
# 10 passed; TypeScript passed.
```

Regressions cover each false/missing/mismatched activation combination even
with test-project flag true; release API stays inactive until both independent
settings match; inactive UI sends no overrides; existing submission recovery
and legacy service tests still pass. Root owns the deployment helper and final
integration review. No owner/node gate, permission, service, pending or real
run change belongs to this fix.

## Scope and state

Implemented on `jiucheng/development/next` from e107f3b. This is a code/test
delivery, not deployment or a real WGS/CCE analysis acceptance. No production
access, live database writes, source edits, formal pending writes, workflow
owner core changes, real analysis dispatch or cloud jobs were performed.
Coordinator owns CURRENT_STATE/TASKS/HANDOFF and subsequent Task2/Task3.

## Implementation

- Vertical pipeline selector; WGS source fields and analysis fields separated;
  responsive layout and per-account/per-pipeline session drafts. Existing
  server recovery preserves the three confirmation phases.
- Audited WGS cc9bde3 release options: DNAscope/Haplotyper and all/ref/no.
  Explicit choices are validated, frozen before submission, propagated through
  runtime request and owner CLI, then checked against prepared config. Unknown
  releases do not inherit unverified option claims. Native CNV is descriptive,
  not an invented toggle. GATK retains HaplotypeCaller and reports configured
  profile separately from unknown/unobserved runtime/operator identity.
- Operator-only test preview freezes source sampleinfo/config hashes, ordered
  sample/data identifiers and exact FASTQ pairs with resolved path/size/mtime.
  Preview creates only a saved draft, not an analysis, directory or DAG.
- Confirmation locks the draft, verifies owner/hash/expiry/current source and
  release, reserves the destination and creates one resumable three-stage
  analysis. PostgreSQL row/advisory locks cover concurrent requests; retries
  reuse the deterministic DAG identity. Another draft cannot reserve the same
  destination already bound to a test run.
- Node-only preparation copies the frozen source table, never existing results
  or source pending. Owner analysis runs with a private outpath, so its native
  prepare/pending ledger remains private. Exact selected-set, no-pending/no-
  excluded, FASTQ target and caller/reference fences precede frozen binding.
  The existing approved CCE Step1-6 and Step7 binding paths remain connected.
  Legacy combined prepare and non-isolated local/SGE target switching reject
  test descriptors. This is not a disconnected prepare-only API.
- Runtime/project projections and diagnostics use the private root; public
  run JSON redacts full test source descriptors and FASTQ paths.

## Isolation and source provenance

Owner inspected at exact deployed commit
`cc9bde3c8ee6ad1cd2f85cf5d2ef49c5611ac081` (WGS4.2.1), not newer local HEAD.
Source contract is sampleinfo.tsv, config.yaml and raw/<data-id>.R[12].fq.gz.
FASTQ targets follow the source config's approved absolute fastqPath. No patient
rows were placed in Git or evidence. Full owner column validation remains the
owner's responsibility; malformed/incomplete source tables fail preparation.

Under the user-requested relative child the platform creates a frozen unique
`WGS_TEST_<16 hex>` directory. This is the owner outpath basename and therefore
the cloud project identity. Source analysis batch and sampleinfo bytes remain
unchanged. `prepare/cce_pipeline_adapter.py` at cc9bde3 scopes SFS run root,
linkage, OBS FASTQ/results and run identity to project/batch. Coordinator's
read-only AST inspection of installed cce-pipeline0.8.4 confirmed batch lock
name `cce-batch-lock-` plus SHA256(project/batch)[:20]. Tests assert two projects
from one source have different project/output roots and lock digests. Existing
Step7 uses the frozen binding rather than a guessed source scope.

## Verification (BS10610 only)

Evidence/source root:
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/OPT20260912-submission`.
Cached backend `airflow-demo/backend:t235-232154f`, cached Node22 builder
`airflow-demo/frontend-builder:node22-lock-35420d5e3ec0`; no pulls/installs.
Containers used network none; optional DB test used only its disposable
PostgreSQL container namespace. All inputs synthetic; tests used task-local
basetemp. The disposable DB container and anonymous volume were removed after
verification; no durable project or live DB was removed.

Final backend command (PYTHONPATH=/src/backend, cwd=/src/backend):

```text
pytest -q tests/test_wgs_test_project.py tests/test_submission_options.py
 tests/test_wgs_submission_service.py tests/test_wgs_runtime_adapter.py
 tests/test_pipeline_registry_api.py tests/test_gatk_registry_api.py
 tests/test_gatk_submission_service.py
 /src/scripts/tests/test_wgs_test_project_gate.py
 /src/scripts/tests/test_wgs_runtime_gate.py --basetemp=/src/test-tmp8 --tb=short
```

Result: **141 passed, 1 skipped**, one third-party anyio deprecation. The
skipped PostgreSQL concurrency test was run separately against disposable
postgres:15-alpine: **1 passed**, four simultaneous confirmations, one analysis
and one deterministic fake Airflow DAG identity. Initial new tests were red
for missing option/test service/gate contracts before implementation; later
regression exposed one transient indentation mistake and a fixture model-field
mistake, both fixed before this final green run. One intermediate scp used the
wrong local cwd; corrected by explicit worktree cwd and re-upload, with the
final suite run against the correct source. No blind retry of failing logic.

Frontend remote cached builder:

```text
vitest run src/SubmissionOptions.test.tsx src/IncompleteSubmission.test.tsx
vitest run src/WgsProductionUi.test.tsx -t "submission|GATK|stage one|preparation screen"
tsc --noEmit
vite build
```

Result: **8 + 7 passed**, 10 unrelated tests deselected, TypeScript and production
build passed (1849 modules). A broader WgsProductionUi run previously exposed
two unrelated baseline expectations in resource-request counts and duplicate
dashboard totals; these are not represented as passing and remain coordinator
Task2/3 scope. Directly affected legacy caller/reference and WGS4.2.0 catalog
expectations were updated to current audited release behavior, not suppressed.
Local `git diff --check` passed; no local pytest/node runtime tests were run.

## Activation, compatibility and limitations

Current preflight supplied by coordinator: server10610 current release
20260912-gatk-81587fcb; scan/dispatch false, no active WGS/GATK runs. Gateway
binds 172.17.106.10:12959. Backend source mount /sg2 is read-only. Node t640 ctapa
UID6801/GID520 can write `/sg2/50.ctapa/project/HWcloud/WGS_test`; output creation
belongs to the existing restricted test gate, never backend mount expansion.

New key: `WGS_TEST_PROJECT_ENABLED`, false by default, must explicitly be true
in backend and `/home/ctapa/.config/airflow-wgs-test/runtime.env`. Preserve
`PLATFORM_ENVIRONMENT=BS10610-Test` (also accepts test, case-insensitive);
production labels reject even if the flag is true. Preserve existing
`WGS_EXECUTION_ENABLED`, `WGS_RUNTIME_ADAPTER_ENABLED`, execution approvals,
test runtime/request roots and server dispatch policy. The gate additionally
requires WGS_test in RUNTIME_RUN_ROOT. No new secret or writable mount is needed.
Missing/unwritable requested parent fails explicitly with no fallback.

Backend/frontend and restricted test gate must be released together; existing
observer needs matching source/image when coordinating the release but no new
observer-specific environment key. Request v4 and prepare receipt v1 schemas
are additive/unchanged; existing DB draft/run tables need no migration and
Airflow DAGs need no new task. New test drafts require the new gate; legacy
non-test runs retain prior behavior.

Synthetic tests do not claim a real owner prepare, Step1 transfer, CCE Master,
Step5/6 result collection or Step7 cleanup ran. A controlled real test project
still requires deployment plus user confirmation of all three phases. FASTQ
fingerprint is metadata, not full file-content hashing. No local lint/full
frontend suite or live Compose rollout was used as a substitute for that
acceptance. Rollback disables the new flag and restores matching services/gate;
preserve draft/run/output audit, do not delete projects or formal pending.

## Review fix round 1

Addresses all three Important findings in OPT20260912_SUBMISSION_REVIEW:

1. Output namespaces now require runtime/root-owned ancestors. Group/other-
   writable parents must have sticky protection; existing directories are never
   chmodded. Target and namespace are private 0700, initialized via no-follow
   directory descriptors, portable atomic mkdir and parent-directory flock.
   Competing creators cannot overwrite a target. A crash after mkdir but before
   the marker is durable leaves an ambiguous private directory: it is retained
   and explicitly requires manual audit recovery, never automatically adopted.
   Marker identity also binds device/inode, not just copied JSON.
   All writable descendant directory symlinks and non-input file symlinks reject
   before owner execution. Private file creation uses O_NOFOLLOW/O_EXCL and
   verifies existing bytes on retry. Parent inode revalidation detects a replaced
   parent before publication. The threat boundary trusts root and the runtime
   UID; a hostile process already holding that UID can also alter runtime keys
   and is not a separate filesystem security principal.
2. The audited release contract now provides defaults plus SHA256 pins for
   owner prepare/config.yaml and cfg/config.template.yaml at cc9bde3. Only the
   private node namespace stores their verified bytes (0600; never public API,
   Git or report content). Audited relative paths are normalized, and owner CLI
   receives explicit private --prepare-config/--config-template. Mutation before
   initial snapshot rejects; later retries use the frozen verified snapshot.
   Every template setting surviving the owner's documented transformations is
   checked against prepared config (including genome/database/CNV/software/script
   paths), in addition to explicit caller/reference and exact sample/FASTQ fences.
   Checks run before binding and before later stages. The UI exposes safe frozen
   release/options/genome/CNV/hash provenance in preview and saved review.
   Source-project config remains provenance/compatibility input only.
3. Preview requests capture an input snapshot and request generation; stale
   replies after edits/unmount cannot recreate a confirmation. Confirmation also
   checks the currently displayed snapshot, and review identifies the frozen
   source. Caller/reference start unset, take audited release defaults, and reset
   old or invalid release drafts. Unknown defaults remain unavailable rather than
   claiming frontend-invented defaults; legacy catalog requests omit options.

### Focused red/green evidence

Old behavior reproduced on BS10610: escaping prepare symlink did not raise;
stale release draft used DNAscope instead of contract Haplotyper/ref. Added real
synthetic regressions for sampleinfo/prepare escapes, parent replacement, sticky
permission fail-closed/acceptance, four concurrent namespace creators, same-inode
retry, copied-marker replacement, mutable effective defaults/templates, prepared
genome drift, delayed preview reply and release-default reset.

Commands use the same cached offline containers as above. Because the mounted
source directory is owned by the host editor rather than the container runtime
UID, the security test correctly rejected that ancestor. Synthetic filesystem
fixtures now use a container-private `/WGS_test` tmpfs, mode0700 (not `/tmp`),
with exec enabled for existing fake-executable gate fixtures; no host/live
permissions were modified. Initial tmpfs noexec caused one existing Step7
fake-kubectl check to fail; enabling exec only on that disposable fixture mount
resolved it without code changes.

```text
docker run --rm --network none --tmpfs /WGS_test:rw,exec,mode=700 ...
 pytest -q /src/scripts/tests/test_wgs_test_project_gate.py
 /src/scripts/tests/test_wgs_runtime_gate.py tests/test_submission_options.py
 tests/test_wgs_test_project.py
 --basetemp=/WGS_test/OPT20260912-fix1-verified --tb=short
vitest run src/SubmissionOptions.test.tsx src/IncompleteSubmission.test.tsx
vitest run src/WgsProductionUi.test.tsx -t "submission|GATK|stage one|preparation screen"
tsc --noEmit
```

Backend/gate: **97 passed, 1 skipped** (unchanged optional PostgreSQL test; this
round does not change DB concurrency logic). Frontend: **9 + 7 passed**;
TypeScript passed. No unrelated full suite or real analysis was run.

### Activation remains gated

Coordinator's node namei inspection found `/sg2`, `/sg2/50.ctapa`, project and
HWcloud protected, but WGS_test currently2770 (not sticky). The new gate rejects
this state. Requested2770→3770 requires separate explicit user authorization;
this patch does not perform it. Coordinator confirmed t640 glibc2.17/kernel
3.10.0-1160.81.1.el7.x86_64 has no libc renameat2 symbol, so the initially tested
renameat2 approach was replaced with portable mkdir plus flock before delivery.
There is no syscall probe, covering rename fallback or new library dependency.
Non-audited live prepare/template bytes also reject
until a separately reviewed release contract is supplied. No new env key,
receipt schema or observer producer was introduced in this fix. Existing test
drafts made before the effective_config contract must be previewed anew; no
silent migration invents their missing frozen values.
