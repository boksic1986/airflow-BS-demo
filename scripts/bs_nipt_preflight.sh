#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/mnt/biodevrwbi/33.chenjiucheng/project/airflow-NIPT}"
NETWORK_NAME="nipt_analysis_test_net"
EXPECTED_SUBNET="192.168.199.0/24"
EXPECTED_GATEWAY="192.168.199.1"
STATIC_IPS=(192.168.199.5 192.168.199.10 192.168.199.11 192.168.199.12 192.168.199.20 192.168.199.40 192.168.199.50)

test -d "$PROJECT_ROOT"
probe="$PROJECT_ROOT/.t126-write-probe-$$"
: > "$probe"
rm -f "$probe"

test -d "$PROJECT_ROOT/shared"
docker run --rm --entrypoint bash --user 50000:0 -v "$PROJECT_ROOT/shared:/shared" \
  "${AIRFLOW_IMAGE:?Set AIRFLOW_IMAGE}" \
  -c ': > /shared/.t126-airflow-write-probe && rm -f /shared/.t126-airflow-write-probe'

ipam="$(docker network inspect "$NETWORK_NAME" --format '{{json .IPAM.Config}}')"
grep -Fq "\"Subnet\":\"$EXPECTED_SUBNET\"" <<<"$ipam"
grep -Fq "\"Gateway\":\"$EXPECTED_GATEWAY\"" <<<"$ipam"

attachments="$(docker network inspect "$NETWORK_NAME" --format '{{range $id, $c := .Containers}}{{$c.Name}} {{$c.IPv4Address}}{{println}}{{end}}')"
project_prefix="${COMPOSE_PROJECT_NAME:-airflow-nipt}-"
for address in "${STATIC_IPS[@]}"; do
  while read -r container_name allocated_address; do
    if [[ "$allocated_address" == "$address/"* && "$container_name" != "$project_prefix"* ]]; then
      echo "Static address is already allocated by $container_name: $address" >&2
      exit 1
    fi
  done <<<"$attachments"
done

for path in \
  "${NIPT_FASTQ_HOST_ROOT:?Set NIPT_FASTQ_HOST_ROOT}" \
  "${NIPT_WORKFLOW_HOST_ROOT:?Set NIPT_WORKFLOW_HOST_ROOT}/niptplus/Snakefile" \
  "${NIPT_WORKFLOW_HOST_ROOT}/refdir" \
  "${NIPT_LOCALE_HOST_ROOT:?Set NIPT_LOCALE_HOST_ROOT}"; do
  test -r "$path" || { echo "Required path is not readable: $path" >&2; exit 1; }
done

echo "T126 preflight passed: project root, external network, static IPs, and NIPT mounts"
