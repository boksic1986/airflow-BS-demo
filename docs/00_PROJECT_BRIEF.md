# Project brief

## Purpose

Provide one operator-facing NGS analysis platform for Huawei Cloud CCE and local compute. The platform must support new workflows without adding pipeline-name conditionals to shared API, navigation, status, or scheduling code.

## Current scope

- WGS is the only deployed and submit-enabled adapter.
- CCE is the default automated execution target.
- Local node capability is adapter-declared and manually selected when enabled.
- SGE remains an extension point and is disabled until validated.
- WES and GATK are compatibility targets for the adapter contract, not mock runnable workflows.

## Non-goals

- The control plane does not replace workflow-owned bioinformatics logic.
- The repository does not ship legacy PGTA/NIPT demo runtimes.
- The platform does not expose raw clinical identifiers or unrestricted filesystem paths.
