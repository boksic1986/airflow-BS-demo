#!/biosoftware/miniconda/envs/snakemake_env/bin/python
import logging
import sys
from pathlib import Path


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logger(name, log_path=None, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # Reinitialize handlers to avoid duplicate logs when script is invoked repeatedly.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    formatter = logging.Formatter(LOG_FORMAT)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_path:
        log_file = Path(log_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def write_rule_audit_log(log_path, metadata_path=None, extra_sections=None):
    log_file = Path(log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with open(log_file, "w", encoding="utf-8") as handle:
        handle.write("=== PIPELINE AUDIT ===\n")
        if metadata_path:
            metadata_text = Path(metadata_path).read_text(encoding="utf-8")
            handle.write(metadata_text)
            if metadata_text and not metadata_text.endswith("\n"):
                handle.write("\n")
        for title, body in extra_sections or []:
            handle.write(f"=== {title} ===\n")
            handle.write(str(body))
            if body and not str(body).endswith("\n"):
                handle.write("\n")
        handle.write("=== COMMAND ===\n")
