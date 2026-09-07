# Task design

## Change sequence

1. Add or update a registry definition and adapter contract tests.
2. Implement adapter behavior behind capabilities.
3. Update generic API and UI projections without pipeline-name branches.
4. Add workflow-specific DAG/runtime work only inside the adapter boundary.
5. Validate backend, DAG imports/contracts, frontend tests/build, Compose, and migrations remotely.
6. Update state and handoff documents before integration.

## Acceptance

- Existing deployed adapters remain functional.
- Disabled adapters are visible only when explicitly requested by capabilities and are never submit-enabled.
- Unknown and unsupported operations return stable errors.
- No real patient data, secrets, or unrestricted paths enter Git or API payloads.
