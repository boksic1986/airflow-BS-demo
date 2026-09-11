# OPT20260912 — BS10610 deployment and acceptance ledger

Status: BS10610 panel deployed from4d3d24e; conditional feature activation and
authenticated browser visual acceptance remain held. Production is out of scope.

## Final deployment record

- Source4d3d24e6c0308b682a92e2b09824026b7a888818, archive SHA256
  8a3401c26caabac5397ef61242778db4a12a831727ed659b55f76062a364347f.
- Current releases/20260912-opt-4d3d24e6; predecessor81587fcb retained.
- Frontendimage airflow-demo/frontend:opt-4d3d24e6,
  sha256:86962cb715fd3b0e5a986cee4f20e2a36c8fa8678d9fd600ba2d16e42c92ae6f.
  Final cached offline fullUI93passed25files/tsc/Vite. Served assets
  index-_c2zYdoZ.js and index-9kcWGY_H.css verified at gateway.
- Backend722fbe887bf6, observer3ecae082215d, frontend5abf5827d3ba changed;
  zero restart counts/import-traceback markers afterstartup.7protected IDs
  unchanged. Both original testenvfiles retained; only newguardfalse/empty.
- Guarded Compose check/deploy/accept used onlybackend,wgs-run-observer,
  frontend-nginx with--no-deps--no-build--pullnever. Current pointer switched
  atomically afterhealth/API/staticasset checks. No migrations/init/network
  recreation or runtime cleanup. Existing shared bind remainsoldrelease/shared.
- Final integration P1/P2closed;29backend/10UIactivationfix and5operational
  rollbacksyntheticpasses. Source4d3 doesnot changeTask2/3collectorcontract.
- GET health, WGSoptionsdisabledreason, GATKconfigured/unobservedruntime,
  resourcefields,3existingGATKworkspace/rules responses verified.0activeDAGruns;
  scan/dispatchfalse. No clinicalsamplevalues logged.
- Actual Heavycollector/API0/25fresh,enforce; waitingunavailablebecausemissing
  Masterwaiting snapshot. BSSnot_configured. No per-rule/saturation claim.
- Browser remainsatnormalSignIn; logged-in layout/narrow/no-flash acceptance
  pendinguserlogin. Frontend93syntheticUItests are not a substitute for that.
- Customprojects andnewcatalogoverrides disabled; stickypermission, matched
  owner/gate contract stillawaitingdecision. No sharedWGSsource/privategate
  replacement. No realrun or productionchange.
- Final readonly postcheck:6Master UID-set hash still
  baa7dd2a10e5f021ac05c661acf62ae08571e8a420e2327e001410480b800e9b;
  privategate/wrapper hashes equal preflight. Heavy snapshot advanced across
  multiple60secondcycles; no refresh_failed. API reason anddisabledflag verified.

Operational helper retained in candidate deploy_test.py (non-secret tool source,
separate from trackedapplicationcommit). Rollback invocation via BS10610 Python:
`python3 <candidate>/deploy_test.py 4d3d24e6c0308b682a92e2b09824026b7a888818 rollback`.
It validatescurrent old/candidate, restoresonly3services, verifiespredecessor
images/mounts/health andatomicallyrestorescurrent. If verification fails it does
not claimrollbackcomplete. Neverdelete data asrollback.

The rest of this document records chronological preflight and superseded
candidate evidence; it must not be mistaken for current activation status.

## Baseline

- Local development worktree: `D:/pipeline/airflow-demo-worktrees/development`, `jiucheng/development/next`, base `e107f3b22044034c329899efc94bb3fbe64e208d`.
- SSH `BS10610`, verified hostname `server10610`.
- Control root `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`.
- Current release `releases/20260912-gatk-81587fcb`.
- Compose contract: `docker-compose.wgs.yaml` plus `docker-compose.gatk.yaml`; retain both external test env files `env/bs10610.wgs.env` and `env/gatk-81587fcb.env`. Never print env values or rendered secret-bearing configuration.
- Gateway binds **172.17.106.10:12959**, not loopback. Read-only health request on this interface returned `{"status":"ok"}`. Loopback curl exit7 was the expected consequence of the interface-specific bind, not an outage.
- WGS scanner and automatic dispatch both disabled; no active test Airflow runs. Three existing GATK test records remain. These switches and records must be preserved.
- External CCE read-only observation found one active Master and 11 reserved Heavy leases in a complete inventory of25. Do not restart or alter this workload for a UI release.

