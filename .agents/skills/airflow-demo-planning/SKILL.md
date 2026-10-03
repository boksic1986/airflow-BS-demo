---
name: airflow-demo-planning
description: Plan and decompose airflow-demo work. Use when creating tasks, coordinating multiple agents, updating TASKS/CURRENT_STATE/HANDOFF, or checking scope boundaries.
---

## Purpose

Use this skill when coordinating airflow-demo development. The goal is to keep tasks small, safe, testable, and aligned with the architecture.

## Required reading

- `AGENTS.md`
- `docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `docs/00_PROJECT_BRIEF.md`
- `docs/15_MULTI_AGENT_BOUNDARIES.md`

## Workflow

1. Read the canonical routing/priority index `docs/36_CROSS_REPO_DEVELOPMENT_BACKLOG.md` and `docs/15_MULTI_AGENT_BOUNDARIES.md`; identify the requested scope and authority. For documentation-only planning, do not contact a remote environment. If remote work is explicitly requested, declare `test` or `production` and verify its fingerprint using `docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md`.
2. Identify the current phase and blocking issues.
3. Break the requested work into small task cards.
4. Assign each task to one owner agent.
5. Define deliverables, acceptance checks, and rollback notes.
6. Update `TASKS.md` and `CURRENT_STATE.md`.
7. Append a concise `HANDOFF.md` entry.

## Rules

- Do not implement large code changes while planning.
- Do not assign two agents to edit the same contract file at the same time.
- Prefer mock/dry-run first, then a bounded remote runtime or Docker canary.
- Treat priority as advisory, not as authorization. Keep one accountable owner per task and split implementation, acceptance, and deployment gates; record dependencies, unknowns, deferrals, and user decisions explicitly.
- On continuation after handoff/compaction, recover from the newest state files and current evidence; do not replay completed operations. Keep routine unchanged-state reporting quiet where the monitor requires it.
