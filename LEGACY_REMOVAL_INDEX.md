# Legacy removal index

T247 separates the current WGS/GATK platform from the retired NIPT, PGT-A,
WES-qsub and early mixed-demo repository shape.

The immutable recovery point is:

```text
archive/pre-t247-wgs-gatk-boundary-20260909
```

## Removed from the active tree

| Removed path | Reason | Current replacement |
| --- | --- | --- |
| `.agents/skills/snakemake-qsub-dev/SKILL.md` | qsub-specific skill no longer describes current cloud runtime | `.agents/skills/wgs-gatk-runtime-dev/SKILL.md` |
| `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md` | filename advertises retired qsub architecture | `docs/08_WORKFLOW_RUNTIME_INTEGRATION.md` |
| `docs/agents/snakemake-qsub-agent.md` | obsolete agent ownership name | `docs/agents/workflow-runtime-agent.md` |
| `docs/superpowers/specs/2026-07-14-bs-wgs-s9-platform-design.md` | historical combined NIPT/WGS project | Git archive tag |
| `scripts/bs10610_wgs_phase1_smoke.py` | mutating T139-era smoke against retired submission contract | current backend/DAG/runtime tests and controlled canaries |

## Deliberately retained

- Alembic revisions remain intact even when filenames mention retired
  pipelines; fresh database upgrades depend on the complete revision chain.
- `backend/tests/test_ngs_platform_hygiene.py` remains as a regression guard
  proving retired runtime modules do not return.
- Current WGS Step1-Step7, GATK, CCE/local runtime, API, frontend and production
  operations documentation remains in the active tree.
- Historical WGS design records remain where they still explain the lineage of
  the current production implementation.

Recover one removed file without resetting the working tree:

```bash
git show archive/pre-t247-wgs-gatk-boundary-20260909:<path>
```
