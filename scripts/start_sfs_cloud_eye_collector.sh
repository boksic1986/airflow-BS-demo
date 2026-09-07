#!/usr/bin/env bash
set -euo pipefail

config_root="${SFS_CLOUD_EYE_CONFIG_ROOT:?set SFS_CLOUD_EYE_CONFIG_ROOT}"
python_bin="${WGS_PYTHON:?set WGS_PYTHON}"
collector="${config_root}/collect_sfs_cloud_eye.py"
pid_file="${config_root}/sfs-cloud-eye.pid"
lock_file="${config_root}/sfs-cloud-eye.lock"
log_file="${config_root}/sfs-cloud-eye.error.log"

if [[ ! -x "${python_bin}" || ! -r "${collector}" ]]; then
  echo "SFS Cloud Eye collector runtime is unavailable" >&2
  exit 1
fi

: "${SFS_CLOUD_EYE_CREDENTIALS:?set SFS_CLOUD_EYE_CREDENTIALS}"
: "${HWC_PROJECT_ID:?set HWC_PROJECT_ID}"
: "${SFS_CLOUD_EYE_RESOURCE_ID:?set SFS_CLOUD_EYE_RESOURCE_ID}"
: "${PLATFORM_CLOUD_METRICS_SPOOL:?set PLATFORM_CLOUD_METRICS_SPOOL}"
if [[ ! -r "${SFS_CLOUD_EYE_CREDENTIALS}" ]]; then
  echo "SFS Cloud Eye credentials are unavailable" >&2
  exit 1
fi
credentials_mode="$(stat -c '%a' "${SFS_CLOUD_EYE_CREDENTIALS}")"
if [[ "${credentials_mode}" != "600" ]]; then
  echo "SFS Cloud Eye credentials must use mode 600" >&2
  exit 1
fi

if [[ -s "${pid_file}" ]]; then
  existing_pid="$(cat "${pid_file}")"
  if [[ "${existing_pid}" =~ ^[0-9]+$ ]] \
    && kill -0 "${existing_pid}" 2>/dev/null \
    && grep -Fq "${collector}" "/proc/${existing_pid}/cmdline" 2>/dev/null; then
    printf '{"status":"running","pid":%s}\n' "${existing_pid}"
    exit 0
  fi
fi

if [[ -f "${log_file}" ]] && (( $(stat -c '%s' "${log_file}") > 10485760 )); then
  mv -f "${log_file}" "${log_file}.1"
fi

nohup setsid flock -n "${lock_file}" \
  "${python_bin}" "${collector}" --interval-seconds 60 \
  </dev/null >>"${log_file}" 2>&1 &
collector_pid=$!
printf '%s\n' "${collector_pid}" >"${pid_file}"
sleep 1
if ! kill -0 "${collector_pid}" 2>/dev/null; then
  echo "SFS Cloud Eye collector failed to stay running" >&2
  exit 1
fi
printf '{"status":"started","pid":%s}\n' "${collector_pid}"
