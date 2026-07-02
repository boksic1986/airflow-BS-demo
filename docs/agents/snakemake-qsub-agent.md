# Snakemake Qsub Agent

Snakemake/qsub agent 负责 Snakefile、profile、qsub wrapper、event logger、resume/rerun 行为。默认先 dry-run/mock qsub。

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
