"""Platform-side marker for newly frozen stage execution requests."""

STAGE_EXECUTION_PROTOCOL = "cce.stage-execution.v1"
STAGE_EXECUTION_EXTENSION = {"protocol": STAGE_EXECUTION_PROTOCOL}


def freeze_stage_execution_protocol(request_payload: dict) -> None:
    """Freeze the public executor protocol before the request hash is computed."""
    if not isinstance(request_payload, dict):
        raise ValueError("stage execution request must be an object")
    if "stage_execution" in request_payload:
        if request_payload["stage_execution"] != STAGE_EXECUTION_EXTENSION:
            raise ValueError("unsupported stage execution protocol")
        return
    request_payload["stage_execution"] = dict(STAGE_EXECUTION_EXTENSION)
