# Frontend specification

## Registry-driven shell

The navigation, pipeline filters, workflow catalog, and deployment availability consume `/api/platform/capabilities`. The shell must tolerate a rolling upgrade response that contains only `deployed_pipelines` and normalize it into minimal registry definitions.

Current production displays WGS because it is the only deployed registry entry. Future adapters appear without modifying shared navigation or generic API clients.

Submit navigation and dashboard calls-to-action are visible only when a deployed, enabled registry entry declares both `submit_enabled` and the `submit` capability and also has a registered frontend submission adapter. The current staged WGS form is an explicitly namespaced adapter UI; a future submit-capable pipeline without its own UI cannot be routed into the WGS form, and the route fails closed instead of issuing WGS API calls.

## Run views

- Dashboard and Runs display shared run status and adapter-projected stages.
- Run Detail renders shared evidence, progress, samples, QC, logs, artifacts, transfers, and lifecycle sections when capabilities provide them.
- QC and workflow stages are rendered from backend projections; the browser does not parse workflow files.
- Disabled capabilities show an explicit unavailable state rather than a mock action.

## Branding

The product label is `NGS Huawei Cloud` with the subtitle `Online analysis platform`. WGS names remain only where they identify the currently deployed workflow or extension.
