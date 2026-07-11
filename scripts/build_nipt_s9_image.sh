#!/usr/bin/env bash
set -euo pipefail

base_image="${NIPT_S9_BASE_IMAGE:-172.17.61.235:2333/niptpro/niptpro:1.0.11}"
expected_base_id="${NIPT_S9_BASE_IMAGE_ID:-sha256:1cd289afbd0c48564a530b1a56dd608dc2803b63ed6a4a4c0ca313ef84380b26}"
target_image="${NIPT_S9_IMAGE:-airflow-demo/niptpro:1.0.11-snakemake9.23.1-v1}"
release_dir="${NIPT_S9_RELEASE_DIR:-/home/jiucheng/pipelines/NIPT/images/niptpro-1.0.11-s9-v1}"

actual_base_id="$(docker image inspect "$base_image" --format '{{.Id}}')"
if [[ "$actual_base_id" != "$expected_base_id" ]]; then
  echo "NIPT base image mismatch: expected=$expected_base_id actual=$actual_base_id" >&2
  exit 1
fi

if [[ "${NIPT_S9_SKIP_BUILD:-false}" != "true" ]]; then
  docker build \
    --build-arg "BASE_IMAGE=$base_image" \
    --tag "$target_image" \
    --file nipt_s9_image/Dockerfile \
    .
else
  docker image inspect "$target_image" >/dev/null
fi

docker run --rm --entrypoint /bin/bash "$target_image" -lc '
  set -euo pipefail
  test "$(/opt/snakemake9/bin/snakemake --version)" = "9.23.1"
  test "$(/opt/conda/bin/snakemake --version)" = "7.32.4"
  PYTHONPATH=/opt/airflow-demo-plugins /opt/snakemake9/bin/snakemake --logger airflow-demo --help >/dev/null
'

mkdir -p "$release_dir"
docker image inspect "$target_image" --format '{{json .}}' > "$release_dir/image-inspect.json"
sha256sum "$release_dir/image-inspect.json" > "$release_dir/image-inspect.json.sha256"
target_image_id="$(docker image inspect "$target_image" --format '{{.Id}}')"
{
  printf 'base_image=%s\n' "$base_image"
  printf 'base_image_id=%s\n' "$actual_base_id"
  printf 'target_image=%s\n' "$target_image"
  printf 'target_image_id=%s\n' "$target_image_id"
  docker run --rm --entrypoint /bin/bash "$target_image" -lc '
    set -euo pipefail
    printf "snakemake9=%s\n" "$(/opt/snakemake9/bin/snakemake --version)"
    printf "snakemake9_python=%s\n" "$(/opt/snakemake9/bin/python --version 2>&1)"
    /opt/snakemake9/bin/python -c "import docker, importlib.metadata as m, pandas; print(\"pandas=\" + pandas.__version__); print(\"docker_py=\" + docker.__version__); print(\"logger_interface=\" + m.version(\"snakemake-interface-logger-plugins\"))"
    printf "analysis_snakemake=%s\n" "$(/opt/conda/bin/snakemake --version)"
    printf "analysis_python=%s\n" "$(/opt/conda/bin/python --version 2>&1)"
    /opt/conda/bin/python -c "from AneuScreen2 import feature_loading; print(f\"aneuscreen2={feature_loading.__file__}\")"
  '
} > "$release_dir/software-versions.txt"
docker run --rm --entrypoint /bin/bash "$target_image" -lc \
  'micromamba list -p /opt/snakemake9 --json' > "$release_dir/snakemake9-packages.json"
docker run --rm --entrypoint /bin/bash "$target_image" -lc \
  '/opt/conda/bin/python -m pip freeze' > "$release_dir/analysis-python-packages.txt"
sha256sum \
  "$release_dir/image-inspect.json" \
  "$release_dir/software-versions.txt" \
  "$release_dir/snakemake9-packages.json" \
  "$release_dir/analysis-python-packages.txt" \
  > "$release_dir/software-manifests.sha256"
if [[ "${NIPT_S9_ARCHIVE:-false}" == "true" ]]; then
  archive="$release_dir/niptpro-1.0.11-snakemake9.23.1-v1.oci.tar.gz"
  archive_partial="$archive.partial"
  docker save "$target_image" | gzip -1 > "$archive_partial"
  mv "$archive_partial" "$archive"
  sha256sum "$archive" > "$archive.sha256"
fi
echo "NIPT S9 image ready: $target_image"
