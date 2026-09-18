# WGS QC two-source contract

## Decision

The platform shall use two distinct batch-level QC sources for WGS V4.2.1.

1. `*.QCstat.tsv` is the required source for every selected sample and remains
   the source of all ordinary QC fields and ordinary QC decisions.
2. `*.multi.QCstat.tsv` is an optional, supplemental source used only for a
   rare-disease sample.  It supplies the native g2/WgsMetrics fields needed by
   that sample's additional checks; it does not replace or reinterpret the
   ordinary QC result.

This is a display and ingestion contract for a future platform change.  It
does not change `prepare_wgs_batch.py`, pending selection, a WGS release's
native QC scripts, thresholds, DAGs, database schema, or a completed run.

## Why the two sources must stay separate

`QCstat.tsv` is the g1/bam2bedGraphWGS result.  Its depth and coverage columns
are the ordinary WGS QC authority.  `multi.QCstat.tsv` aggregates g2 Sentieon
`WgsMetricsAlgo` output.  The latter excludes bases under its own effective
coverage filters, including paired-end overlap, mapping quality, duplicate and
base-quality treatment.

Consequently, identically named fields such as mean depth or `>=30X` are not
interchangeable and must never be compared, substituted, or collapsed into one
API field.  The platform must preserve the source identity on every projected
value.

## Source discovery and row matching

For the frozen release/batch binding, resolve exactly these two aggregate
artifacts inside the bound `07_QC` result directory:

| Artifact | Required | Purpose |
| --- | --- | --- |
| `*.QCstat.tsv` | Yes | Ordinary WGS QC for all selected samples |
| `*.multi.QCstat.tsv` | Only when selected rare-disease samples exist | g2 supplemental QC for those samples |

The resolver must use the batch artifact declared by the frozen binding.  It
must not choose a per-sample `*.QCstat.tsv`, search another batch, infer a
filename from user input, or read an unrestricted path.  The existing
hash/relative-artifact authorization model remains the boundary.

Rows match the selected sample by the canonical sample identifier from the
frozen sampleinfo.  Missing, duplicate or non-matching rows are an evidence
problem: the affected source fields are unavailable and cannot be reported as
pass.  No row may be borrowed from another sample.

## Applicability

The native V4.2.1 rare-disease predicate is sample identifier matching
`F57J|UPC`.  This predicate must be release-pinned with the existing native QC
policy; the browser must not infer it from a column name or an operator label.

| Selected sample kind | Read `QCstat.tsv` | Read/project `multi.QCstat.tsv` |
| --- | --- | --- |
| Ordinary sample | Yes | No |
| `F57J` or `UPC` rare-disease sample | Yes | Yes, as supplemental evidence |

For a batch with no selected rare-disease sample, the platform skips
`multi.QCstat.tsv` entirely.  It must not render its columns as `unknown`,
`not provided`, or a failing status for ordinary samples.

For a rare-disease sample, a missing or malformed `multi.QCstat.tsv` produces
an explicit supplemental-evidence-unavailable state.  It must never turn into
a green result or silently fall back to the same-named ordinary QCstat value.

## Field contract

### Ordinary fields from `QCstat.tsv`

The existing allowlisted ordinary metrics remain the primary table/detail:
raw bases, mapped reads, raw/clean GC, clean Q30, average depth, Fold 80 base
penalty, coverage `>=1X`, `>=10X`, `>=20X`, `>=30X`, `>=50X`, `>=100X`,
contamination, sex consistency, and the existing safe count/relationship
evidence where the release supplies it.

Existing native policy remains authoritative.  For ordinary projects the
currently active checks include raw bases, mapped reads, GC, clean Q30, depth,
Fold 80, `>=1X`, `>=20X`, contamination, sex and other native criteria.  The
ordinary `>=10X`, `>=30X`, `>=50X`, and `>=100X` columns are retained as
measurements where available, but are not implicitly made pass/fail criteria.
Special item policy remains separately release-pinned.

### Rare-disease supplemental fields from `multi.QCstat.tsv`

For an applicable `F57J`/`UPC` sample, add a clearly labelled **Rare-disease
supplemental QC (WgsMetrics)** section with these source-specific fields:

| Display field | Source metric | Native V4.2.1 supplemental check |
| --- | --- | --- |
| Deduplicated bases | `Dedup_bases` | `<120G` is abnormal |
| Mean depth | `Mean_Depth` | `<40` is abnormal |
| Clean Q30 | `Clean_Q30%` | `<=85%` is abnormal |
| Coverage `>=30X` | g2 `>=30X` | `<90%` is abnormal |
| Coverage `>=10X` | g2 `>=10X` | `<98%` is abnormal |
| Duplicated reads | `Duplicated_reads%` | `>10%` is abnormal |

The labels must include `WgsMetrics` or `rare-disease supplemental`; do not
label them merely `MultiQC`, and do not overwrite the ordinary QCstat field
with the same display name.

## API and UI presentation requirements

- Keep the existing batch-level aggregate/native QC status visible and do not
  recompute it from browser values.
- Return source-qualified metric objects: value, unit, source kind
  (`qcstat` or `wgsmetrics_supplemental`), applicability, judgment and safe
  reason.  Keep raw paths, provenance blobs and clinical free text private.
- The normal QC table contains ordinary fields only.  Do not append six empty
  supplemental columns to every row.
- A rare-disease row exposes its supplemental metrics in an expandable/detail
  section, or a batch-level supplemental panel filtered to applicable samples.
  Mixed batches therefore remain readable without an excessively wide table.
- An ordinary row has no supplemental section.  This means **not applicable**,
  not `unknown` and not `pass`.
- A rare row with unavailable supplemental evidence displays a compact source
  reason and an unknown supplemental judgment; it does not claim that the
  ordinary QC value satisfies the g2 criterion.
- Preserve existing release/version policy behavior.  Historical or unaudited
  releases remain unknown where their policy is unavailable; never apply the
  current V4.2.1 criteria retrospectively.

## Implementation sequence and acceptance

1. Extend the WGS QC projector to register and parse the exact optional batch
   `multi.QCstat.tsv`, with source-qualified output and no database migration.
2. Add release-pinned rare-disease applicability and native g2 judgments while
   retaining the current QCstat projection unchanged for ordinary samples.
3. Update the QC response contract and the Run Detail QC component to render
   supplemental fields only for rare-disease samples.
4. Use synthetic fixtures only: ordinary-only batch, rare-disease batch with
   both artifacts, and rare-disease batch missing the supplemental artifact.

Acceptance is limited to: correct source selection; no same-name metric
substitution; no supplemental columns for an ordinary-only batch; source-aware
supplemental values and reasons for an applicable sample; and no change to the
native aggregate QC source, pending files, or analysis execution.

## Evidence basis

This contract was reconciled with the WGS V4.2.1 QC logic: g1
`QCstat.tsv`/`g1.Collect_QC.py`, g2 `multi.QCstat.tsv`/
`g2.Collect_multiqc_QC.py`, and the release-pinned `qc_config.json`.  The
consulted WGS workflow review confirms that g2 uses the per-sample
`*.multi.QC.tsv` inputs aggregated by the batch `*.multi.QCstat.tsv`; the
platform contract deliberately consumes the two batch artifacts above.
