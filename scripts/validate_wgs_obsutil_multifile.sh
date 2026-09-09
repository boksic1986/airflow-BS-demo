#!/usr/bin/env bash
set -euo pipefail
umask 077

evidence_root=${1:?usage: validate_wgs_obsutil_multifile.sh EVIDENCE_ROOT}
target_parent=${WGS_CANARY_TARGET_PARENT:?WGS_CANARY_TARGET_PARENT is required}
obsutil_bin=${WGS_CANARY_OBSUTIL_BIN:-/bi/BioCodeHub/WGS/obsutil}
obsutil_config=${WGS_CANARY_OBSUTIL_CONFIG:-/bi/BioCodeHub/WGS/obs.config}
wrapper=${WGS_CANARY_WRAPPER:-$(dirname "$0")/wgs_obsutil_progress.py}
payload_bytes=67108864
analysis_id=WGS_20260909_120000_C4A4A1

raw_root="$evidence_root/raw"
download_root="$evidence_root/download/cram"
upload_progress="$evidence_root/progress-upload"
download_progress="$evidence_root/progress-download"
checkpoint_root="$evidence_root/checkpoint"
upload_plan="$evidence_root/upload-plan.json"
download_plan="$evidence_root/download-plan.json"
summary="$evidence_root/summary.txt"
target_root="${target_parent%/}/T241-multifile-$(date +%Y%m%dT%H%M%S)-$$"
first_target="$target_root/raw/S1_R1.fastq.gz"
second_target="$target_root/raw/S1_R2.fastq.gz"

mkdir -p \
  "$raw_root" "$download_root" "$upload_progress" "$download_progress" \
  "$checkpoint_root/upload-1" "$checkpoint_root/upload-2" \
  "$checkpoint_root/download-1" "$checkpoint_root/download-2"
chmod 700 "$evidence_root" "$raw_root" "$download_root" \
  "$upload_progress" "$download_progress" "$checkpoint_root" \
  "$checkpoint_root/upload-1" "$checkpoint_root/upload-2" \
  "$checkpoint_root/download-1" "$checkpoint_root/download-2"