Protected service IDs confirmed again before candidate deployment: Airflow worker `fdaf00067050`, scheduler `ba14b9433b2f`, API `9ba5b54ce74c`, Postgres `6cf33066b97a`, Redis `ae5b4e30caf0`, node probe `d77affe7a22d`. Affected candidates currently backend `8eca1592b509`, observer `add051b157d5`, frontend `e90c834e3fa6`, metrics collector `5629edc808c8` (only replace if resource collector code requires it).

The live `/data/airflow-demo` shared bind currently resolves into the predecessor release's `shared` directory. A new immutable source release must explicitly preserve this existing shared target; do not let relative Compose `./shared` silently create an empty independent runtime root. Unchanged Airflow services remain pinned to their existing source mounts.

## Planned activation boundary

After task reviews and pinned candidate acceptance, stage an immutable test source release; record commit, checksums, image provenance and predecessor. Render Compose quietly before changes. Recreate only affected backend, observer and frontend; preserve Airflow worker/scheduler/API, Postgres, Redis and unrelated collectors unless the final reviewed change demonstrably requires an affected collector replacement. No Master, work Pod, DAG submission or scan/dispatch change.

Node-owned test preparation and Heavy collection use `/home/ctapa/.config/airflow-wgs-test`, not the production private directory. Existing test runtime references its private operator config in place. Do not copy operator credentials into source, logs, Git or build context. Test-only project output is `/sg2/50.ctapa/project/HWcloud/WGS_test`; backend mount remains read-only, actual preparation is performed by ctapa on t640. Record prior gate hash and owner-only rollback sibling before atomic replacement.

Task1 requires explicit backend and restricted-gate test feature flags. Keep defaults disabled and never set these in production. Task3 requires an explicit test output location for Heavy snapshot. Billing remains `not_configured` until a dedicated BSS read-only identity is available; no reuse of regional Cloud Eye credentials.

Targeted read-only installed-source check on t640: nipttest distribution reports cce-pipeline0.8.4; `_batch_lock_name` hashes `identity.project/identity.batch` (SHA256 prefix20), not batch alone. Owner prepare likewise derives SFS/OBS suffix from project/batch. A distinct frozen test project namespace can isolate the lock without rewriting source batch columns; verify the final generated bundle scope before acceptance. This was source inspection only, not pipeline revalidation or execution.

### Pending exact permission approval

Task1 independent review found a shared-parent replacement race for owner preparation. Fresh `namei -l` on t640: `/sg2` root755; `/sg2/50.ctapa`, `project`, `HWcloud` ctapa755; only `WGS_test` ctapa:bioinfo2770. User has been asked whether to add sticky bit **only to this directory** (2770→3770), with no recursive operation or access expansion. No permission change has been performed. Implementation must fail closed on unsafe writable parents, and preserve private0700 descendants/no-follow/inode ownership. Synthetic tests can validate that mechanism; actual custom test entry remains disabled until this prerequisite and code review pass. Other panel features do not depend on this permission.

Additional read-only target probe: t640 nipttest uses glibc2.17 and `ctypes.CDLL(None)` does **not** export renameat2. Task1 must not rely solely on a newer libc symbol that passed in the cached backend container. Implementer notified to retain no-overwrite safety using a target-compatible mechanism; no system library or file was changed by the probe.

Task1 d5a4e1d resolves this with portable mkdir/flock and passed scoped review. Further read-only source check found shared WGS owner repository HEAD68f5dccee5ea6d7d8104d998118a69a5cb5ac4da, plus modified prepare/config.yaml. Both live prepare/config.yaml and cfg/config.template.yaml differ from the audited cc9bde3 pins. This is source/release drift, not authority to reset or rewrite the shared WGS repo. Custom test execution stays gated pending aligned owner release selection; independent panel monitoring updates may still be deployed. No owner source/config was changed.

