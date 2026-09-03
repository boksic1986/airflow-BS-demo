# T173 WGS three-stage submission and SFS monitoring implementation plan

1. Add failing backend/DAG tests for the two approval gates, split prepare
   stages, canonical DagRun ID and legacy in-flight compatibility.
2. Extend the restricted runtime request with `prepare_sampleinfo` and
   `prepare_analysis`; register/import safe samples after each phase.
3. Add authenticated approve-config and approve-execution endpoints with RBAC,
   idempotency and audit events.
4. Rebuild Submit Run as pipeline-selectable three-stage UI. WGS is enabled;
   WES is visible as unavailable. Move reference/resource controls to stage 2.
5. Add node200 SFS Cloud Eye collector and SFS-only API/UI tests. Do not return
   or render OBS resources.
6. Run backend, scripts, DagBag, frontend and Compose tests in `.96` Docker.
7. Check the active DagRun before deployment; preserve it or wait for terminal.
   Deploy application services without recreating database, volumes or network.
8. Verify authenticated SFS metrics, three-stage API/UI, canonical ID and fixed
   network boundaries. Update API/DAG/frontend/deployment/state/handoff docs.

No Git commit is created by Codex for this task.
