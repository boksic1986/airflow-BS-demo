# HANDOFF.md

> Agent 交接记录。最新记录放在最上面。

## Handoff Template

```markdown
## <YYYY-MM-DD HH:MM> - <agent name> - <task id/title>

### Goal

### Completed

### Changed files

### Commands run

| Command | Result | Notes |
|---|---|---|
|  |  |  |

### Tests

### Not run / why

### Current git status

### Risks

### Open questions

### Next recommended task

### Rollback notes
```

## Records

## 2026-07-02 22:47 - Codex - Docker image cleanup and tag pinning

### Goal

Clean duplicate/dangling `<none>` Docker images on `fengxian`, avoid implicit `latest` for airflow-demo images, and verify required compose images can be pulled or built without starting services.

### Completed

- Inspected running containers, all images, dangling images, compose images, latest-tag images, and Docker disk usage on `fengxian`.
- Removed 37 dangling `<none>:<none>` image IDs using exact `docker image rm` IDs.
- Did not run `docker system prune`, `docker volume prune`, or `docker compose down -v`.
- Did not touch running containers: `cosmetic-db-web` and `yunse-bio`.
- Did not delete non-project `latest` images such as `yunse-bio:latest` or `fischbachlab/*:latest`.
- Added explicit backend image tag `airflow-demo/backend:0.1.0` to compose and `.env.example`.
- Rebuilt backend on `fengxian` with the fixed tag and removed old project tag `airflow-demo-backend:latest`.
- Verified `docker compose config --images` now uses explicit tags and no airflow-demo `latest`.
- Pulled external compose images successfully: Airflow, Postgres, Redis, MailHog, nginx.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker ps -a` / `docker images` / `docker images --filter dangling=true` | success | Found 37 dangling images; found project backend image using implicit `latest` |
| `docker image rm <37 dangling ids>` | success | Dangling images reduced to zero; no force used |
| `docker system df` | success | Images count dropped from 54 to 17; no volume cleanup performed |
| `docker compose config --images` | success | Shows `airflow-demo/backend:0.1.0`; no project `latest` image |
| `docker compose build backend` | success | Built/tagged backend as `airflow-demo/backend:0.1.0` using cached layers |
| `docker image rm airflow-demo-backend:latest` | success | Removed old project latest tag only |
| `docker compose pull postgres redis mailhog frontend airflow-api-server airflow-scheduler airflow-worker` | success | Pulled external compose images; scheduler/worker reused Airflow image |
| image inspect loop | success | Verified Airflow, postgres, redis, mailhog, nginx, and backend images exist |
| `docker compose ps` | success | No airflow-demo containers running after checks |

### Tests

Remote-only evidence on `fengxian`:

- Dangling image list is empty after cleanup.
- `docker compose config --quiet` passed.
- Required compose images are present locally.
- `docker images` has no `airflow-demo*:latest`.

### Not run / why

- Airflow containers were not started; this task only checked image availability and cleanup.
- No frontend app container was built; frontend is still nginx placeholder only.
- No database migration was run.
- No volume cleanup was run, by project safety rule.

### Current git status

Code/docs changes for explicit backend image tag are committed and pushed as `07a63fa`; state docs from this cleanup are expected to be committed and pushed next.

### Risks

- Docker still reports reclaimable space from unused non-project images and unused volumes, but those were intentionally left untouched.
- Several non-project `latest` images remain on `fengxian`; deleting or retagging them needs separate owner confirmation.

### Open questions

- Whether airflow-demo should later use an internal registry or image digest pinning for stricter reproducibility.
- Whether to configure Docker registry mirrors for future Airflow/base-image pulls.

### Next recommended task

Proceed to T011: start and initialize Airflow services using the already pulled `apache/airflow:2.9.3-python3.11` image, then verify Airflow `/health`.

### Rollback notes

- The removed dangling images had no tags; rollback would require rebuilding or repulling the workloads that produced them.
- Revert the backend tag change with a normal Git revert if needed; do not force push.

## 2026-07-02 22:24 - Codex - T010/T012/T013/T014/T020 fengxian base skeleton

### Goal

Build the fengxian base runtime surface before PGT-A DAG/frontend work: user-level Docker Compose v2 readiness, GitHub mirror sync, Docker Compose service skeleton, shared directory contract, and minimal FastAPI `/api/health`.

### Completed

- Added minimal FastAPI backend at `backend/app/main.py` with `GET /api/health -> {"status":"ok"}`.
- Added backend Dockerfile and pinned minimal backend requirements.
- Added `docker-compose.yaml` with fixed `172.30.10.0/24` network and services: postgres, redis, mailhog, backend, frontend placeholder, airflow-api-server, airflow-scheduler, airflow-worker.
- Added tracked shared directory placeholders while keeping runtime contents ignored.
- Updated `.env.example`, engineering spec, API contract, deployment runbook, testing rules, agent workflow, and PGT-A plan.
- Added project constraint: local Windows repo is for editing/Git/docs only; runtime tests are remote-only.
- Re-ran fengxian Level 0 preflight: Docker 20.10.21, PGT-A/Snakemake paths readable, `172.30.10.0/24` non-conflicting.
- Installed Docker Compose v2.24.7 as a user-level CLI plugin at `/home/jiucheng/.docker/cli-plugins/docker-compose`.
- After user correction, replaced the plugin using local Windows GitHub Release download plus `scp` to fengxian; final plugin SHA256 is `19c9deb6f4d3915f5c93441b8d2da751a09af82df62d55eab097c2cbfebd519f`.
- Cloned `git@github.com:boksic1986/airflow-BS-demo.git` into empty `fengxian:/home/jiucheng/project/airflow-demo` as a code mirror.
- Created remote ignored `.env` for smoke only; no `.env` committed.

### Changed files

- `.env.example`
- `.gitignore`
- `AGENTS.md`
- `backend/Dockerfile`
- `backend/app/__init__.py`
- `backend/app/main.py`
- `backend/requirements-dev.txt`
- `backend/requirements.txt`
- `backend/tests/test_health.py`
- `dags/.gitkeep`
- `docker-compose.yaml`
- `shared/.gitkeep`
- `shared/uploads/.gitkeep`
- `shared/runs/.gitkeep`
- `shared/reports/.gitkeep`
- `shared/logs/.gitkeep`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/05_API_CONTRACT.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `docs/14_AGENT_WORKFLOW.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `ssh fengxian` Level 0 preflight | success | Docker 20.10.21/API 1.41, PGT-A path and Snakefile readable, Snakemake 8.5.4, Python 3.12.2, no `172.30.10.0/24` conflict |
| direct `curl` GitHub release on fengxian | timed out | Left a partial plugin file, later replaced |
| TUNA Docker CE focal deb unpack to user plugin | success | Produced `Docker Compose version v2.24.7`; used as fallback path |
| local `curl.exe --proxy socks5h://127.0.0.1:1080` GitHub Release download + `scp` | success | Official `docker-compose-linux-x86_64` downloaded locally and synced to fengxian |
| `docker compose version` on fengxian | success | `Docker Compose version v2.24.7` |
| `git clone git@github.com:boksic1986/airflow-BS-demo.git /home/jiucheng/project/airflow-demo` | success | Directory was empty; mirror is on `main`, clean, commit `dd1d8a7` for tested code |
| `docker compose config --services` | success | Listed postgres, redis, airflow-worker, backend, frontend, mailhog, airflow-api-server, airflow-scheduler |
| `docker compose config --quiet` | success | Re-run after local GitHub plugin replacement also passed |
| `docker compose up -d postgres redis mailhog backend` | success | Built backend image, pulled base images, started minimal services |
| `curl -fsS http://127.0.0.1:8000/api/health` | success | Returned `{"status":"ok"}` |
| `docker compose down` | success | Used safe stop only, no `-v` |
| `curl -fsSI http://127.0.0.1:8025` | failed | MailHog returned 404 for HEAD; not a service failure |
| `curl -fsS http://127.0.0.1:8025/` | success | MailHog GET probe found page content |
| `docker compose ps` after cleanup | success | No running demo containers |

