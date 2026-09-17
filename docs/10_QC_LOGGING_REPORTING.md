# QC, logging, and reporting

2026-09-17 candidate supersedes the threshold-label wording below: preserve
the original judged-metric columns, values and colored statuses, but hide
threshold text in headings/cells. The backend retains threshold checks and
provenance. Exact release ebf1f4b additionally applies >90% coverage >=20X to
ordinary projects, matching native g1. Historical policies and source aggregate
QC are unchanged. See releases/2026-09-17-qc-policy-ebf1f4b.md.

2026-09-15 UI simplification: all eligible WGS metrics appear as columns, with
thresholds in headings (sample-specific bounds in cells when they differ) and
one final Reason column. No raw/provenance disclosure. Contamination display
uses actual finite CHARR/AB and audited native joint AND cutoffs, not an
unverified source PASS label; unavailable evidence cannot pass. Source aggregate
QC remains untouched. Details: releases/2026-09-15-ui-simplification.md.

- Adapters define allowed QC fields and normalize them into the shared QC response.
- The frontend renders normalized values and never parses workflow output files.
- Raw logs remain in controlled evidence storage; the database records opaque keys, hashes, terminal summaries, and structured events.
- Public APIs expose controlled relative paths only.
- Patient names, hospitals, clinical notes, and unrestricted file paths are excluded.

The WGS adapter reads the single frozen batch `QCstat.tsv` and exposes only approved metrics. Future adapters must provide their own parser and allowlist.
