from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any, Dict, Iterable, List


RUN_MODE_ALIASES = {"k8s": "cce"}


def normalize_run_mode(value: str) -> str:
    mode = RUN_MODE_ALIASES.get(str(value).strip().lower(), str(value).strip().lower())
    if mode not in {"sge", "local", "cce"}:
        raise ValueError("run mode must be sge, local, or cce")
    return mode


def batch_execution_config(run_mode: str) -> Dict[str, str]:
    return {"executor": normalize_run_mode(run_mode)}


def _quote(value: object) -> str:
    return shlex.quote(str(value))


def _runtime_binds(template: Dict[str, Any], analysis_dir: Path, fastq_sources: Iterable[str]) -> str:
    binds: List[str] = []
    for bind in template.get("runtime_binds", {}).values():
        if not isinstance(bind, dict):
            continue
        source = bind.get("source")
        destination = bind.get("destination")
        mode = bind.get("mode", "ro")
        if source and destination:
            binds.append(f"{source}:{destination}:{mode}")
    binds.append(f"{analysis_dir}:{analysis_dir}:rw")
    for source in fastq_sources:
        lexical_parent = Path(source).expanduser().parent
        resolved_parent = Path(source).expanduser().resolve().parent
        binds.append(f"{lexical_parent}:{lexical_parent}:ro")
        if resolved_parent != lexical_parent:
            binds.append(f"{resolved_parent}:{resolved_parent}:ro")
    binds.append("/sys/fs/cgroup:/sys/fs/cgroup:ro")
    return ",".join(dict.fromkeys(binds))


