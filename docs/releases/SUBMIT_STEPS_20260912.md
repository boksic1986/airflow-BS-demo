# SUBMIT-STEPS-20260912

User approved vertical WGS steps with visually distinct headings and descriptions.
Implementation: `e0eb7155740f68a0a4102e2531971d1231fecb90`, development worktree,
branch `jiucheng/development/next`. No Git main merge/push or production clone update.

## Exact rollout

| | BS10610 test | BS96 production |
| --- | --- | --- |
| Verified hostname | server10610 | server96 |
| Control root | /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS | /data/airflow-WGS |
| Current release, unchanged | releases/20260912-opt-4d3d24e6 | releases/20260912-panel-opt-4d3d24e6 |
| Previous frontend | 5abf5827d3ba | cb620c371dde |
| New frontend | d2cab64aa403 | ecfe66fc6820 |
| Previous image | airflow-demo/frontend:opt-4d3d24e6 | airflow-demo/frontend:prod-opt-4d3d24e6 |
| New image | airflow-demo/frontend:submit-e0eb715 | airflow-demo/frontend:submit-e0eb715 |
| New image SHA256 | ce90ddf889beb456b11b579e31bf45f8408b99e6a1f353f21eefcc610c70a21a | 43f2a2938e37af6685b5c036c87640efa8b3776ce992b55e1e463a9ea7d7c215 |

This is an image overlay, not a whole-backend release. For future frontend Compose
recreation append `<root>/candidates/submit-steps-20260912/compose.frontend.json`
after the unchanged current WGS/GATK/panel-only Compose files and original env files.
No environment, network, port, source bind, scanner, observer or worker changes.
BS96 used existing ctapa identity/key; no permissions modified.

Evidence is `<root>/candidates/submit-steps-20260912/` on each host:
`before-ui.json`, `after-ui.json`, `build.log`, pinned source archive and
`e0eb715/.build/frontend-offline/frontend-image-provenance.json`.
Run `python3 <evidence>/submit_frontend_deploy.py rollback` to recreate only the
frontend from its exact predecessor image. Keep all analysis/pending/database data.

## Verification

- RED: two intended regression failures (missing step semantics). First harness
  omitted vite.config.ts; that window-not-defined failure was fixed before RED.
- GREEN:21 targeted tests; full25files/93tests and tsc/Vite build passed on BS10610
  and production cached builders (`--pull=false`, network none).
- `/api/health` OK on both; release `wgs-4.2.1-cc9bde3`; gates remainfalse.
- Both gateways serve `index-D6ET2oXn.js` and `index-B5uRRBmd.css`.
- Run state digests unchanged: test3histories/0active; production7histories/0active.
- Every non-frontend container ID/image/mount fingerprint unchanged.
- Browser connector failed; authenticated visual/narrow-screen review remains open.

No caller activation: it requires separate retained-node compatibility work.
Platform option no longer implies a fixed WGS4.2.0 version; its submitted platform
ID is unchanged and the current release card is the version authority.
