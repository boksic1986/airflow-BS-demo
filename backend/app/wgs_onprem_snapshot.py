"""Private native registration evidence; read inputs, never run or rewrite WGS."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re

import yaml


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


_SECRET = re.compile(r"password|passwd|token|secret|access[_-]?key|private[_-]?key", re.I)


def _has_credentials(value):
    if isinstance(value, dict):
        return any((_SECRET.search(str(key)) and child not in (None, "", False))
                   or _has_credentials(child) for key, child in value.items())
    return isinstance(value, list) and any(_has_credentials(child) for child in value)


def capture_inputs(project: Path, mode: str, argv: list[str]):
    for arg in argv:
        if (len(arg) > 4096 or "\x00" in arg or "\n" in arg
                or _SECRET.search(arg) or arg.split("=", 1)[0] == "--worker"
                or re.search(r"https?://[^/\s]*@", arg)):
            raise ValueError("Native arguments contain credentials or internal worker options")
    sources = {"config.yaml": project / "config.yaml", "Step1_run.sh": project / "Step1_run.sh"}
    # Avoid duplicate reads when the two WGS fields refer to the same file.
    captured = {}

    def read(path):
        resolved = path.resolve()
        if (path.is_symlink() or not path.is_file() or project.resolve() not in resolved.parents):
            raise ValueError("Native input is unavailable or outside its project")
        with path.open("rb") as handle:
            data = handle.read(16 * 1024 * 1024 + 1)
        if len(data) > 16 * 1024 * 1024:
            raise ValueError("Native input exceeds small-file snapshot limit")
        return resolved, data

    def capture(path):
        resolved = path.resolve()
        if resolved not in captured:
            _, captured[resolved] = read(path)
        else:
            # A second reference must still be a valid project file, not a symlink alias.
            if path.is_symlink() or project.resolve() not in resolved.parents:
                raise ValueError("Native input reference is invalid")
        return captured[resolved]

    config_bytes = capture(sources["config.yaml"])
    try:
        config = yaml.safe_load(config_bytes)
    except yaml.YAMLError as exc:
        raise ValueError("Native config is invalid") from exc
    if (not isinstance(config, dict) or not isinstance(config.get("execution"), dict)
            or config["execution"].get("executor") != mode or _has_credentials(config)):
        raise ValueError("Native config is invalid, contains credentials or differs from execution mode")
    contents = {"config.yaml": config_bytes, "Step1_run.sh": capture(sources["Step1_run.sh"])}
    # Fixed native profile contract, not a recursive workflow dependency snapshot.
    # runtime.yaml is prepare provenance; Step1 consumes config.yaml directly.
    profile = project / "pipeline" / "cfg" / "profiles" / mode
    if (not profile.is_dir() or profile.is_symlink()
            or {path.name for path in profile.iterdir()} != {"config.yaml", "runtime.yaml"}):
        raise ValueError("Native profile differs from the supported two-file contract")
    for filename in ("config.yaml", "runtime.yaml"):
        name = f"profile.{filename}"
        sources[name] = profile / filename
        contents[name] = capture(sources[name])
        try:
            profile_config = yaml.safe_load(contents[name])
        except yaml.YAMLError as exc:
            raise ValueError("Native profile is invalid") from exc
        if not isinstance(profile_config, dict) or _has_credentials(profile_config):
            raise ValueError("Native profile is invalid or contains credentials")
    for field in ("sample_info", "new_sample_info"):
        reference = config.get(field)
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError("Native config must reference its current sample information")
        source = Path(reference)
        sources[f"{field}.tsv"] = source if source.is_absolute() else project / source
        data = capture(sources[f"{field}.tsv"])
        contents[f"{field}.tsv"] = data
    # WGS rules expand config.sample (data IDs), not all metadata rows. The second
    # table is delivery input only and cannot expand or replace configured scope.
    configured = config.get("sample")
    if (not isinstance(configured, list) or not configured
            or any(not isinstance(item, str) or not item or item.strip() != item for item in configured)):
        raise ValueError("Native config.sample must contain data identifiers")
    configured = list(dict.fromkeys(configured))
    table = csv.DictReader(io.StringIO(contents["sample_info.tsv"].decode("utf-8-sig")), delimiter="\t")
    if not {"数据编号", "样本编号", "家系编号"}.issubset(table.fieldnames or []):
        raise ValueError("Native sample input lacks data/sample/family identity columns")
    identities = {}
    for row in table:
        data_id = str(row.get("数据编号") or "").strip()
        if data_id not in configured:
            continue
        sample_id = str(row.get("样本编号") or "").strip()
        if data_id in identities or not sample_id:
            raise ValueError("Configured data ID has ambiguous or missing metadata")
        identities[data_id] = {"data_id": data_id, "sample_id": sample_id,
                               "family_id": str(row.get("家系编号") or "").strip() or None}
    if set(identities) != set(configured):
        raise ValueError("Configured data IDs differ from current sample metadata")
    for source in sources.values():
        resolved, current = read(source)
        if current != captured[resolved]:
            raise ValueError("Native inputs changed during capture; retry registration before launch")
    refs = {name: {"source": str(sources[name]), "sha256": digest(data)} for name, data in contents.items()}
    return contents, refs, [identities[data_id] for data_id in configured]


def persist_snapshot(settings, project: Path, execution_id: str, contents: dict, manifest: dict):
    configured = getattr(settings, "wgs_onprem_snapshot_root", "")
    base = Path(configured)
    if (not configured or not base.is_absolute() or base.is_symlink() or not base.is_dir()
            or base.resolve() == project.resolve() or project.resolve() in base.resolve().parents
            or base.stat().st_mode & 0o077):
        raise ValueError("Native snapshot root must be an existing private directory outside the project")
    directory = base / execution_id
    directory.mkdir(mode=0o700, exist_ok=False)
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8")
    # Manifest last marks complete evidence. Partial/unreferenced evidence is retained,
    # never overwritten or used to infer that a controller was started.
    for name, data in {**contents, "manifest.json": manifest_bytes}.items():
        descriptor = os.open(directory / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    for path in (directory, base):
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    return directory, digest(manifest_bytes)
