# 12 测试和验收设计

## 1. 测试层级

```text
unit tests
  sample parser, qc parser, airflow client mock, log tail
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
- 样本表解析成功。
- 样本表缺列失败。
- 创建 analysis_run。
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
上传 wes_mock.tsv
  -> 生成 WES_*
  -> Airflow DAG success
  -> Snakemake all success
  -> QC pass/warn
  -> report artifacts
  -> MailHog 收到 success email
```

### 失败场景

```text
上传包含 FAIL_SAMPLE 的 mock sheet
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