def render_step1(
    analysis_dir: Path | str,
    run_mode: str,
    prepare_config: Dict[str, Any],
    analysis_template: Dict[str, Any],
    fastq_sources: Iterable[str] = (),
) -> str:
    run_mode = normalize_run_mode(run_mode)
    if run_mode == "cce":
        raise ValueError("CCE batches use the generated upload/run/status/finish Step scripts")
    project = Path(analysis_dir)
    runtime = prepare_config["runtime"]
    _ = analysis_template, fastq_sources

    return f'''#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR={_quote(project)}
PYTHON_BIN={_quote(runtime["python"])}
SNAKEMAKE={_quote(runtime["snakemake"])}
RUN_MODE={_quote(run_mode)}
PROFILE_DIR="${{PROJECT_DIR}}/pipeline/cfg/profiles/${{RUN_MODE}}"

BACKGROUND=0
WORKER=0
WORKER_ATTEMPT=""
SNAKEMAKE_ARGS=()
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --background)
      BACKGROUND=1
      shift
      ;;
    --worker)
      WORKER=1
      WORKER_ATTEMPT="$2"
      shift 2
      ;;
    --)
      shift
      SNAKEMAKE_ARGS+=("$@")
      break
      ;;
    *)
      SNAKEMAKE_ARGS+=("$1")
      shift
      ;;
  esac
done

TIME_ARGS=(-v)
export WGS_PYTHON="${{PYTHON_BIN}}"

if [[ -n "${{WORKER_ATTEMPT}}" ]]; then
  ATTEMPT_ID="${{WORKER_ATTEMPT}}"
else
  ATTEMPT_ID="${{WGS_ATTEMPT_ID:-$(date +%Y%m%d_%H%M%S)}}"
fi
case "${{ATTEMPT_ID}}" in
  *[!A-Za-z0-9_.-]*) echo "invalid WGS_ATTEMPT_ID: ${{ATTEMPT_ID}}" >&2; exit 64 ;;
esac

LOG_DIR="${{PROJECT_DIR}}/log"
ATTEMPT_TMP="${{PROJECT_DIR}}/tmp/${{ATTEMPT_ID}}"
LOG_FILE="${{LOG_DIR}}/step1.${{ATTEMPT_ID}}.log"
PID_FILE="${{LOG_DIR}}/step1.${{ATTEMPT_ID}}.pid"
TIME_FILE="${{LOG_DIR}}/step1.${{ATTEMPT_ID}}.time.txt"
EXIT_FILE="${{LOG_DIR}}/step1.${{ATTEMPT_ID}}.exitcode"
META_FILE="${{LOG_DIR}}/step1.${{ATTEMPT_ID}}.metadata.tsv"
mkdir -p "${{LOG_DIR}}" "${{ATTEMPT_TMP}}/tmp" "${{ATTEMPT_TMP}}/apptainer-cache" "${{ATTEMPT_TMP}}/snakemake-source-cache"
export TMPDIR="${{ATTEMPT_TMP}}/tmp"
export APPTAINER_TMPDIR="${{ATTEMPT_TMP}}/tmp"
export APPTAINER_CACHEDIR="${{ATTEMPT_TMP}}/apptainer-cache"
export SNAKEMAKE_SOURCE_CACHE="${{ATTEMPT_TMP}}/snakemake-source-cache"
SNAKEMAKE_CMD=(
  "${{SNAKEMAKE}}"
  --snakefile "${{PROJECT_DIR}}/pipeline/WGS_pipe.smk"
  --configfile "${{PROJECT_DIR}}/config.yaml"
  --directory "${{PROJECT_DIR}}"
  --profile "${{PROFILE_DIR}}"
)
SNAKEMAKE_CMD+=(
  --rerun-incomplete
  --rerun-triggers mtime
  --keep-going
  --printshellcmds
)
if [[ "${{#SNAKEMAKE_ARGS[@]}}" -gt 0 ]]; then
  SNAKEMAKE_CMD+=("${{SNAKEMAKE_ARGS[@]}}")
fi

run_workflow() {{
  printf '%s\n' "$$" > "${{PID_FILE}}"
  printf 'hostname\t%s\n' "$(hostname)" > "${{META_FILE}}"
  printf 'run_mode\t%s\n' "${{RUN_MODE}}" >> "${{META_FILE}}"
  printf 'started_at\t%s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" >> "${{META_FILE}}"
  printf 'command\t' >> "${{META_FILE}}"
  printf '%q ' "${{SNAKEMAKE_CMD[@]}}" >> "${{META_FILE}}"
  printf '\n' >> "${{META_FILE}}"
  set +e
  /usr/bin/time "${{TIME_ARGS[@]}}" -o "${{TIME_FILE}}" "${{SNAKEMAKE_CMD[@]}}"
  workflow_rc=$?
  set -e
  printf '%s\n' "${{workflow_rc}}" > "${{EXIT_FILE}}"
  printf 'finished_at\t%s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" >> "${{META_FILE}}"
  if [[ "${{workflow_rc}}" -eq 0 ]]; then
    case "${{ATTEMPT_TMP}}" in
      "${{PROJECT_DIR}}"/tmp/*) rm -rf -- "${{ATTEMPT_TMP}}" ;;
      *) echo "refusing unsafe tmp cleanup: ${{ATTEMPT_TMP}}" >&2; return 70 ;;
    esac
  fi
  return "${{workflow_rc}}"
}}

if [[ "${{BACKGROUND}}" -eq 1 && "${{WORKER}}" -eq 0 ]]; then
  SCRIPT_PATH="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
  BACKGROUND_COMMAND=(bash "${{SCRIPT_PATH}}" --worker "${{ATTEMPT_ID}}" --)
  if [[ "${{#SNAKEMAKE_ARGS[@]}}" -gt 0 ]]; then
    BACKGROUND_COMMAND+=("${{SNAKEMAKE_ARGS[@]}}")
  fi
  nohup "${{BACKGROUND_COMMAND[@]}}" > "${{LOG_FILE}}" 2>&1 &
  worker_pid=$!
  printf '%s\n' "${{worker_pid}}" > "${{PID_FILE}}"
  echo "Step1 已在后台启动，PID=${{worker_pid}}，日志=${{LOG_FILE}}"
  exit 0
fi

if [[ "${{WORKER}}" -eq 1 ]]; then
  run_workflow
  exit $?
fi

set +e
run_workflow 2>&1 | tee "${{LOG_FILE}}"
workflow_rc=${{PIPESTATUS[0]}}
set -e
exit "${{workflow_rc}}"
'''


def write_step1(
    path: Path | str,
    analysis_dir: Path | str,
    run_mode: str,
    prepare_config: Dict[str, Any],
    analysis_template: Dict[str, Any],
    fastq_sources: Iterable[str] = (),
) -> None:
    target = Path(path)
    target.write_text(
        render_step1(analysis_dir, run_mode, prepare_config, analysis_template, fastq_sources=fastq_sources),
        encoding="utf-8",
    )
    target.chmod(0o755)
