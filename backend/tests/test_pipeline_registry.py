import pytest

from app.pipeline_registry import (
    PipelineAdapter,
    PipelineCapabilityUnavailable,
    PipelineNotAvailable,
    PipelineNotRegistered,
    PipelineRegistryError,
    build_pipeline_registry,
)


def registry_payload():
    return {
        "version": 1,
        "pipelines": {
            "wgs": {
                "display_name": "Whole genome sequencing",
                "dag_id": "bio_wgs",
                "version": "4.1.1",
                "adapter": "wgs",
                "enabled": True,
                "submit_enabled": True,
                "capabilities": ["intake", "submit", "rules", "qc", "artifacts"],
                "execution_targets": ["cce", "local", "sge"],
            },
            "wes": {
                "display_name": "Whole exome sequencing",
                "dag_id": "bio_wes",
                "adapter": "synthetic",
                "enabled": False,
                "submit_enabled": False,
                "capabilities": ["submit", "rules", "qc"],
                "execution_targets": ["local"],
            },
            "gatk": {
                "display_name": "GATK workflow",
                "dag_id": "bio_gatk",
                "adapter": "synthetic",
                "enabled": False,
                "submit_enabled": False,
                "capabilities": ["submit", "artifacts"],
                "execution_targets": ["cce", "local"],
            },
        },
    }


def build_registry():
    return build_pipeline_registry(
        registry_payload(),
        adapters={
            "wgs": PipelineAdapter(adapter_id="wgs"),
            "synthetic": PipelineAdapter(adapter_id="synthetic"),
        },
    )


def test_registry_projects_deployed_pipeline_capabilities_without_core_name_checks():
    registry = build_registry()

    definition = registry.require("wgs", capability="submit")

    assert definition.pipeline_id == "wgs"
    assert definition.adapter.adapter_id == "wgs"
    assert definition.execution_targets == ("cce", "local", "sge")
    assert registry.deployed_pipeline_ids == ("wgs",)
    assert registry.public_payload()["pipelines"][0] == {
        "id": "wgs",
        "display_name": "Whole genome sequencing",
        "dag_id": "bio_wgs",
        "version": "4.1.1",
        "enabled": True,
        "submit_enabled": True,
        "capabilities": ["artifacts", "intake", "qc", "rules", "submit"],
        "execution_targets": ["cce", "local", "sge"],
    }


def test_wes_and_gatk_use_the_same_registry_contract_without_becoming_deployed():
    registry = build_registry()

    assert registry.get("wes").adapter.adapter_id == "synthetic"
    assert registry.get("gatk").adapter.adapter_id == "synthetic"
    assert registry.get("wes").enabled is False
    assert registry.get("gatk").enabled is False
    assert registry.deployed_pipeline_ids == ("wgs",)


def test_registry_distinguishes_unregistered_disabled_and_unsupported_capability():
    registry = build_registry()

    with pytest.raises(PipelineNotRegistered) as unregistered:
        registry.require("unknown")
    assert unregistered.value.code == "PIPELINE_NOT_REGISTERED"

    with pytest.raises(PipelineNotAvailable) as disabled:
        registry.require("wes")
    assert disabled.value.code == "PIPELINE_NOT_AVAILABLE"

    with pytest.raises(PipelineCapabilityUnavailable) as unsupported:
        registry.require("wgs", capability="resume")
    assert unsupported.value.code == "PIPELINE_CAPABILITY_UNAVAILABLE"


def test_registry_rejects_deployment_values_not_declared_by_configuration():
    with pytest.raises(PipelineNotRegistered, match="missing"):
        build_pipeline_registry(
            registry_payload(),
            adapters={
                "wgs": PipelineAdapter(adapter_id="wgs"),
                "synthetic": PipelineAdapter(adapter_id="synthetic"),
            },
            deployed_pipeline_ids=("wgs", "missing"),
        )


@pytest.mark.parametrize(
    "payload, message",
    [
        (None, "mapping"),
        ([], "mapping"),
        ({"version": 1, "pipelines": []}, "pipelines"),
        (
            {
                "version": 1,
                "pipelines": {
                    "wgs": {
                        "display_name": "WGS",
                        "dag_id": "bio_wgs",
                        "adapter": "wgs",
                        "enabled": "false",
                        "submit_enabled": False,
                        "capabilities": [],
                        "execution_targets": [],
                    }
                },
            },
            "enabled",
        ),
        (
            {
                "version": 1,
                "pipelines": {
                    "wgs": {
                        "display_name": "WGS",
                        "dag_id": "bio_wgs",
                        "adapter": "wgs",
                        "enabled": True,
                        "submit_enabled": False,
                        "capabilities": "submit",
                        "execution_targets": [],
                    }
                },
            },
            "capabilities",
        ),
        (
            {
                "version": 1,
                "pipelines": {
                    "wgs": {
                        "display_name": "WGS",
                        "dag_id": "bio_wgs",
                        "adapter": "wgs",
                        "enabled": True,
                        "submit_enabled": False,
                        "capabilities": [],
                        "execution_targets": "cce",
                    }
                },
            },
            "execution_targets",
        ),
    ],
)
def test_registry_rejects_malformed_configuration(payload, message):
    with pytest.raises(PipelineRegistryError, match=message):
        build_pipeline_registry(
            payload,
            adapters={"wgs": PipelineAdapter(adapter_id="wgs")},
        )


def test_registry_rejects_explicit_deployment_of_disabled_pipeline():
    with pytest.raises(PipelineNotAvailable, match="disabled"):
        build_pipeline_registry(
            registry_payload(),
            adapters={
                "wgs": PipelineAdapter(adapter_id="wgs"),
                "synthetic": PipelineAdapter(adapter_id="synthetic"),
            },
            deployed_pipeline_ids=("wes",),
        )
