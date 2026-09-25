# P0 final candidates and operational gates — 2026-09-25

Candidate evidence only, not a deployment or activation receipt. The coordinator
does not run builds/Compose; each repository owner executes its assigned scope.
The immutable [Task5 record](2026-09-24-p02-task5-offline-artifacts.md) remains
historical and is not overwritten by these successors.

## Plugin candidate accepted

- Owner: `WGS-cloud-plugins`, task019f9d79-be3f-7701-af33-3595d72bbfac.
- Version: `0.6.4+bs8.dev2`.
- Source: `5ffcb07bf20d45d48b0be0fca4ad6c1ae111a82e` (parent81132cf).
- Source tree: `36ad4f02572050675cfb374a3792680203c432b4`.
- Documentation HEAD: `4f10c2768ab3fcaf284fb724ee2c8b7f0d20e958`.
- Wheel SHA256: `4adf2595794b3f08cc22b506173c33e99dcad795102417079f8a2d042a828b1a`.
- Remote evidence root:
  `/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/smk-k8s-group/p0-final-plugin-20260925`.
- Wheel below that root:
  `dist/snakemake_executor_plugin_kubernetes-0.6.4+bs8.dev2-py3-none-any.whl`.
- Owner receipt: `D:/pipeline/task-artifacts/p0-final-plugin-20260925/receipt.md`
  and `provenance.json`; committed component record `docs/P0_FINAL_PLUGIN_BS8_DEV2.md`.

Actual-wheel checks:4 passed9.97s, all10 packaged Python files match source bytes;
plugin/logger load from wheel-site, Snakemake metadata/import from cached image
9.24.0+biosan1. Cases: RPC candidate/redaction, mixed-error sealing, actual
Snakemake submission-failure close, representative Worker TTL. No source-suite
repeat. Coordinator inspected receipt/provenance and Git diff: only three version
values changed in two source files; documentation separate, worktree clean.

Two stopped harness failures were reported and preserved: build-only testdeps
shadowed image Snakemake; checker incorrectly located failure_summary under
executor rather than logger. Corrected harness only, strict path/version checks
retained. Final verify reused the existing hash-pinned wheel without rebuilding.
No shared pip install, dependency upgrade, WGS environment change, push or deploy.
Operator testing follows nipttest; compatible Master/executor image is separate.

## Native / WGS and GATK Master candidates

Owner `huawei-cloude`, task019f8355-2b77-7413-9553-6670c35a1a2f.
Native source `d84bace615a8f0c9b16f8e9d8c3f7f58a50ab2ee` changes only two version
strings from accepted1bc67fd; version `0.8.5+p02.dev2`. Worktree checked clean.
Wheel SHA256 `0b8737425f52ffb6e41a11afe5d706c810ab0d8a51a8d83c17ea784c6b61d0e5`.
Remote evidence root:
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p0-final-native-20260925`;
wheel `artifacts-attempt2/dist/cce_pipeline-0.8.5+p02.dev2-py3-none-any.whl`.

Accepted as offline artifacts only. TTL template3 passed; terminal module first
skipped because CCE_PLUGIN_SOURCE was missing. First supplement failed collection
importing submission_recovery from old base plugin. Corrected supplement uses
final WGS image, frozen plugin fixture, native wheel-site and task-local basetemp:
only the missing6 cases,6 passed/0 skipped in3.78s, no rebuild. Both image smokes
passed. Coordinator read raw logs/receipt and recomputed wheel/provenance/script
hashes; these match the owner's record. No further runtime checks required here.

Local-only image config IDs, NOT SWR manifest digests (RepoDigests empty):
- WGS: `sha256:d938f8e61fe88d9b28ad80ef4362747ab822ded6046748bc9937e41a807604d3`.
- GATK: `sha256:95d2fd8b6859ffbebc93b83b65bc15b6ab55ee7c253d6ff0d5240a12591e2e2f`.

Both image smokes assert Snakemake9.24.0+biosan1, plugin0.6.4+bs8.dev2 loaded
from image site-packages, no Operator cce_pipeline package, exact standalone
runtime/writer hashes. Owner receipt:
`D:/pipeline/task-artifacts/p0-final-native-ops-20260925/FINAL_NATIVE_RECEIPT.md`;
copied raw evidence under sibling `remote-evidence` and remote `artifacts-attempt3`.
Provenance SHA256 `44ff7b991be07c47be2a107286e3f8f20960768491650723ec37dd55b020bd59`;
corrected supplement script SHA256
`5720ac7d662388e770a6c673fa86e8d85509fb7e0a0a3fdc6d746108bc1c6de7`.
Native wheel remains under attempt2; no production or installed-version claim.

Execution-order reconciliation: owner reports old-base failure completed17:15:07,
then received the final-image/6-case correction; corrected6 passed completed
17:16:25. Exact app-message receipt timestamp unavailable. Raw failure retained;
pre-correction supplement script was overwritten without a prior hash, so no
claim of fully preserved script provenance for that failed attempt.

Stopped harness failures retained: attempt1 tried build/lib in read-only source;
attempt2 wheel built but checker imported nonexistent package_source_commit.
Corrected to original RW task scratch and actual provenance.source_commit API.
Attempt3 verifies the same wheel hash without rebuilding. Neither failure was a
business-code defect; no shared chmod/install or alternative privilege entry.

## Operational preflight — partial, gate remains open

Owner receipt: `D:/pipeline/task-artifacts/p0-final-native-ops-20260925/OPS_READONLY_RECEIPT.md`.
Owner verified BS10610/server10610 uid6708:520; control current remains
20260912-opt-4d3d24e6; backend /app uses20260923-step7-ae416fa read-only.
Scanner/dispatch false, recovery switches unset. WGS catalog/profile still pins
cce-pipeline0.8.4; no final-candidate activation. GATK actual writer/profile
coverage is not established by the WGS check.

Using the documented personal BS10610 Operator (no restricted-gate bypass),
namespace snakemake-ns and both declared SFS/OBS PV/PVC UID/Bound claimRef pairs
match. Snapshot:178 Jobs (2 active,172 Complete,4 without recognized terminal),
20 Pods (18 Running,2 Pending); all178 Jobs have no TTL. Existing objects are
untouched. Ten nodes' allocatable Pod counts sum1100; no ResourceQuota objects
listed. Neither fact establishes the provider AP/account limit or completes
all-entry concurrency accounting. Heavy11/25 alone is not Pod-capacity evidence.

AOM Prometheus binding/data freshness and alert/notification evidence are
unverified, not proven absent. A Kubernetes event collector alone is insufficient.
User has been asked for an approved read-only cloud control-plane entry and for
two bounded synthetic TTL Jobs plus exact failure cleanup; answers pending.
No cloud writes, historical TTL patches, AOM enablement/cost, notification send,
runtime install or service switch. Full operational acceptance remains open.

## Rollback / next

Before activation, do not select these candidates; retain old artifacts/evidence.
Next complete only authorized live gates; no more candidate rebuild/test work.
No production approval or same-batch rerun authority follows from this record.
