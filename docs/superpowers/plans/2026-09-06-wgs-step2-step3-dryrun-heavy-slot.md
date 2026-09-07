# T206 WGS Step2/Step3 Dry-Run and Heavy Slot Implementation Plan

1. Add failing cce-pipeline tests for the default analysis mode, explicit
   dry-run mode, Master command selection and terminal marker provenance.
2. Implement the minimal generic workflow contract and Master dry-run branch;
   run focused and full cce-pipeline tests.
3. Add failing backend/DAG tests for the hidden validation scope, dedicated
   gate, Step3 exit branch, exact finalizer evidence and workspace projection.
4. Implement the backend request propagation, runtime bundle override with
   provenance, Step3 finalizer and DAG topology; run focused and full suites.
5. Add a tested no-compute Heavy Slot Lease probe and exact-holder cleanup.
6. Build provenance-bearing cce-pipeline wheel/Master image and a disabled
   airflow-demo release on BS10610.
7. Run one synthetic trio canary through Step3 only, then the 26-contender
   Lease probe. Capture exact evidence and clean only canary resources.
8. Restore all gates and pause states, run final regressions, and update state,
   task, handoff, API/DAG/runtime/runbook documentation and MANIFEST.

