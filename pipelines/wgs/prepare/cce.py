"""CCE-only batch configuration and operator Step script generation."""

from __future__ import annotations

import copy
from pathlib import Path, PurePosixPath
import re
import shlex
from typing import Any, Dict, Mapping

import yaml


SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
PROTECTED_RUNTIME_KEYS = {
    "images",
    "image_digests",
    "workloads",
    "containers",
    "container_tools",
    "container_resources",
    "runtime",
    "runtime_binds",
    "apptainer",
    "shell",
    "sentieon_license_secret",
}
METADATA_KEYS = {
    "sample",
    "pedigree",
    "trio",
    "trioPair",
    "sample2pedigree",
    "BKWsampleList",
    "BKWpedigree",
    "BKWprobandonly",
    "mtPedigreeList",
    "CS",
    "phenotype",
    "VariantTypeSet",
    "use_reference",
    "extension",
}


def _quote(value: object) -> str:
    return shlex.quote(str(value))


def _replace(value: Any, replacements: Mapping[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace(child, replacements) for key, child in value.items()}
    if isinstance(value, list):
        return [_replace(child, replacements) for child in value]
    if isinstance(value, str):
        for old, new in replacements.items():
            value = value.replace(old, new)
    return value


def _workspace_path(value: str, label: str) -> str:
    path = PurePosixPath(value)
    workspace = PurePosixPath("/workspace")
    if not path.is_absolute() or ".." in path.parts or workspace not in path.parents:
        raise ValueError(f"{label} must be a normalized path below /workspace")
    return str(path)


def _obs_path(value: str, label: str) -> str:
    path = PurePosixPath(value)
    obs_root = PurePosixPath("/obs-data")
    if not path.is_absolute() or ".." in path.parts or obs_root not in path.parents:
        raise ValueError(f"{label} must be a normalized path below /obs-data")
    return str(path)


def build_cce_batch_config(
    source: Mapping[str, Any],
    template_path: Path | str,
    *,
    batch: str,
    run_id: str,
    pipeline_release: str,
    owner: str,
    fastq_dir: str,
    workflow_target: str = "cloud_wgs_all",
) -> Dict[str, Any]:
    """Build a small batch contract without OCI, SIF, Group, or Secret fields."""

    for label, value in (
        ("batch", batch),
        ("run-id", run_id),
        ("pipeline-release", pipeline_release),
        ("owner", owner),
    ):
        if SAFE_COMPONENT.fullmatch(value) is None:
            raise ValueError(f"{label} must be a safe path component")
    template = yaml.safe_load(Path(template_path).read_text(encoding="utf-8")) or {}
    if not isinstance(template, dict):
        raise ValueError("CCE template must be a YAML mapping")
    result = copy.deepcopy(template)
    for key in PROTECTED_RUNTIME_KEYS:
        result.pop(key, None)
    for key in METADATA_KEYS:
        if key in source:
            result[key] = copy.deepcopy(source[key])

    if workflow_target not in {"cloud_wgs_all", "cloud_sentieon_stage_all"}:
        raise ValueError("unsupported CCE workflow target")
    run_root = _workspace_path(f"/workspace/wgs/runs/{batch}/{run_id}", "CCE run root")
    pipeline_root = _workspace_path(
        f"/workspace/wgs/pipelines/3.9.3/{pipeline_release}", "CCE pipeline release"
    )
    result = _replace(
        result,
        {
            "/workspace/wgs/runs/BATCH/RUN_ID": run_root,
            "/workspace/wgs/pipelines/3.9.3/PIPELINE_RELEASE": pipeline_root,
            "PIPELINE_RELEASE": pipeline_release,
            "BATCH": batch,
            "RUN_ID": run_id,
        },
    )
    result["version"] = "V3.9.3"
    result["batch"] = batch
    result["workflow"] = {
        "schema_version": 3,
        "pipeline_release": pipeline_release,
        "snakefile": "WGS_cloud.smk",
        "target": workflow_target,
    }
    result["execution"] = {"executor": "cce"}
    result["run"] = {
        "owner": owner,
        "batch": batch,
        "run_id": run_id,
        "root": run_root,
    }
    result["workDir"] = f"{run_root}/work"
    result["fastqDir"] = _obs_path(fastq_dir, "CCE FASTQ directory")
    result["fastqPath"] = result["fastqDir"]
    result["sample_info"] = f"{run_root}/config/sampleinfo.tsv"
    result["new_sample_info"] = result["sample_info"]
    result["qc_cfg"] = f"{pipeline_root}/cfg/qc_config.json"
    cloud = result.setdefault("cloud", {})
    cloud.update(
        run_root=run_root,
        evidence_root=f"{run_root}/evidence",
        external_side_effects=False,
        fastq_md5_manifest=f"{run_root}/config/FASTQ.MD5SUMS",
    )
    cloud.pop("pipeline_release", None)
    cloud.pop("code_root", None)
    cloud.pop("sfs_identity", None)
    result["export"] = {
        "transport": "sfs_turbo_linkage",
        "linkage_root": _workspace_path(
            f"/workspace/wgs-obs-sync/wgs-results/{batch}/{run_id}",
            "CCE SFS Turbo linkage root",
        ),
        "include_final_results": True,
        "include_cram_crai": True,
    }
    result.pop("scheduler", None)
    for key in PROTECTED_RUNTIME_KEYS:
        if key in result:
            raise ValueError(f"generated CCE batch contains protected key: {key}")
    return result


def write_cce_steps(
    bundle_dir: Path | str,
    *,
    run_root: str,
    run_id: str,
    master: str,
    namespace: str,
    kubectl_bin: str,
    kubeconfig: str,
    repository_root: str,
    evidence_root: str,
    pipeline_dir: str,
    workflow_target: str,
) -> None:
    bundle = Path(bundle_dir)
    selector = f"app.kubernetes.io/name={master}"
    evidence = str(PurePosixPath(evidence_root) / run_id)
    scripts = {
        "Step1_upload_config.sh": f'''#!/usr/bin/env bash
set -euo pipefail
bundle_dir="$(cd "$(dirname "$0")" && pwd)"
kubectl_bin={_quote(kubectl_bin)}
kubeconfig={_quote(kubeconfig)}
namespace={_quote(namespace)}
master={_quote(master)}
run_root={_quote(run_root)}
"${{kubectl_bin}}" --kubeconfig "${{kubeconfig}}" -n "${{namespace}}" exec deployment/"${{master}}" -- mkdir -p "${{run_root}}/config"
for name in config.yaml sampleinfo.tsv FASTQ.MD5SUMS; do
  "${{kubectl_bin}}" --kubeconfig "${{kubeconfig}}" -n "${{namespace}}" exec -i deployment/"${{master}}" -- \
    sh -c 'cat > "$1/config/$2.partial" && sync "$1/config/$2.partial" && mv -f "$1/config/$2.partial" "$1/config/$2"' sh "${{run_root}}" "${{name}}" \
    < "${{bundle_dir}}/${{name}}"
done
''',
        "Step2_run.sh": f'''#!/usr/bin/env bash
set -euo pipefail
evidence={_quote(evidence)}
mkdir -p "${{evidence}}"
nohup env KUBECTL_BIN={_quote(kubectl_bin)} KUBECONFIG={_quote(kubeconfig)} NAMESPACE={_quote(namespace)} MASTER_SELECTOR={_quote(selector)} \
  {_quote(repository_root + '/huawei-cloud/scripts/run_cce_workflow.sh')} {_quote(run_root)} "${{evidence}}" {_quote(run_id)} \
  > "${{evidence}}/launcher.log" 2>&1 < /dev/null &
printf '%s\n' "$!" > "${{evidence}}/launcher.pid"
printf 'started pid=%s log=%s\n' "$!" "${{evidence}}/launcher.log"
''',
        "Step3_status.sh": f'''#!/usr/bin/env bash
set -euo pipefail
evidence={_quote(evidence)}
test -f "${{evidence}}/launcher.log" && tail -n 100 "${{evidence}}/launcher.log" || true
if [[ -f "${{evidence}}/discovery/job_names.txt" ]]; then
  while IFS= read -r job; do
    [[ -n "${{job}}" ]] || continue
    {_quote(kubectl_bin)} --kubeconfig {_quote(kubeconfig)} -n {_quote(namespace)} get job "${{job}}"
    {_quote(kubectl_bin)} --kubeconfig {_quote(kubeconfig)} -n {_quote(namespace)} get pods -l "job-name=${{job}}"
  done < "${{evidence}}/discovery/job_names.txt"
fi
''',
        "Step4_finish.sh": f'''#!/usr/bin/env bash
set -euo pipefail
evidence={_quote(evidence)}
test "$(cat "${{evidence}}/analysis.exit_code")" -eq 0
{_quote(kubectl_bin)} --kubeconfig {_quote(kubeconfig)} -n {_quote(namespace)} exec deployment/{_quote(master)} -- \
  snakemake --snakefile {_quote(pipeline_dir + '/WGS_cloud.smk')} --configfile {_quote(run_root + '/config/config.yaml')} \
  --directory {_quote(run_root + '/work')} --profile {_quote(pipeline_dir + '/cfg/profiles/cce')} --dry-run --nolock -- {_quote(workflow_target)} \
  | tee "${{evidence}}/final-dryrun.log"
grep -F 'Nothing to be done' "${{evidence}}/final-dryrun.log"
{_quote(kubectl_bin)} --kubeconfig {_quote(kubeconfig)} -n {_quote(namespace)} scale deployment/{_quote(master)} --replicas=0
''',
    }
    for name, source in scripts.items():
        path = bundle / name
        path.write_text(source, encoding="utf-8")
        path.chmod(0o755)
