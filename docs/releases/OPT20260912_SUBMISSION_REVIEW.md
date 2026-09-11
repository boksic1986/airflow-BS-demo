# Task1 review — accepted after fix round1

## Scoped re-review at d5a4e1d

submission_review closed all three findings below and found no new Important or
Critical issues. The fixed paths use private no-follow namespaces/portable
mkdir+flock, pinned effective prepare/template snapshots, and request-generation
guards with release-owned defaults. Reviewer checked the owner transformations
against audited cc9bde3. Tests were not rerun by the reviewer; the reported
97 backend/gate passes (1 optional skip),16 focused UI passes and TypeScript pass
are implementation acceptance evidence. See OPT20260912_SUBMISSION_REPORT.md.

This is code acceptance, not activation or live analysis acceptance. The test
root sticky prerequisite and drifted shared owner source remain separate gates.

## Original findings at a5aedc9 (resolved)

Independent submission_review: spec not yet compliant;3 Important, no Critical. Read-only source review; no tests/deployment/SSH by reviewer. Existing synthetic141+PG1/UI15 build evidence accepted, not sufficient for gaps below.

1. `scripts/wgs_runtime_gate.py:113-152,175-179`: target/output/source ancestor checks do not protect output/sampleinfo or output/prepare symlinks. `mkdir(exist_ok=True)` can accept an escaping directory symlink and subsequent exclusive file creation writes outside output; owner pending may follow prepare symlink. Check/use gaps exist in shared group-writable parent. Marker contents alone are not ownership. Secure all write descendants, including pending, with no-follow/dirfd or equivalent non-replaceable controlled directories; cover escaped sampleinfo/prepare, parent replacement, concurrent creation and retry recovery.
2. `scripts/wgs_runtime_gate.py:1187-1193,503-548,468-483`, `backend/app/wgs_test_project.py:97-110`: source config hash does not constrain actual repository prepare/config.yaml used by owner. Only algo/use_reference output checks exist. Freeze audited effective defaults/templates+options, use controlled snapshot or validate frozen hash at execution, verify effective prepared configuration and expose frozen values in review. Do not blindly copy arbitrary source config commands/paths. Test live-default mutation after confirmation (reject or use frozen snapshot).
3. `frontend/src/pages/SubmitPage.tsx:117-118,175-186`: editable inputs can invalidate preview while delayed old response unconditionally restores it. UI can show source B and confirm source A. Add request-generation/input-snapshot protection or lock every affected input; confirmation must match displayed source/options, and review should identify frozen source. Delayed response regression required.

Strengths: backend/node double gate, owner-bound transactional draft/advisory locks, deterministic DAG ID, unique project/batch namespace, retained three confirmations and connected Step1-6/7, exact selected/FASTQ fences, actual caller names, honest configured/observed GATK metadata. No concrete account leakage found through ordinary login/logout unmount.

Coordinator ruling on intended configuration scope: freeze the audited release's effective configuration and explicit user options; source project config is compatibility/provenance input, not permission to inherit arbitrary scripts/paths. User-required full effective freeze is not satisfied by only source hash and two options.

Coordinator concrete call-site check within finding2: SubmitPage lines53-54 hardcode all/DNAscope initial values and line186 has fallback reference enums. User requires release-owned defaults/enums. Include audited defaults in release contract and initialize/validate draft choices against that contract; test stale draft/release defaults. This is part of the configuration freeze correction, not a new feature.
