# W423-R1-UNIFIED089 final candidate

Latest status: **UNIFIED089/WGS423 ACTUAL PROD RELEASE AND ORIGINAL GATE
RESTORATION ACCEPTED**. Shared089, four private node envs/five wrappers, TEST
and PROD Heavy pairs, six gateway services on each host, and genuine WGS423
catalog selection are accepted at the stated bounded minimum. TEST and PROD
original backend execution gates are restored. PROD effective scan is true,
while effective auto remains false under its inherited policy. No new analysis
or producer replay is claimed. Phase evidence archive, HANDOFF and coordinator
reporting remain separate closeout work. Historical WGS422 is frozen for
rollback only; the cancelled 422-native089 drafts remain OBSOLETE/NOT SELECTED.

## Gate4 final release and original-gate readback (2026-10-01)

PROD genuine receipt registration and catalog CAS completed at 14:52:31Z,
changing current from `wgs-4.2.2-441d5e7` to `wgs-4.2.3-bafd27c`.
`gate3-prod-catalog-result.json` SHA256
`0856802d8308b4002e002a5061ac5553785ee67b5837bd8faa3d125c53fc3c34`
records registration and CAS. Catalog SHA256 changed from
`cb33a15f67a9baa5f7b27503b5be0f6c61d72d102a0b2ca36bba476ffc80d976`
to `35c53a2e396009357fd85cc39ce8b7ce6f9d3347b1aae2fe472eb4564912433c`.
This transaction retained closed admission until final gate restoration.

Six PROD gateway selections passed actual installed minimum acceptance:
`gate3-prod-gateway-apply-result.json` SHA256
`cf052e6693e73575d9ffa07ba26e7be37517eacf42b518644174dafebd522892`,
`gate3-prod-gateway-accept-result.json` SHA256
`bef51b0ca014a2de14a91a50f56bf89241f57f9b77ed20ba14fd5ad9e8aea6b3`,
`gate3-prod-mount-contract-result.json` SHA256
`c9d26e8824eb9201b674d40f6332a87dcc0dc99087c98297a8735b060930d32f`,
and `gate3-prod-http-readback-result.json` SHA256
`7b80cb64422b1ac79ae0b8eb931d054fd76e9a465604b7eae8c2a4818d603689`.
All 60 service mounts matched their source/destination/RW contract with no
duplicate destinations; 18 required Airflow imports passed with zero errors;
four external HTTP checks returned 200. Historical Rules GETs returned WGS
total400/page20 with 12 associated group rows and GATK total562/page20 with
zero associated group rows. These are read-model checks, **not** a new089
producer replay, new analysis or clinical canary.

Gate4 TEST restore completed at 14:56:34Z (`gate4-BS10610-backend-restore-result.json`
SHA256 `1d7ef5d1d6366d4b327741b15574940b647ae8b638f04324cbe02cb4c8ec823e`).
PROD backend restore completed at 14:57:18Z. The initial invoker's
`gate4-BS96-backend-restore-result.json` SHA256
`1e9cd6c7124741d3d0ae1ae8486cb694681defc567df3d14b4014fba1e3688cb`
retains exit5/`GATE4_RESTORE_NEEDS_REVIEW`: it incorrectly expected effective
auto dispatch to equal restored env `WGS_AUTO_DISPATCH_ENABLED=true`.
The original read-only policy at `/af05-config/intake.json`, mounted from
`/data/airflow-WGS/auto-intake-20260917-config/intake.json`, has
`auto_dispatch_enabled=false`, so **effective auto remains false**. The observed
policy SHA256 is
`7df771bcae6257893d098d6f29cd4a697f1cec0aa9cd7bb802bb465dbc08194b`;
project YAML SHA256 is
`20cb6f432a6fa9a74b130ae0a230ff34310e6119344d647138cfad44926096d8`.
Inherited source config.py SHA256
`ac14bd31c147abe29c54e9edf4f35ea8fc880cccb8d3e1dec564003e661715f6`
and wgs_project_catalog.py SHA256
`574a61dbfc7a227d07b19d3e86f9668411e62b100b29a65d0f933970ef585714`
remain original. No historical byte snapshot of the original policy files was
captured, so the observed policy hashes are not a before/after byte proof;
the final read-only mount/source and coordinator-confirmed original effective
auto state support the preserved policy conclusion. No policy change, duplicate
catalog POST, or gate apply replay was made to fix the checker.

