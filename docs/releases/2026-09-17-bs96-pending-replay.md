# BS96 formal pending sequence replay

User approved BS96 and formal0912C as baseline, excluding temporary six-sample
0912C. Runtime identity ctapa(uid6801); published source ebf1f4b. No workflow
code changes. Normal samplelist readiness and basecount checks enabled throughout.

Historical new-intake order follows final sampleinfo and Step1 timestamps, not
batch-name sorting or directory last modification. Old-input R reanalysis
projects are not submitted as new intake.

| Batch | Selected / hanjj | Pending after | Exact identity match |
| --- | --- | --- | --- |
| 20260912C | 12 / 12 | 0 | yes |
| 20260912B | 12 / 12 | 0 | yes |
| 20260912F | 9 / 9 | 3 | yes |
| 20260912E | 13 / 13 | 0 | yes |
| 20260913B | 12 / 12 | 0 | yes |
| 20260914D | 8 / 8 | 6 | yes |
| 20260914C | 8 / 8 | 0 | yes |
| 20260915C | 12 / 12 | 0 | yes |
| 20260915B | 6 / 6 | 0 | yes |

Comparison keys: order, sample, sequencing batch and data identity. All3 pending
from0912F appear in0912E selected; all6 pending from0914D appear in0914C selected.
Recovery filled1 and3 missing sequencing-batch fields respectively. This verifies
selection and pending continuity, not re-execution of historical biological work.
Metadata was queried now; matching selected identities does not assert every
clinical field equals its historical value.

Private evidence remains only on96 at
`/sg2/50.ctapa/Clinical/WGS_Clinical/prepare/replay-from-20260912C`.
Each batch has a log, source sampleinfo, selected/pending snapshots and numeric
summary. No clinical rows or credentials enter this repository.

Final replay pending0 is byte-identical to existing formal pending. No official
pending replacement, historical scanner input copy, DB mutation, workflow launch
or service restart occurred. The six-sample temporary analysis is preserved.

Final API check: scanner600seconds,auto-dispatch enabled,last scan2026-09-17
14:34:41Z,error null. Supplied0917A Samplelist remains in approved scanner root;
intake has no analysis ID and waits `sequencing_directory_pending`. Actual
automatic analysis remains dependent on normal FASTQ readiness; no bypass.

Application tests are not applicable to this operational replay; no source logic
was changed. Existing service versions retained. No rollback needed. Preserve
private checkpoints and do not replay accepted batches into active scan input.
