# BS96 original-file ledger deployment

## Final state

Source c2e491c plus scoped identity fix9bf47b3 and operator boundary6e902b9.
Actual release: `/data/airflow-WGS/releases/20260914-ledger-c2e491c`.
Backend c787bfd06e5b, frontend f981776fc70c, new worker061ff3623876.
Runtime configuration: release/private/compose.json and worker.env; do not print
or commit environment contents. Only wgs_files source is registered.
PostgreSQL upgraded0021->0024; protected business-before.dump retained in private/.
No analysis/sample/pending data deleted; existing execution behavior retained.

History starts with retained0910A analysis WGS_20260913_164341_4B5DBA attempt2.
Earlier imported operations remain audit records, excluded from normal operation
API visibility. API reports one operation after the boundary. Current pending is
the actual shared file (29 rows), not reconstructed from old receipts.
Original full identity is retained through scoped HMAC; legacy execution IDs are
not globally unique, so operation identity includes analysis/attempt/generation.

## Verification within approved scope

- Existing13 focused tests: 10.44s after identity fix, 5.63s after boundary change;
  no new scenarios, full workflow tests or clinical replay.
- One cached frontend production build passed, existing rule-layout CSS retained.
- Candidate backend imports and Compose config passed; no image pulls.
- Authenticated health/current/source/history API HTTP200.
- Source ready, no error; automatic generations7->9 between09:37:19Z and09:39:19Z.
- Public health200 and curl direct(no proxy) root200 with new JS/CSS.
- In-app browser failed ERR_EMPTY_RESPONSE; authenticated browser visual check
  remains user confirmation, not falsely marked passed. No access rules changed.
- Airflow/scanner/observer container IDs unchanged. Scantrue/autofalse preserved.

## Deployment incident / deferred recovery

Backend restart windows caused GATK wait_step3_analysis connection-refused
failures:0907A09:23:11Z,0823A09:26:43Z. Root informed user and accepts this as
deployment impact. Both cloud Masters independently verified Running, ready,
restartCount0;0823A158/184,0907A70/184 at inspection. User requested no recovery
yet. No task clearing, rerun, new Master, cleanup or upload occurred.
Do not repeat backend restarts while active GATK wait tasks lack outage tolerance.

## Rollback

Stop reference worker, restore exact previous backend mount/environment and
frontend image from protected before.json and prior service composition.
Retain schema0024, all records, backup and original files. Reload frontend nginx
after backend address changes (it caches upstream DNS; observed502 cleared by
validated nginx reload). Never use remove-orphans or database downgrade.