Final **read-only** closure accepted both hosts: TEST at 15:04:56Z,
`gate4-BS10610-final-readback-result.json` SHA256
`d7093fad978a7d93f88c7172eaf10a111f962217d85722c8d0ad7d64be921898`,
and PROD at 15:05:16Z, `gate4-BS96-final-readback-result.json` SHA256
`18ff3d914f5f2f319f8d9489f05f728050fdb4c225ee27e7295a0e3c31ca9f6f`.
WGS/GATK execution is true on both. TEST scan/auto are false and watermark
empty. PROD effective scan is true with the exact original watermark literal
`2026-09-17T09:34:19.655673+00:00`; effective auto is false, auth true and
current423. Both external gateway `/api/health` reads returned 200. Original
env/image/mounts and unrelated service IDs remained unchanged after restore.
There was no nginx restart, dist rebuild, new analysis/canary, UE04/05/06 or
17+2 rerun, or full-suite test. Four env/five wrappers/native were already
accepted and were not reselected or reinstalled during final closure.

## Gate3 PROD selection and still-closed acceptance (prior checkpoint, 2026-10-01)

Coordinator accepted TEST and granted complete PROD GO. The initial read-only
runs page-size-200 request timed out, while health/page1 passed. The bounded
small-page retry then covered six pages/27 runs, 50 transfers and related
DAG/TI state with nonterminal counts zero, complete coverage and no mutation:
`gate3-prod-activity-v2-result.json` SHA256
`674720db7330e03d211cd186cff52ab1af3ddb3d09ae8db52d50d5c9004ddeaf`.
This is the activity preflight result; it does not attest the selected services.

PROD Heavy selected entry SHA256
`dc5c1d34cea68b7d99b84f1a63df5185dec9714ceb2123448706c60ada0a4fcc`,
core `554f3edc1c8f3fe656600a2417532087f9f96ec0b1df07b894c63a0823e4cd87`
and original launcher
`5f2a8190c785819cbb2d31d4dc1f93a2c380ebe792842ea5723a7d11e19f071e`,
all mode0644. New flock PID190070/starttime3077813668 and Python
PID190480/starttime3077813775 were observed. Two complete payloads at
14:42:24.369308Z and 14:43:30.797281Z each had one actual Lease GET returning
25 exact names, held/used/waiting0, limit25 and idle. Read-only acceptance
`gate3-heavy-accept-result.json` SHA256
`51b871640e54603d2917015357f35e875d7cd541edb341f8438f1e12514db46f`;
21-file actual index SHA256
`2c3e826c9c3a951a505fb5a19c2d4e32670ae594da2608e24d72e8c471da232c`.

The exact stop sent one TERM to the old Python only; flock exited naturally.
The finish invoker exited1 during its final new-process check after core/entry
installation and one original-launcher call. A just-starting flock is a
possible cause, not a proven root cause: fail-moment rows were not recorded.
A later read-only check found the correct new pair and accepted both payloads.
No further signal, launcher call or finish replay was made; no ad hoc product
patch was required.

PROD selected six reviewed gateway services from 14:46:19 to 14:46:52Z:
backend `dfca6fe5...`, WGS observer `c21e8c41...`, Airflow API `5339e3f9...`,
scheduler `a66f8604...`, worker `e483a853...`, frontend `4df1c67c...`.
Infra's installed minimum checks continue. PROD catalog has not been POSTed;
execution/auto gates are still closed, and `v2.paired` final admission
restoration has not occurred. Do not call this a final production release or
claim a new analysis. Accepted UE04/05/06 and 17+2 evidence is reused without
full-suite repetition. The Gate2 section below is a prior checkpoint.

## Gate2 selected state and bounded TEST acceptance (prior checkpoint)

