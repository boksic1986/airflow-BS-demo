# Step7 registration and run-page reads — 2026-10-02

Status: implementation, focused BS10610 checks, both coordinator review gates,
normal branch synchronization and TEST/BS96 two-service acceptance are complete.
The original failed Step7 action was not retried. This is not a cleanup receipt.

## Authorization and source

The human authorized the Step7 function fix, webpage loading fix, synchronization
of accepted code to main and `jiucheng/release/production`, and BS96 deployment.
The coordinator confirmed STEP7-PERF-20261002 and the webpage interpretation.
Network-interface/firewall changes, maintenance retries and data deletion were
outside the release scope.

Product source is `fd8559347dc71ddd015e8c3c757d1805d33260f7`, based on accepted
product80abdfc and documentation parent93ff950. Both remote target branches were
`ce497d61efaa725a4a45266e76dd996d7767fe74`, an ancestor of this tree. Normal atomic
fast-forward synchronized main and the actual production branch, retaining
accepted UE01–UE06, native089, WGS423 and GATKr5 history. Local corresponding refs
were also fast-forwarded. Following documentation closure does not alter the
deployed product bytes. No force push/reset or whole-overlay replacement occurred.

Coordinator point1 accepted scoped source and TEST results; point2 accepted the
exact PROD packet, source/mount delta, activity gate, two-service list and rollback
identity checks before apply. Root was the sole production writer. The coordinator
accepted the final apply/readback receipts; accepted runtime parts were not
reverified during documentation closure.

## Bounded changes

- Shared request freezer marks only native Step1–6. Step7 stays legacy; explicit
  unsupported protocol/stage markers fail closed. Matching old unmarked
  payload/hash reuse is preserved.
- Later empty/generic monitor errors preserve an already-failed Step7 concrete
  error. Real successful receipt priority is unchanged. Old requests, sidecars,
  database records and clinical bindings were not patched. Synthetic recovery
  preserves old database request body/hash; a later authorized retry may reuse
  the request filename, so indefinite preservation of file bytes is not claimed.
- Runs list/workspace use QCstat status and selected sample rows already queried.
  Variant counts/hashes/MultiQC/full QC stay in rich Samples/QC. Workspace uses
  one session/run lookup. Public GATK detail skips frozen-file scans; cleanup
  POST/default strict capability retain frozen/runtime checks. Dispatch GET does
  not initialize/commit a missing claim; action initializers remain explicit.
- GET has a shared30s deadline over fetch/body/existing one network retry;
  cancellation interrupts backoff. Batch Runs/Run Detail carry scope signals,
  stale completion cannot own a newer refresh, and loaded content stays visible.
  Workspace renders first and avoids duplicate initial summary reads. Only404
  permits fallback; POST is unchanged.
- Rules default to the displayed attempt and preserve explicit history/all scope.
  Rules/Samples/Pods reject known mismatches. Transfers retain labeled older
  history and reject a known newer attempt. Logs require a successful summary
  before reading because responses lack attempt identity. Missing identity keeps
  existing compatibility, without claiming complete response validation.

## Focused TEST evidence

All runtime checks used BS10610, synthetic SQLite/mock fixtures, pinned existing
images and isolated network-disabled containers. No clinical mount, real analysis
or real deletion test was used. Local work was editing/Git/documentation only.

| Check | Observed result |
| --- | --- |
| Step7 RED | 30 cases:6 expected failures,24 pass,0 errors |
| Step7 GREEN plus existing controls | 37 pass,30 deselected,2.33s |
| Backend read RED | 8 true defects plus2 initially invalid registry fixtures |
| Corrected workspace RED | 2 expected duplicate-session assertion failures |
| Backend read GREEN plus rich QC/GATK controls | 26 pass,4.13s |
| Frontend RED | 13 selected:9 fail,4 pass;22 skipped,0 errors |
| Frontend pre-boundary GREEN | 24 selected pass;2 new boundary cases then RED |
| Final frontend affected GREEN/build | 7 pass,23 skipped,9.77s;tsc/Vite build pass |

