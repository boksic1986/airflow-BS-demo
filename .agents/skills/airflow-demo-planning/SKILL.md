---
name: airflow-demo-planning
description: Plan and decompose airflow-demo work. Use when creating tasks, coordinating multiple agents, updating TASKS/CURRENT_STATE/HANDOFF, or checking scope boundaries.
---

## Purpose

Use this skill when coordinating airflow-demo development. The goal is to keep tasks small, safe, testable, and aligned with the architecture.

## Required reading

- `AGENTS.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `docs/00_PROJECT_BRIEF.md`
- `docs/15_MULTI_AGENT_BOUNDARIES.md`

## Workflow

1. Identify the current phase and blocking issues.
2. Break the requested work into small task cards.
3. Assign each task to one owner agent.
4. Define deliverables, acceptance checks, and rollback notes.
5. Update `TASKS.md` and `CURRENT_STATE.md`.
6. Append a concise `HANDOFF.md` entry.

## Rules

- Do not implement large code changes while planning.
- Do not assign two agents to edit the same contract file at the same time.
- Prefer mock/dry-run first, then real qsub/docker.
