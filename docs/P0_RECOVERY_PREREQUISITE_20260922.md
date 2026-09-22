# P0 recovery prerequisite review — 2026-09-22

Status: external producer/artifact implementation approved; isolated synthetic
testing released during the existing upload. Formal service integration/deploy
still gated. CR-01 through CR-05 are not complete. Baseline: test `1da45f3`.

## Verified source findings

- `scripts/gatk_runtime_gate.py` Step3 turns a nonzero runtime exit into the last
  2000 characters of stderr/stdout. This is not structured Worker-create fatal
  evidence bound to Master UID and execution identity.
- `scripts/gatk_resume.py` still checks that OBS results are empty via
  `inspect_reset_obs` and resumes through `runtime.step2`. This needs adapter
  alignment before the proposed checkpoint recovery can be enabled.
- Read-only BS10610 inspection found the executor checkout at
  `/mnt/biodevrwbi/33.chenjiucheng/project/wgs-cloud-platform/projects/snakemake-kubernetes-plugins`,
  HEAD `1ca1e88`. Its `snakemake_executor_plugin_kubernetes/__init__.py`
  lines 923–958 create a Worker Job and append its discovery manifest only after
  a successful response. Lines 1370–1403 wrap errors generically and include a
  delayed replay after MaxRetryError. They do not produce the proposed trusted
  final Worker-create failure record or prove lost-response reconciliation.
- This checkout observation does NOT establish the version installed in each
  frozen WGS/GATK Master image. Exact release/artifact binding remains to verify.

## Required decision

Confirm the external executor source and release-artifact work needed for CR-01,
including identifying the exact WGS/GATK Master plugin versions and delivering
the scoped fix through their normal release path. Do not patch frozen bundles,
infer fatal causes from arbitrary log keywords, rebuild unrelated Worker images,
or enable automatic recovery on historical attempts.

After confirmation: fix/prove the producer contract first, then implement
CR-02 budget/fences, CR-03 adapter Resume/DAG continuation, CR-04 shared display,
and CR-05 focused synthetic acceptance. Keep automatic policy disabled until its
adapter path is accepted. Production deployment is separate.

## Checks and environment

Only Git/source review and read-only SSH were performed. BS10610 returned
`server10610`; current resolves to release `20260912-opt-4d3d24e6`, while actual
backend `/app` is mounted from `20260917-native-ui-76915d8-r2/backend`.
Neither the symlink nor this runtime is asserted to contain the development tip.
No service, permission, database, real run, image, main or production was changed.

Two SSH attempts failed at the BS jump host with connection reset/aborted;
the jump host was then reachable and bounded read-only retries succeeded.
Remote `rg` was unavailable, so source inspection used `grep` and `sed`.
No runtime tests were run: no implementation exists yet and the producer
prerequisite needs confirmation. Documentation changes are reversible with Git;
no analysis data rollback is involved.