These are separate focused selections, not a full-suite total. Synthetic Step7
checks cover stopped predecessor→failed→new legacy generation and reject late
accepted revival. No actual worker was stopped; accepted UE04–UE06/native089/
WGS423/17+2 or full-suite checks were not repeated.

Raw logs/XML remain at BS10610
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/step7-perf-fix-20261002`.
Local scripts/results/audit/failures are in
`.codex-artifacts/step7-perf-fix-20261002` (not committed). Initial guessed
frontend container name failed before writes; docker ps identified frontend-nginx.
An optional dependency search met protected old paths; pinned image dependencies
were reused without permission changes. Invalid synthetic registry fixtures were
corrected and only their two workspace RED cases repeated. No GREEN/deploy failure.

## Exact packet and actual deployment

The bundle exports exactfd855934 source: nine backend increments, three built
dist files and release metadata. The nine backend/four frontend source bytes
matched those tested on BS10610. Bundle SHA256:
`4cb63fee4bb9f0dfe6b38b481a1899de37b9c1781a330966c279fee88ac8d19f`.
Three-file dist archive SHA256:
`1b8948e595d3d3bb90e7892a43e481ed4eae84d3d526441ed58842eff4d7f019`.
Dist index/JS/unchanged CSS SHA prefixes are69dc1b93/d46daf92/34fb8798.

| Environment | Exact release control root | Packet SHA256 |
| --- | --- | --- |
| TEST | `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/step7-perf-20261002-fd85593-control` | `b87597374ff13a5228a45b9781901c778cb230f8f26b1e6118192f832c66a24f` |
| PROD | `/data/airflow-WGS/step7-perf-20261002-fd85593-control` | `26ba1e4d0e21b6356c2070e563b8466de26788abaf643037e7df21bbf32275c0` |

Each root binds `merged/backend` read-only to `/app/app` and
`source/frontend/dist` read-only to `/usr/share/nginx/html`. All110 backend hashes
match its packet; exactly nine reviewed increments preserve the accepted actual
parent. Inherited Heavy remains
`dd4fb66ac628366a90e64cffddd5f6706550a86d1bd25134248f39bda9310bb3`;
separate node collector already uses554f3ed. Observer's ten inherited differences
and Airflow/node/native layers remain preserved. The Git source identifies reviewed
increments, not equality of every runtime tree with a checkout.

| Target | Check/apply/accept | Apply UTC | Backend ID | Frontend-nginx ID | Other IDs |
| --- | --- | --- | --- | --- | --- |
| BS10610/server10610 | PASS/PASS/PASS | 2026-10-01T17:32:10Z | `8f223ceaca15584a7f79356f054601d711da99ff23e8952b5a0ecfeb56b2d5ef` | `49bbc7078a8c0c3333f74687a86e196c6738b2f7d42120c438ee749cf73f04fc` | 8 unchanged |
| BS96/server96 | PASS/PASS/PASS | 2026-10-01T17:36:40Z | `ef698b65b3ac07e75653976b1b1b1344acd2bd8d201eebd8eb73fe972dbd8640` | `04811cf1d3bbaffc9cc9dcddb44687f775a3812c2189d3ff49027ffcd075e6e9` | 10 unchanged |

BS96 apply at17:36:40.202437Z is Oct2 01:36:40 Asia/Shanghai. The two selected
services preserve image/Env/network/ports/policy/project and unrelated mounts.
PROD image IDs are backend
`0e2d6f0cdf4b89b5ade30b3855cdb8593f33e4c23085a0f5adcd644095cf6912` and
frontend `05cf5152f9e822cb01ab14da61c4894a6fc0783df7cbdaaee19d5258cd0bc0c8`.
The original control `current` link remains `releases/20260912-panel-opt-4d3d24e6`
on PROD and `releases/20260912-opt-4d3d24e6` on TEST; actual source binds above
identify the newly deployed services.

The17:34:48Z PROD fingerprint retained accepted80 parents and old IDs. Complete
business GET at17:34:50Z found27 terminal runs (23 success/2 failed/2 cancelled).
Eight global Airflow GETs at17:34:55Z returned0 queued/running DagRuns and0
running/queued/scheduled/deferred/up_for_retry/up_for_reschedule task instances.
This is bounded scheduler evidence, not absence of every external process.

Both formal gateways (`http://172.17.106.10:12959` and
`http://172.17.61.96:12959`) returned health/index200; served index bytes match
built dist. Unauthenticated API returned401. No login/action POST was used.
Catalog remains `wgs-4.2.3-bafd27c`, WGS/GATK execution true. TEST scan/auto false,
watermark empty,7 terminal runs (4/2/1). PROD scan true; auto env true but inherited
intake policy leaves **effective auto false**. Its original watermark remains
`2026-09-17T09:34:19.655673+00:00`;27 runs remain terminal (23/2/2).
No DB migration/direct access, scanner/auto/pool/watermark change, new analysis,
original Step7 retry/request mutation or clinical/SFS/OBS data action occurred.

