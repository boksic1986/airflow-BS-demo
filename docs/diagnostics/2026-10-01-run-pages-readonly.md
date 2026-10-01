# PERF-RUN-PAGES-20261001: bounded production timing

## Scope and environment

Coordinator airflow-cloud-demo authorized diagnosis only for slow Batch Runs
and Run Detail loading. The user later clarified that entering detail from
Batch Runs is especially slow, with GATK more noticeable. No fix, deployment,
restart, cleanup, new analysis, DB direct access, login/session creation,
policy/gate change, load test or instrumentation install was performed.

BS96/server96 was checked at 2026-10-01 15:44:37Z. Actual backend7aadaf93 and
frontend4df1, both images and complete mounts, matched the final restored
release record. `/data/airflow-WGS/current` remains
`releases/20260912-panel-opt-4d3d24e6` as recorded; actual product source is the
approved final80 merged mount. Eleven relevant backend file hashes and three
frontend dist hashes matched the pinned final merged manifest SHA256
`5f1d1e9ea8ee9d7bbb2d004c00dbd23224a8d6492faa72b08a36bb83f3466046`.
Auth and WGS/GATK execution are enabled; scan is effective true and auto
dispatch effective false under the original policy. Watermark is unchanged.

Important mounted source SHA256 values:

| File | SHA256 |
| --- | --- |
| main.py | 84cf19122bededce743b1205f17063187200188be3feb6ead6f0e02619d1bab5 |
| run_service.py | 6cdf54bc79dda83996daaf66eb0399c813efda68a833047be1307ae3e08e1c91 |
| gatk_step7_service.py | 58d6d03ff300cb6e5b0ae704479943901b70329b8531d0f487288637b3bd5e33 |
| pipeline_registry_service.py | 3a58c412e4cade8e0583092b33c6f7c39c55a1de1f01291cbff22e7a23299978 |

## Measurement

One request per listed endpoint, serially, with a fresh HTTP connection.
TTFB measures elapsed time through the first response body byte, including
connection setup, headers and server wait. Total ends after reading the body.
Bodies were parsed only in memory; output contains sizes and nonclinical counts,
without tokens, cookies, sample identifiers or full payloads. Measurements were
captured locally, with no remote evidence file written.

Authenticated API measurements used the existing internal service token at
backend loopback. `main.py:185-190` takes this branch before browser session
authentication. This channel bypasses session/cookie lookup, nginx, user
network and browser navigation. It is not a browser end-to-end measurement.

| Endpoint | UTC start | HTTP | TTFB seconds | Total seconds | Bytes |
| --- | --- | --- | --- | --- | --- |
| Gateway health, host without internal header | 15:45:54 | 200 | 0.006957 | 0.006982 | 15 |
| Internal health | 15:45:54 | 200 | 0.010767 | 0.010827 | 15 |
| Internal runs, pipeline=deployed, created_desc, limit20, offset0 | 15:45:54 | 200 | 2.278214 | 2.278426 | 86103 |
| Internal historical GATK base detail | 15:47:20 | 200 | 0.483291 | 0.483357 | 2200 |
| Internal historical GATK workspace | 15:47:20 | 200 | 0.124054 | 0.124118 | 6029 |
| Internal historical GATK samples | 15:47:21 | 200 | 0.013691 | 0.013732 | 5773 |
| Internal runs, pipeline=gatk, created_desc, limit20, offset0 | 15:50:35 | 200 | 0.062711 | 0.062800 | 20475 |
| Internal /api/platform/capabilities | 15:50:35 | 200 | 0.004912 | 0.004968 | 515 |

Historical representative is `GATK_20260929_024231_F246CD`, success, 43 samples
and 562 rules. Deployed first page returned20 of27 records (17 success,
2 cancelled, 1 failed). GATK first page returned all6 records, all success.
Capabilities reported Production and two pipelines.

Initial container-origin requests carrying the internal header to the formal
gateway returned403: health0.009552s and runs0.001994s, 153 bytes each. These
responses are retained as rejected-entry evidence, not successful page API
timings. No whitelist or auth setting was changed. Gateway health without the
internal header subsequently returned200.

## Resources and existing logs

One docker stats snapshot at15:47:23Z: backend CPU0.16%, memory565.4MiB;
frontend nginx CPU0.00%, memory108.8MiB. Neither showed high consumption at
that instant; this does not rule out an earlier or intermittent resource issue.

The existing last-five-minute logs, capped at200 lines per service, contained
117 backend HTTP200 responses and no matched exception class or5xx; nginx
contained131 HTTP200 and the two diagnostic403 responses, without5xx.
Raw logs were not output. The actual nginx `main` access format lacks both
`request_time` and `upstream_response_time`, so those logs cannot reconstruct
the original browser request durations. Log configuration was unchanged.

## Findings and limits

- The deployed20 list request spent about2.28s before the first body byte;
  body transfer then took about0.00021s. This identifies waiting in the
  internal response path, without separating DB queries from file reads.
- The selected GATK detail/workspace/samples and capabilities returned200
  quickly in this sample. The user's slow navigation has not been reproduced
  or explained by these timings. GATK6-record and deployed20-record timings
  cannot isolate page size, pipeline or cache effects.
- Base detail ran before workspace, so subsequent file/cache warming is
  possible. Their difference does not measure the isolated workspace cost.
- Run Detail publishes detail after workspace returns. The normal200 first
  screen does not necessarily wait for the following samples request.
- WGS detail/workspace can lazily create a missing execution_dispatch row.
  Existing release evidence did not establish the association for a candidate;
  those GETs were therefore omitted to preserve this task's no-write scope.
- Existing GATK capability projection hashes frozen bundle files on each
  eligible read. This is a source review candidate, not a measured root cause;
  no profiler, trace or stage timing was installed.
- Root-cause attribution for browser session authentication, navigation,
  frontend lifecycle and intermittent latency remains with the coordinator's
  existing frontend/backend source review. No extra production sampling is
  included in this report.

## Evidence and commands

Local evidence folder: `.codex-artifacts/perf-run-pages-20261001`.
Scripts were piped literally through `ssh BS96 "tr -d '\r' | bash -s"`.
All four remote scripts exited0. The initial403 group is deliberately retained.
The manifest pin is enforced by group1-fingerprint-timing.sh before its JSON
fingerprint is emitted. Its existing local copy in
`.codex-artifacts/w423-unified089-20261001/final-gateway-final-BS96.json` also
hashes to5f1d1e9e below; the four result JSONL files do not themselves contain
that manifest digest.

| Local result | SHA256 |
| --- | --- |
| group1-result.jsonl | a3db466fae22c60c76a3e6448dd52b713c2145529cc44e4c0412536f710aebbd |
| group2-result.jsonl | bd6a5e916c37166f4b61d84bdd766901470c80dfea3e4c9b72dffbde152a3945 |
| group3-result.jsonl | f87e70ab40995fede5ec03beb5cb921c091abccd63a6132596263f45679b1aca |
| group4-result.jsonl | 6e72028725e819d49b815fe6dacc8ce7ef81fbbd12be44eb06e6c50200e7019a |
| group1-fingerprint-timing.sh | e505fbfc3b76b19107a0dd2598698fab228f346eeac2541338f147dec98a5d65 |
| Existing final-gateway-final-BS96.json | 5f1d1e9ea8ee9d7bbb2d004c00dbd23224a8d6492faa72b08a36bb83f3466046 |

No implementation tests were requested or run. Local documentation whitespace,
task references and evidence hashes are checked; these are not runtime tests.
Only documentation changes need rollback; production state was not changed.
