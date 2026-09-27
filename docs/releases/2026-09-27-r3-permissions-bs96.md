# WGS r3 permission binding repair

User authorized platform registration update and repair of the original failed
preparation. No workflow algorithm, native installation, Master image or resource
content change. Native remains0.8.7, WGS4.2.2, profile revisionr3.

## Publication and consumer fix

- Same-content SFS publication: `20260927.3-wgs422-permissions`, PASS.
- New catalog identity: `wgs-4.2.2-d38322e-permissions`; old identity retained.
- Source: `d38322e457bda9f33289fe40c6ee2bd9a262c877` unchanged.
- Profile SHA: `daad51fcbaaa35352e7504a1943890ab75f5285f9677db17f7cbc5ec034e282a`.
- Receipt SHA: `fe530b2022a536e0a106d90f1d49b233051016ad5e8d066e46a9162c4614f31d`.
- Prepare config SHA: `c9cc826a467a3cae4d1f39f26d29e3b149c5f07cf03eaaca5ae4f8ec1e6af4d5`.
- Permissions:bioinfo/520,2775/0664/0775.139 files postchecked, owners unchanged.

Source953ff94 changes only catalog and runtime-request release identity syntax.
Optional safe configuration qualifier permits separate immutable registration;
commit-prefix consistency, receipt/hash checks and conflict refusal are preserved.
BS10610 cached backend image, networknone, synthetic tests:2 fail5 pass before,
7pass after. No broad suite or cloud analysis tests requested or run.

## Production window

BS96 server96; actual backend baseline20260927-p0-local-84510df.
Idle checks11:58:23Z and11:59:43Z:business/Airflow/transferleases0.
Only backend/scanner/observer consumers receive readonly file overlays beneath
`/data/airflow-WGS/releases/20260927-release-identity-953ff94`.
Backend gets2 files; scanner/observer get onlycatalog parser. No unrelated source
updates, Airflow restart or image rebuild. Private Compose active/freeze/rollback
at `/data/airflow-WGS/release-identity-953ff94-control` preserves originalsettings.
All three original environments verified restored, gateway200.

Official registerAPI then CASactivate succeeded while admission frozen. ctapa
gate maps add the new identity to existing immutable source and new independent
r3 prepare config. Old profile/maps/catalog entries and request receipts retained.

## Original-run repair

Only WGS_20260927_090701_56DC81, pre-executionfailedattempt3, dispatchpreparing,
committed_atnull, projectabsent. Previous params backed up on production only at
`/sg2/50.ctapa/project/HWcloud/airflow-wgs/runtime/repair-backups/r3-permissions-20260927/before.json`.
RunAction `repair_release_binding` records old/newidentity/profileSHA. No sample,
pending or prior attempt records deleted. StandardresumeAPI createdattempt4;
same previously approvedall/default configuration confirmed. Final execution
approval not granted. Preparation outcome recorded in latestHANDOFF.

## Rollback

Do not restore old consumers while the new catalog identity is present: old parser
rejects that entry even when it is notcurrent. Coordinate catalog rollback and
run binding under an idle admission window, retain both genuine receipts/history.
Private original Compose and ctapa runtime.env.before are retained; they are not
an automatic rollback command for an active analysis. ExactPOSIX snapshots support
permission reversal only after checking active consumers. ACL unavailable, no ACL
backup claim. No business data or raw FASTQ was deleted.
