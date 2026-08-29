#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <staged-repository-root>" >&2
  exit 2
fi

stage_root=$(readlink -f "$1")
test_db="t143_wgs_t7_migration"
postgres_container="airflow-wgs-postgres-1"
backend_container="airflow-wgs-backend-1"
backend_image="airflow-demo/backend:t139-wgs-4.1.1-disabled"
docker_network="nipt_analysis_test_net"

if [[ ! -d "${stage_root}/backend/alembic" ]]; then
  echo "staged repository is missing" >&2
  exit 2
fi
if [[ -n $(docker exec "${postgres_container}" psql -U airflow -d postgres -Atc \
  "SELECT 1 FROM pg_database WHERE datname = '${test_db}'") ]]; then
  echo "refusing to reuse existing database ${test_db}" >&2
  exit 3
fi

cleanup() {
  docker exec "${postgres_container}" dropdb -U airflow --if-exists "${test_db}" >/dev/null
}
trap cleanup EXIT
docker exec "${postgres_container}" createdb -U airflow -O biodemo "${test_db}"

database_url=$(docker exec "${backend_container}" printenv DATABASE_URL)
test_database_url="${database_url%/*}/${test_db}"
backend_env_args=()
while IFS= read -r environment_entry; do
  [[ -z "${environment_entry}" ]] && continue
  [[ "${environment_entry%%=*}" == "DATABASE_URL" ]] && continue
  backend_env_args+=( -e "${environment_entry}" )
done < <(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "${backend_container}")

run_alembic() {
  docker run --rm \
    --network "${docker_network}" \
    "${backend_env_args[@]}" \
    -e "DATABASE_URL=${test_database_url}" \
    -e "PYTHONPATH=/workspace/backend" \
    -v "${stage_root}:/workspace:ro" \
    -w /workspace/backend \
    "${backend_image}" \
    alembic "$@"
}

run_alembic upgrade 20260827_0010
run_alembic upgrade 20260829_0011

docker exec -i "${postgres_container}" psql -v ON_ERROR_STOP=1 -U biodemo -d "${test_db}" <<'SQL'
DO $$
DECLARE
  revision text;
  nullable_count integer;
  delete_rule text;
  scanner_table_count integer;
  action_table_count integer;
BEGIN
  SELECT version_num INTO revision FROM alembic_version;
  IF revision <> '20260829_0011' THEN
    RAISE EXCEPTION 'unexpected revision: %', revision;
  END IF;
  SELECT count(*) INTO nullable_count
  FROM information_schema.columns
  WHERE table_name = 'wgs_intake_batch'
    AND column_name = 'analysis_id'
    AND is_nullable = 'YES';
  IF nullable_count <> 1 THEN
    RAISE EXCEPTION 'wgs_intake_batch.analysis_id is not nullable';
  END IF;
  SELECT rc.delete_rule INTO delete_rule
  FROM information_schema.referential_constraints rc
  WHERE rc.constraint_name = 'wgs_intake_batch_analysis_id_fkey';
  IF delete_rule <> 'SET NULL' THEN
    RAISE EXCEPTION 'unexpected analysis_id delete rule: %', delete_rule;
  END IF;
  SELECT count(*) INTO scanner_table_count
  FROM information_schema.tables
  WHERE table_name = 'wgs_intake_scanner_state';
  SELECT count(*) INTO action_table_count
  FROM information_schema.tables
  WHERE table_name = 'wgs_maintenance_action';
  IF scanner_table_count <> 1 OR action_table_count <> 1 THEN
    RAISE EXCEPTION 'new WGS intake/maintenance tables are missing';
  END IF;
END $$;
SQL

run_alembic downgrade 20260827_0010
run_alembic upgrade 20260829_0011

echo "migration smoke passed: 20260827_0010 -> 20260829_0011 -> 20260827_0010 -> 20260829_0011"
