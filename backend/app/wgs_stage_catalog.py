from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


class StageContractError(ValueError):
    pass


@dataclass(frozen=True)
class StageDefinition:
    code: str
    label: str
    predecessor: str | None
    executor: str
    timeout_seconds: int
    poll_interval_seconds: int
    evidence_type: str
    predecessors_by_submission_mode: dict[str, str]


@dataclass(frozen=True)
class HeavyRuleGroup:
    group_id: str
    rules: tuple[str, ...]


@dataclass(frozen=True)
class HeavyIoContract:
    quota_name: str
    limit: int
    mode: str
    heartbeat_seconds: int
    reclaim_after_seconds: int
    groups: tuple[HeavyRuleGroup, ...]


@dataclass(frozen=True)
class WgsStageContract:
    version: int
    stages: dict[str, StageDefinition]
    heavy_io: HeavyIoContract


def load_wgs_stage_contract(path: Path | str) -> WgsStageContract:
    source = Path(path)
    if not source.is_file():
        raise StageContractError(f"WGS stage contract does not exist: {source}")
    try:
        payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise StageContractError(f"WGS stage contract is unreadable: {error}") from error
    if not isinstance(payload, dict) or payload.get("version") != 2:
        raise StageContractError("WGS stage contract version must be 2")
    defaults = payload.get("defaults")
    raw_stages = payload.get("stages")
    raw_heavy = payload.get("heavy_io")
    if not isinstance(defaults, dict) or not isinstance(raw_stages, dict) or not isinstance(raw_heavy, dict):
        raise StageContractError("WGS stage contract is missing defaults, stages, or heavy_io")
    stages: dict[str, StageDefinition] = {}
    for code, raw in raw_stages.items():
        if not isinstance(raw, dict):
            raise StageContractError(f"stage {code} must be a mapping")
        predecessor = raw.get("predecessor")
        stages[str(code)] = StageDefinition(
            code=str(code),
            label=_required_text(raw, "label", f"stage {code}"),
            predecessor=str(predecessor) if predecessor is not None else None,
            executor=str(raw.get("executor") or defaults.get("executor") or ""),
            timeout_seconds=_positive_int(raw.get("timeout_seconds", defaults.get("timeout_seconds")), f"stage {code} timeout"),
            poll_interval_seconds=_positive_int(raw.get("poll_interval_seconds", defaults.get("poll_interval_seconds")), f"stage {code} poll interval"),
            evidence_type=str(raw.get("evidence_type") or defaults.get("evidence_type") or ""),
            predecessors_by_submission_mode=_predecessors_by_mode(
                raw.get("predecessors_by_submission_mode"), f"stage {code}"
            ),
        )
    for stage in stages.values():
        if stage.predecessor and stage.predecessor not in stages:
            raise StageContractError(f"stage {stage.code} references unknown predecessor {stage.predecessor}")
    groups = tuple(
        HeavyRuleGroup(_required_text(item, "id", "heavy group"), tuple(str(rule) for rule in item.get("rules", [])))
        for item in raw_heavy.get("groups", [])
        if isinstance(item, dict)
    )
    heavy = HeavyIoContract(
        quota_name=_required_text(raw_heavy, "quota_name", "heavy_io"),
        limit=_positive_int(raw_heavy.get("limit"), "heavy_io limit"),
        mode=str(raw_heavy.get("mode") or "monitor-only"),
        heartbeat_seconds=_positive_int(raw_heavy.get("heartbeat_seconds"), "heavy_io heartbeat"),
        reclaim_after_seconds=_positive_int(raw_heavy.get("reclaim_after_seconds"), "heavy_io reclaim timeout"),
        groups=groups,
    )
    if heavy.mode not in {"monitor-only", "enforce"}:
        raise StageContractError("heavy_io mode must be monitor-only or enforce")
    return WgsStageContract(version=2, stages=stages, heavy_io=heavy)


def _required_text(value: dict, key: str, owner: str) -> str:
    text = str(value.get(key) or "").strip()
    if not text:
        raise StageContractError(f"{owner} requires {key}")
    return text


def _positive_int(value, label: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise StageContractError(f"{label} must be an integer") from error
    if parsed < 1:
        raise StageContractError(f"{label} must be positive")
    return parsed


def _predecessors_by_mode(value, owner: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise StageContractError(f"{owner} predecessors_by_submission_mode must be a mapping")
    result: dict[str, str] = {}
    for mode, predecessor in value.items():
        key = str(mode).strip()
        stage = str(predecessor).strip()
        if not key or not stage:
            raise StageContractError(f"{owner} has an invalid submission-mode predecessor")
        result[key] = stage
    return result