Native independently installed shared nipttest0.8.9/source1f5/wheelf843 and
bootstrap; accepted receipt SHA256
`1727e1f475d0f1c675fbb4676639ad739c58e7111c78d0989207fd48aeb39c17`.
AF selected common16/policy and four private runtime.env/five wrappers. The
node-pair receipt SHA256
`2d5164f94b8e0860276858860362294e048a9736c640bf142825f4b00fec62a2`
records the selection without opening admission or touching PROD gateway/Heavy.
The installed `gate2-node-select.log` reports4/4 imports,4/4 CLI and profiles PASS;
four effective selectors matched the actual PVC/PV, 4/4 read-only PASS
(`gate2-pvc-result.json`, SHA256 `2b823fa1...`). PROD env/wrapper and shared
native changes are classified as **production node configuration changes**;
they are not a production gateway/catalog or full release.

TEST six actual gateway services were recreated with the reviewed variants,
backend `backend.v2.paired-frozen.json`, original project/directory and
`--no-deps --pull never`. Unrelated services were unchanged. Apply receipt
`gate2-test-gateway-apply-result.json` SHA256 `8ca5a037...`; acceptance
`gate2-test-gateway-accept-v2-result.json` SHA256 `5439a205...` confirms
actual loaded backend/DAG modules, three Airflow service imports, zero DAG
import errors, API health200, auth required and execution/scan/auto false.
The separate complete mount check covered all six services, source/destination,
RW and duplicate-destination contract: PASS (`gate2-test-mount-contract-result.json`,
SHA256 `30461ce6...`). WGS and GATK Rules GET returned200 with zero rows in
the checked historical analyses; this is endpoint/schema acceptance, not a
real Group event replay or a new analysis.

The TEST catalog registered the genuine WGS publisher receipt SHA256
`16f131a4...` and CAS selected `wgs-4.2.3-bafd27c` from prior
`wgs-4.2.2-3b1dae5` with execution gates closed. Initial registration and
activation HTTP assertions passed, but the final local readback assertion
compared publisher raw profile SHA256 `436a6608...` with installed canonical
SHA256 `21558a4c...` and exited1. Read-only closure confirmed current423,
raw/canonical distinction and catalog-after SHA256
`342d4e073d2ac3d201ad4028016449daf550a7d88e4da5a2dcd9439754b16069`;
POST was not repeated. Closure receipt `gate2-test-catalog-result.json` SHA256
`b542f880e8b80a76b26ca1ba91efebfc3329d4b27741ea4c3e124829e3bbbe69`.
This was a checker assertion error after successful API mutation, not a second
catalog operation or a product source change.

TEST Heavy alone uses new core SHA256
`554f3edc1c8f3fe656600a2417532087f9f96ec0b1df07b894c63a0823e4cd87`,
original entry `dc5c1d...` and launcher `65991c5...`; new flock/Python PIDs
113056/113067. Two fresh complete snapshots at 13:55:05.298335Z and
13:56:24.895783Z each used one Lease GET returning25 exact names,
held/used/waiting0,
limit25 and idle. The first read-only acceptance timed out because it compared
SFS mtime with node launch wall time. The corrected payload timestamp/hash
check passed; raw mtime remains 599/604 seconds behind payload timestamps.
This is a clock-source difference, not evidence that the snapshots were stale.
Earlier apply invoker failures (missing pidfd API and exiting `/proc` read)
were recorded with exact PID fences: the first made no mutation; the second
ended only the old TEST process pair before core selection. No ad hoc product
patch was made. See ignored `gate2-heavy-final-audit.md` for the commands,
rollback and read-only acceptance limits. PROD Heavy was untouched.

The coordinator accepted TEST and granted the complete PROD gate GO. The first
read-only PROD runs page-size-200 request timed out; health and page 1 passed.
Infra is completing a smaller-page full active-use refresh. Page 1 does not
establish global idleness, so PROD gateway source/catalog/Heavy are still prior
with no mutation in this phase. Next: finish exact preflight, bounded PROD
gateway/catalog/Heavy pairing and acceptance, then `v2.paired` **LAST** for
approved admission restoration. Neither PROD catalog CAS nor a new
analysis/attempt or full regression is claimed. Once
any marked089 attempt exists, global native downgrade and automatic old
backend/DAG rollback remain invalid; retain compatible code with gates closed.