## Rollback identity boundary

Each exact release root retains `backend.rollback.json` and
`frontend-nginx.rollback.json`, pinned in its packet. PROD rollback hashes are
`98b4db11435bd7368c891d8f9d93c3e4b026898668387ca54955307fc26ba4b0` and
`b4cecf37325769e41acf5411d7f4295ea5b1bfdfa1d28d186964a1b3d8877621`.
TEST hashes are8c2c779c/53bc5c09; full pins are in TEST prepare/packet.
Original accepted80 source roots are:

- PROD: `/data/airflow-WGS/unified089-wgs423-0afd253-20261001-control/releases/20261001-unified089-80abdfc`
- TEST: `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/unified089-wgs423-0afd253-20261001-control/releases/20261001-unified089-80abdfc`

Rollback restores those roots' `merged/backend` and `frontend-dist` at the original
read-only destinations. It verifies original full trees/configs and rollback copies
without depending on candidate contents; current-link drift fails closed.
`apply-private/scope.json`, hash-pinned `before-inspect.json`, each service's
`*.step.json` and final apply receipt when present establish exact instance ownership.
Stable image/Env/mount/project/service identity and candidate provenance must match;
unchanged original instances may be skipped. Missing/foreign evidence or a later
deployment fails closed, including partial-apply recovery. Dynamic complete inspect
bytes from prepare/apply are not assumed equal; stable identity and separately pinned
apply-before evidence are used. Full inspect/Env/configs stay private remotely.
Recovery recreates only selected services with original configs, `--no-deps --pull
never`, without resetting DB/data/volumes/networks. Rollback was not executed or
runtime-tested; exact guarded recovery was reviewed before this successful apply.

## Single internal timings and retained evidence

Before-values come from the bounded [diagnosis](../diagnostics/2026-10-01-run-pages-readonly.md).
After-values are individual authenticated internal backend GETs, all200, using
historical GATK `GATK_20260929_024231_F246CD`.

| Request | Before (s) | After (s) |
| --- | --- | --- |
| Default deployed list,20 rows | 2.278426 | 0.166185 |
| GATK list,6 rows | 0.062800 | 0.053244 |
| Historical GATK base detail | 0.483357 | 0.067499 |
| Historical GATK workspace | 0.124118 | 0.091388 |

TEST list7 rows took0.022774s. Warm cache is possible. These requests bypass
browser session/nginx/navigation/network. Browser/P95/complete slow navigation
were not remeasured; removal of all user-visible latency is not claimed.
The original failure remains separate: see the
[exact Step7 diagnosis](../diagnostics/2026-10-02-step7-20260927C-readonly.md).
This release neither retries that action nor proves cloud deletion/retention.

Local public `test-*`/`prod-*` prepare/check/apply/accept receipts and final PROD
preflight/Airflow activity records are under the task artifact root.
`public-evidence-index.json` binds23 named public artifacts with SHA256
`5c23f017e675339450421ded4e11fb1666cf77ec19f0de200e8bf9ccc47780d1`.
Private configs/credentials/Env and patient fields are excluded. HANDOFF records
full commands, tests, review gates and pins. No new runtime checks followed acceptance.
