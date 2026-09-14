# Compact controls / ledger closeout

User-approved styling only: Samples view tabs and Rules/table pagination share
`frontend/src/controls.css`, imported after the base stylesheet. White background,
8px border radius/gaps, 32px minimum height, selected/disabled/focus states.
No API, navigation state, workflow or selection changes.

BS96 verified `server96`. Actual frontend source is under
`/data/airflow-WGS/releases/20260914-ledger-c2e491c/frontend`; only main.tsx and
controls.css overlaid, preserving other deployed source and rule-layout CSS.
Cached Node22 build (network none, no pull): tsc/vite passed,1852 modules,2.23s.
Frontend image `airflow-demo/frontend:controls-20260914`, digest
`sha256:20a237ed65e7e2f67783e5c4e0a47b2fcaacdd3adecd10efa064a19b25ade9d7`.
Container `60049e7897bc`; JS index-D1kVxuPt.js, CSS index-79eAEDQ2.css.
Compose config and nginx configuration checks passed; root/CSS/health HTTP200.
The CSS response contains the tab and escaped Rule-pages selectors and all states.
Authenticated visual confirmation remains user-side; no browser check claimed.

Deployment uses release/private/compose.json plus release/compose.controls.json,
`up -d --no-deps --pull never frontend-nginx`. Existing nginx bind/allowlist unchanged.
Backend c787bfd06e5b, ledger worker061ff3623876, scanner and all Airflow service
IDs retained. Rollback only frontend image to `airflow-demo/frontend:ledger-c2e491c`
using the previous composition; do not remove orphans or touch data.

Ledger recheck: HTTP200, source ready/no reason, pending29, visible history1,
automatic generation17->19. No further ledger code change needed for current scope.
WGS-pipeline task01a09149-ad9d-7e92-b98a-16d9cae075e2 received follow-on request:
keep original file handoff/local/SGE, do not expand tests or auto-submit batches.
GATK recovery deferred. Formal future path migration/reset is not executed here.
