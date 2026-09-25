"""Controlled on-disk contract checks; no live Master or Kubernetes calls."""
import importlib
import json
import os

import pytest

from test_cce_recovery_evidence import evidence


@pytest.fixture
def saved(tmp_path, evidence):
    root = tmp_path / "controlled"
    root.mkdir()
    scope = root / "execution-one"
    scope.mkdir()
    for name, value in zip(("executor-failure.json", "master-terminal.json"), evidence[1:]):
        (scope / name).write_text(json.dumps(value), encoding="utf-8")
    return root, scope, evidence[0]


def read(saved, relative="execution-one"):
    root, _, context = saved
    module = importlib.import_module("app.cce_recovery_reader")
    return module.read_recovery_evidence(root=root, relative_dir=relative,
                                        expected_context=context)


def test_reads_fixed_bound_pair_without_modifying_files(saved):
    _, scope, _ = saved
    before = {p.name: p.read_bytes() for p in scope.iterdir()}
    result = read(saved)
    assert result["source_master_uid"] == "master-one"
    assert result["evidence_key"] == "execution-one/master-terminal.json"
    assert {p.name: p.read_bytes() for p in scope.iterdir()} == before


@pytest.mark.parametrize("relative", ["../execution-one", "/execution-one", "execution-one/../execution-one"])
def test_path_traversal_never_reads_outside_bound_directory(saved, relative):
    with pytest.raises(ValueError):
        read(saved, relative)


@pytest.mark.parametrize("target", ["file", "directory", "root"])
def test_symlink_at_any_scope_layer_is_rejected(saved, tmp_path, target):
    root, scope, context = saved
    if target == "file":
        terminal = scope / "master-terminal.json"
        actual = scope / "retained.json"
        terminal.rename(actual)
        terminal.symlink_to(actual)
    elif target == "directory":
        (root / "alias").symlink_to(scope, target_is_directory=True)
        with pytest.raises(ValueError):
            read(saved, "alias")
        return
    else:
        alias = tmp_path / "alias"
        alias.symlink_to(root, target_is_directory=True)
        saved = alias, scope, context
    with pytest.raises(ValueError):
        read(saved)


@pytest.mark.parametrize("case", ["duplicate_keys", "missing", "fifo", "oversized", "hardlink"])
def test_invalid_or_nonregular_evidence_fails_closed(saved, case):
    _, scope, _ = saved
    terminal = scope / "master-terminal.json"
    if case == "duplicate_keys":
        original = terminal.read_text()
        terminal.write_text('{"complete":false,' + original[1:])
    elif case == "oversized":
        terminal.write_bytes(b" " * (1024 * 1024 + 1))
    elif case == "hardlink":
        os.link(terminal, scope / "extra-link")
    else:
        terminal.unlink()
        if case == "fifo":
            os.mkfifo(terminal)
    with pytest.raises(ValueError):
        read(saved)


def test_other_execution_cannot_be_substituted(saved):
    _, _, context = saved
    context["execution_id"] = "other-execution"
    with pytest.raises(ValueError):
        read(saved)