test -x "$obsutil_bin"
test -r "$obsutil_config"
test -x "$wrapper"
rm -f "$upload_progress"/*.json "$download_progress"/*.json

cleanup() {
  "$obsutil_bin" rm "$first_target" -f -config="$obsutil_config" >/dev/null 2>&1 || true
  "$obsutil_bin" rm "$second_target" -f -config="$obsutil_config" >/dev/null 2>&1 || true
  rm -f \
    "$raw_root/S1_R1.fastq.gz" "$raw_root/S1_R2.fastq.gz" \
    "$download_root/S1.cram.partial" "$download_root/S2.cram.partial"
}
trap cleanup EXIT

dd if=/dev/zero of="$raw_root/S1_R1.fastq.gz" bs=8M count=8 conv=fsync status=none
dd if=/dev/zero of="$raw_root/S1_R2.fastq.gz" bs=8M count=8 conv=fsync status=none

python3 - "$upload_plan" "$download_plan" "$payload_bytes" <<'PY'
import json
import pathlib
import sys

upload_path, download_path, size = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), int(sys.argv[3])
upload_path.write_text(json.dumps({"entries": [
    {"relative_path": "raw/S1_R1.fastq.gz", "size_bytes": size},
    {"relative_path": "raw/S1_R2.fastq.gz", "size_bytes": size},
]}) + "\n", encoding="utf-8")
download_path.write_text(json.dumps({"entries": [
    {"relative_path": "cram/S1.cram", "size_bytes": size},
    {"relative_path": "cram/S2.cram", "size_bytes": size},
]}) + "\n", encoding="utf-8")
PY

run_upload() {
  local source=$1 target=$2 checkpoint=$3
  env \
    WGS_REAL_OBSUTIL_BIN="$obsutil_bin" \
    WGS_TRANSFER_PROGRESS_ROOT="$upload_progress" \
    WGS_TRANSFER_PLAN_PATH="$upload_plan" \
    WGS_TRANSFER_ANALYSIS_ID="$analysis_id" \
    WGS_TRANSFER_ATTEMPT=1 \
    WGS_TRANSFER_STAGE=step1_upload \
    WGS_TRANSFER_DIRECTION=upload \
    "$wrapper" cp "$source" "$target" -f -config="$obsutil_config" \
      -cpd="$checkpoint" -threshold=1MB -ps=8MB -p=2 -vmd5 -vlength \
      >/dev/null 2>&1
}

run_upload "$raw_root/S1_R1.fastq.gz" "$first_target" "$checkpoint_root/upload-1" &
upload_one=$!
run_upload "$raw_root/S1_R2.fastq.gz" "$second_target" "$checkpoint_root/upload-2" &
upload_two=$!
wait "$upload_one"
wait "$upload_two"

run_download() {
  local source=$1 target=$2 checkpoint=$3
  env \
    WGS_REAL_OBSUTIL_BIN="$obsutil_bin" \
    WGS_TRANSFER_PROGRESS_ROOT="$download_progress" \
    WGS_TRANSFER_PLAN_PATH="$download_plan" \
    WGS_TRANSFER_ANALYSIS_ID="$analysis_id" \
    WGS_TRANSFER_ATTEMPT=1 \
    WGS_TRANSFER_STAGE=step5_download \
    WGS_TRANSFER_DIRECTION=download \
    "$wrapper" cp "$source" "$target" -f -config="$obsutil_config" \
      -cpd="$checkpoint" -tempFileDir="$evidence_root/download-temp" \
      -threshold=1MB -ps=8MB -p=2 -vmd5 -vlength >/dev/null 2>&1
}

mkdir -p "$evidence_root/download-temp"
run_download "$first_target" "$download_root/S1.cram.partial" "$checkpoint_root/download-1" &
download_one=$!
run_download "$second_target" "$download_root/S2.cram.partial" "$checkpoint_root/download-2" &
download_two=$!
wait "$download_one"
wait "$download_two"

cmp "$raw_root/S1_R1.fastq.gz" "$download_root/S1.cram.partial"
cmp "$raw_root/S1_R2.fastq.gz" "$download_root/S2.cram.partial"

python3 - "$upload_progress" "$download_progress" "$payload_bytes" "$summary" <<'PY'
import json
import pathlib
import re
import sys

upload_root, download_root = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
expected_size, summary_path = int(sys.argv[3]), pathlib.Path(sys.argv[4])
result = {}
for direction, root in (("upload", upload_root), ("download", download_root)):
    rows = [json.loads(path.read_text(encoding="utf-8")) for path in root.glob("*.json")]
    assert len(rows) == 2, (direction, len(rows))
    assert len({row.get("file_key") for row in rows}) == 2
    assert all(re.fullmatch(r"[0-9a-f]{64}", str(row.get("file_key") or "")) for row in rows)
    assert all(row.get("state") == "success" for row in rows)
    assert all(row.get("source") == "obsutil-checkpoint" for row in rows)
    assert all(row.get("bytes_total") == expected_size for row in rows)
    assert all(row.get("bytes_done") == expected_size for row in rows)
    assert all(row.get("checksum_status") == "verified" for row in rows)
    assert all(row.get("checkpoint_observed") is True for row in rows)
    serialized = json.dumps(rows)
    assert "obs://" not in serialized and "/sg2/" not in serialized
    result[f"{direction}_files"] = len(rows)
    result[f"{direction}_bytes"] = sum(row["bytes_done"] for row in rows)
summary_path.write_text("\n".join([
    "status=pass",
    f"upload_files={result['upload_files']}",
    f"upload_bytes={result['upload_bytes']}",
    f"download_files={result['download_files']}",
    f"download_bytes={result['download_bytes']}",
    "checkpoint_progress=observed",
    "checksum=verified",
    "privacy=pass",
]) + "\n", encoding="utf-8")
PY

trap - EXIT
set +e
"$obsutil_bin" rm "$first_target" -f -config="$obsutil_config" >/dev/null 2>&1
first_cleanup_rc=$?
"$obsutil_bin" rm "$second_target" -f -config="$obsutil_config" >/dev/null 2>&1
second_cleanup_rc=$?
"$obsutil_bin" stat "$first_target" -config="$obsutil_config" >/dev/null 2>&1
first_stat_rc=$?
"$obsutil_bin" stat "$second_target" -config="$obsutil_config" >/dev/null 2>&1
second_stat_rc=$?
set -e
rm -f \
  "$raw_root/S1_R1.fastq.gz" "$raw_root/S1_R2.fastq.gz" \
  "$download_root/S1.cram.partial" "$download_root/S2.cram.partial"
test "$first_cleanup_rc" -eq 0
test "$second_cleanup_rc" -eq 0
test "$first_stat_rc" -ne 0
test "$second_stat_rc" -ne 0
printf 'remote_cleanup=verified\n' >> "$summary"
sed -n '1,20p' "$summary"
