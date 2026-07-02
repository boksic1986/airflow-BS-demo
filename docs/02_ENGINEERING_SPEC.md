# 02 工程规范

## 1. 仓库结构

```text
airflow-demo/
  dags/                       # Airflow DAGs
  backend/                    # FastAPI app
  frontend/                   # React app
  pipelines/
    common/                   # common wrappers/scripts
    wes/
      workflow/Snakefile
      config/
      profiles/qsub/
    nipt_qsub/
    nipt_docker/
  shared/                     # local demo volume, usually gitignored
  docs/
  .agents/skills/
```

## 2. Python 规范

- Python 版本：由 `SERVER_INFO.md` 补齐，建议 3.11 或 3.12。
- 后端使用 FastAPI + SQLAlchemy/SQLModel + Alembic。
- 类型注解优先。
- 业务错误返回结构化 JSON。
- 日志使用标准 logging，禁止 print 密码/token。

## 3. Frontend 规范

- React + TypeScript。
- API client 独立封装。
- 状态颜色统一：success/running/failed/warn/skipped。
- 日志查看组件必须支持大日志分页或 tail，不一次性加载巨大文件。
- 所有用户输入在前后端都要校验。

## 4. Airflow 规范

- DAG 文件放 `dags/`。
- 每个 pipeline 一个 DAG：`bio_wes_qsub`、`bio_nipt_qsub`、`bio_nipt_docker`。
- DAG task 数量保持项目级，不按 Snakemake rule 拆分。
- DAG run conf 必须包含：`analysis_id`、`pipeline`、`mode`、`sample_sheet_path`、`workdir`、`email_to`、`params`。
- DAG task 日志中不得打印敏感信息。

## 5. Snakemake 规范

- Snakefile 中所有 rule 必须有明确 input/output/log。
- 每个 rule 应显式重定向 stdout/stderr。
- 所有 rule 输出必须在 workdir 下。
- 不得把生产绝对路径硬编码进 Snakefile；使用 config.yaml。
- 默认开启 `--rerun-incomplete`，禁止默认 `--forceall`。

## 6. qsub 规范

- qsub 提交必须通过统一 wrapper。
- wrapper 必须记录：analysis_id、rule、sample、snakemake jobid、qsub jobid、stdout、stderr。
- demo 限制最大 jobs，例如 `MAX_DEMO_JOBS=<TO_BE_FILLED>`。
- 默认 queue 从 `SERVER_INFO.md` 或 `.env` 读取。

## 7. 文件路径规范

```text
shared/uploads/<analysis_id>/samples.{csv,tsv,xlsx}
shared/runs/<analysis_id>/config/config.yaml
shared/runs/<analysis_id>/logs/snakemake.stdout.log
shared/runs/<analysis_id>/logs/snakemake.stderr.log
shared/runs/<analysis_id>/logs/rules/<rule>/<sample>.stdout.log
shared/runs/<analysis_id>/logs/rules/<rule>/<sample>.stderr.log
shared/runs/<analysis_id>/results/...
shared/reports/<analysis_id>/multiqc_report.html
shared/reports/<analysis_id>/snakemake_report.html
```

## 8. 环境变量

| Variable | Required | Example | Notes |
|---|---|---|---|
| PROJECT_ROOT | yes | /opt/airflow-demo | 服务器项目目录 |
| SHARED_ROOT | yes | /data/airflow-demo | 上传、run、报告目录 |
| AIRFLOW_BASE_URL | yes | http://airflow-api-server:8080 | 容器内地址 |
| DATABASE_URL | yes | postgresql+psycopg://demo:***@postgres:5432/biodemo | 不提交真实密码 |
| SMTP_HOST | no | mailhog | demo 邮件 |
| SMTP_PORT | no | 1025 | demo 邮件 |
| QSUB_QUEUE | no | all.q | 服务器补齐 |
| MAX_DEMO_JOBS | yes | 20 | 防止压垮集群 |

## 9. Git 忽略建议

```text
.env
*.local.md
shared/
data/
*.fastq.gz
*.fq.gz
*.bam
*.cram
*.vcf.gz
*.bcf
*.npz
*.log
__pycache__/
node_modules/
```

## 10. 代码审查 checklist

- 是否越过任务边界？
- 是否引入未批准依赖？
- 是否泄露路径/密码/患者信息？
- 是否更新相应文档？
- 是否有最小测试？
- 是否支持失败定位？
- 是否支持 resume 而不是强制全量重跑？
