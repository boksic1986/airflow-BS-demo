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

## Cross-repository status handoff

- Link the relevant card in `docs/36_CROSS_REPO_DEVELOPMENT_BACKLOG.md` and route through `docs/15_MULTI_AGENT_BOUNDARIES.md`.
- Distinguish a local documentation snapshot from source-repository HEAD, installed version, test runtime, and production release. State observation time and evidence freshness.
- Record only material status changes; preserve quiet-monitor intent for unchanged state. On continuation, revalidate active run/attempt, target host, permissions, mounts, and gates before any remote/runtime action; documentation-only edits require no remote preflight.
- Do not turn historical unchecked items, candidate rankings, or an owner suggestion into authorized implementation/deployment work.
- For material changes, have the technical owner report task ID, repo/worktree/branch/commit, implementation/acceptance/deployment states, delta, exact evidence and remaining checks, blocker/next step/decision owner, and observation time to both coordinator and documentation owner. The documentation owner records/routes status but does not approve technical work. Preserve old records; mark an evidenced superseded card with a link, and escalate conflicting/incomplete evidence to coordinator plus original owner.
