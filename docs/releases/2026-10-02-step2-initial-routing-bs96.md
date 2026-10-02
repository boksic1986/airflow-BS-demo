# BS96 first Master after Step1 recovery

## Scope and approvals

Task: `W423-323D3F-STEP2-INITIAL-ROUTING-20261002`.
The human approved the bounded glue repair in coordinator message
`01a0fc79-2523-7f22-9a6d-8d190e1abdc2`. Independent code review accepted
commit `b86105225da0484d663aa830554ff581764b3d15` and the BS10610
GREEN3/GREEN4 results. The deployment checkpoint accepted the exact local
targets and fresh active-impact evidence. See the
[implementation and acceptance record](../reviews/2026-10-02-step2-initial-after-step1-resume.md).

## Actual deployment: 2026-10-02 12:42:43Z

Host `server96`, control root `/data/airflow-WGS`, node identity `6801:520`.
The two targets are on local ext4 `/dev/sdb2`. The existing canonical path
name contains an older commit; this record identifies its actual new bytes.

| Target | Old SHA256 | Installed SHA256 | Mode |
|---|---|---|---|
| `/home/ctapa/.config/airflow-common/releases/initial-recover-a2a0bbc-c8d07c21/scripts/cce_paired_runtime.py` | `66f7999a27c4232fc05746c74e9dd838eccf291817cb91a84c454e6a469dd084` | `981e7e82a0054a38d233a64c4120219094c34879b5820661d08907230806f588` | 0644 |
| `/home/ctapa/.config/airflow-common/policies/initial-recover-a2a0bbc-c8d07c21-v2.json` | `033a58198b5cb8c9140fda1bfd89c150d1fe173cf2bb7bf4548793dcafec5ace` | `ec6f35920a10e2879f34602c112325d31be1aaedee68717d3027caa8b2ba5210` | 0600 |

The policy delta is the single `writers.platform.sha256` byte replacement.
Original source/policy bytes, exact manifest and once/success receipts are
private under
`/home/ctapa/.config/airflow-common/candidates/w423-323d3f-step2-initial-routing-20261002`.
Directory mode is 0700; saved files are 0600. Manifest SHA256:
`1c81d4593f337175b324b9c35054fd963af4621aeb6f0eb3b54bff489486b6be`.

Old-SHA CAS, same-parent temporary files, fsync and atomic replacement preserved
owner, mode and xattrs. The source was replaced before its policy pin; the
existing trust check rejects the transient mismatch. The actual WGS environment
imported its gate and called only `selected_runtime()`, successfully selecting
the unchanged nipttest native source/operator Python. Related and unreadable
ctapa process counts were zero before and after installation.

All five restricted wrappers, `wgs_resume.py`, both bootstrap documents,
native runtime/guard, node200/GATK source and policy, services, images, mounts,
route, SSH configuration and environment retained their bytes. No maintenance
wrapper or new admission mechanism was introduced. No native package was
installed and no workflow or cloud request ran during the import check.

## Recovery and current operational evidence

Run `WGS_20261002_095408_323D3F`, attempt 1, received exactly one normal
`resume-stage` POST for `step2_master` at 12:43:29Z. Key:
`w423-323d3f-a1-step2-initial-routing-20261002`.

- Action: `resume_c17cd7cf8b3ab245ae80304d`.
- Platform Step2 generation 2: `wse_c67b199d729c19f374c2eb51`.
- Request hash: `c6c6f1e8dd471d7ceba4cd6d3616cd4f459601fbd3f4f6333557b085c2cf0ce8`.
- Step2 business success at 12:45:17Z; SHA256 `1ffdff2213a4561c429523e8bf56e8ed38c27b8ca2a760b283a56480e97f6a6d`.
- Native terminal succeeded, matched business SHA; Airflow submission succeeded.

An exact current producer/handoff read at 12:49:47Z confirmed the initial
submission journal and `START_CONFIRMED`. Native first generation is 1;
the frozen view's platform producer matches Step2 generation 2. Master Job UID
is `eb02fef8-5f0d-46ab-a5dd-41a593b9494b`, Pod UID
`cf2ab97c-b078-41e8-8252-a2f906650dc0`. This read made no cloud query or write.

Step3 naturally registered `wse_b7f6bc858e2a3284ed0c01a0`, generation 1,
request hash `744d85bdf5b47002a834c16022e628ff8b83ea2ba1448d0454f7e007fff4d8b1`.
At 12:47Z native monitoring was running, 1/333 completed, 0.3%, retry count 0.
Airflow and the public run were running. The 12:51Z workspace response showed
`step3_monitor` / `WGS workflow running`, Step1/2 success and Step4–6 pending.
The old `submission_phase=failed` and workspace percent 0 remain projection
limitations; this release did not change them.

## Evidence and continuation

Private local evidence is under
`C:\Users\11217\.codex\worktrees\gatk-prod-compat\airflow-demo\.codex-artifacts\wgs-step2-initial-routing-20261002`:
`production-impact.safe.jsonl`, `production-native-facts.safe.jsonl`,
`deployment-once.safe.jsonl`, `resume-step2-a1-once.safe.jsonl`,
`current-stages-after-step2-resume.normalized.safe.jsonl`,
`current-master-start.safe.jsonl`, `current-workspace-stage.safe.jsonl`.
The original stage read is preserved; its initial `identity_matches=false`
used the wrong generation field. Local normalization with `stage_generation`
confirms every actual execution/hash/generation match. This was a reader
projection error and caused no production change.

Deployment and recovery once guards are consumed. Do not replay them or
mechanically downgrade after the new execution registration. Before recovery,
known installation failure would have restored only the original pair using
CAS; unknown SSH outcomes require receipt/hash readback, not replay.

The unique hourly monitor continues read-only Step3–6. Prepare, Step1 and the
five selected samples remain successful and protected. Complete Step1–6
receipts, final results and consistent Airflow/platform/frontend success are
still required. No Step7, deletion or cleanup is authorized by this release.
