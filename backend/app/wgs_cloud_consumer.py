"""Strict, bounded, read-only projection of one cloud-only producer execution.

This module intentionally does not import producer code.  All paths are rooted in an
operator-registered project and no returned value contains raw TSV or link targets.
"""
from dataclasses import dataclass
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat

from app.sample_reference_reader import Tree, opaque

PINNED_PRODUCER_COMMIT = "cb57479d7fa896c3b2295a80eb697942d5083ce6"
MAX_ROWS = 100_000
MAX_ARTIFACT_DIRECTORIES = 10_000
MAX_ARTIFACT_DEPTH = 32
REQUEST_KEYS = {"schema_version","scope_id","analysis_id","attempt","generation","execution_id","request_hash","release_id","source_snapshot_id","source_sha256","source_commit","config_sha256"}
SAMPLEINFO_ORDER = ["上机批次","分析批次","上传批次","重新实验/暂停分析","注意事项","家系人数","projectId","订单编号","样本条码","家系编号","家系名","姓名","样本编号","数据编号","样本类型","是否患者","家系关系","性别","出生日期","收样日期","预计报告日期","送检医院","送检医生","项目编号","检测项目","检测方法","临床主诉","中文关键词","英文关键词","医院编号","医院条码号","analysisTaskId","taskSampleId","version"]
SAMPLEINFO_COLUMNS = set(SAMPLEINFO_ORDER)

class CloudConsumerError(ValueError):
    def __init__(self, code): self.code=code; super().__init__(code)

@dataclass(frozen=True)
class CloudRequestIdentity:
    analysis_id: str
    attempt: int
    generation: int
    execution_id: str
    request_hash: str
    producer_commit: str

def _need(ok, code="history_invalid"):
    if not ok: raise CloudConsumerError(code)

def _sha(raw): return hashlib.sha256(raw).hexdigest()
def _digest(v): return isinstance(v,str) and re.fullmatch(r"[0-9a-f]{64}",v) is not None
def _exact(v, keys, code="history_invalid"): _need(type(v) is dict and set(v)==set(keys),code)

