import argparse
import json
import os
import time
from pathlib import Path

from app.db import get_sessionmaker
from app.wgs_observer import ingest_evidence_once


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, default=Path(os.getenv("WGS_EVIDENCE_ROOT", "/data/wgs-evidence")))
    parser.add_argument("--binding-root", type=Path, default=Path(os.getenv("WGS_BINDING_ROOT", "/config/wgs-bindings")))
    parser.add_argument("--catalog", type=Path, default=Path(os.getenv("WGS_RELEASE_CATALOG_PATH", "/config/wgs_releases.yaml")))
    parser.add_argument("--interval", type=float, default=float(os.getenv("WGS_OBSERVER_INTERVAL", "5")))
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    while True:
        result = ingest_evidence_once(
            session_factory=get_sessionmaker(),
            evidence_root=args.evidence_root,
            binding_root=args.binding_root,
            catalog_path=args.catalog,
        )
        print(json.dumps(result, sort_keys=True), flush=True)
        if args.once:
            return 0
        time.sleep(max(1.0, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
