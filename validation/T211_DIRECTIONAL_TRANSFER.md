# T211 directional OBS transfer hotfix

- Deployed: 2026-09-07 Asia/Shanghai
- Base release: `20260906-wgs-4.1.1-6c98281-t210-transfer-lease-r1`
- Release: `20260907-wgs-4.1.1-6c98281-t211-directional-transfer-r1`
- Scope: backend runtime API and transfer-lease service only
- Upload row: `wgs-obs-upload-01`
- Download row: `wgs-obs-download-01`
- Legacy row: `wgs-obs-transfer-01` retained empty for rollback
- Production Alembic revision remains `20260901_0013`; only the two additive
  fixed row values were inserted transactionally.
- Candidate direction tests: `2 passed`
- Production-baseline backend tests: `343 passed, 1 skipped`
- External `/api/health`: HTTP 200
- Docker network: `nipt_analysis_test_net`, `192.168.199.0/24`
- Published application port: `172.17.61.96:12959 -> frontend:80`
- Airflow API, scheduler and worker were not restarted.

Runtime file SHA256:

- `backend/app/main.py`: `4de6a631e102e85bcd79bf491a511a9c4a0d1e8c578385100c86ed7eebe1f589`
- `backend/app/wgs_platform_service.py`: `5f1f24324630454eaee766acf704b6ab75890eba9c2a330a4ef0423032c4db4c`
- `backend/app/wgs_transfer_lease.py`: `15ef1f70c351adc8663a490d4932d33bb39096385d3d6811e7204f79fcc7ccdc`

Rollback: repoint `current` to the base release and restart backend only. The
two empty directional rows may remain; the base application ignores them.