## Pre-Gate2 candidate packet and rollback plan (historical)

The sections below preserve the original frozen candidate, first-gate closure
plan and rollback inventory. Their pending-install wording is superseded by the
selected Gate2 state above; production actions are still pending.

## Current -> target

| Component | Pre-Gate2 observed state | Fixed target |
| --- | --- | --- |
| AF | Actual service snapshots with deployed regression safeguards | `80abdfceea0d604e6524375e2b1a2aa32022ee65`, sole parent accepted `0afd253e158b649c33daaf83d428c191e0420dc3` |
| Shared native | nipttest0.8.8/source417de59 | 0.8.9 / `1f5e1e0d7d7095ab43b14f514aafe623f4f89ca3`; wheel `f843cfa7766169bb7e5485b2af99ffbe933aac9ae7e667056aa3223da62c098d` |
| PROD WGS | `wgs-4.2.2-441d5e7`, frozen private088 | `wgs-4.2.3-bafd27c`, source `bafd27ce5f38e736aae516d5c00247e449872479` |
| TEST WGS | `wgs-4.2.2-3b1dae5`, historical profile/bootstrap drift | Same final423 target, own private prepare config |
| WGS Master/profile | Original pins retained in backups | Master `e48125333a8a4343921eed4a63dd3346d80a981b33ba7e5090136ef3da94f941`; raw profile `436a6608ed0b5d76739b8191589b4de435db15d7be720cc537c7e59f94566abc`; canonical `21558a4c8ff146715ee25f988c0711f2cd39f1f3ce1fad992c4160b69547bdc1` |
| GATK | Business7.6.0 and existing repository/runtime/pipeline paths | Same workflow; Master `a4f8d15e728b9e9c4f56d4b7cea320cef57998b32ae59875d286b9d975f6be1d`; r5 raw profile `17d2bb5911abf7ac15fdca63c0da7b8617411b159f62cf6cf7e2c541799d7e78`; canonical `fd652a12443d4db1ce255c77a3e31b95158da85763908c144e23b8f8d84f2b24` |

80ab contains only two reviewed safeguards: preserve the precise deployed
`_controls` queued-resume exception, and delete one duplicate stage sync while
the run row is locked. Receipt-digest, identity, successor ordering and execution
gates remain. Existing focused tests: controls RED2/15pass -> GREEN17; isolated
real PostgreSQL lock RED1/1pass -> GREEN2. Coordinator and independent source
review accepted the changes. No migration or new API.

Profile digests were computed once from frozen f843 input schema with no install
or cloud/analysis call: **INPUT_SCHEMA_ONLY**, installed acceptance pending.
Genuine WGS publisher receipt canonical SHA:
`16f131a4ed501bd3c2f7747e3532f34bd84b18d024d39f90525b55693282893f`.
Historical publisher BOM remains unchanged;80ab operator pairing is separate.

## Concrete inactive gateway files

| Host/identity | Private control root | Selected source differences |
| --- | --- | --- |
| BS96/server96/6708:520 | `/data/airflow-WGS/unified089-wgs423-0afd253-20261001-control` (2700, permission bits0700) | backend13, observer8; three Airflow services each6; frontend3 dist files |
| BS10610/server10610/6708:520 | `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/unified089-wgs423-0afd253-20261001-control` (0700) | backend19, observer10 including explicit catalog953 parity; each Airflow service6; same frontend |

Versioned public source: `releases/20261001-unified089-80abdfc` inside each root.
Source tar SHA `6d88eae330a255ae7f8c1efd82259a46af99737e8ec1cf3f0864adaa65880f15`.
TEST includes accepted workspace/registry/observer/catalog/adapter/timing fixes;
its observer catalog953 is selected for schema parity, not because a plain423
ID needs suffix parsing. Observer old code was captured independently.

Six DAG files are `bio_wgs.py`, `bio_gatk.py`, `cce_publish_dispatch.py`,
`cce_worker_wait.py`, `common/stage_execution.py`, `common/ssh_transport.py`.
Existing common initializer/six files and auxiliary DAGs are preserved; SSH
banner handling remains. Scanner delegates to backend and needs no source/restart;
sample-reference-worker retains its separate ledger source. Other service IDs
and definitions remain unchanged.