def _json(raw, code="history_invalid"):
    def pairs(items):
        out={}
        for k,v in items: _need(k not in out,code); out[k]=v
        return out
    try: value=json.loads(raw.decode("utf-8"),object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (UnicodeError,ValueError,json.JSONDecodeError): raise CloudConsumerError(code) from None
    canonical=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()+b"\n"
    _need(raw==canonical,code)
    return value

def _tsv(raw, code="history_invalid"):
    _need(bool(raw) and not raw.startswith(b"\xef\xbb\xbf"),code)
    try: rows=list(csv.reader(io.StringIO(raw.decode("utf-8"),newline=""),delimiter="\t",strict=True))
    except (UnicodeError,csv.Error): raise CloudConsumerError(code) from None
    _need(bool(rows) and bool(rows[0]) and all(rows[0]) and len(rows[0])==len(set(rows[0])) and SAMPLEINFO_COLUMNS.issubset(rows[0]),code)
    _need(len(rows)-1<=MAX_ROWS and all(len(r)==len(rows[0]) for r in rows[1:]),code)
    return rows[0],[dict(zip(rows[0],r)) for r in rows[1:]]

def _projection_context(identity_secret, scope_id):
    _need(isinstance(identity_secret, bytes) and len(identity_secret)>=32,"identity_secret_invalid")
    _need(type(scope_id) is str and bool(scope_id.strip()),"registration_invalid")

def _safe(rows, identity_secret, scope_id, *, pending=False):
    result=[]
    for r in rows:
        # Exact pinned pending.order_group_key/pending_identity, not sample-only.
        group=None
        for column,prefix in (("analysisTaskId","task:"),("订单编号","order:")):
            value=r.get(column,"").strip()
            if value not in ("", ".", "None", "nan"):
                group=prefix+value; break
        identity=[group or "sample:"+r["样本编号"].strip(),r["样本编号"].strip(),r["上机批次"].strip(),r["数据编号"].strip()]
        codes=["pending_reason_unclassified"] if pending else []
        result.append({"record_key":opaque(identity_secret,scope_id,"identity",identity),"sample_id":r["样本编号"],"data_id":r["数据编号"],"family_id":r["家系编号"],"sequencing_batch":r["上机批次"],"analysis_batch":r["分析批次"],"reason_codes":codes,"reason_code":codes[0] if codes else None})
    return result

def _descriptor(tree, descriptor, expected_path, *, json_value=False):
    _exact(descriptor,{"path","sha256","byte_size","row_count"})
    _need(descriptor["path"]==expected_path and _digest(descriptor["sha256"]) and type(descriptor["byte_size"]) is int and 0<=descriptor["byte_size"]<=64*1024*1024 and type(descriptor["row_count"]) is int and 0<=descriptor["row_count"]<=MAX_ROWS)
    raw=tree.read(expected_path); _need(len(raw)==descriptor["byte_size"] and _sha(raw)==descriptor["sha256"])
    if json_value: return raw,_json(raw)
    header,rows=_tsv(raw); _need(len(rows)==descriptor["row_count"])
    return raw,rows

def _pending(tree, identity):
    _need(identity.producer_commit==PINNED_PRODUCER_COMMIT,"registration_mismatch")
    _need(type(identity.attempt) is int and identity.attempt>0 and type(identity.generation) is int and identity.generation>0 and _digest(identity.request_hash),"identity_mismatch")
    h=_sha(identity.execution_id.encode()); base=f"prepare/cloud-pending/v1/requests/{h}"
    try:
        request_raw=tree.read(base+"/request.json"); request=_json(request_raw); _exact(request,REQUEST_KEYS)
        _need(request["schema_version"]=="wgs.cloud-pending.request.v1")
        _need(all(type(request[k]) is str and request[k].strip() for k in ("scope_id","analysis_id","execution_id","release_id","source_snapshot_id")))
        _need(type(request["attempt"]) is int and request["attempt"]>0 and type(request["generation"]) is int and request["generation"]>0)
        _need(all(_digest(request[k]) for k in ("request_hash","source_sha256","config_sha256")) and type(request["source_commit"]) is str and re.fullmatch(r"[0-9a-f]{40}",request["source_commit"]) is not None)
        _need((request["analysis_id"],request["attempt"],request["generation"],request["execution_id"],request["request_hash"])==(identity.analysis_id,identity.attempt,identity.generation,identity.execution_id,identity.request_hash),"identity_mismatch")
        request_sha=_sha(request_raw[:-1])
        started=_json(tree.read(base+"/started.json")); _exact(started,{"schema_version","request_sha256"}); _need(started=={"schema_version":"wgs.cloud-pending.started.v1","request_sha256":request_sha})
        receipt=_json(tree.read(base+"/receipt.json")); _exact(receipt,{"schema_version","request","request_sha256","status","before_exists","snapshots","links"})
        _need(receipt["schema_version"]=="wgs.cloud-pending.receipt.v1" and receipt["request"]==request and receipt["request_sha256"]==request_sha and receipt["status"]=="prepared" and type(receipt["before_exists"]) is bool)
        _exact(receipt["snapshots"],{"source","before","selected","pending"})
        tables={}
        for name in ("source","before","selected","pending"):
            raw,rows=_descriptor(tree,receipt["snapshots"][name],f"{base}/{name}.tsv"); tables[name]=(raw,rows)
        _need(request["source_sha256"]==_sha(tables["source"][0]))
        if receipt["before_exists"] is False:
            _need(tables["before"][0]==("\t".join(SAMPLEINFO_ORDER+["pending_reason","pending_at","source_analysis_batch","source_sampleinfo"])+"\n").encode())
        _,links=_descriptor(tree,receipt["links"],f"{base}/links.json",json_value=True)
        _exact(links,{"schema_version","execution_id","request_sha256","selected_sha256","links"})
        _need(links["schema_version"]=="wgs.cloud-pending.links.v1" and links["execution_id"]==identity.execution_id and links["request_sha256"]==request_sha and links["selected_sha256"]==receipt["snapshots"]["selected"]["sha256"] and type(links["links"]) is list and len(links["links"])==receipt["links"]["row_count"])
        destinations=set()
        for link in links["links"]:
            _exact(link,{"sample_id","read","source","destination_name"}); _need(all(type(link[k]) is str and link[k] for k in link) and link["read"] in ("R1","R2"))
            name=link["destination_name"]
            _need(name not in destinations and name not in (".","..") and not any(c in name for c in ("/","\\","\x00")) and link["source"].startswith("/") and "\x00" not in link["source"])
            destinations.add(name)
        return base,receipt,tables,links
    except FileNotFoundError: raise CloudConsumerError("history_incomplete") from None
    except CloudConsumerError: raise
    except Exception: raise CloudConsumerError("history_invalid") from None

def _artifact(tree,base,pending,links):
    ad=base+"/artifact-v1"
    if not tree.exists(ad): return "prepared"
    try:
        started=_json(tree.read(ad+"/started.json"),"artifact_invalid"); receipt=_json(tree.read(ad+"/receipt.json"),"artifact_invalid")
        common={"execution_id","artifact_request_sha256","pending_request_sha256","selected_sha256","links_sha256","effective_config_sha256","source_manifest_sha256","source_kind","destination"}
        _exact(started,{"schema_version","cce_pipeline_sha256",*common},"artifact_invalid")
        _exact(receipt,{"schema_version","analysis_state","status","manifest",*common},"artifact_invalid")
        _need(started["schema_version"]=="wgs.cloud-artifact.started.v1" and receipt["schema_version"]=="wgs.cloud-artifact.receipt.v1","artifact_invalid")
        _need(all(started[k]==receipt[k] for k in common) and all(_digest(receipt[k]) for k in ("artifact_request_sha256","pending_request_sha256","selected_sha256","links_sha256","effective_config_sha256","source_manifest_sha256")) and _digest(started["cce_pipeline_sha256"]),"artifact_invalid")
        _need(receipt["execution_id"]==pending["request"]["execution_id"],"artifact_invalid")
        _need((receipt["status"]=="no_analysis_needed") == (pending["snapshots"]["selected"]["row_count"]==0),"artifact_invalid")
        _need(receipt["pending_request_sha256"]==pending["request_sha256"] and receipt["selected_sha256"]==pending["snapshots"]["selected"]["sha256"] and receipt["links_sha256"]==pending["links"]["sha256"] and receipt["source_kind"]=="synthetic" and receipt["analysis_state"]=="not_started" and receipt["status"] in ("artifact_ready","no_analysis_needed"),"artifact_invalid")
        destination=receipt["destination"]; parts=destination.split("/"); _need(parts and parts[0]!="prepare" and all(p not in ("",".","..") for p in parts),"artifact_invalid")
        if receipt["status"]=="no_analysis_needed":
            _need(receipt["manifest"] is None and not tree.exists(destination),"artifact_invalid"); return receipt["status"]
        raw,manifest=_descriptor(tree,receipt["manifest"],ad+"/manifest.json",json_value=True)
        _exact(manifest,{"schema_version","files"},"artifact_invalid"); _need(manifest["schema_version"]=="wgs.cloud-artifact.manifest.v1" and type(manifest["files"]) is list and len(manifest["files"])==receipt["manifest"]["row_count"],"artifact_invalid")
        expected={}; expected_links={"raw/"+x["destination_name"]:x["source"] for x in links["links"]}; actual_links={}; ancestors=set()
        for entry in manifest["files"]:
            _exact(entry,{"path","kind","sha256","byte_size","target"},"artifact_invalid"); p=entry["path"]
            _need(type(p) is str and p and p not in expected and all(x not in ("",".","..") for x in p.split("/")) and entry["kind"] in ("file","symlink") and _digest(entry["sha256"]) and type(entry["byte_size"]) is int and entry["byte_size"]>=0,"artifact_invalid")
            if entry["kind"]=="file": _need(entry["target"] is None,"artifact_invalid")
            else:
                _need(p in expected_links and entry["target"]==expected_links[p] and _sha(entry["target"].encode())==entry["sha256"] and len(entry["target"].encode())==entry["byte_size"],"artifact_invalid")
                actual_links[p]=entry["target"]
            components=p.split("/"); _need(len(components)<=MAX_ARTIFACT_DEPTH,"artifact_invalid")
            for n in range(1,len(components)): ancestors.add("/".join(components[:n]))
            _need(len(ancestors)<=MAX_ARTIFACT_DIRECTORIES,"artifact_invalid")
            expected[p]=entry
        _need(actual_links==expected_links,"artifact_invalid")
        _need(list(expected)==sorted(expected),"artifact_invalid")
        actual=set(); todo=[""]; directory_count=1
        while todo:
            prefix=todo.pop()
            for name,info in tree.children(destination+("/"+prefix if prefix else "")):
                p=prefix+"/"+name if prefix else name
                if stat.S_ISDIR(info.st_mode):
                    directory_count+=1
                    # Pinned producer _build_artifact creates empty root log/tmp.
                    _need(directory_count<=MAX_ARTIFACT_DIRECTORIES and len(p.split("/"))<=MAX_ARTIFACT_DEPTH and (p in ancestors or p in ("log","tmp")),"artifact_invalid")
                    todo.append(p); continue
                _need(p in expected,"artifact_invalid"); entry=expected[p]; actual.add(p)
                if entry["kind"]=="file":
                    _need(stat.S_ISREG(info.st_mode),"artifact_invalid"); data=tree.read(destination+"/"+p); _need(len(data)==entry["byte_size"] and _sha(data)==entry["sha256"],"artifact_invalid")
                else:
                    _need(stat.S_ISLNK(info.st_mode),"artifact_invalid")
                    with tree.parent(destination+"/"+p) as (fd,n): _need(os.readlink(n,dir_fd=fd)==entry["target"],"artifact_invalid")
        _need(actual==set(expected),"artifact_invalid")
        return receipt["status"]
    except FileNotFoundError: raise CloudConsumerError("history_incomplete") from None
    except CloudConsumerError: raise
    except Exception: raise CloudConsumerError("artifact_invalid") from None

def _live(tree, identity_secret, scope_id):
    try:
        import fcntl
        lock=tree.open("prepare/pending_samples.tsv.lock")
        try:
            fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
            _,rows=_tsv(tree.read("prepare/pending_samples.tsv"),"live_unavailable")
        finally: os.close(lock)
        return {"status":"available","row_count":len(rows),"records":_safe(rows,identity_secret,scope_id,pending=True)}
    except Exception: return {"status":"unavailable","row_count":None,"records":[]}

def read_live_pending(project_root: Path, *, identity_secret: bytes, scope_id: str) -> dict:
    """Observe live pending independently, including when history is invalid."""
    _projection_context(identity_secret,scope_id)
    _need(isinstance(project_root,Path) and project_root.is_absolute(),"registration_invalid")
    tree=None
    try:
        tree=Tree(project_root)
        return _live(tree,identity_secret,scope_id)
    except Exception: return {"status":"unavailable","row_count":None,"records":[]}
    finally:
        if tree: tree.close()

def read_cloud_execution(project_root: Path, expected: CloudRequestIdentity, *, identity_secret: bytes, scope_id: str) -> dict:
    _projection_context(identity_secret,scope_id)
    _need(isinstance(project_root,Path) and project_root.is_absolute(),"registration_invalid")
    tree=None
    try:
        tree=Tree(project_root); base,pending,tables,links=_pending(tree,expected)
        _need(pending["request"]["scope_id"]==scope_id,"identity_mismatch")
        status=_artifact(tree,base,pending,links)
        return {"schema_version":"airflow-demo.wgs-cloud-consumer.v1","producer_commit":PINNED_PRODUCER_COMMIT,"analysis_id":expected.analysis_id,"attempt":expected.attempt,"generation":expected.generation,"execution_id":expected.execution_id,"request_hash":expected.request_hash,"stage_status":status,"analysis_state":"not_started","synthetic_execution_allowed":False,"selected":_safe(tables["selected"][1],identity_secret,scope_id),"historical_pending":_safe(tables["pending"][1],identity_secret,scope_id,pending=True),"live_pending":_live(tree,identity_secret,scope_id)}
    except CloudConsumerError: raise
    except Exception: raise CloudConsumerError("history_invalid") from None
    finally:
        if tree: tree.close()
