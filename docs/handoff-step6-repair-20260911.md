# 0909B Step6 and0901B submission recovery

## Outcome

- 0909B `WGS_20260910_185417_D804A1-a1`: success,5selected; Step6/materialize waiter/finalize/release all success. Verified marker at `cce/cloud_delivery/MATERIALIZED` is VERIFIED/PASS with exact same run. Completion05:02:58Z September11. No Step1-5 clear, download or analysis rerun.
- Root cause: whole-project permission normalization touched two chenjc-owned Python cache files under cce/__pycache__. Result entries themselves belong to ctapa. Fix narrows normalization to journal-owned results plus marker, preserving required2775/0664/0775 modes. All12top-level result directories already committed; journal resume succeeds without re-extraction.
- 0901B `WGS_20260911_035115_CEF046-a1`: existing run retained, config_review;9candidate records previewed via inventory;0selected until analysis preparation. User still needs to confirm configuration/execution. No duplicate create or auto-approve.
- Gate previously validated six handoff identity fields then discarded them. Safe projection now preserves those fields. Existing successful derived status repaired only after original receipt/request/schema/artifact SHA validation; original receipt/TSV untouched.
- Submit wizard persists pipeline+analysis_id URL and restores via GET. Config candidate preview is fenced by exact analysis_id/current attempt/candidate decision, not included in selected run counts. Failure does not offer a new submit implicitly.

## Production and tests

server96 current `/data/airflow-WGS/releases/20260910-t260-recovery-runtime-r1`; production preflight verified actual backend/worker/observer/frontend mounts. Node200 t640 under ctapa; BS node005 used only for future cce asset/source exact patch. No Git operation or service/pod restart. No scan/auto-dispatch changes. No WGS pending/MEI edits, real ledger edits or full workflow validation.

BS10610 cached network-disabled frontend builder:7targeted submission Vitest passed; tsc+Vite passed, final `index-BsfeK10d.js` / `index-DKwrIjzs.css`. Synthetic Python:2materialization tests and4gate tests passed. Red-green reproduced foreigncache EPERM, missingidentity, transient request-open failure and missingcandidate preview. Full WgsProductionUi file earlier14/17: submission reset regression subsequently fixed; two unrelated preexisting assertions reflect newer UI (Total duplicate and resource-tab markup), not claimed fullsuite green. Browser visual inspection not performed; API/static asset/live run verification performed.

## Exact sources and rollback

- Local actual-release candidate `.codex-runtime/selection-release/{live_wgs_runtime_gate.py,cce_delivery.py,frontend-src/pages/SubmitPage.tsx,frontend-src/api.ts,frontend-src/WgsProductionUi.test.tsx,test_handoff_identity.py,test_materialize_scope.py}`. Do not overwrite production using the older tracked checkout wholesale.
- Gate target `/home/ctapa/.config/airflow-wgs/wgs_runtime_gate.py`: before `ea2120b4a93141e02c16e764b19eb745aef2c8854259d503bcaa11fd16d120bd`, final `ddc287315878915e4017f300ac93d2ace2f2f694251f05acdfd2ca20ab238ca8`.
- 0909B frozen `cce/cce_delivery.py`, nipttest installed `cce_pipeline/assets/cce_delivery.py`, and cloud-runtime source `src/cce_pipeline/assets/cce_delivery.py`: before `5a344655432f469deca1caf8f8c1ceafe831247cfaca6d6a9d37bb3318561f0f`, after `da01a7b7a2b437e8e3e2316e320da9d009ce3853bba38cd7adbed9b2723779fc`. Exact hash guard prevented unrelated source replacement. Package remains0.8.4 with this narrow hotpatch; no image changes.
- Code rollback copies in `/sg2/50.ctapa/project/HWcloud/WGS_test/cce-evidence/handoff-step6-20260912/{gate.before.py,delivery.before.py}` (artifact label retained despite live September11 timestamps); installed/source files have `.before-handoff-step6-20260912` copies. Frontend rollback `/data/airflow-WGS/current/rollback/handoff-step6-20260912/index.html`, old assets retained.
- Restore code/static entry only if needed; do not restore stale failed status, remove pending/audit/results, clear completed steps, or restart unrelated computation.

## Recovery incident log

First Airflow clear preview had no state field: diagnostic print KeyError, stopped before mutation; fixed print to optional state. First scoped recovery then failed at node200 request-open FileNotFound during NFS visibility window. Bounded request-reader retry added and tested. An imported gate helper initially used its default ngs-huaweicloud request root, creating an empty retry directory; no files moved there. Empty directory was verified and removed; corrected helper explicitly binds actual airflow-wgs request root and retains original failed Step6 sidecar under worker/status locks. Second scoped recovery succeeds; Airflow task try3, analysis attempt still1. No blind full rerun.

Transient SSH connection abort recovered after hostname verification; no DockerHub access. Invalid local quoting command failed before remote execution. Idle incorrect scp invocation terminated; correct batch-mode upload succeeded.