Task3 read-only node compatibility probe: t640 nipttest has sdkcore3.1.210;
GlobalCredentials.sign_request accepts SdkRequest and returns SdkRequest. No
credentials were read and no cloud request made. A network-blocked synthetic
signing/transport contract test remains required before collector activation.

Synthetic signer probe subsequently passed on t640 nipttest Python3.9/core3.1.210:
4 signed fake-session requests,0 network connections,exit0. Probe blocks socket
connect and uses only synthetic AK/SK/domain; foreign route and302/403/429 paths
tested. Staged only3 non-secret source/test files at ctapa-owned0700
`/sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-ctapa/wgs-runtime/cce-evidence/OPT20260912-bss-node-probe`.
Collector hash3dba4573e1589bbca5505184c810de047a76c3d3743e050aff793656e8184fb1;
contract b047d2e36c47efac06dd238c26b33381372faf23cf6e27db1ecf625afd614b4d;
probe a740637eb045157b28f72ce08e228a011ada111b5bfcfcceb37be8388c6e0127.
No BSS identity was read and no real cloud request sent. Recheck if transport changes.

Setup failures: test-d for the BS task-root alias returned1 (node did not see
that child); direct `/sg2/33.chenjiucheng/WGS_test/cce-evidence` mkdir returned
Permission denied, no child created. Used the already-approved writable test
runtime evidence root instead; no permission change, mount change or /tmp use.

## Browser access

Final Task3 f08d6b3 synthetic SDK probe passed on t640:6 signed requests,
0 network connections,exit0. GET units and both POST body/signature contracts,
redirect rejection and403/429 safe mappings tested against core3.1.210.
Final collector SHA256 fc03e5b38b5d548865a295979f31a5b0ffb0ed6ccc6b1feae331b0ecb026483a;
contract199e9896f0a3b06f15d7d15297345c19f86c5df744875dedfbd93ed56e239251;
probe0d9163a4554f5021fb9f941fa95acbaaf30f619ca26e064d5830b565423405f6.
No actual BSS identity/request used. Fresh BS10610 preflight still81587fcb,
protected service IDs unchanged,0 active WGS/GATK DAG runs,scan/dispatchfalse.
Task3 needs no metrics-container restart: backend reads validated spools directly.

Desktop direct gateway access timed out; server-side health succeeded. A temporary SSH tunnel bound only to `127.0.0.1:22959` forwards to the existing gateway through BS10610. Browser reached the normal sign-in page; existing-account login requested from the user. No firewall or published port changed. Close the temporary tunnel at task completion unless still needed for the user's acceptance.

## Acceptance still required

Candidate f08d6b3 offline build passed92UI tests and tsc/Vite. Image
sha256:13dc750988a7b5823c79393e81196ce81a7e321aac11dbfc6f73461686b67390.
Final combined backend regression:86passed,1optionalPGskip,5gate failures due to
untrusted NFS-mounted synthetic scratch parent. Intended ancestry guard rejected
the harness before any project copy. Only gate file rerun with root-owned0700
container tmpfs /WGS_test:7passed. No safety condition changed. One preexisting
upstream Starlette/anyio deprecation warning remains; no production DB test.

Latest readonly cloud inventory:25leases,0holders,6Masters/1active; UID-set hash
baa7dd2a10e5f021ac05c661acf62ae08571e8a420e2327e001410480b800e9b.
This supersedes earlier11holders/8Masters observation; no cloud mutation by task.
All six new private collector target filenames are absent, so installation will
not overwrite existing SFS/gate/runtime configuration.

Whole-branch review found activation compatibility risk before cutover: new
catalog caller choices need the new node gate, not merely custom-mode disabling.
Retained private gate cannot claim those choices effective. Consolidated final
fix wave must fence new catalog-option activation while preserving old submission
and scanner/dispatch behavior. No service deployment performed while gate open.

