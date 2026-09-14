# Original WGS pending file projection

Current approved scope: WGS-FILE-LEDGER-MINIMAL-20260914. Original WGS prepare,
Step flow, file handoff and local/SGE behavior are unchanged. The existing shared
pending file is the authority; the platform database is its read-only projection.
This adapter does not require or activate the experimental cloud-only protocol.

## Operator registration

The existing worker remains disabled unless `SAMPLE_REFERENCE_ENABLED=true` is
explicitly set by an operator. Its `SAMPLE_REFERENCE_SOURCES_FILE` JSON may contain:

```json
[
  {
    "source_type": "wgs_files",
    "source_id": "wgs-shared-pending",
    "scope_id": "operator-owned-stable-scope",
    "project_root": "/approved/original/WGS/project"
  }
]
```

The current-membership file is `<project_root>/prepare/pending_samples.tsv`.
Optional operator `runtime_root` enables existing final selection history under
that root's fixed `runs/<analysis>/attempt-N/prepare-handoff/prepare_analysis/generation-N`
directories. There are no producer-commit, journal, execution, or user-provided
pending-path keys.
`SAMPLE_REFERENCE_IDENTITY_SECRET` must contain at least 32 bytes. The registration
fence binds source type, source ID, scope, root and secret; it cannot silently
retarget an existing source. These are operator settings, not a web registration
or arbitrary filesystem API. Existing cloud-only/legacy routes remain preserved;
none is enabled by adding this implementation.

## Read and projection contract

- At most 64 MiB, 100,000 rows and 256 columns. File and ancestors are opened
  read-only without following symlinks. A complete final newline, unique headers
  and consistent row widths are required. UTF-8 TSV, UTF-8 BOM, CRLF and additional
  original/extended columns are accepted. Required identity columns are
  样本编号, 上机批次 and 数据编号; family/analysis batch and task/order are optional.
- The file descriptor and path inode/device/size/mtime/ctime/link count are
  compared across the read; replacement of the registered root is also detected.
  Missing, inaccessible, malformed, symlinked or observed-changing files retain
  last-good DB membership and report a safe diagnostic. No lock file or new
  write-side locking protocol is required. This is an optimistic stable snapshot,
  not a claim of transactional publication by an unchanged producer.
- Full identity is scoped HMAC of task (preferred), order, or sample fallback,
  plus sample ID, sequencing batch and data ID. Raw task/order IDs, patient names,
  free text and unrecognized columns never enter DB or API. Only safe sample,
  family, data, sequencing-batch and analysis-batch fields are stored.
- Current pending source analysis batch comes from explicit source_analysis_batch
  with analysis_batch fallback; sequencing_batch remains identity metadata only.
- `reason_code`, or pending_reason when absent, accepts existing allowlisted
  enums. The native missing-sequencing-batch phrase is mapped to its existing enum
  without retaining sample names/free text. Other missing/unknown reasons become
  pending_reason_unclassified. UI renders finite Chinese labels, not raw text.
- Existing reference/source/snapshot tables are reused without migration.
  Unchanged safe content does not create another snapshot; complete header-only
  input clears current pending membership. Disappearance is not consumption.
  Duplicate identities are flagged for review. DB rollback/retry and per-source
  reservation fencing preserve already accepted data and prevent stale apply.
- Existing authenticated sample-reference APIs and independent periodic worker
  are reused. The worker waits 60 seconds after each completed pass. No AnalysisRun,
  Sample, readiness, workflow state or original file is written. Pending rows set
  origin_batch from verified sequencing_batch; no pending destination is guessed.

## Original receipt history (optional runtime_root)

The same worker pass now imports original retained selection history separately
from live membership. At most 1,000 run entries, 32 matched attempts per run,
64 generation entries per prepare-analysis directory and 1,000 receipts per pass
are enumerated in sorted identity/numeric attempt/generation order. Existing Tree
read budgets also apply (64 MiB/file, 512 MiB total history reads per pass).
Only fixed file names are read, with bounded nofollow stable reads:
handoff-request.json, prepare_analysis.receipt.json, final-sampleinfo.snapshot.tsv
and the attempt's batch-binding.json. There is no recursive arbitrary path scan.

The reader validates request/receipt analysis, attempt, generation, execution,
request hash and release; original binding schema/identity/release/control root,
shared analysis_project_root and exact batch directory; source snapshot ID/hash
agreement; exact final artifact key, SHA256, row count and the multiset of five
safe identity/display fields against receipt.selected. Full scoped HMAC comes
from the final TSV's task/order+sample+sequencing-batch+data identity, never a
sample-only join. Source hash is the retained request/receipt assertion; the
potentially changed current candidate sampleinfo is deliberately not reread.
Missing or inconsistent evidence is an error, not inferred identity or execution.

Each accepted selection creates an immutable sample_reference_operation and
decision_selected history rows, never clears current pending. For compatibility,
immutable history origin_batch remains selected sequencing_batch (legacy wire
semantics), not current pending's source analysis batch; UI no longer shows this
legacy origin arrow. destination_batch is the selected analysis_batch.
No batch is derived from a directory name. Repeated destinations/executions remain
history, not overwritten into one potentially stale latest target. A bad receipt
or immutable replay cannot block later valid entries; DB failures retry safely.

Existing operation API adds bounded selection_history metadata with selection_only,
execution_status=unknown, release_id, attempt, generation
and retained final/source hashes. producer_commit and mode are explicitly unknown.
sequence_semantics is database_import_order, not producer chronology; completed_at
and logical_transaction_at remain null in the API. Required legacy pending_hash
storage contains the final-artifact hash for this operation type, not a claim
about historical/current pending. completed_at storage is import-observed only.
Only an existing WGS AnalysisRun is linked; none is created. No readiness or
success status is inferred from selected evidence.

The original attempt receipt.pending subset is never the whole shared pending
authority. Historical batch acceptance must compare its corresponding completed
final sampleinfo counts/sets, not today's mutable pending. The six-batch method
acceptance is already complete and is not repeated by this reader. Deployment,
runtime registration and production activation remain separately authorized steps.