Initial individual-file variants are preserved as v1 drafts. Static review
identified new files beneath read-only parents as a runtime mount uncertainty.
**Select only variants recorded by `final-gateway-candidate-final-manifest.json`**:
actual effective full `/app/app` copies for backend/observer and full DAG `common`
copies per service, merged with only selected files. All unselected files and
symlinks are preserved; Python bytecode caches are excluded. Only these parent
directory binds replace overlapping file binds. The original `/app` mount and
other mounts remain. Full original parent snapshots stay private on each host.

Per-service JSON0600 freezes actual environment, immutable running image digest
and original project name/directory. Other service definitions compare equal.
Rollback variants preserve original mounts/env. Backend additionally provides
freeze, paired-frozen and paired-management variants. All candidate configs passed
`docker compose config --quiet`; no up/run occurred. Later commands require
`up -d --no-deps --pull never <exact-service>`. Runtime imports/mounts remain
**PENDING_WINDOW**, not established by syntax validation.

The final manifest supersedes the v2 freeze variant: `backend.v3.freeze.json`
preserves original source/mounts and changes only admission flags. Paired variants
use the merged target code. The discarded v2 freeze is retained as unselected
history, not used as the initial window gate closure.

Only three GATK environment keys change: console/profile/revision. Biological
repository/runtime/pipeline paths are unchanged. PROD freeze closes only WGS/GATK
execution and WGS auto-dispatch, retaining scan and original watermark
`2026-09-17T09:34:19.655673+00:00`. V2 also prepares a TEST execution-only freeze
option for coordinator review; its original scan/auto false and rollback remain.
Both original management flags are true; authentication/admin gates remain.

Frontend reuses the existing real Group build without rebuild/tests:110 current
inputs match unchanged accepted source; three dist hashes and builder defaults
are pinned. Archive SHA `c3862e5bce76ab8d77dc6067a46bb07e58e129969177c31f74cff52f5313e3a5`.
Existing script/log plus current input/output pins do not invent immutable
build-time inputs. Only html mount changes; nginx config/auth/routing/image stay.

`catalog-transaction.json` prepares POST of the genuine receipt to
`/api/wgs/releases`, then final423 activation using its canonical receipt digest
and exact old current ID as CAS. Neither operation ran. Historical entries and
directory mounts supporting atomic replacement remain; no direct DB mutation.

## Node common source and four trusted consumers

AF owns common platform files and existing policy/bootstrap; native alone writes
shared nipttest and package-adjacent bootstrap as6708. Node route is NGS jump plus
ctapa key to172.17.61.200, t640/6801:520. Full file/old-new/hash/mode inventory:
`final-node-profile-manifest.json`.

- Common16 files: `/home/ctapa/.config/airflow-common/releases/unified089-0afd253/scripts`;
  unchanged0afd->80ab bytes justify retaining the historical directory name.
- Existing schema2 policy SHA `ae8a367a35d74dfb1985b6f3b106a63f8ba1a0acb7275d2ee2d1e3e7c3862dea`;
  source schema1 bootstrap SHA `9e36cdef574e2e5a3af6a0bb6d36f5989be10e7f94dfce99d04ceacb7b6452f9`.
  Native-adjacent bootstrap write remains pending with its sole native owner.
- Metadata journal `/home/ctapa/.config/airflow-common/journal`; four private
  credential/request/result/control roots stay distinct. Actual common PVC/PV
  is pinned; no protocol/schema/dependency addition.
- Four envs and five wrappers: each private root's
  `candidates/unified089-wgs423-0afd253`; exact originals in
  `backups/unified089-20261001`. Env0600/wrappers0700/leaves0700, active hashes unchanged.
- Each private423 prepare uses its own actual config. Only repo/template/profile/
  native-console references change, with reverse-field biological comparison equal.
  PROD SHA `087f1b8bf461c4840542318ebfb0aeb44b4dbef3458cdbdd69d433ec489434aa`;
  TEST SHA `e158f0ac1ebcf28e4049b05632bd87de31385e6b7c8dc95b632902fe224dbc8e`.
  Published423 deliberately has no private prepare/config.yaml; TEST uses its own
  existing config and preserves FQ settings.

