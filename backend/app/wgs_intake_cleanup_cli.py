import argparse
import json

from app.db import get_sessionmaker
from app.wgs_intake_cleanup import reset_wgs_intake_baseline


CONFIRMATION = "RESET-WGS-INTAKE-BASELINE"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    if args.confirm != CONFIRMATION:
        raise SystemExit("exact --confirm RESET-WGS-INTAKE-BASELINE is required")
    with get_sessionmaker().begin() as session:
        result = reset_wgs_intake_baseline(session)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
