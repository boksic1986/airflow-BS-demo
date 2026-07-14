#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="${1:?usage: package_bs_platform_images.sh OUTPUT_DIR GIT_SHA}"
GIT_SHA="${2:?usage: package_bs_platform_images.sh OUTPUT_DIR GIT_SHA}"
mkdir -p "$OUTPUT_DIR"

images=(
  "airflow-demo/airflow:bs-nipt-$GIT_SHA"
  "airflow-demo/backend:bs-nipt-$GIT_SHA"
  "airflow-demo/frontend:bs-nipt-$GIT_SHA"
  "postgres:15-alpine"
  "redis:7-alpine"
  "172.17.61.235:2333/niptpro/pytorch:biosan"
)

for image in "${images[@]}"; do
  docker image inspect "$image" >/dev/null
  name="$(sed 's#[/:]#_#g' <<<"$image")"
  archive="$OUTPUT_DIR/$name.tar.gz"
  docker save "$image" | gzip -1 > "$archive"
  sha256sum "$archive" > "$archive.sha256"
  docker image inspect "$image" --format '{{.RepoTags}} {{.Id}}' > "$archive.image-id.txt"
done

(cd "$OUTPUT_DIR" && sha256sum *.tar.gz > SHA256SUMS)
echo "Packaged ${#images[@]} platform images into $OUTPUT_DIR"