## Existing Heavy standalone core wiring

Backend binds cannot change a loaded node collector. This packet stages the
accepted entry/core wiring; no new framework or dependency is introduced.

| Environment | Candidate under private root | Old entry/core -> target | flock/Python PID:field22 |
| --- | --- | --- | --- |
| PROD airflow-wgs | `candidates/unified089-wgs423-0afd253/heavy` | direct entry dd4fb66a -> thin entry dc5c1d34; core ABSENT ->554f3edc |58159:2928014220 /58165:2928014222 |
| TEST airflow-wgs-test | same relative leaf | dc5c entry retained; core7b261882 ->554f3edc |148288:2907479590 /148291:2907479596 |

Original launchers, nipttest Python and exact config/evidence/flock/log paths
are recorded in `final-heavy-candidate-manifest.json`. Originals are byte-backed
in each `backups/unified089-20261001/heavy`; PROD absent core is honestly ABSENT.
No process was signaled/restarted. Reader exclusion affects Master waiting/mode;
used remains Lease-holder count. No Lease clearing or forced0/25.

Earlier six-process evidence used a narrow matcher and saw three SFS/BSS pairs;
it missed these two Heavy pairs and did not establish global analysis idleness.
Before a window, refresh actual workload and PID/starttime/lock identities.

## Window, acceptance and rollback

1. First-gate GO now permits fresh host/control/current/effective IDs/mounts,
   old-hash and complete related run/DAG/transfer/node-writer preflight. True drift
   or unresolved related writers stop before mutation. Mount entries are compared
   as complete sorted records, preserving all Mode/RW/Propagation and other fields.
2. If idle and unchanged, apply only backend.v3.freeze.json: old source/mounts,
   PROD two execution flags+auto false, TEST two execution flags false. Preserve
   scan and actual original watermark literal2026-09-17T09:34:19.655673+00:00.
   The coordinator corrected its equivalent +08 display to this literal. STOP
   and report effective gates/IDs/mounts/health/rollback. This closure is complete;
   native's separate GO already granted after direct human scope decision.
3. Native owner alone installs/pairs f843 package/bootstrap under its independent
   GO and records actual import/source/console/dependency evidence. AF pairing GO
   selects common/private consumers and complete TEST producer/client/backend/
   Group with v2.paired-frozen or paired-management, retaining closed gates.
4. Perform approved minimum TEST acceptance, reusing UE/Group/phase/17+2 results.
   Actual mounts/imports/pairing and approved Heavy loadedSHA/freshsnapshot only;
   no clinical/new analysis, FQ/delivery/LIMS, framework or full-suite rerun.
5. After TEST acceptance and applicable GO: PROD genuine receipt registration/
   catalog CAS plus bounded actual pairing checks. **v2.paired is LAST**, restoring
   each exact original gate/watermark only after all acceptance. Never open earlier.

Before any new marked089 attempt, native owner may restore its exact088
distribution/entry/bootstrap inventory; AF restores original wrappers/env/Compose/
catalog/collector bytes. Preflight compares **29 old native source files**;
**197 other distributions** are fingerprints, not197 package files or a dependency
reinstallation instruction. Rollback wheel SHA
`45c99c0c8fb2d39442088d5c5ee7ad6c7be004d2c30495d80d96a4e8a20672c8`.
Complete distribution rollback stays with native owner's exact inventory.

After a marked089 attempt exists, retain089; shared global downgrade and automatic
rollback to old backend/DAG producer/client are invalid. Keep an089-compatible
stack with gates closed for repair; do not let old code silently ignore089 markers.
Preserve frozen088/history. TEST old drift is restorable evidence, not validated
health. Historical manual resume is not newly attested. Collector rollback needs
approved process replacement and restores PROD's original single entry/absent
core or TEST's exact old core. Protected offline data are not deleted.

Evidence: ignored `.codex-artifacts/w423-unified089-20261001/final-packet.json`
and referenced manifests; non-secret archive in approved
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/w423-unified089-20261001`.
Private secrets/Compose/inspect/catalog/parent backups never leave private roots.