### Tests

Remote-only acceptance evidence:

- `docker compose config --quiet` passed on fengxian with user-level Compose v2.24.7.
- Minimal service smoke passed on fengxian: postgres, redis, mailhog, backend started; backend health returned `{"status":"ok"}`; services were stopped with `docker compose down`.
- MailHog HTTP GET probe passed on fengxian.

Local note: a local pytest/YAML parse check was run before the user clarified the remote-only testing rule. Those local results are not counted as acceptance evidence, and the temporary `.venv` was removed.

### Not run / why

- Airflow web/scheduler/worker startup: out of scope for this batch; T011 remains next.
- Airflow `/health`: not run because Airflow services were not started.
- frontend functional test: out of scope; frontend is only an nginx placeholder.
- biodemo DB migration: not implemented yet.
- PGT-A metadata/dry-run/failure smoke: intentionally deferred to T027/T035/T045/T057/T084.
- Snakemake dry-run: not run in this batch.

### Current git status

Local repo has the implementation commit `dd1d8a7` pushed to `origin/main`; this handoff/state-doc update is expected to be committed and pushed as a follow-up docs/state commit. Fengxian mirror is clean at the tested code commit.

### Risks

- Remote image and pip downloads can be slow; consider adding Docker registry/pip mirror configuration in a later infra task if builds remain slow.
- The current Postgres smoke starts only the default Airflow database; biodemo DB/schema creation is still pending.
- Airflow services are defined but not validated; the Airflow image may still require initialization/user setup in T011.
- The remote `.env` contains local-only demo credentials and is ignored; it must not be committed.

