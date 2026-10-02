# Initial Step2 after Step1 recovery

## Scope and authority

Direct human message `01a0fc79-2523-7f22-9a6d-8d190e1abdc2` in the coordinator
thread approved the bounded Airflow submission/reader fix, minimum synthetic
validation on BS10610, reviewed BS96 deployment and normal same-attempt Step2
recovery. Airflow thread `01a0e728-4c99-71d0-87e9-987b311022c9` is the sole
implementation, deployment and recovery owner. Native/WGS core, public API,
DB/schema, package installs, images, other runs and all data remain outside this
change. Source validation is complete; production deployment has not happened.

## Actual failure and correction

Run `WGS_20261002_095408_323D3F`, attempt1, retains successful preparegen2 and
Step1gen2. First Step2gen1 `wse_f8d5379ec0f42ccb961215ae`, request hash
`4ea810b8ec4a1dbd9538602bf31b2f6b81f4f5483669eeba8eb619bb0136c99a`,
inherited action `resume_e41f326ef299c287817b94ff` and entered replacement
recovery. Its error was `current owner has no unique native submission`.

The once-only 11:54:53Z exact read found zero native views/replay/submission
candidates, no frozen handoff/CREATE intent, and no exact Master Job. The
directory CM was OWNED by this run/attempt, native initialgen1 action with an
empty Master UID. This is a first-Master routing error; no full cloud inventory
was needed or claimed. Safe diagnostic:
`../../.codex-artifacts/wgs-3a001e-direct-resubmit-20261002/current-step2-exact-native-owner.safe.jsonl`.

Only `scripts/cce_paired_runtime.py` changes production behavior:

- Extract the existing initial producer into a function called while the
  existing writer scope is held; its CREATE intent, reconciliation, handoff,
  UID binding and VerifiedMasterResult logic remain intact.
- Under the existing recovery worker/launch/writer locks, recognize an initial
  continuation using the exact successful Step1 execution/generation/receipt,
  initial registration action, frozen inputs, journals and directory owner.
  New initial dispatch requires an empty UID and exact absent Job. Matching
  same-producer replay reuses its journal and allows only its proven bound UID.
  Other/unknown producers stay on the existing reconciliation/recovery path.
- Independently inventory the bounded submission/recovery/resume artifacts
  before a fresh initial CREATE. The legacy journal reader can skip entries
  without platform identity, so only authenticated current-producer journal
  and directory replay artifacts are allowed in this first-submission scope.
  Other or orphan JSON/directories/intents block dispatch and remain intact.
- Select downstream initial/recovery journals by the exact verified platform
  producer identity, then keep the existing native/receipt/owner validation.
  The presence of a recovery action does not determine journal type.

Requests, action and hashes are preserved. No run-specific branch or native
change is introduced. Platform Step2gen2 can create native initialgen1.

## Minimum BS10610 acceptance

Fresh preflight confirmed server10610, test control root/current release,
actual backend/worker RO source mounts, scan/auto gates false and the existing
cached image. The isolated container used uid6708:520, `--network none`, RO
platform/native/plugin/pytest dependencies, no bytecode/plugin/cache writes,
and a fresh evidence root. Native runtime SHA matched installed production:
`bfa1e15f75f83ebe816897e1e454225ca2f78128b1761a2212230d033cd3c3d1`.
No clinical canary, cloud operation or service change occurred.

Remote root:
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/wgs-step2-initial-routing-20261002T1206Z`.
Local result/helper directory:
`../../.codex-artifacts/wgs-step2-initial-routing-20261002/`.

| Phase | Actual result | Raw log SHA256 |
|---|---|---|
| red | 1failed with the exact production no-unique-submission error | c8f2537a35ffe78add45336982a3dc5bb3691c586df82b73cde8cc1163fa0c6c |
| delta | 5passed/3failed: bound-UID replay and reader gaps; failed-Step1 test injection initially ineffective | b3fc05c277284464010a87727dbdbe25cc98be9339aa4f4eeb80a98399590e20 |
| green | Collection RC4, no tests ran: incorrect parameter node IDs; no product change | a86d5407582f8194178cfe55ad14c8d3f889bb08114ba72e71f2d0fa0b65d45a |
| green2 | 15passed/1failed: older WGS fixture lacked required runtime-root configuration | 2a292c0f692f30b090974c1d085b8955de1533ddffd89294d69b22a884c98d1a |
| green3 | 16passed/RC0, 18.77s | b9e46d2f00ba40d358aa91e1c9733eb2737034867c0dc2767ab5aa965e4dfcc1 |
| review-red | 1failed: unknown legacy recovery JSON plus native intent did not block CREATE | 07c6b935ff14e6974020e4a93b22e1c41f26bf198ce338e3855b8d2f4f96a57e |
| green4 | Final affected delta 10passed/RC0, 7.59s | 1d25adfa7767b65ef644a7fe82666e8765abb460ae9e6f690552ca2d00146c14 |

Ten new cases cover platformgen2/nativegen1 initial submission and replay,
unknown CREATE/no second CREATE, late matching-Job reconciliation, foreign
owner, failed/changed/wrong-generation predecessor, unknown journal rejection
unregistered legacy recovery JSON/CREATE intent and carried-action reader
reconstruction. Seven existing selected cases cover
real WGS/GATK replacement, unknown/lost-response/bound-crash initial submission,
normal GATK initial submission and recovery. The older `registered` fixture
now supplies its synthetic runtime root; production validation was not relaxed.
The failed-Step1 fixture writes a synthetic failed receipt and matches its
actual SHA, instead of attempting to regress an immutable successful receipt.
Only this minimum selection ran; no full-suite or repeated smoke was requested.

Candidate platform SHA:
`981e7e82a0054a38d233a64c4120219094c34879b5820661d08907230806f588`.
Final tested archive SHA:
`b536227d6a3e7240578970decd4f3c9806cdea20e36193ccc5fb9565172de2c3`.

## Production checkpoint and rollback plan

After independent code/GREEN review, collect the exact actual source/policy,
consumer/active-impact facts and original private bytes before deployment.
The planned same-canonical-path delta is the 96 platform file and only its
96 local policy `writers.platform.sha256`. Both bootstrap documents, native
runtime/guard/package/console/RECORD, 200 policy/source/GATK, wrappers and images
keep their original bytes. A manifest must identify the new commit/SHA and
old private rollback copy; the historical directory name is not a byte version.

Use the existing restricted maintenance window, old-SHA CAS, atomic replace,
fsync and exact paired readback. Restore original source/policy while still
closed if installation fails before recovery. Do not mechanically downgrade
after a new execution is registered. The deployment checkpoint must approve
actual target/modes/pins/active impact; no production write is recorded here.
Then use only the normal same-a1 Step2 resume API once, excluding successful
prepare/Step1. Record new action/generation/execution/hash, actual Master
UID/START and Step3 evidence. Unknown POST results require readback, not replay.
Full Step1–6/results/Airflow/platform/frontend success remains outstanding.
