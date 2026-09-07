# Testing and acceptance

## Required suites

- Backend: full pytest plus registry/adapter contract tests.
- DAG: import and WGS contract regressions.
- Frontend: Vitest, TypeScript, and production build.
- Compose: configuration rendering only.
- Database: migration upgrade to one Alembic head in isolation.
- Hygiene: active code and manifests contain no retired runtime assets.

## Registry cases

- deployed WGS adapter works through generic endpoints;
- synthetic WES and GATK definitions can register without shared-code edits;
- disabled, unregistered, and unsupported requests return stable codes;
- database audit identity is not rewritten by display aliases.

Tests use existing approved remote environments. They must not start production work, pull public images, create Docker networks, or publish new ports.
