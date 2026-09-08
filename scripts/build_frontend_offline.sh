#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 1 ]]; then
  echo "usage: $0 <release-image-tag>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
FRONTEND_DIR="${ROOT_DIR}/frontend"
RELEASE_IMAGE="$1"
NODE_MAJOR="${NODE_MAJOR:-22}"
LOCK_SHA256="$(sha256sum "${FRONTEND_DIR}/package-lock.json" | awk '{print $1}')"
BUILDER_IMAGE="${FRONTEND_BUILDER_IMAGE:-airflow-demo/frontend-builder:node${NODE_MAJOR}-lock-${LOCK_SHA256:0:12}}"
RUNTIME_IMAGE="${FRONTEND_RUNTIME_IMAGE:-airflow-demo/frontend-runtime:nginx-1.30.3-local-contract}"
OUTPUT_DIR="${FRONTEND_OFFLINE_OUTPUT_DIR:-${ROOT_DIR}/.build/frontend-offline}"
TEST_IMAGE="airflow-demo/frontend-build-test:node${NODE_MAJOR}-lock-${LOCK_SHA256:0:12}"
BUILD_IMAGE="airflow-demo/frontend-build-artifact:node${NODE_MAJOR}-lock-${LOCK_SHA256:0:12}"

mkdir -p "${OUTPUT_DIR}"
STAGE_DIR="$(mktemp -d "${OUTPUT_DIR}/stage.XXXXXX")"
BUILD_CONTAINER=""
cleanup() {
  if [[ -n "${BUILD_CONTAINER}" ]]; then
    docker rm "${BUILD_CONTAINER}" >/dev/null 2>&1 || true
  fi
  rm -rf "${STAGE_DIR}"
}
trap cleanup EXIT

docker image inspect "${BUILDER_IMAGE}" >/dev/null
docker image inspect "${RUNTIME_IMAGE}" >/dev/null

RECORDED_LOCK="$(docker image inspect --format '{{ index .Config.Labels "io.airflow-demo.frontend.lock-sha256" }}' "${BUILDER_IMAGE}")"
RECORDED_NODE_MAJOR="$(docker image inspect --format '{{ index .Config.Labels "io.airflow-demo.frontend.node-major" }}' "${BUILDER_IMAGE}")"
if [[ "${RECORDED_LOCK}" != "${LOCK_SHA256}" ]]; then
  echo "builder image does not match frontend/package-lock.json" >&2
  exit 1
fi
if [[ "${RECORDED_NODE_MAJOR}" != "${NODE_MAJOR}" ]]; then
  echo "builder image Node major does not match NODE_MAJOR=${NODE_MAJOR}" >&2
  exit 1
fi

docker build \
  --pull=false \
  --network none \
  --build-arg "FRONTEND_BUILDER_IMAGE=${BUILDER_IMAGE}" \
  --target test \
  --tag "${TEST_IMAGE}" \
  --file "${FRONTEND_DIR}/Dockerfile.offline-build" \
  "${FRONTEND_DIR}"

docker build \
  --pull=false \
  --network none \
  --build-arg "FRONTEND_BUILDER_IMAGE=${BUILDER_IMAGE}" \
  --target build \
  --tag "${BUILD_IMAGE}" \
  --file "${FRONTEND_DIR}/Dockerfile.offline-build" \
  "${FRONTEND_DIR}"

mkdir -p "${STAGE_DIR}/dist"
BUILD_CONTAINER="$(docker create "${BUILD_IMAGE}")"
docker cp "${BUILD_CONTAINER}:/app/dist/." "${STAGE_DIR}/dist/"
docker rm "${BUILD_CONTAINER}" >/dev/null
BUILD_CONTAINER=""

docker build \
  --pull=false \
  --network none \
  --build-arg "BASE_FRONTEND_IMAGE=${RUNTIME_IMAGE}" \
  --tag "${RELEASE_IMAGE}" \
  --file "${FRONTEND_DIR}/Dockerfile.runtime-overlay" \
  "${STAGE_DIR}"

RUNTIME_IMAGE_ID="$(docker image inspect --format '{{.Id}}' "${RUNTIME_IMAGE}")"
RELEASE_IMAGE_ID="$(docker image inspect --format '{{.Id}}' "${RELEASE_IMAGE}")"
BUILDER_IMAGE_ID="$(docker image inspect --format '{{.Id}}' "${BUILDER_IMAGE}")"
if [[ -n "${FRONTEND_SOURCE_COMMIT:-}" ]]; then
  GIT_COMMIT="${FRONTEND_SOURCE_COMMIT}"
elif GIT_COMMIT="$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null)"; then
  :
else
  GIT_COMMIT="unknown"
fi
CREATED_AT="$(date --iso-8601=seconds)"
PROVENANCE_PATH="${OUTPUT_DIR}/frontend-image-provenance.json"

cat > "${PROVENANCE_PATH}" <<EOF
{
  "release_image": "${RELEASE_IMAGE}",
  "release_image_id": "${RELEASE_IMAGE_ID}",
  "runtime_image": "${RUNTIME_IMAGE}",
  "runtime_image_id": "${RUNTIME_IMAGE_ID}",
  "builder_image": "${BUILDER_IMAGE}",
  "builder_image_id": "${BUILDER_IMAGE_ID}",
  "node_major": "${NODE_MAJOR}",
  "package_lock_sha256": "${LOCK_SHA256}",
  "git_commit": "${GIT_COMMIT}",
  "created_at": "${CREATED_AT}"
}
EOF

printf 'release_image=%s\nrelease_image_id=%s\nprovenance=%s\n' \
  "${RELEASE_IMAGE}" "${RELEASE_IMAGE_ID}" "${PROVENANCE_PATH}"
