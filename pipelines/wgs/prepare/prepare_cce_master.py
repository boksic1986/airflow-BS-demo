#!/usr/bin/env python3
"""Generate an isolated CCE Master manifest and its control scripts."""

from __future__ import annotations

import argparse
import re
from pathlib import Path, PurePosixPath

import yaml


ROOT = Path(__file__).resolve().parents[1]
DNS_NAME = re.compile(r"^[a-z0-9](?:[-a-z0-9]*[a-z0-9])?$")
DEFAULT_MASTER_IMAGE = (
    "swr.cn-east-3.myhuaweicloud.com/biosanwgs/wgs-group-base@sha256:"
    "d86d280ef8cbe2ea97e8b94c28fdfb9c82d51b9096861b0fa2155707354d4e06"
)


def _write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)


def _workspace_path(value: str) -> str:
    path = PurePosixPath(value)
    workspace = PurePosixPath("/workspace")
    if not path.is_absolute() or ".." in path.parts or workspace not in path.parents:
        raise ValueError("run root must be a normalized path below /workspace")
    return str(path)


def generate(args: argparse.Namespace) -> None:
    if DNS_NAME.fullmatch(args.name) is None or len(args.name) > 63:
        raise ValueError("Master name must be a Kubernetes DNS label")
    run_root = _workspace_path(args.run_root)
    if args.output.exists():
        raise FileExistsError(f"output already exists: {args.output}")
    args.output.mkdir(parents=True)

    deployment = yaml.safe_load(
        (ROOT / "huawei-cloud/kubernetes/05-master-deployment.yaml").read_text(
            encoding="utf-8"
        )
    )

    deployment["metadata"].update(name=args.name, namespace=args.namespace)
    deployment["metadata"]["labels"]["app.kubernetes.io/name"] = args.name
    deployment["spec"]["selector"]["matchLabels"]["app.kubernetes.io/name"] = args.name
    pod = deployment["spec"]["template"]
    pod["metadata"]["labels"]["app.kubernetes.io/name"] = args.name
    pod["spec"]["serviceAccountName"] = args.master_service_account
    pod["spec"]["initContainers"][0]["image"] = args.master_image
    pod["spec"]["initContainers"][0]["args"] = [f"mkdir -p {run_root}"]
    pod["spec"]["containers"][0]["image"] = args.master_image
    pod["spec"]["containers"][0]["workingDir"] = run_root
    for volume in pod["spec"]["volumes"]:
        if volume["name"] == "sfs-workspace":
            volume["persistentVolumeClaim"]["claimName"] = args.workspace_pvc
        elif volume["name"] == "obs-data":
            volume["persistentVolumeClaim"]["claimName"] = args.obs_pvc

    (args.output / "master.yaml").write_text(
        yaml.safe_dump(deployment, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    common = (
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        f"kubectl_bin={args.kubectl_bin!s}\n"
        f"kubeconfig={args.kubeconfig!s}\n"
        f"namespace={args.namespace}\n"
        f"master={args.name}\n"
    )
    _write_executable(
        args.output / "Step1_create_master.sh",
        common
        + '"${kubectl_bin}" --kubeconfig "${kubeconfig}" -n "${namespace}" apply -f "$(dirname "$0")/master.yaml"\n'
        + '"${kubectl_bin}" --kubeconfig "${kubeconfig}" -n "${namespace}" scale deployment/"${master}" --replicas=1\n'
        + '"${kubectl_bin}" --kubeconfig "${kubeconfig}" -n "${namespace}" rollout status deployment/"${master}" --timeout=10m\n',
    )
    _write_executable(
        args.output / "Step2_master_status.sh",
        common
        + '"${kubectl_bin}" --kubeconfig "${kubeconfig}" -n "${namespace}" get deployment "${master}"\n'
        + '"${kubectl_bin}" --kubeconfig "${kubeconfig}" -n "${namespace}" get pods -l "app.kubernetes.io/name=${master}"\n',
    )
    _write_executable(
        args.output / "Step3_scale_down.sh",
        common
        + '"${kubectl_bin}" --kubeconfig "${kubeconfig}" -n "${namespace}" scale deployment/"${master}" --replicas=0\n',
    )


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("--name", required=True)
    value.add_argument("--namespace", default="snakemake-ns")
    value.add_argument("--workspace-pvc", required=True)
    value.add_argument("--obs-pvc", required=True)
    value.add_argument("--run-root", required=True)
    value.add_argument("--output", type=Path, required=True)
    value.add_argument("--master-image", default=DEFAULT_MASTER_IMAGE)
    value.add_argument("--master-service-account", default="wgs-snakemake-master")
    value.add_argument("--kubectl-bin", type=Path, default=Path("/home/chenjc/.local/bin/kubectl"))
    value.add_argument("--kubeconfig", type=Path, default=Path("/home/chenjc/.kube/bioinfo-cce.yaml"))
    return value


def main(argv=None) -> int:
    generate(parser().parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
