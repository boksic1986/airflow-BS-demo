---
name: handoff-review
description: Review and write agent handoff notes for airflow-demo. Use when finishing tasks, summarizing current state, or preparing another agent to continue safely.
---

## Required reading

- `AGENTS.md`
- `docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md`
- `HANDOFF.md`
- `CURRENT_STATE.md`
- `TASKS.md`

## Handoff content

Include:

- Goal
- Completed work
- Changed files
- Commands run and results
- Tests not run and why
- Current git status
- Risks
- Open questions
- Next recommended task
- Rollback notes
- Target environment, SSH alias and verified hostname
- Source commit and current/rollback release paths
- Directory permission and mount checks
- Services changed and preserved, including scanner/dispatch state

## Quality bar

A good handoff lets the next agent continue without rediscovering the same state.
