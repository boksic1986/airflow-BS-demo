# WGS Step4/6 ETA — source-only delivery

Base f241149; independent worktree wgs-eta-production-20260915. No production
publication, runtime changes or data operations. Original prepare/pending intact.

Reuses existing generation-scoped database baseline, same release/target/history
criteria. WGS only changes eased estimate to elapsed/baseline*100 capped99;
success100 remains authoritative. Optional display elapsed/remaining fields go
through existing dashboard projection. Unknown history remains unknown. Tracker
and detail use the same EstimatedStageProgress wrapper and RunProgressBar. No CSS.

BS10610 candidate:
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/wgs-eta-20260915`.
Backend cached image `airflow-demo/backend:t235-232154f`, readonly candidate
mounted /work, workdir /work/backend, network none:
`python -m pytest -q --tb=short -p no:cacheprovider tests/test_monitor_estimates.py`.
7 passed, including retained GATK behavior and WGS stage4/stage6 parameterization.
Frontend `airflow-demo/frontend-builder:node22-lock-35420d5e3ec0`, network none,
readonly /source copied inside disposable builder /app:
`npm test -- --run src/components/WgsEstimatedProgress.test.tsx src/components/EstimatedStageProgress.test.tsx --reporter=dot && npm run build`.
4 passed; tsc/Vite1852modules passed. CSS index-CdK5PwQa, JS index-DlfxtMEO.
After RED/GREEN, review found that a frozen estimate with stale running status
could retain active color. Corrected presentation to neutral and extended the
existing assertion; only the same two affected UI files and build were checked
again (4 passed). No clinical run or browser acceptance claimed.

Runtime resume_stage remains separate work; estimates reset only when that work
creates the actual new stage generation/start. This patch does not restart a
stage, invent old missing timestamps or create historical baselines on reads.
Rollback code only. Installation/publishing requires separate approval.
