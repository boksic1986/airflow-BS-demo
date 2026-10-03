# WGS DNAscope panel configuration release — 2026-10-02

User authorized an original-profile update and matching AF panel/catalog update,
limited to correspondence/connectivity; no full suite, clinical batch or joint replay.
AF root owns catalog/deployment; native owns profile. Historical runs/requests remain.

## Source and configuration

- New release `wgs-4.2.3-3f98682`, commit `3f986821172e5fbd5f5abd1213baea64c6b976f9`.
- Publication `20261002.1-wgs423-dnascope`; three default entries select DNAscope.
- Original profile `wgs-4.2.3@r1`, native0.8.9, raw SHA `f0150c6015b5997e9304c680e9a5400a508e69c189f16ddbfe1972de345cbc80`.
- Build SHA `051371a9d63549a656004ded74bfe523bb1c810022826853827f44da83bf7b08`.
- AF policy source `fd0a01b591280963e03380ac06df4c991a591d5c`; SHA `b5707e9e1af8e6d3949bc15f6673656713141123e686e74fae7ea8f249b8ba40`.
- Rule tree/14 phase sources match423; its18 additions and7 overrides were copied for the exact newID.

Existing `cce-release.v1` wrapper digest `cb6aca329a923296f06b823c779561cf03c75c61af5fccdac7d9b58f0d411352`
attests AF configuration handoff from pipeline-only PASS, profile and immutable owner
proof. It does not attest fresh joint native execution. TEST/PROD registration and
CAS activation200 select newID from bafd; old entries and frozen bundles remain.

## Installed readbacks

Native bindings reached node200/t640 (`NATIVE_BINDING_PASS`); old mappings/other
fields remain. Inspected22 WGS runs were terminal with no active prepare.
Release GET confirms source/profile/build; formal health/index200 and auth401.
Options false: new submissions use native DNAscope default. Gates/watermark unchanged.
Policy file alone is read-only at `/app/app/policies/wgs_phases_cc9bde3.json` in backend/observer.
PROD root `/data/airflow-WGS/wgs-panel-20261002-3f98682-control`; TEST root
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/wgs-panel-20261002-3f98682-control`.
PROD backend `0c9914ab…`/observer `2dac00a9…`; ten other IDs unchanged, including nginx/Airflow.
Original fd855934 backend and inherited observer code, images, Env values and other mounts remain.
Env-order guard comparison was corrected without replaying TEST deployment.

## Evidence and rollback

Receipts in `.codex-artifacts/wgs-panel-release-20261002`: `native-last-effective-binding-result.jsonl`,
`test-policy-final.jsonl`, `test-registration.jsonl`, `prod-policy-deploy.jsonl`, `prod-registration.jsonl`.
No new runtime test, analysis or data action. Exact service rollback uses each root's
`backend.rollback.json`/`wgs-run-observer.rollback.json`; coordinate native profile/config
rollback and CAS to retained423 receipt (expected current=newID). No rollback executed.
