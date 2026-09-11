# GATK selective promotion and production main

## Authorization and global constraints

User approved selective GATK promotion (not the complete test branch), publication to main, a normal production clone rather than linked worktree, new development worktree, BS10610 synchronization and BS96 actual manual GATK enablement. GATK output root is `/sg2/50.ctapa/project/HWcloud/WES_Clinical`. Input projects have no configured business-root whitelist, but retain authenticated submission, explicit project identity, path/structure validation and frozen-request checks. No automatic GATK submissions or destructive test-data operations authorized.

Preserve current WGS 4.2.1 and all production repairs. Preserve active workloads and source FASTQ/results/pending, credentials, databases and existing dirty worktrees. No whole test branch merge, force push, Docker Hub pull or copying test DB to production. Execute cached synthetic tests on BS10610 before production enablement. Other pending-sample design is documentation only.

## Tasks

1. Record production/local/test fingerprints; commit existing design documents separately; establish independent normal production clone, retaining original dirty repository.
2. Port only GATK implementation/test hunks from T262 chain; integrate necessary generic changes without reverting production WGS/frontend behavior. Add explicit unrestricted-source policy under user authorization, with frozen project scope and negative safety tests. Review diff and test on BS10610.
3. Reconcile live production source drift before candidate promotion; add WGS+GATK deployment config, safe mounts/gates and runtime references. Inspect source/output distinction and existing GATK input roots.
4. Run targeted backend/DAG/runtime/registry tests and frontend production build using cached test environment. Review candidate.
5. Publish approved production tree to main with normal forward Git history, not test-branch merging or force push; keep prior main history. Verify remote head.
6. Retain independent production clone at `D:/pipeline/airflow-demo-production`; create development worktree from main. Old dirty main directory and linked worktrees remain recoverable, not deleted. Document this safer directory choice.
7. Deploy source-pinned test and production releases preserving environment-specific data/runtime. Enable manual GATK only after host/runtime/profile/preflight checks. Keep WGS scan/dispatch switches unchanged and never start real analysis as a smoke test.
8. Record actual health, capabilities, Git/worktree state, test/deploy provenance and rollback. Never mark partial work as complete.

## Review boundaries

GATK implementer owns gatk modules/DAG/gate/tests and minimal required shared hunks. Coordinator owns infrastructure, release docs, Git layout and deployments. Cross-cutting policy changes must have tests and cannot replace whole shared files from test. Production backend-only restart is not automatically sufficient if worker env/mount changes are needed; active-run preflight controls service restart list.
