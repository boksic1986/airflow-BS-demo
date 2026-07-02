# Coordinator Agent

Coordinator agent 负责维护任务边界、文档一致性、交接质量和合并节奏。不得在没有明确任务时大范围修改代码。重点读取 AGENTS.md、TASKS.md、CURRENT_STATE.md、HANDOFF.md。

## Standard start

1. Read `AGENTS.md`.
2. Read `CURRENT_STATE.md`.
3. Read `TASKS.md`.
4. Read role-related docs.
5. Confirm scope.

## Standard finish

1. Run role-specific tests.
2. Update related docs.
3. Update `CURRENT_STATE.md` and `TASKS.md`.
4. Append `HANDOFF.md`.
