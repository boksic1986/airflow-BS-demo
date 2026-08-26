#!/usr/bin/env bash
set -euo pipefail

source_root=${1:-/mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1}
development_root=${2:-/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development}
source_root=$(realpath "${source_root}")
development_root=$(realpath "${development_root}")
case "${source_root}" in
  /mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1) ;;
  *) echo "unexpected WGS source root: ${source_root}" >&2; exit 2 ;;
esac
case "${development_root}" in
  /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development) ;;
  *) echo "unexpected Airflow development root: ${development_root}" >&2; exit 2 ;;
esac

source_commit=$(git -C "${source_root}" rev-parse HEAD)
source_status=$(git -C "${source_root}" status --porcelain=v1)
[[ -z "${source_status}" ]] || { echo "source worktree must be clean" >&2; exit 2; }
expected_source_commit=3489b3958869e5cfab983aca1eb9c7f158c06dff
[[ "${source_commit}" == "${expected_source_commit}" ]] || {
  echo "unexpected WGS source commit: ${source_commit}" >&2
  exit 2
}
cce_pipeline_version=0.5.0
cce_pipeline_source_commit=70a9a737c62865f232ed0b49f682aa7c9a69e467
cce_pipeline_wheel_sha256=43a4ab478e8b8810b1691bb755e54336b0bc8fd86a16d4fed9be3783036e1756
cce_profile_id=wgs-4.1.1-r1
cce_profile_sha256=19a7cc76cfc086c032c5e2329310d4ff90cd67e5cb52632bfb98f1b4fea59276
master_image_digest=sha256:815d70a6105b08b8fc6031a425cfed5ced8773e4d66c18ad98502b9a61ffeecc
content_sha=$(cd "${source_root}" && find . -path ./.git -prune -o -path '*/__pycache__' -prune -o -path './.pytest_cache' -prune -o -type f -printf '%P\0' | sort -z | xargs -0 -r sha256sum | sha256sum | awk '{print $1}')
snapshot_id="wgs-v4.1.1-candidate-${source_commit:0:7}-${content_sha:0:8}"
staging="${development_root}/.${snapshot_id}.staging.$$"
target="${development_root}/${snapshot_id}"
[[ ! -e "${target}" ]] || { echo "candidate snapshot already exists: ${target}" >&2; exit 3; }
mkdir -p "${staging}"
trap 'rm -rf --one-file-system "${staging}"' EXIT
# The source repository is copy-only. Private site configuration and legacy
# publication helpers are deliberately not admitted to an Airflow candidate.
rsync -a \
  --exclude='.git/' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  --exclude='prepare/config.yaml' \
  --exclude='script/z1.upload.sh' \
  --exclude='script/z3.save.sh' \
  --exclude='script/z4.delete_tmp.sh' \
  --exclude='script/z5.archive.sh' \
  --exclude='script/z6.sendmail.sh' \
  "${source_root}/" "${staging}/"
cat > "${staging}/PRIVATE_FILES_EXCLUDED.txt" <<'EOF'
prepare/config.yaml
script/z1.upload.sh
script/z3.save.sh
script/z4.delete_tmp.sh
script/z5.archive.sh
script/z6.sendmail.sh
EOF
cat > "${staging}/HOST_CONFIGURATION_REQUIRED.txt" <<'EOF'
prepare/config.yaml is intentionally excluded from this immutable snapshot.
The node200 runtime must mount or select the host-only production file.
EOF
cat > "${staging}/SOURCE_PROVENANCE.json" <<EOF
{"schema_version": "3", "source_path": "${source_root}", "source_commit": "${source_commit}", "source_content_sha256": "${content_sha}", "snapshot_id": "${snapshot_id}", "cce_pipeline_version": "${cce_pipeline_version}", "cce_pipeline_source_commit": "${cce_pipeline_source_commit}", "cce_pipeline_wheel_sha256": "${cce_pipeline_wheel_sha256}", "cce_profile_id": "${cce_profile_id}", "cce_profile_sha256": "${cce_profile_sha256}", "master_image_digest": "${master_image_digest}", "status": "candidate", "execution_enabled": false}
EOF
(cd "${staging}" && find . -path '*/__pycache__' -prune -o -path './.pytest_cache' -prune -o -type f ! -name SNAPSHOT_MANIFEST.sha256 -printf '%P\0' | sort -z | xargs -0 -r sha256sum > SNAPSHOT_MANIFEST.sha256)
manifest_sha=$(sha256sum "${staging}/SNAPSHOT_MANIFEST.sha256" | awk '{print $1}')
mv "${staging}" "${target}"
trap - EXIT
printf 'snapshot_id=%s\nsource_commit=%s\nsource_content_sha256=%s\nmanifest_sha256=%s\ntarget=%s\n' "${snapshot_id}" "${source_commit}" "${content_sha}" "${manifest_sha}" "${target}"
