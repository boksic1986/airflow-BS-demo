#!/usr/bin/env bash
set -euo pipefail

SOURCE_IMAGE="${SOURCE_IMAGE:-airflow-demo/niptpro:1.0.11-snakemake9.23.1-v1}"
TARGET_IMAGE="172.17.61.235:2333/niptpro/niptpro:1.1.11"
EXPECTED_SOURCE_ID="sha256:71df36b7f8080762f2db771e13e4daa7f4a666b3e1efc19c3bf12add22187254"
OUTPUT_DIR="${1:?usage: package_nipt_1_1_11.sh OUTPUT_DIR}"

mkdir -p "$OUTPUT_DIR"
source_id="$(docker image inspect "$SOURCE_IMAGE" --format '{{.Id}}')"
test "$source_id" = "$EXPECTED_SOURCE_ID" || {
  echo "Unexpected validated S9 source image: $source_id" >&2
  exit 1
}

docker tag "$SOURCE_IMAGE" "$TARGET_IMAGE"
runtime="$(docker run --rm --entrypoint /bin/bash "$TARGET_IMAGE" -lc \
  '/opt/snakemake9/bin/snakemake --version && /opt/snakemake9/bin/python --version && test -x /opt/airflow-demo/bin/run_nipt_s9.sh && echo logger=airflow-demo')"
grep -Fq '9.23.1' <<<"$runtime"
grep -Fq 'Python 3.12' <<<"$runtime"
grep -Fq 'logger=airflow-demo' <<<"$runtime"

archive="$OUTPUT_DIR/niptpro-1.1.11.tar.gz"
docker save "$TARGET_IMAGE" | gzip -1 > "$archive"
sha256sum "$archive" > "$archive.sha256"
target_id="$(docker image inspect "$TARGET_IMAGE" --format '{{.Id}}')"
cat > "$OUTPUT_DIR/image-provenance.json" <<EOF
{
  "source_image": "$SOURCE_IMAGE",
  "source_image_id": "$source_id",
  "target_image": "$TARGET_IMAGE",
  "target_image_id": "$target_id",
  "snakemake": "9.23.1",
  "python": "3.12",
  "logger": "airflow-demo"
}
EOF
sha256sum "$OUTPUT_DIR/image-provenance.json" > "$OUTPUT_DIR/image-provenance.json.sha256"
echo "$runtime"
echo "Packaged $TARGET_IMAGE as $archive"
