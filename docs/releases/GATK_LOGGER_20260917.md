# GATK group logger release

User-approved GATK main -> separate SFS assets -> BS10610 -> BS96 promotion.
No Airflow application/DAG code changes. Original dirty workspaces untouched.

## Published inputs

- GATK GitLab code: `aeff617029e597218ad835cd5a7dfd4a02b5abc4` (fast-forward
  from95bf89c through2d2972f; subsequent GATK commits may only record deployment).
- Repository root on both backends and node200 gates:
  `/bi/biodevrwbi/33.chenjiucheng/project/gatk-cloud-airflow/releases/aeff617-group-logger924`.
- Profile `gatk-scmc-v7.6.0`, revision `r2`.
- SFS `/workspace/gatk-cloud/pipelines/7.6.0-logger924-20260917`.
- Payload SHA256 `1c52af46deb023c6a76b4d9dfaaa3c66a84a9600ca00056eac6d0cee8c2e490c`.
- Master `swr.cn-east-3.myhuaweicloud.com/biosanwgs/wgs-cce-master@sha256:ee93eaf24505af753e853aa6c0786a67c3a6896d65539de39cfb3a74075bad5a`.
- Both `gatk_worker` and `gatk_sentieon`:
  `swr.cn-east-3.myhuaweicloud.com/biosanwgs/gatk-cloud@sha256:c696bc2881f73b18691de7c64ad89031e63bdf01e022afbcd89b343cd8adfae2`.
- Snakemake9.24.0+biosan1 plus matching Worker rule-status module. Four named
  GATK groups use the same Worker; fastp unchanged. Host cce-pipeline untouched.

SFS baseline was95bf89c, not the older Airflow source-directory name. Biological
workflow SHA `ebee79067e17544774ff9607fc714d197189abb49cc5b82af297abbee8b03701`
is unchanged. GATK main restores the already deployed Airflow handoff/version
discovery, retaining main's two-column sample map and per-sample reheader fix.

## Acceptance

BS10610 isolated cached Master/network none:8 unittest cases passed. New tests
first failed for missing handoff and V7.6.1/V7.7.2 source discovery. Existing
semantic tests remain green. Prior image checks proved two sequential synthetic
group children emit6 events, correct attempts, timer-cancellation fix and exact
SWR image IDs. No full biological workflow or real batch was auto-submitted.

Node200ctapa published the five static runtime files with a single-purpose Job:
payload SHA, inventory, baseline workflow equality, atomic new-directory publish;
Job gatk-release-publish-lf-20260917 completed1/1 in23s. No old SFS root/reference
or run changed. First CRLF archive failed the baseline hash guard before publish;
Linux Git export corrected it. The small failed staging directory is unpublished
and retained for audit. Completed serverless Pod log retrieval later returned
NotFound; Job completion and installer validation, not an assumed log response,
are the publication evidence. Temporary release ConfigMaps contain source only.

Both release APIs return r2. Backend-read source commit, profile root,
Master/Worker digests and build SHA checks passed. Business records remain4test/
8production,0active; production bio_gatk running/queued DAG lists empty.
Both actual gateways: GET /api/health200; POST /api/auth/login with empty JSON422,
which checks proxy routing without credentials or creating a session.

No real batch-wide event ingestion verified in this release. API observed runtime
identity intentionally remains unverified; historical reruns keep frozen images.

Final official CCE profile validation exposed an rN-only revision constraint:
the descriptive interim revision was corrected to r2 in aeff617 before handoff.
The official installed validator on BS10610 now passes. Both backends were
recreated once more for that final source/revision. The SFS marker retains the
runtime-payload source2f173d7; aeff617 only corrects external profile metadata and
documentation, and its five SFS runtime files are unchanged.

## Exact service changes and rollback

| Environment | Backend before -> after | Effective private Compose/rollback |
| --- | --- | --- |
| BS10610/server10610 |294cb11c1731 ->9943939015f6|`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/gatk-logger924-r2-20260917-control/{compose,rollback}.json`|
| BS96/server96 |5a8348a6d068 ->77e65737b68b|`/data/airflow-WGS/gatk-logger924-r2-20260917-control/{compose,rollback}.json`|

Only backend recreated for three settings: GATK_REPOSITORY_ROOT,
GATK_PIPELINE_ROOT, GATK_RUNTIME_PROFILE_REVISION. Effective environment compared
against live before editing. Source mounts remain test onprem-main-d705a46 and
production sampleinfo-f72a12e, not stale `current` symlinks. WGS v2, Clinical
output roots, scanner/dispatch/canary/local/SGE gates all preserved byte-for-byte.
Observer, scanner, ledger worker, Airflow API/scheduler/worker, probes, metrics,
frontend container, PostgreSQL and Redis retained IDs. No remove-orphans.

Node200 private runtime.env in airflow-gatk-test and airflow-gatk changed only
GATK_REPOSITORY_ROOT. Ownerctapa/mode0600 retained. Private rollback sibling:
`runtime.env.pre-logger924-20260917`. No key/config contents left those directories.

nginx -t and graceful reload performed after each backend recreation. The other
platform task had just fixed an independent502 from cached old backend IP .10
versus actual .12; this release includes real proxy-API verification to prevent
that regression. No nginx configuration or frontend rebuild required.

Rollback restores only each private backend Compose and corresponding gate
runtime.env, then reloads nginx. Retain new SFS assets and all analysis state.
Recheck active tasks before rollback. Existing bundles are never regenerated.
The final rollback.json deliberately references the original pre-release
81f347e binding, not the rejected interim descriptive revision.

Operational failures handled: an NGS SSH reset used the approved BS jump; node200
task evidence path required /sg2/biodevrwsg2 rather than /sg2; production private
Compose was chenjc-owned, so used its owner instead of ctapa, without ACL changes;
list-form environment normalized after verifying exact live values. No retry
submitted a real analysis or overwrote assets.
