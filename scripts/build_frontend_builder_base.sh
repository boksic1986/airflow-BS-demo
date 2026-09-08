#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
FRONTEND_DIR="${ROOT_DIR}/frontend"

NODE_IMAGE="${NODE_IMAGE:-node:22-bookworm}"
NODE_MAJOR="${NODE_MAJOR:-22}"
LOCK_SHA256="$(sha256sum "${FRONTEND_DIR}/package-lock.json" | awk '{print $1}')"
BUILDER_IMAGE="${FRONTEND_BUILDER_IMAGE:-airflow-demo/frontend-builder:node${NODE_MAJOR}-lock-${LOCK_SHA256:0:12}}"
OUTPUT_DIR="${1:-${ROOT_DIR}/.build/frontend-builder}"

mkdir -p "${OUTPUT_DIR}"
umask 027

docker image inspect "${NODE_IMAGE}" >/dev/null
docker build \
  --pull=false \
  --build-arg "NODE_IMAGE=${NODE_IMAGE}" \
  --build-arg "NODE_MAJOR=${NODE_MAJOR}" \
  --build-arg "FRONTEND_LOCK_SHA256=${LOCK_SHA256}" \
  --tag "${BUILDER_IMAGE}" \
  --file "${FRONTEND_DIR}/Dockerfile.builder-base" \
  "${FRONTEND_DIR}"

RECORDED_LOCK="$(docker image inspect --format '{{ index .Config.Labels "io.airflow-demo.frontend.lock-sha256" }}' "${BUILDER_IMAGE}")"
RECORDED_NODE_MAJOR="$(docker image inspect --format '{{ index .Config.Labels "io.airflow-demo.frontend.node-major" }}' "${BUILDER_IMAGE}")"
if [[ "${RECORDED_LOCK}" != "${LOCK_SHA256}" ]]; then
  echo "builder lock label mismatch" >&2
  exit 1
fi
if [[ "${RECORDED_NODE_MAJOR}" != "${NODE_MAJOR}" ]]; then
  echo "builder Node major label mismatch" >&2
  exit 1
fi

ARCHIVE_BASENAME="frontend-builder-node${NODE_MAJOR}-lock-${LOCK_SHA256:0:12}.tar"
ARCHIVE_PATH="${OUTPUT_DIR}/${ARCHIVE_BASENAME}"
PROVENANCE_PATH="${OUTPUT_DIR}/frontend-builder-provenance.json"
docker save --output "${ARCHIVE_PATH}" "${BUILDER_IMAGE}"
(cd "${OUTPUT_DIR}" && sha256sum "${ARCHIVE_BASENAME}" > "${ARCHIVE_BASENAME}.sha256")

NODE_IMAGE_ID="$(docker image inspect --format '{{.Id}}' "${NODE_IMAGE}")"
BUILDER_IMAGE_ID="$(docker image inspect --format '{{.Id}}' "${BUILDER_IMAGE}")"
if [[ -n "${FRONTEND_SOURCE_COMMIT:-}" ]]; then
  GIT_COMMIT="${FRONTEND_SOURCE_COMMIT}"
elif GIT_COMMIT="$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null)"; then
  :
else
  GIT_COMMIT="unknown"
fi
CREATED_AT="$(date --iso-8601=seconds)"

cat > "${PROVENANCE_PATH}" <<EOF
{
  "builder_image": "${BUILDER_IMAGE}",
  "builder_image_id": "${BUILDER_IMAGE_ID}",
  "node_image": "${NODE_IMAGE}",
  "node_image_id": "${NODE_IMAGE_ID}",
  "node_major": "${NODE_MAJOR}",
  "package_lock_sha256": "${LOCK_SHA256}",
  "git_commit": "${GIT_COMMIT}",
  "created_at": "${CREATED_AT}",
  "archive": "${ARCHIVE_BASENAME}"
}
EOF

printf 'builder_image=%s\narchive=%s\nprovenance=%s\n' \
  "${BUILDER_IMAGE}" "${ARCHIVE_PATH}" "${PROVENANCE_PATH}"
