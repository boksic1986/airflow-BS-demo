# W423-ACK-RECONNECT-20261003

## Scope and current operating state

Direct human authorization in the coordination thread: `01a0ffea-32b1-77a1-b7f0-4ee45758a933`, accepting the minimal startup ACK correction and reconnection of the existing cloud computation. The automatic hourly monitor remains stopped under the separate direct instruction `保持停止自动监控`.

Analysis `WGS_20261002_095408_323D3F`, attempt1, original five inputs and release `wgs-4.2.3-3f98682-perm2775` remain fixed. Current failed observer is action `resume_4d7613c596c453f582e8764c`, Step3 generation3, execution `wse_a8c703f0c3c1e6491e74cad8`, request hash `fd1b03b8fa151f4fd2d90903934e28377aa3cd9d70257ad486860821b2a03686`. Its real cloud producer has native generation2, Job UID `cb75dde6-d06c-4f06-a4c3-63db8dc04ca7`, Pod UID `671407ee-676a-4bf5-9000-01f1270cfb4e`. Original compute deadline is `2026-10-07T12:45:38.887362+00:00`.

Fresh 04:06:22Z exact Job/Pod read found active/Running; 04:06:54Z actual ACK SHA `24a224a620fac3a7ff7dbf1a0fde8bebdbb575427d2c073d38f2b5334e3ff8f3` matched all original identity keys. Its confirmed epoch was within the original startup deadline. Host/AF/platform remained failed; API success or stale controller handoff never establishes cloud completion. Fresh 04:38:16–18Z BS96 host/current/service mount/environment/gates and the failed platform/Airflow tuple matched. No production source change or reconnect has yet been executed.

## Existing entry and minimal repair

Same-key Resume returns the existing action. Gate and native StageExecutor preserve the old generation's terminal receipt. A normal new key registers a new observer generation within the same attempt and archives prior requests; it does not reopen old generation3.

The installed paired source excludes recovery `created` journals from its selected observer path; ordinary `prepare_monitor_registered` therefore enters `resume_registered`, which includes replacement. The patch adds a strict WGS path for the authenticated previous Step3 producer (`resume_previous_execution`) and, for downstream observations, the already verified exported producer binding. It verifies the unique journal, original producer request bytes/hash, canonical parent/view, full recovery identity, frozen inputs, original compute deadline, exact directory owner and native handoff/UID/Pod.

Factory registration/storage validation runs under existing writer serialization before assigning the independently verified producer owner. This avoids asking the schema3 cloud current-owner resolver to find START_CONFIRMED before the pending ACK has been accepted. The original guard and its identity/ACL/locking rules are unchanged. The selected native producer retains its platform execution identity; the observer never becomes its producer. The directory lock context retains its exact legal key set.

Only native `_finish_master_handoff` for an already validated `START_SENT` record accepts the real ACK; this branch only awaits confirmation and sends no START or inputs. Native commit `e93b20c381504702147ae4dd01cd8d77d7b00f19` changes the live ACK read to the existing per-Job-UID archive. The paired patch leaves the recovery journal bytes/state `created` intact. Subsequent selected/expected-source observations revalidate this confirmed source and use the existing read-only observer. Any selected-candidate failure stops; no replacement fallback.

This WGS-only glue repairs the present WGS Resume boundary. The native ACK change remains shared. This is not a claim of a new GATK production acceptance, new public endpoint, database schema, permission, or recovery framework.

## Source and evidence pins

| File or evidence | SHA256 |
| --- | --- |
| Installed paired baseline, exact `git show b861052:scripts/cce_paired_runtime.py` | `981e7e82a0054a38d233a64c4120219094c34879b5820661d08907230806f588` |
| Thin production candidate: baseline981 plus only this patch | `aa9bc59ec86107a32c79a17ed4b31b3c22ed268869c53d0a8f4179b09e7b580f` |
| Native ACK candidate, commit e93b20c | `af05ea224ef77bcb98b10ce3a702bce53379ced7c6f5ea3f401ba501ace5cb2b` |
| Actual production guard, equal to the BS10610 c8 test guard | `e99378dcb1a0f71d3561c6705f4b5fe2f9886bc9e0307b5dc7c1b822de6e6d0f` |
| Final targeted test source | `0b5b541ae9aa9f36adcdd9ee5bbbb77a8cef454d439ec14129f3ca8a17b8b41b` |
| Functional RED3 raw log | `3a2710d422ca6a33b12047f391249f17609de5a8d4a83af0974b03b0db5cee3a` |
| Final GREEN raw log | `bf4280bbfff123d6447456b1a00f4dc5dc57d29d68c04aa3c603b03078321022` |

