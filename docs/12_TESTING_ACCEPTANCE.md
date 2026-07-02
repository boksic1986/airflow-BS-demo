# 12 测试和验收设计

## 1. 测试层级

测试执行位置约束：

- 本地 `D:\pipeline\airflow-demo` 只做编辑、Git、文档一致性和 manifest 检查。
- 运行时验收测试一律在远端执行，当前默认节点为 `ssh fengxian`。
- 不把本地 pytest、Docker Compose、Snakemake、Airflow 或服务启动结果作为验收证据。
- 如果某项远端测试无法执行，必须在 `HANDOFF.md` 记录命令、原因和下一步环境条件。

```text
unit tests
  input scanner, run creation, qc parser, airflow client mock, log tail
integration tests
  backend + DB, event receiver, artifact registry
DAG tests
  import, conf validation, mock task execution
Snakemake tests
  dry-run, mock execution, failure/resume
frontend tests
  render, API client, key flows
E2E smoke
  submit -> airflow -> snakemake -> qc -> email
```

## 2. Backend tests

必须覆盖：

- `/api/health`。
- `/api/input/scan` 成功发现白名单路径下的 R1/R2 候选样本。
- `/api/input/scan` 拒绝白名单外路径。
- `/api/runs` 用 selected samples 创建 `analysis_run` 和 `sample`。
- `/api/runs` 生成 `samples.selected.tsv` 和 `request.json`。
- event receiver 幂等 upsert。
- log API 防路径穿越。
- reanalysis mode 生成正确 payload。

## 3. DAG tests

必须覆盖：

- DAG import 无错误。
- `validate_request` 对缺字段报错。
- `generate_pipeline_config` 输出 config。
- `run_pipeline` 根据 mode 生成正确 Snakemake flags。
- failure callback 能生成 error summary。

## 4. Snakemake tests

必须覆盖：

- `snakemake -n` 通过。
- mock 运行成功。
- mock rule 故意失败时生成 stderr。
- resume 后不重复已成功输出。
- qsub wrapper mock mode 生成 event。

## 5. Frontend tests

必须覆盖：

- Submit 页面必填校验。
- Runs table 渲染。
- Rule table status 渲染。
- Log viewer 处理空日志/不存在日志。
- Reanalysis button 调用正确 API。

## 6. E2E smoke 场景

### 成功场景

```text
PGT-A v1:
  扫描服务器 rawdata_root
  -> 勾选 1-2 个样本
  -> 创建 PGTA_*
  -> analysis_run.status = created
  -> sample.fq1/fq2 保存服务器路径
  -> 生成 samples.selected.tsv 和 request.json
  -> 不触发 Airflow DAG
```

完整 E2E 后续场景：

```text
提交已创建的 run
  -> Airflow DAG success
  -> Snakemake all success
  -> QC pass/warn
  -> report artifacts
  -> MailHog 收到 success email
```

### 失败场景

```text
提交包含 FAIL_SAMPLE 的 mock input
  -> mock rule intentional_fail 返回非零
  -> Airflow run failed
  -> rule table 显示 failed
  -> stderr 展示 intentional error
  -> MailHog 收到 failure email
```

### Resume 场景

```text
修复 mock 条件
  -> 点击 resume
  -> 已成功 rule skipped/cached
  -> 失败 rule 重跑
  -> run success
```

## 7. 验收报告模板

```markdown
# Acceptance Report

Date:
Agent:
Commit:
Environment:

## Commands

## Results

## Screenshots / URLs

## Known issues

## Decision

- [ ] accepted
- [ ] accepted with issues
- [ ] rejected
```
