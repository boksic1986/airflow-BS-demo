# 14 Codex / Agent 执行流程

## 1. 单 agent 标准流程

```text
Read context
  -> confirm task scope
  -> inspect repo/server state
  -> make focused changes
  -> run tests
  -> update docs/state/handoff
  -> summarize result
```

## 2. 开始任务 checklist

- [ ] 读取 `AGENTS.md`。
- [ ] 读取 `CURRENT_STATE.md`。
- [ ] 读取 `TASKS.md`。
- [ ] 读取任务相关 docs。
- [ ] 检查 git status。
- [ ] 检查 `git remote -v`，确认 `origin` 指向 `git@github.com:boksic1986/airflow-BS-demo.git`。
- [ ] 检查当前分支；默认开发分支为 `main`，功能分支按任务需要从 `main` 创建。
- [ ] 确认不修改生产数据。
- [ ] 确认任务 ID 和验收标准。

## 3. 结束任务 checklist

- [ ] 功能实现或明确部分完成。
- [ ] 运行最小测试。
- [ ] 记录未运行测试和原因。
- [ ] 更新 `CURRENT_STATE.md`。
- [ ] 更新 `TASKS.md` 状态。
- [ ] 更新相关 docs。
- [ ] 写入 `HANDOFF.md`。
- [ ] 在 `HANDOFF.md` 记录当前 branch、commit、dirty files 和 remote。
- [ ] 给出下一步建议。

## 4. 失败时行为

不要盲目扩大范围。先：

1. 保存失败命令。
2. 保存 stderr 摘要。
3. 判断是否环境问题、依赖问题、代码问题、权限问题。
4. 如果能在任务范围内修复，则修复并测试。
5. 如果超出范围，则标记 blocked 并交接。

## 5. 不确定时行为

优先做安全、可回滚、小范围的最佳努力：

- 使用 mock 数据。
- 使用 dry-run。
- 写清楚假设。
- 不执行破坏性命令。
- 不申请真实大规模 qsub。

## 6. 推荐 agent prompt 格式

```text
你是 airflow-demo 项目的 <agent role>。
请先读取 AGENTS.md、CURRENT_STATE.md、TASKS.md 和相关 docs。
执行任务 <TXXX>。
只修改任务范围内文件。
完成后运行相关测试，并更新 CURRENT_STATE.md、TASKS.md、HANDOFF.md。
```

## 7. 代码变更范围声明

每次开始实现前，agent 应输出计划：

```text
I will touch:
- file A
- file B

I will not touch:
- production pipeline dirs
- secrets
- unrelated frontend/backend modules
```

## 8. 合并前 review checklist

- [ ] diff 是否小而聚焦？
- [ ] 是否有不该提交的大文件？
- [ ] 是否有密码/token？
- [ ] 是否有真实样本信息？
- [ ] 是否更新文档？
- [ ] 是否测试通过？
- [ ] 是否有清楚的回滚方式？

## 9. 插件使用约定

### Superpowers

开始较实质任务时先选择适用的 superpowers 技能。常用路由：

```text
new design / behavior change -> brainstorming
multi-step implementation plan -> writing-plans
approved plan execution -> executing-plans or subagent-driven-development
bug / failure / unexpected result -> systematic-debugging
feature or bugfix implementation -> test-driven-development
before completion claim -> verification-before-completion
```

如果 superpowers 技能建议与 `AGENTS.md` 或用户最新明确要求冲突，优先遵守用户最新明确要求和 `AGENTS.md`。

### GitHub plugin

GitHub 工作遵循 connector-first、local-git-for-local-state 的混合模式：

```text
repo / issue / PR metadata -> GitHub connector via github plugin
review comments -> github:gh-address-comments
CI failure / Actions logs -> github:gh-fix-ci plus gh CLI
commit / push / draft PR -> github:yeet with local git
```

发布或推送前必须先检查：

```bash
git status --short --branch
git remote -v
```

仓库 remote 应为：

```text
origin git@github.com:boksic1986/airflow-BS-demo.git
```
