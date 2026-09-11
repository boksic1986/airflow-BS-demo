# Staged WGS submission cancellation

Status: design revision awaiting approval after discovering missing cancellation executor. No production changes or real cancellation performed.

## Scope and UI

Submit wizard title actions and incomplete-submission Attention cards offer Cancel submission. A read-only server preview returns current analysis ID, attempt, phase, effects and blockers. Confirmation is tied to that preview identity and revision. Cancel affects only manual, uncommitted submissions; upload/analysis cancellation is outside scope. Card continuation and cancellation must be separate accessible controls, not a button nested inside a link.

## Existing gap

Actual-release candidate app/wgs_platform_service.py action_wgs_run merely writes cancel_requested. Repository search finds no consumer. The submission approval sensor reads approval flags only. Consequently the existing cancel API cannot fulfill the user-approved semantics and must not be wired directly to a success dialog.

## Cancellation protocol

1. Preview validates current attempt, preparation receipts, exclusive ownership of artifacts, execution dispatch and active preparation. It reports exact effects without exposing clinical payloads.
2. Confirmation atomically fences configuration/execution approval and new preparation/dispatch for that attempt. Repeated confirmation resumes the same cancellation action, not a second cleanup.
3. Existing background orchestration processes the action. Wait for an already running preparation to reach a verifiable safe boundary; never delete underneath an active writer. Stop the original DAG's remaining submission path through supported Airflow controls, and verify no downstream execution was committed.
4. Config review before configuration approval: no pending rollback or formal analysis-directory deletion. Remove only this submission's proven-owned candidate sampleinfo, if not reused or modified; preserve immutable receipt/audit evidence. Mark candidate participation cancelled while retaining sample history and previously existing records.
5. Execution review after preparation: require full protected before/after pending material and ownership provenance. Under the shared pending lock, apply a conditional inverse of this attempt's changes to latest rows, preserving other batches and subsequent changes. Ambiguous concurrent edits block with an explicit reason. Do not reconstruct full rows from redacted receipts or replace the whole ledger.
6. Restore sample participation using the same attempt-scoped provenance. Delete only a positively verified newly created, exclusively owned local batch directory after the cancellation fence and writer checks; refuse reused directories, symlinks escaping approved roots and unexpected contents. No OBS/SFS/raw FASTQ deletion.
7. Persist each completed phase in existing action metadata for crash recovery. Only after verified effects mark cancelled and remove the incomplete card. Errors remain visible as cancellation needing attention, never successful cancellation. Observer terminal synchronization must preserve the cancellation state.

## Prerequisite for prepared submissions

Current prepare code uses an in-memory local_pending_snapshot, but that does not prove a durable full rollback journal is available for historical attempts. Audit available protected artifacts before enabling cancellation for execution_review. Add attempt-scoped durable change provenance for future prepares when required. Historical attempts without enough evidence are blocked, not force-reverted. Coordinate prepare file boundaries with the WGS owner.

## Tests and release

Synthetic tests only: config-review cancellation; approval/cancel race; preparing writer fence; duplicate requests and crash retry; wrong attempt; pending concurrent changes/conflicts; owned/reused/symlink directories; observer preservation; UI preview/confirm/errors and retained cards. BS10610 cached backend/frontend tests and build, no Docker Hub or real analysis test. Production release requires an explicit affected-service list and preserved-computation check; do not restart active workers/Masters. No Git synchronization. Feature installation does not itself cancel0901B or any other real task.

## Review decision

Approve this backend lifecycle extension before implementing the two UI buttons. The safer alternative is a config-review-only first release with later prepared-stage cancellation disabled and explained; that is a scope reduction and requires user selection rather than silent implementation.
