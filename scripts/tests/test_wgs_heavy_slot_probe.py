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
                raise RuntimeError(
                    f"all {self.limit} WGS high-I/O work-pod slots are occupied"
                )
            claim = SimpleNamespace(
                lease_name=f"wgs-heavy-io-{len(self.claims):02d}",
                holder=f"{run_label}:{job_name}",
            )
            self.claims.append(claim)
            return claim

    def release(self, claim) -> bool:
        self.released.append(claim.holder)
        return True


class FailingQuota(FakeQuota):
    def acquire(self, *, run_label: str, job_name: str):
        if job_name.endswith("25"):
            raise RuntimeError("Kubernetes API unavailable")
        return super().acquire(run_label=run_label, job_name=job_name)


class ReleaseFailingQuota(FakeQuota):
    def release(self, claim) -> bool:
        self.released.append(claim.holder)
        if len(self.released) == 1:
            raise RuntimeError("synthetic release failure")
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


def test_probe_does_not_treat_api_errors_as_waiting_and_releases_claims() -> None:
    probe = load_probe()
    quota = FailingQuota(limit=25)

    try:
        probe.contend(quota=quota, contenders=26, run_label="t206-probe")
    except RuntimeError as error:
        assert "Kubernetes API unavailable" in str(error)
    else:
        raise AssertionError("unexpected API failure must fail the probe")

    assert len(quota.released) == 25


def test_probe_attempts_every_release_when_one_release_fails() -> None:
    probe = load_probe()
    quota = ReleaseFailingQuota(limit=25)

    try:
        probe.contend(quota=quota, contenders=26, run_label="t206-probe")
    except RuntimeError as error:
        assert "synthetic release failure" in str(error)
    else:
        raise AssertionError("release failure must fail the probe")

    assert len(quota.released) == 25


def test_heavy_slot_rbac_uses_precreated_named_leases() -> None:
    source = (ROOT.parent / "config" / "wgs-heavy-slot-rbac.yaml").read_text(
        encoding="utf-8"
    )

    assert source.count("kind: Lease\n") == 25
    assert 'verbs: ["get", "update"]' in source
    assert 'verbs: ["list", "create"]' not in source
    assert '"patch"' not in source
