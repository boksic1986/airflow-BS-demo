#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <airflow-demo-source> <revision>" >&2
  exit 2
}

[[ $# -eq 2 ]] || usage

SOURCE_ROOT="$(readlink -f "$1")"
REVISION="$2"
PROJECT_ROOT="${WGS_PROJECT_ROOT:-/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS}"
CONDA_BIN="${WGS_CONDA_BIN:-/sg2/33.chenjiucheng/software/miniforge3/condabin/conda}"
ENV_ROOT="$PROJECT_ROOT/envs/wgs-snakemake9"
RELEASES_ROOT="$PROJECT_ROOT/releases"
RELEASE_ROOT="$RELEASES_ROOT/$REVISION"

[[ "$REVISION" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "Unsafe revision: $REVISION" >&2; exit 1; }
[[ -x "$CONDA_BIN" ]] || { echo "Conda is not executable: $CONDA_BIN" >&2; exit 1; }
for path in \
  "$SOURCE_ROOT/pipelines/wgs_s9/WGS_pipeline.Snakefile" \
  "$SOURCE_ROOT/dags/wgs_host_runner.py" \
  "$SOURCE_ROOT/dags/common/resource_monitor.py" \
  "$SOURCE_ROOT/dags/snakemake_logger_plugin_airflow_demo/__init__.py" \
  "$SOURCE_ROOT/scripts/wgs_ssh_gate.sh"; do
  [[ -r "$path" ]] || { echo "Missing release input: $path" >&2; exit 1; }
done

mkdir -p "$PROJECT_ROOT"/{bin,env,envs,releases,shared/ssh}
if [[ ! -x "$ENV_ROOT/bin/snakemake" ]]; then
  "$CONDA_BIN" create -y -p "$ENV_ROOT" -c conda-forge -c bioconda \
    python=3.12 snakemake=9.23.1 pandas pyyaml snakemake-interface-logger-plugins
fi
[[ "$($ENV_ROOT/bin/snakemake --version)" == "9.23.1" ]] || {
  echo "Existing WGS scheduler environment is not Snakemake 9.23.1: $ENV_ROOT" >&2
  exit 1
}

[[ ! -e "$RELEASE_ROOT" ]] || { echo "Release already exists: $RELEASE_ROOT" >&2; exit 1; }
STAGING="$RELEASES_ROOT/.$REVISION.staging.$$"
trap 'rm -rf -- "$STAGING"' EXIT
mkdir -p "$STAGING"/{dags/common,dags/snakemake_logger_plugin_airflow_demo,pipelines}
cp -a "$SOURCE_ROOT/pipelines/wgs_s9" "$STAGING/pipelines/"
cp -a "$SOURCE_ROOT/dags/wgs_host_runner.py" "$STAGING/dags/"
cp -a "$SOURCE_ROOT/dags/common/__init__.py" "$SOURCE_ROOT/dags/common/resource_monitor.py" "$STAGING/dags/common/"
cp -a "$SOURCE_ROOT/dags/snakemake_logger_plugin_airflow_demo/__init__.py" "$STAGING/dags/snakemake_logger_plugin_airflow_demo/"

(
  cd "$STAGING"
  find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
)
mv "$STAGING" "$RELEASE_ROOT"
ln -sfn "releases/$REVISION" "$PROJECT_ROOT/current.next"
mv -Tf "$PROJECT_ROOT/current.next" "$PROJECT_ROOT/current"
install -m 0755 "$SOURCE_ROOT/scripts/wgs_ssh_gate.sh" "$PROJECT_ROOT/bin/wgs-ssh-gate"

"$CONDA_BIN" list -p "$ENV_ROOT" --explicit > "$PROJECT_ROOT/envs/wgs-snakemake9.explicit.txt"
sha256sum "$PROJECT_ROOT/envs/wgs-snakemake9.explicit.txt" > "$PROJECT_ROOT/envs/wgs-snakemake9.explicit.txt.sha256"
PYTHONPATH="$RELEASE_ROOT/dags" "$ENV_ROOT/bin/snakemake" --logger airflow-demo --help >/dev/null
trap - EXIT

echo "WGS S9 host release deployed: $RELEASE_ROOT"
echo "Current release: $(readlink "$PROJECT_ROOT/current")"
