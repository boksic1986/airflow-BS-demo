#!/biosoftware/miniconda/envs/snakemake_env/bin/python
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path

import yaml

from pipeline_logging import setup_logger


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a predict-mode config that points to an existing WisecondorX reference NPZ file.",
        epilog=(
            "Example:\n"
            "/biosoftware/miniconda/envs/snakemake_env/bin/python scripts/init_predict_config.py "
            "--base-config /data/project/CNV/PGT-A/2026-03-16/predict_samples.yaml "
            "--reference-xx-npz /data/project/CNV/PGT-A/reference/XX/result/ref_xx_best.npz "
            "--reference-xy-npz /data/project/CNV/PGT-A/reference/XY/result/ref_xy_best.npz "
            "--gender-reference-npz /data/project/CNV/PGT-A/reference/gender/result/ref_gender_best.npz "
            "--common-reference-binsize /data/project/CNV/PGT-A/reference/gender/common_best_binsize.txt "
            "--output-config /data/project/CNV/PGT-A/2026-03-16/config_predict.yaml"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--base-config", required=True, help="Base config YAML used for project/sample settings")
    parser.add_argument("--reference-npz", default="", help="Optional single-reference NPZ for non-sex-specific prediction")
    parser.add_argument("--reference-xx-npz", default="", help="Existing WisecondorX XX reference NPZ for prediction")
    parser.add_argument("--reference-xy-npz", default="", help="Existing WisecondorX XY reference NPZ for prediction")
    parser.add_argument("--gender-reference-npz", default="", help="Existing mixed-sex gender reference NPZ for WisecondorX gender")
    parser.add_argument("--common-reference-binsize", default="", help="Text file containing the shared binsize used by XX/XY/gender references")
    parser.add_argument("--output-config", required=True, help="Output predict config YAML path")
    parser.add_argument("--log", default="", help="Optional log file path")
    return parser.parse_args()


def load_yaml(yaml_path: Path):
    with open(yaml_path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def build_predict_overlay(
    base_config: Path,
    reference_npz: Path | None = None,
    reference_xx_npz: Path | None = None,
    reference_xy_npz: Path | None = None,
    gender_reference_npz: Path | None = None,
    common_reference_binsize: Path | None = None,
):
    wisecondorx_cfg = {
        "cnv": {
            "enable": True,
        },
    }
    if reference_npz is not None:
        wisecondorx_cfg["reference_output"] = str(reference_npz)
    if reference_xx_npz is not None or reference_xy_npz is not None or gender_reference_npz is not None or common_reference_binsize is not None:
        if not (reference_xx_npz and reference_xy_npz and gender_reference_npz and common_reference_binsize):
            raise ValueError(
                "Sex-specific predict config requires --reference-xx-npz, --reference-xy-npz, "
                "--gender-reference-npz and --common-reference-binsize together."
            )
        wisecondorx_cfg["reference_output_by_sex"] = {
            "XX": str(reference_xx_npz),
            "XY": str(reference_xy_npz),
        }
        wisecondorx_cfg["gender_reference_output"] = str(gender_reference_npz)
        wisecondorx_cfg["common_reference_binsize_output"] = str(common_reference_binsize)

    return {
        "base_config": str(base_config),
        "core": {
            "wisecondorx": wisecondorx_cfg,
        },
        "pipeline": {
            "mode": "predict",
            "targets": ["mapping", "metadata", "cnv_qc", "cnv"],
        },
    }


def main():
    args = parse_args()
    logger = setup_logger("init_predict_config", args.log or None)

    base_config = Path(args.base_config).resolve()
    output_config = Path(args.output_config).resolve()

    if not base_config.exists():
        raise FileNotFoundError(f"Base config not found: {base_config}")

    reference_npz = Path(args.reference_npz).resolve() if args.reference_npz else None
    reference_xx_npz = Path(args.reference_xx_npz).resolve() if args.reference_xx_npz else None
    reference_xy_npz = Path(args.reference_xy_npz).resolve() if args.reference_xy_npz else None
    gender_reference_npz = Path(args.gender_reference_npz).resolve() if args.gender_reference_npz else None
    common_reference_binsize = Path(args.common_reference_binsize).resolve() if args.common_reference_binsize else None

    provided_single = reference_npz is not None
    provided_dual = any(path is not None for path in [reference_xx_npz, reference_xy_npz, gender_reference_npz, common_reference_binsize])
    if provided_single and provided_dual:
        raise ValueError("Use either --reference-npz or the sex-specific --reference-xx-npz/--reference-xy-npz/--gender-reference-npz set, not both.")
    if not provided_single and not provided_dual:
        raise ValueError(
            "Either --reference-npz or the sex-specific "
            "--reference-xx-npz/--reference-xy-npz/--gender-reference-npz/--common-reference-binsize set is required."
        )

    for path_value, label in [
        (reference_npz, "reference_npz"),
        (reference_xx_npz, "reference_xx_npz"),
        (reference_xy_npz, "reference_xy_npz"),
        (gender_reference_npz, "gender_reference_npz"),
        (common_reference_binsize, "common_reference_binsize"),
    ]:
        if path_value is not None and not path_value.exists():
            raise FileNotFoundError(f"{label} not found: {path_value}")

    base_cfg = load_yaml(base_config)
    if "samples" not in base_cfg and "base_config" not in base_cfg:
        raise ValueError("Base config must contain samples directly or be a config overlay with base_config")
    base_mode = str(base_cfg.get("pipeline", {}).get("mode", "")).strip().lower()
    if base_mode in {"build_ref", "reference", "build_reference"}:
        raise ValueError(
            "Base config is a build_ref config. Use a dedicated predict_samples.yaml as --base-config."
        )
    if base_cfg.get("build_reference", {}).get("groups"):
        raise ValueError(
            "Base config still contains build_reference.groups. Use a dedicated predict_samples.yaml as --base-config."
        )

    predict_cfg = build_predict_overlay(
        base_config=base_config,
        reference_npz=reference_npz,
        reference_xx_npz=reference_xx_npz,
        reference_xy_npz=reference_xy_npz,
        gender_reference_npz=gender_reference_npz,
        common_reference_binsize=common_reference_binsize,
    )

    output_config.parent.mkdir(parents=True, exist_ok=True)
    with open(output_config, "w", encoding="utf-8") as handle:
        yaml.safe_dump(predict_cfg, handle, sort_keys=False, allow_unicode=True)

    logger.info("predict config written: %s", output_config)
    if reference_npz is not None:
        logger.info("reference_output -> %s", reference_npz)
    else:
        logger.info("reference_output_by_sex.XX -> %s", reference_xx_npz)
        logger.info("reference_output_by_sex.XY -> %s", reference_xy_npz)
        logger.info("gender_reference_output -> %s", gender_reference_npz)
        logger.info("common_reference_binsize_output -> %s", common_reference_binsize)
    logger.info("pipeline.targets -> mapping,metadata,cnv_qc,cnv")


if __name__ == "__main__":
    main()
