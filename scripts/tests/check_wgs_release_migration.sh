#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <staged-repository-root> <wgs-env-file|->" >&2
  exit 2
fi

stage_root=$(readlink -f "$1")
env_file="$2"
test_db="t142_wgs_release_migration"
postgres_container="airflow-wgs-postgres-1"
backend_image="airflow-demo/backend:t139-wgs-4.1.1-disabled"
docker_network="nipt_analysis_test_net"

if [[ ! -d "${stage_root}/backend/alembic" ]]; then
  echo "staged repository is missing" >&2
  exit 2
fi
if [[ "${env_file}" != "-" ]]; then
  env_file=$(readlink -f "${env_file}")
  if [[ ! -f "${env_file}" ]]; then
    echo "environment file is missing" >&2
    exit 2
  fi
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

if [[ "${env_file}" == "-" ]]; then
  DATABASE_URL=$(docker exec airflow-wgs-backend-1 printenv DATABASE_URL)
else
  set -a
  # shellcheck disable=SC1090
  source "${env_file}"
  set +a
fi
test_database_url="${DATABASE_URL%/*}/${test_db}"

backend_env_args=()
while IFS= read -r environment_entry; do
  [[ -z "${environment_entry}" ]] && continue
  environment_name="${environment_entry%%=*}"
  if [[ "${environment_name}" == "DATABASE_URL" ]]; then
    continue
  fi
  backend_env_args+=( -e "${environment_entry}" )
done < <(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' airflow-wgs-backend-1)

run_alembic() {
  docker run --rm \
    --network "${docker_network}" \
    "${backend_env_args[@]}" \
    -e "DATABASE_URL=${test_database_url}" \
    -e "PYTHONPATH=/workspace/backend" \
    -v "${stage_root}:/workspace:ro" \
    -w /workspace/backend \
    "${backend_image}" \
    alembic upgrade "$1"
}

run_alembic 20260826_0009

docker exec -i "${postgres_container}" psql -v ON_ERROR_STOP=1 -U biodemo -d "${test_db}" <<'SQL'
INSERT INTO analysis_run (
  analysis_id, pipeline_name, dag_id, mode, execution_mode, attempt,
  status, workdir, params_json
) VALUES (
  'T142-MIGRATION-SENTINEL', 'wgs', 'bio_wgs', 'new', 'cce', 1,
  'created', '/sentinel',
  '{"pipeline_snapshot_id":"wgs-4.1.1-1778fca","source_commit":"1778fcabd99b5253aa90cd410112dc2f78e0c51a","snapshot_manifest_sha256":"obsolete"}'::jsonb
);

INSERT INTO observer_run_state (
  analysis_id, attempt, pipeline_snapshot_id, run_label,
  relative_evidence_path, status, updated_at
) VALUES (
  'T142-MIGRATION-SENTINEL', 1, 'wgs-4.1.1-1778fca',
  't142-migration', 'runs/t142/evidence', 'pending', now()
);

INSERT INTO user_account (
  username, password_hash, role, enabled, created_at, updated_at
) VALUES (
  't142-migration-admin', 'sentinel-not-a-real-password', 'admin', true,
  now(), now()
);
SQL

run_alembic head

docker exec -i "${postgres_container}" psql -v ON_ERROR_STOP=1 -U biodemo -d "${test_db}" <<'SQL'
DO $$
DECLARE
  revision text;
  release_id text;
  source_commit text;
  old_key_count integer;
  release_column_count integer;
  snapshot_column_count integer;
  admin_count integer;
BEGIN
  SELECT version_num INTO revision FROM alembic_version;
  IF revision <> '20260827_0010' THEN
    RAISE EXCEPTION 'unexpected revision: %', revision;
  END IF;

  SELECT params_json->>'pipeline_release_id', params_json->>'wgs_source_commit',
         ((params_json ? 'pipeline_snapshot_id')::int
          + (params_json ? 'source_commit')::int
          + (params_json ? 'snapshot_manifest_sha256')::int)
    INTO release_id, source_commit, old_key_count
  FROM analysis_run
  WHERE analysis_id = 'T142-MIGRATION-SENTINEL';

  IF release_id <> 'wgs-4.1.1-1778fca'
     OR source_commit <> '1778fcabd99b5253aa90cd410112dc2f78e0c51a'
     OR old_key_count <> 0 THEN
    RAISE EXCEPTION 'analysis_run payload was not migrated correctly';
  END IF;

  SELECT count(*) INTO release_column_count
  FROM information_schema.columns
  WHERE table_name = 'observer_run_state'
    AND column_name = 'pipeline_release_id';
  SELECT count(*) INTO snapshot_column_count
  FROM information_schema.columns
  WHERE table_name = 'observer_run_state'
    AND column_name = 'pipeline_snapshot_id';
  IF release_column_count <> 1 OR snapshot_column_count <> 0 THEN
    RAISE EXCEPTION 'observer_run_state column rename is incomplete';
  END IF;

  SELECT count(*) INTO admin_count
  FROM user_account
  WHERE username = 't142-migration-admin' AND role = 'admin' AND enabled;
  IF admin_count <> 1 THEN
    RAISE EXCEPTION 'administrator sentinel was not preserved';
  END IF;
END $$;
SQL

echo "migration smoke passed: 20260826_0009 -> 20260827_0010"
