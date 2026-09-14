"""Operator-only registration; no public registration/path/write endpoint."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
from app.sample_reference_reader import RegisteredSource, SourceError, require

@dataclass(frozen=True)
class ReferenceConfig:
    enabled: bool
    secret: bytes
    sources: tuple[RegisteredSource, ...]

def load_reference_config():
    enabled = os.getenv("SAMPLE_REFERENCE_ENABLED", "false").lower() in ("true","1","yes")
    if not enabled:
        return ReferenceConfig(False,b"",())
    secret=os.getenv("SAMPLE_REFERENCE_IDENTITY_SECRET", "").encode()
    require(len(secret)>=32,"identity_secret_invalid")
    try:
        path=os.environ["SAMPLE_REFERENCE_SOURCES_FILE"]
        raw=Path(path).read_bytes(); require(len(raw)<=65536,"registration_invalid")
        items=json.loads(raw)
        require(type(items) is list and 0 < len(items) <= 100,"registration_invalid")
        sources=[]
        for item in items:
            if type(item) is dict and item.get("source_type")=="wgs_files":
                from app.wgs_file_reference import FileSource
                require(set(item)-{"runtime_root"}=={"source_type","source_id","scope_id","project_root"}
                    and type(item["project_root"]) is str and ("runtime_root" not in item or type(item["runtime_root"]) is str),"registration_invalid")
                sources.append(FileSource(item["source_id"],item["scope_id"],Path(item["project_root"]),
                    runtime_root=Path(item["runtime_root"]) if "runtime_root" in item else None))
                continue
            if type(item) is dict and item.get("source_type")=="wgs_cloud_only":
                from app.wgs_cloud_reference import CloudSource
                from app.wgs_cloud_consumer import CloudRequestIdentity
                require(set(item)=={"source_type","source_id","scope_id","project_root","executions"},"registration_invalid")
                require(type(item["executions"]) is list and len(item["executions"])<=100 and type(item["project_root"]) is str,"registration_invalid")
                sources.append(CloudSource(item["source_id"],item["scope_id"],Path(item["project_root"]),tuple(CloudRequestIdentity(**e) for e in item["executions"])))
                continue
            require(type(item) is dict and set(item)=={"source_id","scope_id","project_root","producer_commits"},"registration_invalid")
            require(type(item["producer_commits"]) is list and type(item["project_root"]) is str,"registration_invalid")
            sources.append(RegisteredSource(item["source_id"],item["scope_id"],Path(item["project_root"]),tuple(item["producer_commits"])))
        require(len({s.source_id for s in sources})==len(sources) and len({s.scope_id for s in sources})==len(sources)
                and len({str(s.project_root) for s in sources})==len(sources),"registration_invalid")
        return ReferenceConfig(True,secret,tuple(sources))
    except SourceError: raise
    except (OSError,KeyError,ValueError,TypeError):
        raise SourceError("registration_invalid") from None
