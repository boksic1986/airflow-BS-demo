# 19 仓库、镜像和插件工作流

## 1. 仓库定位

本地 `D:\pipeline\airflow-demo` 是 airflow-demo 的主开发仓库。

```text
repo_url: git@github.com:boksic1986/airflow-BS-demo.git
default_branch: main
local_role: primary development checkout
fengxian_role: server code mirror
```

`fengxian:/home/jiucheng/project/airflow-demo` 作为 GitHub 代码镜像目录使用，不作为日常开发分支直接提交代码。服务器上的代码更新只允许使用 Git 同步命令，不允许通过复制覆盖或手工修改作为主流程。

## 2. 本地 Git 初始化约定

首次初始化：

```bash
git init -b main
git remote add origin git@github.com:boksic1986/airflow-BS-demo.git
git status --short --branch
git remote -v
git ls-remote origin HEAD
```

首次提交建议：

```bash
git add .gitignore .gitignore.template .env.example AGENTS.md README.md CURRENT_STATE.md TASKS.md HANDOFF.md SERVER_INFO.md MANIFEST.json docs .agents
git commit -m "docs: initialize airflow demo planning repo"
git push -u origin main
```

不得提交：

```text
.env
*.local.md
shared/
data/
FASTQ/BAM/VCF/BCF/NPZ
passwords
tokens
patient identifiers
```

## 3. 服务器代码镜像约定

若服务器目录为空，可初始化镜像：

```bash
git clone git@github.com:boksic1986/airflow-BS-demo.git /home/jiucheng/project/airflow-demo
```

若服务器目录已存在文件，必须先确认内容和备份策略，不得覆盖式同步。建议流程：

```bash
cd /home/jiucheng/project/airflow-demo
git status --short --branch
git remote -v
git pull --ff-only
```

服务器镜像规则：

- 只用 `git pull --ff-only` 更新已跟踪代码。
- 不在服务器镜像中直接开发或提交。
- 服务器本地 `.env`、`*.local.md`、`shared/` 必须保持未跟踪。
- 部署、Docker、Airflow、PGT-A smoke 的运行记录写入 `HANDOFF.md` 或验收报告，不写入密钥。

## 4. Superpowers 插件使用约定

后续 agent 在 airflow-demo 中工作时，必须按任务选择相关 superpowers 技能：

| 场景 | 推荐技能 |
|---|---|
| 开始任何较实质任务 | `superpowers:using-superpowers` |
| 新功能、流程设计、行为变更 | `superpowers:brainstorming` |
| 多步骤实现计划 | `superpowers:writing-plans` |
| 执行已批准计划 | `superpowers:executing-plans` 或 `superpowers:subagent-driven-development` |
| bug、失败、异常行为 | `superpowers:systematic-debugging` |
| 功能或 bugfix 实现 | `superpowers:test-driven-development`，除非任务明确只写文档 |
| 完成前声明通过/完成 | `superpowers:verification-before-completion` |
| 开发分支完成后准备集成 | `superpowers:finishing-a-development-branch` |

项目规则优先级：

```text
用户最新明确要求
  > AGENTS.md
  > docs contract
  > superpowers 技能建议
  > agent 自己推断
```

如果技能建议与本仓库安全规则冲突，优先遵守本仓库安全规则。

## 5. GitHub 插件使用约定

GitHub 相关工作优先使用 GitHub 插件能力获取结构化信息；本地仓库状态和推送仍使用 local `git` / `gh`。

| 场景 | 工具/技能约定 |
|---|---|
| repo、issue、PR 总览 | `github:github`，优先 GitHub connector |
| review comment / requested changes | `github:gh-address-comments` |
| GitHub Actions 失败 | `github:gh-fix-ci` + `gh` 查看 Actions 日志 |
| commit、push、开 draft PR | `github:yeet` |
| 本地分支、diff、commit、push | local `git` |
| GitHub auth、Actions log fallback | `gh` CLI |

发布变更前必须：

1. `git status --short --branch`
2. 检查 diff 是否只包含当前任务范围。
3. 显式 stage 相关文件；工作树混杂时禁止 `git add -A`。
4. 运行与变更匹配的最小验证。
5. push 到 GitHub 后，必要时创建 draft PR。

## 6. 当前仓库描述

推荐 GitHub description：

```text
Airflow + Snakemake bioinformatics workflow demo for WES/NIPT/PGT-A submission, monitoring, logs, QC, and resumable reruns.
```