### Open questions

- Whether to keep direct commits to `main` during early bootstrap or switch to task branches/PRs for T011 onward.
- Which migration tool to use first for biodemo DB: Alembic with SQLAlchemy/SQLModel or plain SQL bootstrap.

### Next recommended task

Run T011: initialize and start Airflow web/scheduler/worker, then verify Airflow `/health` and document the minimal Airflow user/auth setup without adding PGT-A DAG yet.

### Rollback notes

- Stop services with `docker compose down` only.
- Remove the user-level Compose plugin with `rm "$HOME/.docker/cli-plugins/docker-compose"` if needed.
- Revert repository changes with a normal `git revert`; do not use `git reset --hard` or force push.

## 2026-07-02 21:16 - Codex - T005/local Git and plugin workflow

### Goal

Initialize `D:\pipeline\airflow-demo` as the local development Git repository, point it at `git@github.com:boksic1986/airflow-BS-demo.git`, and document server mirror, superpowers, and GitHub plugin usage rules.

### Completed

- Added `.gitignore` from the existing template so `.env`, local notes, shared data, FASTQ/BAM/VCF/NPZ, logs, caches, and build outputs stay untracked.
- Added `.gitattributes` to keep text files normalized to LF in the repository.
- Added `docs/19_REPO_AND_PLUGIN_WORKFLOW.md` with GitHub remote, local-vs-server mirror responsibilities, server pull-only rules, superpowers usage, GitHub plugin routing, and repository description.
- Updated `docs/14_AGENT_WORKFLOW.md` to require git status, remote, branch, commit/dirty-state checks and to document superpowers/GitHub plugin routing.
- Updated `docs/16_CODEX_PROMPTS.md` with Git/GitHub, superpowers, and GitHub plugin prompt templates.
- Updated `CURRENT_STATE.md`, `TASKS.md`, and `MANIFEST.json` for the new Git/GitHub workflow.
- Initialized local Git repository on branch `main` and added `origin` remote.

### Changed files

- `.gitignore`
- `.gitattributes`
- `docs/19_REPO_AND_PLUGIN_WORKFLOW.md`
- `docs/14_AGENT_WORKFLOW.md`
- `docs/16_CODEX_PROMPTS.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git status --short --branch` | initially failed before `git init` | Confirmed the directory was not yet a Git repo |
| `gh --version` | success | GitHub CLI available: `2.92.0` |
| `gh auth status` | success | Authenticated as `boksic1986`, SSH git protocol |
| `git init -b main` | success | Created local repository |
| `git remote add origin git@github.com:boksic1986/airflow-BS-demo.git` | success | Added GitHub remote |
| `git status --short --branch` | success | Showed no commits yet on `main` with untracked project files |
| `git remote -v` | success | `origin` fetch/push both point to `git@github.com:boksic1986/airflow-BS-demo.git` |
| `git ls-remote origin HEAD` | success with no output | Remote is reachable; no HEAD advertised, consistent with an empty remote repo |
| `git commit -m "docs: initialize airflow demo planning repo"` | failed | Git author identity was not configured locally; no commit was created |
| `git push -u origin main` | failed | No commit existed yet, so `main` refspec did not exist |
| `git config user.name "boksic1986"` and `git config user.email "boksic1986@users.noreply.github.com"` | success | Set repo-local identity only; did not modify global Git config |
| final manifest/keyword/safety checks | success | Manifest `48/48`, keywords found, no unsafe file candidates |
| `git commit -m "docs: initialize airflow demo planning repo"` | success | Created initial commit `73ca47f` |
| `git push -u origin main` | success | Pushed `main` to `git@github.com:boksic1986/airflow-BS-demo.git` and set upstream |

### Tests

Pending final verification before commit/push:

- Manifest `file_count` and listed files must match.
- Required GitHub/plugin/server mirror keywords must be searchable.
- Git safety check must confirm ignored secrets/data patterns are not staged.
- `git ls-remote origin HEAD` must remain accessible.

### Not run / why

- Docker/Airflow/PGT-A tests were not run; this task only initializes Git and updates documentation.
- GitHub PR creation was not run; the requested flow is initial commit and push to `main`, not a draft PR.

### Current git status

Local repository initialized on `main` with `origin=git@github.com:boksic1986/airflow-BS-demo.git`. Initial commit `73ca47f` was pushed to `origin/main`; a follow-up documentation-state commit records the final status.

### Risks

