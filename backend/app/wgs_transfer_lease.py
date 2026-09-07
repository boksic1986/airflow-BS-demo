from __future__ import annotations


OBS_UPLOAD_SLOT = "wgs-obs-upload-01"
OBS_DOWNLOAD_SLOT = "wgs-obs-download-01"
LEGACY_OBS_TRANSFER_SLOT = "wgs-obs-transfer-01"

OBS_TRANSFER_SLOT_BY_KIND = {
    "input": OBS_UPLOAD_SLOT,
    "result": OBS_DOWNLOAD_SLOT,
}
