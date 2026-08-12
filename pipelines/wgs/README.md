# WGS 3.9.2 Docker/Apptainer流程

本分支提供WGS 3.9.2单机Snakemake + Apptainer运行方案。Snakemake在宿主机负责解析DAG，每个实际分析rule按模块进入对应SIF。Step1不使用qsub；qsub: N/A。

## 运行边界

- 基础入口只生成并运行生物信息分析Step1。
- newMaster、更新批次、Step2/Step3、上传、Redis和邮件代码保留在源码仓库中，供完整生产流程使用。
- 基础Docker批次不会复制或执行发布脚本。
- 软件命令使用SIF内路径；参考基因组、数据库、FASTQ和Sentieon许可证通过精确只读挂载提供。
- 项目目录是唯一读写挂载，不挂载整个`/bi`、`/sg2`或`/mnt`。

## 环境要求

批次配置在BS登录节点生成，实际Snakemake分析在安装Apptainer的单机节点运行，例如server10609。

```text
Python/Snakemake: /bi/software/Python-3.7.11/bin/snakemake
Snakemake:        7.32.4
Apptainer:        1.3.4
WGS运行镜像:      /sg2/33.chenjiucheng/software/wgs-runtime/V3.9.2/sif/
```

执行Python 3.7或Snakemake前必须设置：

```bash
export LD_LIBRARY_PATH=/bi/software/Python-3.7.11/lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
```

## 1. 生成批次目录

在BS登录节点执行。`--project-dir`填写server10610或server10609可见的完整分析目录。生成器仅对这两个执行节点使用的共享存储前缀做BS侧写入路径转换：

| server10610/server10609路径 | BS登录节点路径 |
|---|---|
| `/mnt/biodevrwbi/...` | `/bi/biodevrwbi/...` |
| `/mnt/biodevrwsg2/...` | `/sg2/biodevrwsg2/...` |

转换只用于BS上创建目录、同步pipeline和写入配置文件；生成的`config.yaml`与`Step1_run.sh`仍保留传入的`/mnt/...`执行路径。其他`/mnt`、`/bi`或`/sg2`路径不会被自动改写。

```bash
env LD_LIBRARY_PATH=/bi/software/Python-3.7.11/lib \
  PYTHONDONTWRITEBYTECODE=1 \
  /bi/software/Python-3.7.11/bin/python3 \
  /bi/biodevrwbi/33.chenjiucheng/project/wgs-3.9.2/script/0.prepare_wgs_batch.py \
    --batch 20260723A \
    --project-dir /mnt/biodevrwbi/33.chenjiucheng/wgs_test/WGS_20260723A_T7Hg38V3.9.2
```

生成器会完成：

1. 根据现有LIMS/Samplelist逻辑生成`sampleinfo.txt`。
2. 在`raw/`中建立FASTQ软链接，不复制FASTQ。
3. 使用当前仓库代码通过rsync生成`pipeline/`。
4. 从`cfg/config.template.yaml`生成全新的`config.yaml`。
5. 生成包含精确Apptainer挂载参数的`Step1_run.sh`。

目录结构：

```text
<project-dir>/
├── pipeline/
├── raw/
├── sampleinfo.txt
├── config.yaml
├── Step1_run.sh
├── logs/
└── tmp/
```

注意：生成器只自动发现当前LIMS中归属于指定芯片批次且满足条件的样本。跨批次家系成员或重分析样本必须先确认完整元数据和FASTQ来源。

## 2. 检查生成结果

在执行节点检查：

```bash
test -s <project-dir>/config.yaml
test -s <project-dir>/sampleinfo.txt
test -x <project-dir>/Step1_run.sh
test -s <project-dir>/pipeline/WGS_pipe.smk
find -L <project-dir>/raw -maxdepth 1 -type l
```

最后一条命令无输出表示没有失效FASTQ软链接。

## 3. Dry-run

登录实际执行节点后运行：

```bash
bash <project-dir>/Step1_run.sh -n
```

Dry-run必须能够构建`rule all`，且日志中不能出现`MissingInputException`或`WorkflowError`。

## 4. 前台运行

```bash
bash <project-dir>/Step1_run.sh
```

`Step1_run.sh`已经固定启用：

```text
--use-singularity
--rerun-incomplete
--rerun-triggers mtime
--latency-wait 120
--keep-going
--reason
--printshellcmds
```

## 5. 后台运行

```bash
cd <project-dir>
attempt=full_$(date +%Y%m%d_%H%M%S)
log="logs/step1.${attempt}.log"

nohup env WGS_ATTEMPT_ID="$attempt" \
  PYTHONDONTWRITEBYTECODE=1 \
  bash <project-dir>/Step1_run.sh >"$log" 2>&1 < /dev/null &

pid=$!
printf '%s\n' "$pid" > "logs/step1.${attempt}.pid"
printf 'host=%s pid=%s log=%s\n' "$(hostname)" "$pid" "$log"
```

查看状态：

```bash
ps -p "$(cat logs/step1.${attempt}.pid)" -o pid,ppid,stat,etime,%cpu,%mem,cmd
tail -f "logs/step1.${attempt}.log"
```

失败后修正镜像、配置或流程代码，再使用同一个项目目录重新执行`Step1_run.sh`；脚本已带`--rerun-incomplete`，不会主动删除已成功产物。

## 6. 完整生产入口

以下脚本属于完整生产辅助链，基础Docker Step1不会自动调用：

```text
script/0.prepare_wgs_batch_newMaster.py
script/1.update_wgs_batch.py
script/1.update_wgs_batch_newMaster.py
script/3.sync_sampleinfo_to_config.py
script/upload.py
script/upload.web.py
Redis和邮件相关脚本
```

Step2/Step3、上传、Redis、邮件和临床发布必须按照生产规范单独执行，不能把基础Step1的成功等同于结果发布完成。

## 7. 主要代码位置

```text
WGS_pipe.smk                 Snakemake总入口
rule/                        11个分析模块规则
cfg/config.template.yaml     批次配置模板、SIF和精确挂载配置
script/0.prepare_wgs_batch.py 基础批次生成入口
script/wgs_basic_batch.py    Docker Step1目录和启动脚本生成逻辑
script/wgs_batch_utils.py    完整生产批次及更新逻辑
script/wgs_rule_helpers.py   容器内rule辅助命令
```
