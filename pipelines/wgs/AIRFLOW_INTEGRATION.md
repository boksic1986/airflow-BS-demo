# Airflow integration copy

This directory is the Airflow-owned development copy of the WGS workflow.
Its upstream source is `/mnt/biodevrwbi/33.chenjiucheng/project/wgs`; Airflow
integration work must not modify that upstream working tree.

`SOURCE_PROVENANCE.json` records the source commit and the two uncommitted CCE
profile files included in this snapshot. Consequently this copy is a
development snapshot, not an immutable production pipeline release. Keep the
Airflow execution gate disabled until a later accepted snapshot is promoted.

Logger, evidence, runner-adapter, and Airflow-specific configuration changes
belong in this directory. Business Rule changes should be made upstream first
and imported again as a new, separately identified snapshot.
