import importlib.util
from pathlib import Path
import threading
from types import SimpleNamespace


ROOT = Path(__file__).parents[1]


def load_probe():
    spec = importlib.util.spec_from_file_location(
        "wgs_heavy_slot_probe_test", ROOT / "wgs_heavy_slot_probe.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeQuota:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.lock = threading.Lock()
        self.claims = []
        self.released = []

    def acquire(self, *, run_label: str, job_name: str):
        with self.lock:
            if len(self.claims) >= self.limit:
                raise RuntimeError("all slots occupied")
            claim = SimpleNamespace(
                lease_name=f"wgs-heavy-io-{len(self.claims):02d}",
                holder=f"{run_label}:{job_name}",
            )
            self.claims.append(claim)
            return claim

    def release(self, claim) -> bool:
        self.released.append(claim.holder)
        return True


def test_probe_accepts_25_and_leaves_the_26th_waiting() -> None:
    probe = load_probe()
    quota = FakeQuota(limit=25)

    result = probe.contend(quota=quota, contenders=26, run_label="t206-probe")

    assert result["acquired"] == 25
    assert result["waiting"] == 1
    assert result["unique_slots"] == 25
    assert result["released"] == 25
    assert len(set(quota.released)) == 25


def test_probe_source_never_creates_a_kubernetes_job() -> None:
    source = (ROOT / "wgs_heavy_slot_probe.py").read_text(encoding="utf-8")

    assert "create_namespaced_job" not in source
    assert "delete_namespaced_job" not in source
