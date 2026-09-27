# BS10610 auxiliary DAG discovery correction — 2026-09-27

Scope: test node only. Canonical test branch source `4fe71cb` keeps all five
DAGs and their graphs. Three auxiliary DAGs defer imports of their main DAGs
until task execution, eliminating duplicate IDs during folder discovery.

Environment: `ssh BS10610` → `server10610`, `chenjc`; control root
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`. The historical
`current` symlink is not a source pin. Before the switch, the five related
DAGs each had zero queued and zero running DagRuns.

Immutable source: `releases/20260927-dag-discovery-4fe71cb/dags`.
Only `bio_wgs_native_monitor.py`, `bio_wgs_maintenance.py` and
`bio_gatk_maintenance.py` were mounted anew, read-only, into Airflow
API/scheduler/worker. Existing backend, main DAGs and unrelated service pins
were preserved. New source directories are 0755 and files 0644.

Private control: `candidates/dag-discovery-4fe71cb-control/compose.json`.
Exact prior control copied to `rollback.json` in the same 0700 directory;
both private files are 0600. Compose configuration passed. Only the three
Airflow services were recreated with `--no-deps --pull never --force-recreate`;
no orphan cleanup, database/volume/network action or clinical run occurred.

Verification: actual bind mounts 9/9; before-change Airflow DagBag reported
two duplicate main-DAG IDs, isolated candidate passed 1/1 regression plus
2/2 native-monitor unit tests and GATK maintenance contract. Live
`airflow dags list-import-errors -o json` returned `[]`/exit 0 after the switch;
all five DAG file locations were correct. Gateway backend and DB health both
returned 200. This verifies DAG discovery, not P0 automatic recovery or a
business analysis run.

Rollback requires a fresh active-run check. Recreate only Airflow
API/scheduler/worker using the retained `rollback.json`; preserve all other
services, DAG metadata, clinical inputs and runtime evidence. No rollback was
performed.
