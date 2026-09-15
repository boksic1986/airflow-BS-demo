# QC-01 implementation brief

User approved continuation of existing reliability plan. Implement only QC-01 from the existing WGS Run detail flow. Worktree: D:/pipeline/airflow-demo-worktrees/wgs-eta-production-20260915, base ead029f. Shared with coordinator who owns docs, backend and other frontend files.

Ownership: frontend/src/features/run-detail/QcMetric.tsx and its tests; new WgsQcTab.tsx and tests; RunDetailPage.tsx only extracting/replacing existing inline WgsQcTab and removing qcMetric helper. Do not edit other files without coordinating. Leave changes uncommitted for parent packaging.

Requirements: existing Sample/data-table/StatusBadge style; no new CSS/overlay. Show key QC values with friendly labels and units, a compact status badge, not a details disclosure per cell. One sample disclosure shows metric table with friendly label/value/judgment/reason/threshold/provenance; raw field identifiers and JSON only in optional diagnostic disclosure. Preserve source QC status separately from individual policy decisions; never infer PASS from raw PASS or missing judgment. Missing values/policy/not applicable/unsupported release honestly visible using existing reason/evidence; required unknowns cannot be dropped; informational metrics must not change source/aggregate decision. No threshold/business-policy changes. Check current wgs_qc_policy.py and packaged policy to map real fields, not guessed units. Reuse QcMetric in the actual WGS page; do not modify unused RunQcTab as a substitute. GATK has no QC capability; no new GATK QC features.

Read applicable skills/instructions yourself. No subagents. User forbids redundant tests, full suites, remote data operations or production access. Write minimal tests first; send parent test paths when ready so parent can run one BS10610 RED baseline then final covering GREEN/build. Do not run local runtime tests or own remote tests. Parent handles test environment. Do not wait after tests ready beyond parent's RED confirmation; then implement. No main merge/push/deploy, no original WGS/pending edits.

Report here in a final appended section: changes, test cases, concerns; parent owns CURRENT_STATE/TASKS/HANDOFF and API/UI docs. Return short summary.

## Results

### Changes

- `QcMetric` now renders the observed value and audited unit beside a compact judgment badge, without a disclosure in every summary cell.
- The actual WGS Run Detail QC tab now uses the extracted `WgsQcTab`. Source QC status remains a separate badge and is never recomputed from individual judgments.
- Each sample has one metric disclosure with friendly labels, values, judgments, Chinese reason text, human-readable thresholds and provenance. Raw field identifiers, original reasons and JSON are confined to the optional diagnostic disclosure.
- All returned judgments, including unknown and informational entries, remain visible; no threshold or backend policy changed.

### Test cases

- Unsupported-policy raw `PASS` remains visually unknown and has no successful badge.
- Numeric metrics retain their exact value/unit and show a compact independent judgment badge.
- WGS QC summary keeps source status separate while showing key metrics, missing values and unknown judgments.
- Per-sample details retain friendly complete criteria, including unsupported policy, not-applicable and informational unknown evidence, while raw identifiers remain diagnostic-only.
- Parent-run isolated BS10610 verification: the two targeted QC files passed `5` tests; the frontend TypeScript/Vite build passed.

### Concerns

- `wgs-4.2.1-34bfcbf` remains intentionally unsupported by the audited QC policy. Its raw values remain visible with unknown judgments and an explicit unavailable-policy reason; this task did not infer equivalence with `cc9bde3` or alter biological thresholds.
- No local runtime test, production access, deployment, commit or push was performed by this task.