- If GitHub remote has branch protection or non-empty hidden state, `git push -u origin main` may fail. Do not force push without explicit user approval.
- Server mirror on fengxian has not been cloned or pulled in this task.

### Open questions

- Whether to configure GitHub repository description through the GitHub UI/API after the initial push.
- Whether future implementation should use direct commits on `main` for early bootstrap or task branches with draft PRs.

### Next recommended task

Run the final verification, commit the bootstrap documentation, push `main`, then use T014 for Docker Compose v2 readiness on fengxian.

### Rollback notes

If no push has happened, remove `.git/` and revert the documentation changes. If push succeeds and rollback is needed, use a normal revert commit; do not use `git reset --hard` or force push without explicit approval.

## 2026-07-02 20:51 - Codex - T004/fengxian PGT-A demo 测试计划

### Goal

将用户确认的 fengxian PGT-A demo 测试方案落地为仓库文档，并同步当前状态、任务表和交接记录；不执行服务器安装、部署、容器启动或 PGT-A 流程运行。

### Completed

- 新增 `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`，记录 `pgta` / `bio_pgta` 命名、Snakemake 8.5.4 暂不升级、用户级 Docker Compose v2 plugin 准入、固定 Docker 网段 `172.30.10.0/24`、Level 0-4 测试层级和 BS10610 迁移预检。
- 更新 `SERVER_INFO.md`，记录 fengxian 与 BS10610 的非敏感只读探测快照。
- 更新 `CURRENT_STATE.md`，标记当前仍处 P0，计划已落地但服务未实现/未启动。
- 更新 `TASKS.md`，新增 T004 计划任务并拆出后续 T014/T027/T035/T045/T057/T084。

### Changed files

- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git status --short --branch` | failed: not a git repository | 当前 `D:\pipeline\airflow-demo` 不是 Git 仓库 |
| `rg -n "PGT|pgta|bio_pgta|fengxian|BS10610|Snakemake 9|docker compose|172\.30\.10"` | success | 修改前仅发现通用 compose 文档，无 PGT-A 计划 |
| `Get-Date -Format 'yyyy-MM-dd HH:mm'` | success | 用于 handoff 时间 |
| PowerShell `ConvertFrom-Json` manifest check | success | `file_count=45`、manifest 列表数 `45`、缺失文件数 `0` |
| old draft identifier and placeholder grep | success: no matches | 无旧草案标识、BS10610 用户名笔误或占位文本 |
| `rg -n "bio_pgta|pipeline=pgta|172\.30\.10\.0/24|v2\.24\.7|Snakemake 8\.5\.4|BS10610|T004|T014|T027|T035|T045|T057|T084" ...` | success | 关键命名、网段、Compose 版本、任务 ID 均可定位 |
| `Select-String ... -Pattern 'docker compose down -v|docker system prune|docker volume prune|baseline_qc|Level 0|metadata|bio_pgta'` | success | 安全禁止项和 Level 0-4 关键测试词均可定位 |

### Tests

文档一致性检查已运行：manifest JSON 可解析且计数匹配；新增计划、任务、状态和交接中可定位 `pgta` / `bio_pgta`、固定网段、Compose 版本、Snakemake 8.5.4、BS10610 和后续任务 ID；旧草案标识和笔误检查无匹配。

### Not run / why

- `docker compose version` / `docker compose config`: 未运行；用户要求本轮不执行服务器变更，且当前本地目录无 compose 文件。
- backend/frontend/DAG/Snakemake tests: 未运行；对应代码尚未实现。
- PGT-A metadata/dry-run smoke: 未运行；本轮只落地计划文档。

### Current git status

不可用。`git status --short --branch` 返回 `fatal: not a git repository (or any of the parent directories): .git`。

### Risks

- `CURRENT_STATE.md` 和 `SERVER_INFO.md` 的服务器信息来自本轮前的只读探测快照，真实执行前仍需重复 Level 0 preflight。
- fengxian 当前没有 Docker Compose v2；后续 T014 必须先解决 Compose 准入。
- BS10610 路径与用户不同，迁移前必须参数化路径，不能复用 fengxian 硬编码路径。

### Open questions

- 是否要把 airflow-demo 初始化为 Git 仓库或从远端仓库重新同步。
- PGT-A Level 4 `baseline_qc` 是否在 Level 1-3 通过后允许运行，以及允许运行的并发上限。

### Next recommended task

执行 T014：在 fengxian 以用户级 Docker CLI plugin 方式安装/启用 Docker Compose v2，并只运行 `docker compose version` 作为准入验收。

### Rollback notes

本轮仅改文档。回滚方式是移除 `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`，并恢复 `SERVER_INFO.md`、`CURRENT_STATE.md`、`TASKS.md`、`HANDOFF.md` 到本轮修改前内容。

### <TO_BE_FILLED>

暂无。
