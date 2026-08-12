import os

shell.executable("/bin/bash")
WDIR = os.getcwd()
workdir: WDIR

# Step1 commands are resolved from the active module SIF.  This prevents an
# unapproved host software path from silently bypassing the container contract.
step1_tools = config.get("container_tools", {})
container_software = config.get("container_software", {})
expected_container_modules = {
    "pre", "SNV", "SV", "MT", "RE", "ROH",
    "CNV", "MEI", "SMA", "CS", "QC",
}
if expected_container_modules != set(step1_tools):
    raise ValueError(
        "container_tools must map exactly these 11 modules: "
        + ",".join(sorted(expected_container_modules))
    )
for module_name, module_tools in step1_tools.items():
    if not isinstance(module_tools, dict) or not module_tools:
        raise ValueError("container tool module must be a non-empty mapping: " + module_name)
    for tool_name, command in module_tools.items():
        if (
            not isinstance(command, str)
            or command != command.strip()
            or not command.startswith("/")
            or os.path.normpath(command) != command
        ):
            raise ValueError(
                "container executable must use one immutable absolute path: "
                + module_name
                + "."
                + str(tool_name)
                + "="
                + repr(command)
            )

if step1_tools:
    execution = config.get("execution", {})
    if execution.get("mode") != "direct_apptainer":
        raise ValueError("execution.mode must be direct_apptainer")
    runtime_root = execution.get("runtime_root", "")
    if not isinstance(runtime_root, str) or not runtime_root.startswith("/"):
        raise ValueError("execution.runtime_root must be an absolute path")

    configured_containers = config.get("containers", {})
    if set(configured_containers) != expected_container_modules:
        raise ValueError(
            "containers must map exactly these 11 modules: "
            + ",".join(sorted(expected_container_modules))
        )
    sif_prefix = runtime_root.rstrip("/") + "/sif/"
    for module_name, image_path in configured_containers.items():
        if not isinstance(image_path, str) or not image_path.startswith(sif_prefix):
            raise ValueError(
                "container image must be under execution.runtime_root/sif: "
                + str(module_name)
                + "="
                + repr(image_path)
            )
        if not image_path.endswith(".sif") or "latest" in image_path:
            raise ValueError(
                "container image must be an immutable SIF path: "
                + str(module_name)
                + "="
                + repr(image_path)
            )

module pre_process:
    snakefile: "rule/pre_sampleInfo_solo.smk"
    config: config

module SNV:
    snakefile: "rule/WGS_SNV.smk"
    config: config

module SV:
    snakefile: "rule/WGS_SV.smk"
    config: config

module MT:
    snakefile: "rule/WGS_MT.smk"
    config: config

module RE:
    snakefile: "rule/WGS_RE.smk"
    config: config

module ROH:
    snakefile: "rule/ROH.smk"
    config: config

module CNV:
    snakefile: "rule/CNV.smk"
    config: config

module MEI:
    snakefile: "rule/MEI.smk"
    config: config

module SMA:
    snakefile: "rule/SMA.smk"
    config: config

module CS:
    snakefile: "rule/WGS_CS.smk"
    config: config

module QC:
    snakefile: "rule/QC.smk"
    config: config


use rule * from pre_process as pre_process_*
use rule * from SNV as SNV_*
use rule * from SV as SV_*
use rule * from MT as MT_*
use rule * from RE as RE_*
use rule * from ROH as ROH_*
use rule * from CNV as CNV_*
use rule * from MEI as MEI_*
use rule * from SMA as SMA_*
use rule * from CS as CS_*
use rule * from QC as QC_*


rule all:
    input:
        rules.pre_process_Preall.input,
        rules.SNV_SNVall.input,
        rules.SV_SVall.input,
        rules.MT_MTall.input,
        rules.RE_REall.input,
        rules.ROH_ROHall.input,
        rules.CNV_CNVall.input,
        rules.MEI_MEIall.input,
        rules.SMA_SMAall.input,
        rules.CS_CSall.input,
        rules.QC_QCall.input
    default_target: True
