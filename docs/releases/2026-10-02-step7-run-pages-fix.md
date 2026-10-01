# Step7 registration and run-page reads — 2026-10-02

Status: source review and focused TEST checks passed; two-service release is
pending. This is not a cleanup receipt.

## Authorization and source

The human authorized the Step7 function fix, webpage loading fix, synchronization
of accepted code to main and `jiucheng/release/production`, and BS96 deployment.
The coordinator confirmed STEP7-PERF-20261002 and the webpage interpretation.
This does not authorize retrying a maintenance action or deleting data.

Candidate is based on accepted product80abdfc and documentation93ff950. Both
remote target branches are ce497d61 ancestors of this tree, so a normal atomic
fast-forward retains the accepted UE01–UE06, native089, WGS423 and GATKr5 history.
The exact candidate commit and final release packet will be recorded after
frontend acceptance and coordinator review.

## Bounded changes

- Shared request freezer marks only the actual native Step1–6 stages. Step7
  stays legacy; explicit unsupported protocol/stage markers fail closed.
  Matching old unmarked payload/hash reuse is preserved.
- A later generic failure callback preserves the prior concrete Step7 error.
  A real successful receipt still takes precedence. Existing old accepted
  requests, sidecars and clinical bindings are not rewritten.
- Runs list/workspace use QCstat status and the selected samples already queried.
  Variant counts, hashes, MultiQC and full QC judgments remain in the rich QC
  projection. Workspace uses one session and one run lookup.
- Public GATK detail projects cleanup prerequisites without frozen-file scans;
  cleanup POST and default strict capability retain the frozen/runtime checks.
  Ordinary dispatch GET does not initialize or commit a missing claim.
- GET has a shared30s deadline over fetch, body and its existing one network
  retry. Cancellation interrupts backoff. Batch Runs and Run Detail pass the
  scope signal; workspace and tabs refresh independently. POST is unchanged.

## TEST evidence

All runtime checks use BS10610, synthetic SQLite/fixtures, pinned existing images
and an isolated network-disabled container. No real analysis or deletion test.

| Check | Observed result |
| --- | --- |
| Step7 RED |30 cases:6 expected failures,24 pass,0 errors |
| Step7 GREEN plus existing controls |37 pass,30 deselected,2.33s |
| Frontend RED |13 selected:9 fail,4 pass;22 skipped,0 errors |
| Backend read RED |8 real defects plus2 initially invalid registry fixtures |
| Corrected workspace RED |2 expected failures at duplicate-session assertion |
| Backend read GREEN plus rich QC/GATK controls |26 pass,4.13s |
| Frontend pre-boundary GREEN |24 selected pass;2 new boundary cases RED |
| Final frontend affected GREEN/build |7 pass;tsc and Vite production build pass |

Raw logs/XML: BS10610
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/step7-perf-fix-20261002`.
Local scripts/results/audit:
`.codex-artifacts/step7-perf-fix-20261002` (not committed).
Initial guessed frontend container name failed before any write; corrected by
docker ps. An optional dependency-directory find encountered denied old paths;
no permission changes were made. Runtime image dependencies were reused instead.

## Deployment boundary

Only backend and frontend-nginx are selected. Each keeps its existing image,
environment, network, port, policy and unrelated mounts; Airflow and observer
remain running on their accepted service-specific parents. The backend parent
is copied and receives exactly the reviewed nine-file increment. Its inherited
Heavy module stays dd4fb66; the separate node collector already uses accepted
554f3ed. These are different consumers, so Git equality of all runtime files
is not claimed. The observer's ten inherited differences are preserved.

BS96 read-only preflight at2026-10-01T16:54:54Z found27/27 runs:23 success,
2 failed,2 cancelled, no submitted/queued/running entries. This snapshot does
not prove absence of every external process or maintenance worker. Effective
scan remains true and effective auto false, with the original activation
watermark. Refresh the activity check immediately before apply.

Candidate private Compose copies and exact original rollback configs will be
pinned in the release packet. Rollback recreates only the selected services
against their original source mounts. There is no DB migration, data rollback,
automatic cleanup or automatic retry in this release.

Frontend bundle: index69dc1b93, JSd46daf92, unchanged CSS34fb8798; the packed
three-file dist SHA256 is
`1b8948e595d3d3bb90e7892a43e481ed4eae84d3d526441ed58842eff4d7f019`.
Attempt checks reject known mismatches; missing identity remains existing
compatibility, not a claim of complete validation. Logs follow a successful
summary before reading because the existing log responses lack attempt identity.

## Remaining acceptance

Record candidate commit, coordinator review receipts,
TEST two-service acceptance, exact PROD packet, apply/readback and final branch
heads. Compare bounded internal API timings without claiming browser timing or
that all sources of user-visible latency have been eliminated.
