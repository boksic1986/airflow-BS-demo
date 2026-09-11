# OPT20260912 resource interface research

Read-only source/documentation research; no billing request or credential change.

## Official BSS contract

- POST https://bss.myhuaweicloud.com/v3/payments/free-resources/query: ListFreeResourceInfos; offset/limit1..1000; region_code/service_type_code_list/status filters; total_count and package free_resources. [Official](https://support.huaweicloud.com/api-oce/api_order_00027.html).
- POST https://bss.myhuaweicloud.com/v2/payments/free-resources/usages/details/query: batch1..100 free_resource_ids; amount is remaining, original_amount total; quota reuse cycle and start/end time determine current allowance period. [Official](https://support.huaweicloud.com/api-oce/api_order_00028.html).
- GET https://bss.myhuaweicloud.com/v2/bases/measurements: unit dictionary; use names/abbreviations, never assume measure IDs. [Official](https://support.huaweicloud.com/api-oce/qct_00006.html).
- Minimal permission billing:resourcePackages:view; GlobalCredentials/domain account scope, not CES regional BasicCredentials. Dedicated private billing identity/config, not blind reuse of existing Cloud Eye credentials.
- CPU core-hours and memory GiB-hours [Autopilot](https://support.huaweicloud.com/price-cce-autopilot/cce_03_0027.html). OBS request allowance may be absent depending package [OBS](https://support.huaweicloud.com/price-obs/obs_42_0011.html); absent is not0.
- Iterate complete pages with bounds/nonadvancing checks, batch usage details, resolve units; atomic publication only after all complete. Decimal values preserve precision; no sum across incompatible units/cycles. Hash identifiers for public keys; do not expose order/package resource IDs. Preserve last-good with explicit failed refresh/stale reason; hourly polling, no browser-triggered billing calls.

## Actual Heavy unit

Local reviewed executor archive D:/pipeline/cce-heavy-T255-build/executor-c44cfd4.tar.gz (biosan5) and cce-heavy-T255-runtime/docs/architecture/heavy-io-profile-contract.md: rule names classify heavy workloads, but acquire holder is run_label:job_name. A GroupJob has one Kubernetes Job and one claim. Public unit must be heavy_work_job/work_pod, never claimed per-rule occupancy.

Root test preflight found absent /data/wgs-evidence/heavy-slot-global.json. Repository launcher uses production fixed paths; independent test producer must use test-owned private config/output and never mutate quota/workloads. Current unavailable is not evidence that slots are0 or enforcement broken.

## Live read-only namespace observation

t640 test-gate runtime.env explicitly uses existing /home/ctapa/.config/wgs/cce.yaml; private configuration contents never copied. Node UID6801 can write test evidence root and /sg2/50.ctapa/project/HWcloud/WGS_test, unlike backend RO source mount. No test Heavy producer/launcher installed in /home/ctapa/.config/airflow-wgs-test.

Invoked collect in-memory without writing snapshot: ValueError Master waiting snapshot missing or stale. Narrow kubectl read-only metadata queries:25 named quota Leases,11 reserved holder identities, complete pagination;8 Masters total, one active with mode=enforce,limit25 and status path declared. No names/private data printed, no workloads changed. These cloud workloads are not active test Airflow runs; do not restart or claim their analysis acceptance.

Required projection repair: occupancy can be authoritatively known from complete Lease inventory while waiting is unknown. Separate per-field availability/freshness/reason rather than discard valid occupancy because an unrelated waiting snapshot is absent. Unit remains reserved heavy_work_jobs; holders are not force-reclaimed. Existing available flag compatibility must not turn missing data into0.