Task3 scoped-approved collectors installed separately while panel final fix is
pending. Exactly six new script/module files plus non-secret env map under test
private root; no existing files overwritten. runtime.env, gate, forced wrapper,
Cloud Eye config/collector/launcher SHA256 unchanged. Heavy PID148291, unconfigured
BSS PID148292; existing SFS PID17658 preserved. No boot/system service installed.
Heavy once returned verified0/25,modeenforce,waitingnull with
waiting_snapshot_unavailable;60second collector now refreshes this test spool.
BSS once reportsnot_configured/dedicated_billing_credentials_missing without
SDK credential lookup/network. API/UI activation still waits for final fix.

Rollback helper P2 synthetic test on BS10610 cached backend/networknone:
5passed (after-accept pointer restore, already-old pointer, unexpected pointer,
wrong predecessor image and bad health). No actual rollback or Docker calls
inside the synthetic tests. Scoped rereview required before helper use.

### Candidate cutover recipe (not executed)

1. Freeze the reviewed implementation commit. Export only tracked source via
   `git archive`; do not upload local .env, runtime evidence, node credentials,
   node_modules or source-project data. Record archive SHA256 and SOURCE_COMMIT.
2. Stage a new immutable `releases/20260912-opt-<commit>` under the verified test
   control root. Preserve the old shared bind through an explicit Compose
   override at `/data/airflow-demo`; do not create an independent mutable root.
3. Build frontend with the cached lock-bound Node22/nginx images, pull=false and
   network=none. Backend uses the verified existing cached dependency image
   with the new readonly source mount; do not invoke its network-installing
   Dockerfile. Compare requirement/lock files before relying on this image.
4. Retain both existing external test env files. Render Compose into process
   memory and validate changed service mounts, readonly /sg2 and /bi, switch
   values and networks; print only the approved safe fingerprint, never secrets.
5. Use `up -d --no-deps --no-build --pull never` for the explicitly reviewed
   affected service names only. Do not run a blanket Compose up, migration/init,
   worker recreation or network/volume cleanup. Gate replacement is independently
   checksum recorded and restricted to the test private path if activated.
6. Health/API/browser checks precede changing the test current symlink. Compare
   all protected service IDs with the baseline and ensure existing source mounts
   remain pinned. If failed, recreate affected services with prior source/image
   contract; retain all runtime, database, pending and project data.

The source-based rule logger correction does not replace an already running
Master image. Synthetic producer/consumer contract tests prove the patch only;
new live child-rule event capture needs a separately compatible producer release.

Source packaging precheck through7033185: backend requirements and frontend lock
files are unchanged from e107f3b. Tracked-file name scan found no .env, secret,
credential or id_rsa paths. Repeat after Task3 before exporting the final archive;
this does not replace content/security review.

### Node gate drift precheck

Readonly test-private gate SHA256:
`589e1f9f3d870b1f081a8939e85e241a01691bfcaff73994d47b9159d1ea0e4e`;
forced-command wrapper SHA256:
`0f0531297c00780d125f8221992aa0a51c5263843e10740d04246ef8c1edff37`.
Compared privately with e107f3b source: node gate lacks4.2.1 allowlisting,
request visibility retries, projected handoff identity fields and the newer
frozen Step7 operator-config validation. It uses configured WGS_PYTHON, whose
test runtime.env currently points to nipttest, rather than the audited source's
WGS preparation interpreter. No private env/wrapper was copied or changed.
The non-secret gate source was retained only in ignored local review artifacts.

Do not claim source-mounted panel release also activates a matching node gate.
Resolve its interpreter/release contract with the already-recorded shared owner
drift before execution activation; preserve the old hash until a reviewed
test-only replacement is explicitly recorded. Monitoring/resource panel deployment
does not depend on enabling custom projects or running owner prepare.

- Task1/2/3 scoped reviews and integration review.
- Exact candidate targeted backend, gate and UI tests plus cached frontend production build.
- Feature environment rejection, synthetic isolated project preparation, API contracts and no source/pending changes.
- Fresh preflight container IDs/mounts, filesystem authority, gate hashes and active workload inventory.
- Post-deploy health, observed API/UI version, submit rail/options, rule filters, QC provenance, estimated progress and partial Heavy metrics.
- Browser desktop/narrow layout and refresh state; do not submit real analysis from the browser.
- Compare protected container IDs and scan/dispatch switches with baseline.
- Record rollback commands and final known limitations without deleting data.