Candidate and exact delta: `.codex-artifacts/wgs323d3f-tmp-recover-20261003/ack-candidate981.py` and `ack-thin.patch`. This checkout's tracked paired source also contains previously uninstalled 4fc progress code. It is not the deployment candidate; never deploy the whole checkout file. The candidate is built by applying only the current diff to raw981 and independently hash checked.

## Minimal BS10610 verification

Test root: `/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/wgs323d3f-ack-observer-20261003`. Existing pinned test image `8ba8858e3bf3`, network none, readonly source/native/plugin mounts; no dependency installation. Exact native af05 and paired candidate pins printed before pytest.

- Initial collection errors (`red`, `red2`) were missing plugin search path and the incorrectly selected backend image; these are not functional REDs.
- Functional `red3`: 1 failed, 5 deselected, 2.26s, at ordinary Resume forbidden by the observer-only test.
- An expanded positive check caught nested writer serialization at real Step4 expected-source (`green3`); fixed by reusing the already held serialization.
- The exact schema3/cloud shape with the original bundle's old Master START_CONFIRMED caught the real guard resolver cycle (`green6`); fixed by the validation order described above.
- Final `green-final`: **6 passed, 10.09s**, including the real dynamic registration/resolver/guard, real native ACK validation, repeated Step3 source selection, Step4 expected-source selection, and five failure cases (ACK UID, owner, journal context, producer request, compute deadline). Directory identity transport alone is synthetic. Native create/recovery and ordinary Resume are forbidden after the original synthetic START; counters remain CREATE1/START1. Original journal and old failure evidence remain unchanged.

Raw logs and XML remain in that private test root. No broad suite or repeated native11 acceptance was run. These tests do not claim old generation3 can restart or that the clinical workflow is complete.

## Production review checkpoint and proposed single operation

Production remains pending independent coordination review. Review the exact two source candidates, tests and active-consumer impact before activation:

1. Fresh BS96 server96/control/current/container/environment/gates and exact installed native bfa, paired981, guard e993, policy/bootstrap pins. Confirm the current failed observer identity, original deadline and current real cloud producer phase.
2. Privately preserve exact native/paired/policy originals. Prepare only the native af05 file, paired aa9 file and actual policy's corresponding two writer hashes; preserve paths/guard/bootstrap/operator/ACL/route/service configuration. Manifest and rollback SHA values must come from actual bytes.
3. Establish a real host-consumer quiet window across affected WGS/GATK entry points before changing shared source/pins. The cloud Master and Workers continue running. If that window cannot be proved, stop without activation. Use a new task-specific once guard; do not replay old deployment guards.
4. Activate only reviewed source/pin bytes, verify readonly selection/import and original permissions, then restore entry availability. No service, cloud Job/Pod, input, lock/lease, or computation restart is part of this operation.
5. One existing normal same-attempt Step3 Resume request with a fresh reviewed key registers only a new observer generation/action. Suggested key: `w423-323d3f-a1-step3-ack-observe-20261003`. Do not call it until activation review and a fresh safe preflight. Unknown response requires readback, never repost.
6. Immediately record actual new observer identity. Verify real producer binding remains action4d/platformgen3/nativegen2/cb75/6714, original compute deadline and successful predecessors unchanged; preserve old terminal/dispatch/request history through existing generation fences. Follow actual cloud phase through normal observations; do not force Running, success or computation restart.

Rollback is the preserved exact native bfa + paired981 + original matching policy, under the same host-consumer quiet-window rule. Do not revert unrelated 55cb platform repair, routes, successful predecessors, cloud execution or old evidence. No Step7, cleanup, automatic monitor recreation, new attempt, input or permission change is authorized.
