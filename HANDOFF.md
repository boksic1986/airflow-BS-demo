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

Planned fix before retry: set repo-local `user.name=boksic1986` and `user.email=boksic1986@users.noreply.github.com`; do not modify global Git config.

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

Local repository initialized on `main` with `origin=git@github.com:boksic1986/airflow-BS-demo.git`. Initial commit/push is pending final checks.

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
