"""Read-only WGS-owned v1 handoffs. No selection, recovery, or pending writes.

Private tuples and TSV bytes exist only during validation. Returned projections
contain scoped keyed identities and allowlisted fields, never raw order keys.
"""
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import csv
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import re
import stat
import uuid

ROLES = ("source", "pending_before", "pending_after", "selected", "pending_current")
FILES = dict(zip(ROLES, ("source.tsv", "pending.before.tsv", "pending.after.tsv", "selected.tsv", "pending.current.tsv")))
REASONS = frozenset(("sequencing_batch_missing", "samplelist_sample_missing", "fastq_ready_missing",
    "target_base_invalid", "basecount_missing", "basecount_parse_error", "sample_not_in_basecount",
    "basecount_below_minimum", "pending_reason_unclassified"))
SAFE_FIELDS = frozenset(("sample_id", "family_id", "sequencing_batch", "analysis_batch", "data_id",
    "source_analysis_batch", "target_analysis_batch", "reason_code", "reason_codes", "reason_message", "order_number_masked"))
MAX_FILE = 64 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024
MAX_ROWS = 100000

class SourceError(ValueError):
    """Only a closed safe diagnostic code, never an underlying OS/parser error."""
    def __init__(self, code="source_invalid"):
        self.code = code
        super().__init__(code)

def require(condition, code="source_invalid"):
    if not condition:
        raise SourceError(code)

def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def opaque(secret, scope, kind, value):
    require(isinstance(secret, bytes) and len(secret) >= 32, "identity_secret_invalid")
    return hmac.new(secret, canonical([scope, kind, value]), hashlib.sha256).hexdigest()

def exact(obj, fields):
    require(type(obj) is dict and set(obj) == set(fields))

def integer(value, minimum=0, maximum=MAX_ROWS):
    require(type(value) is int and minimum <= value <= maximum)

def string(value, maximum=128, nullable=False):
    if value is None and nullable:
        return
    require(type(value) is str and 0 < len(value) <= maximum and value == value.strip()
            and not any(ord(c) < 32 for c in value))

def sha(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None)

def operation_uuid(value):
    require(type(value) is str)
    try:
        require(str(uuid.UUID(value)) == value)
    except (ValueError, AttributeError):
        raise SourceError() from None

def timestamp(value):
    require(type(value) is str and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z", value) is not None)
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise SourceError() from None

def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result)
            result[key] = value
        return result
    def reject(_):
        raise SourceError()
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_float=reject, parse_constant=reject)
        require(canonical(value) == raw)
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise SourceError() from None

def relative(path):
    require(type(path) is str and len(path) <= 1024 and "\\" not in path and "\x00" not in path)
    parts = path.split("/")
    require(all(part not in ("", ".", "..") for part in parts), "unsafe_path")
    return parts

@dataclass(frozen=True)
class RegisteredSource:
    source_id: str
    scope_id: str
    project_root: Path
    producer_commits: tuple[str, ...]

    def __post_init__(self):
        require(bool(re.fullmatch(r"[A-Za-z0-9_-]{1,128}", self.source_id)))
        string(self.scope_id)
        require(self.project_root.is_absolute(), "registration_invalid")
        require(bool(self.producer_commits) and all(re.fullmatch(r"[0-9a-f]{40}", c) for c in self.producer_commits), "registration_invalid")

class Tree:
    """Descriptor-relative nofollow reads, including every configured ancestor."""
    def __init__(self, root):
        require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"), "locking_unavailable")
        self.fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        try:
            for component in root.parts[1:]:
                next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.fd)
                os.close(self.fd); self.fd = next_fd
        except BaseException:
            os.close(self.fd)
            raise
        self.total = 0

    def close(self):
        os.close(self.fd)

    @contextmanager
    def parent(self, path):
        parts = relative(path); fd = os.dup(self.fd)
        try:
            for component in parts[:-1]:
                child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd); fd = child
            yield fd, parts[-1]
        finally:
            os.close(fd)

    def open(self, path, directory=False):
        with self.parent(path) as (fd, name):
            value = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK |
                            (os.O_DIRECTORY if directory else 0), dir_fd=fd)
        info = os.fstat(value)
        if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
            os.close(value); raise SourceError("unsafe_path")
        return value

    def read(self, path):
        fd = self.open(path)
        try:
            before = os.fstat(fd)
            require(before.st_size <= MAX_FILE and before.st_nlink == 1, "source_bounds")
            chunks = []; size = 0
            while True:
                chunk = os.read(fd, min(1024 * 1024, MAX_FILE + 1 - size))
                if not chunk: break
                size += len(chunk); chunks.append(chunk)
                require(size <= MAX_FILE, "source_bounds")
            after = os.fstat(fd)
            require((before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns) ==
                    (after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns), "source_changed")
            self.total += size
            require(self.total <= MAX_TOTAL, "source_bounds")
            return b"".join(chunks)
        finally:
            os.close(fd)

    def info(self, path):
        with self.parent(path) as (fd, name):
            return os.stat(name, dir_fd=fd, follow_symlinks=False)

    def exists(self, path):
        try: self.info(path); return True
        except FileNotFoundError: return False

    def children(self, path):
        fd = self.open(path, directory=True)
        try:
            with os.scandir(fd) as entries:
                result = []
                for entry in entries:
                    require(len(result) < 10000, "source_bounds")
                    result.append((entry.name, entry.stat(follow_symlinks=False)))
                return result
        finally: os.close(fd)

def validate_intent(raw, source, operation_id):
    value = parse(raw)
    exact(value, ("schema_version", "operation_id", "execution_id", "request_sha256", "scope_id",
        "publication_sequence", "mode", "cloud", "source_commit", "previous_operation_id",
        "previous_commit_sha256", "before_exists", "identities", "config_sha256", "artifacts", "created_at", *ROLES))
    require(value["schema_version"] == "wgs.shared-handoff.intent.v1" and value["operation_id"] == operation_id)
    require(value["scope_id"] == source.scope_id and value["source_commit"] in source.producer_commits, "registration_mismatch")
    string(value["execution_id"], 1024); sha(value["request_sha256"]); sha(value["config_sha256"])
    integer(value["publication_sequence"], 1, 10000); timestamp(value["created_at"])
    require(type(value["before_exists"]) is bool and value["mode"] in ("local", "sge", "cce"))
    if value["cloud"] is not None:
        exact(value["cloud"], ("analysis_id", "attempt", "generation"))
        string(value["cloud"]["analysis_id"])
        integer(value["cloud"]["attempt"], 1); integer(value["cloud"]["generation"], 1)
    if value["previous_operation_id"] is None:
        require(value["publication_sequence"] == 1 and value["previous_commit_sha256"] is None)
    else:
        operation_uuid(value["previous_operation_id"]); sha(value["previous_commit_sha256"])
    for role in (*ROLES, "identities"):
        descriptor = value[role]
        exact(descriptor, ("path", "sha256", "byte_size", "row_count") if role in ROLES else ("path", "sha256", "byte_size"))
        require(descriptor["path"] == FILES.get(role, "identities.json"))
        sha(descriptor["sha256"]); integer(descriptor["byte_size"], maximum=MAX_FILE)
        if role in ROLES: integer(descriptor["row_count"])
    require(type(value["artifacts"]) is list and len(value["artifacts"]) <= 1000)
    return value

def validate_marker(raw, intent, intent_raw):
    value = parse(raw)
    exact(value, ("schema_version", "operation_id", "intent_sha256", "pending_after_sha256", "committed_at"))
    require(value["schema_version"] == "wgs.shared-handoff.commit.v1" and value["operation_id"] == intent["operation_id"])
    require(value["intent_sha256"] == digest(intent_raw) and value["pending_after_sha256"] == intent["pending_after"]["sha256"])
    timestamp(value["committed_at"])
    # This authenticated value is a deterministic logical transaction time.
    # Marker presence is still required for completion, but it is never a
    # measured publication/stage completion timestamp.
    require(value["committed_at"] == intent["created_at"])
    return value

def validate_artifacts(tree, base, intent):
    roots = []; manifests = set(); finals = []
    ownership = {"shared": False, "leaves": [], "directories": [], "exclusive": []}
    for artifact in intent["artifacts"]:
        exact(artifact, ("staged_path", "final_path", "manifest_path", "manifest_sha256"))
        staged, final, manifest = (artifact[k] for k in ("staged_path", "final_path", "manifest_path"))
        relative(staged); relative(final); relative(manifest); sha(artifact["manifest_sha256"])
        require(staged.startswith("artifacts/") and manifest.startswith("manifests/"), "unsafe_path")
        require(not any(final == x or final.startswith(x+"/") or x.startswith(final+"/") for x in
                ("prepare/handoffs", "prepare/pending_samples.tsv", "prepare/pending_samples.tsv.lock")), "unsafe_path")
        for previous in roots: require(not (staged == previous or staged.startswith(previous+"/") or previous.startswith(staged+"/")))
        for previous in finals: require(not (final == previous or final.startswith(previous+"/") or previous.startswith(final+"/")))
        require(manifest not in manifests); roots.append(staged); finals.append(final); manifests.add(manifest)
        raw = tree.read(base+"/"+manifest); require(digest(raw) == artifact["manifest_sha256"])
        value = parse(raw); exact(value, ("schema_version", "operation_id", "entries"))
        require(value["schema_version"] == "wgs.shared-handoff.artifact-manifest.v1" and value["operation_id"] == intent["operation_id"])
        entries = value["entries"]; require(type(entries) is list and len(entries) <= MAX_ROWS)
        expected = {}; paths = []
        for entry in entries:
            require(type(entry) is dict and entry.get("type") in ("directory", "file", "symlink"))
            kind = entry["type"]
            exact(entry, {"directory":("type","path","mode"), "file":("type","path","mode","byte_size","sha256"), "symlink":("type","path","target")}[kind])
            relative(entry["path"]); path = entry["path"]; paths.append(path)
            require(path not in expected); expected[path] = entry
            if kind != "symlink":
                require(entry["mode"] in (("0755","2775") if kind=="directory" else ("0644","0664","0755","0775")))
            if kind == "file": sha(entry["sha256"]); integer(entry["byte_size"], maximum=MAX_FILE)
            if kind == "symlink":
                require(type(entry["target"]) is str and 0 < len(entry["target"]) <= 4096 and not any(c in entry["target"] for c in "\x00\r\n"))
        require(paths == sorted(paths))
        if final == "sampleinfo":
            ownership["shared"] = True
            for entry in entries:
                full = final + "/" + entry["path"]
                ownership["directories" if entry["type"] == "directory" else "leaves"].append(full)
        else:
            ownership["exclusive"].append(final)
        actual = set(); todo = [""]
        while todo:
            prefix = todo.pop()
            for name, info in tree.children(base+"/"+staged+("/"+prefix if prefix else "")):
                path = prefix+"/"+name if prefix else name
                require(path in expected); entry=expected[path]; actual.add(path)
                leaf=base+"/"+staged+"/"+path
                if entry["type"] == "directory":
                    require(stat.S_ISDIR(info.st_mode)); todo.append(path)
                elif entry["type"] == "file":
                    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1)
                    data=tree.read(leaf); require(len(data)==entry["byte_size"] and digest(data)==entry["sha256"])
                else:
                    require(stat.S_ISLNK(info.st_mode))
                    with tree.parent(leaf) as (fd, name): require(os.readlink(name,dir_fd=fd)==entry["target"])
                if entry["type"] != "symlink": require(f"{stat.S_IMODE(info.st_mode):04o}" == entry["mode"])
        require(actual == set(expected))
    return ownership

class _PathIndex:
    """Component trie with work bounded by total canonical path components."""
    def __init__(self):
        self.root = {"children": {}, "terminal": False, "count": 0}

    def has_ancestor(self, path):
        node = self.root
        for part in path.split("/"):
            node = node["children"].get(part)
            if node is None:
                return False
            if node["terminal"]:
                return True
        return False

    def overlaps(self, path):
        node = self.root
        for part in path.split("/"):
            node = node["children"].get(part)
            if node is None:
                return False
            if node["terminal"]:
                return True
        return node["count"] > 0

    def has_descendant_or_equal(self, path):
        node = self.root
        for part in path.split("/"):
            node = node["children"].get(part)
            if node is None:
                return False
        return node["count"] > 0

    def add(self, path):
        node = self.root
        node["count"] += 1
        for part in path.split("/"):
            node = node["children"].setdefault(
                part, {"children": {}, "terminal": False, "count": 0})
            node["count"] += 1
        node["terminal"] = True

def validate_artifact_ownership(operations):
    leaves = _PathIndex()
    directories = _PathIndex()
    exclusive = _PathIndex()
    shared_used = False
    for operation in operations:
        ownership = operation.pop("_artifact_ownership")
        if ownership["shared"]:
            require(not exclusive.overlaps("sampleinfo"), "artifact_ownership_conflict")
            for directory in ownership["directories"]:
                require(not leaves.has_ancestor(directory), "artifact_ownership_conflict")
            for leaf in ownership["leaves"]:
                require(not leaves.overlaps(leaf), "artifact_ownership_conflict")
                require(not directories.has_descendant_or_equal(leaf),
                        "artifact_ownership_conflict")
            shared_used = True
        for root in ownership["exclusive"]:
            require(not exclusive.overlaps(root), "artifact_ownership_conflict")
            require(not (shared_used and (root == "sampleinfo" or root.startswith("sampleinfo/")
                         or "sampleinfo".startswith(root + "/"))), "artifact_ownership_conflict")
        for leaf in ownership["leaves"]:
            leaves.add(leaf)
        for directory in ownership["directories"]:
            directories.add(directory)
        for root in ownership["exclusive"]:
            exclusive.add(root)

def identity(value):
    require(type(value) is list and len(value) == 4 and all(type(x) is str and len(x) <= 2048 for x in value))
    return tuple(value)

def safe_row(entry, role):
    exact(entry, ("row_number", "identity", "safe")); ident=identity(entry["identity"])
    safe=entry["safe"]; exact(safe,SAFE_FIELDS)
    for key in SAFE_FIELDS - {"reason_codes", "reason_message", "order_number_masked"}:
        string(safe[key], nullable=key != "sample_id")
    require(safe["reason_message"] is None and safe["order_number_masked"] is None)
    require((safe["sample_id"], safe["sequencing_batch"] or "", safe["data_id"] or "") == ident[1:])
    require(safe["target_analysis_batch"] == safe["analysis_batch"])
    codes=safe["reason_codes"]
    require(type(codes) is list and all(type(c) is str and c in REASONS for c in codes) and codes==sorted(set(codes)))
    require(safe["reason_code"] == (None if not codes else codes[0] if len(codes)==1 else "pending_multiple_reasons"))
    if role in ("pending_before", "pending_after", "pending_current"): require(bool(codes))
    if role == "selected": require(not codes)
    return ident, safe

def project_operation(tree, base, intent, intent_raw, marker_raw, source, secret):
    table_bytes={}
    for role in (*ROLES, "identities"):
        desc=intent[role]; raw=tree.read(base+"/"+desc["path"])
        require(len(raw)==desc["byte_size"] and digest(raw)==desc["sha256"])
        if role in ROLES:
            try:
                rows=list(csv.reader(io.StringIO(raw.decode("utf-8")), delimiter="\t", strict=True))
            except (UnicodeError,csv.Error): raise SourceError() from None
            require(bool(rows) and len(rows)-1 == desc["row_count"] and len(rows[0]) == len(set(rows[0])) and
                    all(len(row)==len(rows[0]) for row in rows))
            table_bytes[role]=raw
        else: indexes=parse(raw)
    exact(indexes, ("schema_version", "operation_id", "tables", "selected", "pending", "consumed"))
    require(indexes["schema_version"]=="wgs.shared-handoff.identities.v1" and indexes["operation_id"]==intent["operation_id"])
    exact(indexes["tables"], ROLES)
    private={}; safe_tables={}
    for role in ROLES:
        table=indexes["tables"][role]; exact(table,("tsv_sha256","row_count","rows"))
        integer(table["row_count"])
        require(table["tsv_sha256"]==intent[role]["sha256"] and table["row_count"]==intent[role]["row_count"])
        require(type(table["rows"]) is list and len(table["rows"])==table["row_count"])
        private[role]=[]; safe_tables[role]=[]
        for number,entry in enumerate(table["rows"],1):
            integer(entry["row_number"],1); require(entry["row_number"]==number)
            ident,safe=safe_row(entry,role); private[role].append((ident,safe))
            safe_tables[role].append({"record_key":opaque(secret,source.scope_id,"identity",list(ident)), "row_number":number, **safe})
    # Index once, preserving the first row used for display and the full Counter
    # for multiplicity checks. Provenance pairs retain all duplicate-row values.
    identities = {}; origins = {}; destinations = {}; first_rows = {}; counts = {}
    for role, rows in private.items():
        identities[role] = {ident for ident, _ in rows}
        origins[role] = {(ident, safe["source_analysis_batch"]) for ident, safe in rows}
        destinations[role] = {(ident, safe["analysis_batch"]) for ident, safe in rows}
        counts[role] = Counter(ident for ident, _ in rows)
        first_rows[role] = {}
        for ident, safe in rows:
            first_rows[role].setdefault(ident, safe)
    source_origins = origins["source"] | origins["pending_before"]
    links=[]
    for kind,role in (("selected","selected"),("pending","pending_current"),("consumed","selected")):
        decisions=indexes[kind]; require(type(decisions) is list and len(decisions)<=MAX_ROWS)
        resolved=[]
        for entry in decisions:
            exact(entry,("source_identity","resolved_identity","source_analysis_batch","target_analysis_batch"))
            original=identity(entry["source_identity"]); target=identity(entry["resolved_identity"])
            string(entry["source_analysis_batch"],nullable=True); string(entry["target_analysis_batch"],nullable=True)
            allowed_origins = origins["pending_before"] if kind == "consumed" else source_origins
            require((original, entry["source_analysis_batch"]) in allowed_origins)
            require((target, entry["target_analysis_batch"]) in destinations[role])
            if kind=="consumed": require(original not in identities["pending_after"])
            resolved.append(target)
            links.append({"kind":kind,"record_key":opaque(secret,source.scope_id,"identity",list(original)),
                          "resolved_key":opaque(secret,source.scope_id,"identity",list(target)),
                          "origin_batch":entry["source_analysis_batch"],"destination_batch":entry["target_analysis_batch"],
                          **{key:first_rows[role][target][key] for key in ("sample_id","family_id","reason_codes")}})
        if kind!="consumed": require(Counter(resolved)==counts[role])
    artifact_ownership = validate_artifacts(tree,base,intent)
    require(tree.read(base+"/COMMITTED.json")==marker_raw, "source_changed")
    marker=parse(marker_raw)
    cloud=intent["cloud"]
    return {"operation_id":intent["operation_id"],"sequence":intent["publication_sequence"],
        "intent_hash":digest(intent_raw),"commit_hash":digest(marker_raw),"pending_hash":intent["pending_after"]["sha256"],
        "before_hash":intent["pending_before"]["sha256"],"previous_operation_id":intent["previous_operation_id"],
        "execution_key":opaque(secret,source.scope_id,"execution",intent["execution_id"]),"request_hash":intent["request_sha256"],
        "mode":intent["mode"],"cloud_key":opaque(secret,source.scope_id,"cloud",cloud["analysis_id"]) if cloud else None,
        "cloud_analysis_id":cloud["analysis_id"] if cloud else None,"attempt":cloud["attempt"] if cloud else None,
        "generation":cloud["generation"] if cloud else None,"producer_commit":intent["source_commit"],
        "logical_transaction_at":marker["committed_at"],"tables":safe_tables,"links":links,
        "_artifact_ownership":artifact_ownership}

def read_source(source, secret):
    """Capture public anchor under SH flock; verify immutable history outside it."""
    opaque(secret,source.scope_id,"check",None)
    tree=None
    try:
        import fcntl
        tree=Tree(source.project_root)
        lock=tree.open("prepare/pending_samples.tsv.lock")
        try:
            try: fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
            except OSError: raise SourceError("locking_unavailable") from None
            protocol="prepare/handoffs/v1"; head_raw=tree.read(protocol+"/HEAD.json"); head=parse(head_raw)
            exact(head,("schema_version","scope_id","publication_sequence","operation_id","intent_sha256","pending_after_sha256"))
            require(head["schema_version"]=="wgs.shared-handoff.head.v1" and head["scope_id"]==source.scope_id)
            integer(head["publication_sequence"],1,10000); operation_uuid(head["operation_id"])
            sha(head["intent_sha256"]); sha(head["pending_after_sha256"])
            inventory={}
            for name,info in tree.children(protocol+"/operations"):
                operation_uuid(name); require(stat.S_ISDIR(info.st_mode),"unsafe_path")
                base=protocol+"/operations/"+name
                has_intent=tree.exists(base+"/intent.json"); has_marker=tree.exists(base+"/COMMITTED.json")
                if not has_intent and not has_marker: continue
                require(has_intent and has_marker,"publication_incomplete")
                marker_raw=tree.read(base+"/COMMITTED.json"); raw=tree.read(base+"/intent.json")
                intent=validate_intent(raw,source,name); validate_marker(marker_raw,intent,raw)
                inventory[name]=(base,intent,raw,marker_raw)
            require(head["operation_id"] in inventory,"publication_incomplete")
            base,intent,raw,marker=inventory[head["operation_id"]]
            require(head["publication_sequence"]==intent["publication_sequence"] and head["intent_sha256"]==digest(raw)
                    and head["pending_after_sha256"]==intent["pending_after"]["sha256"])
            after=tree.read(base+"/pending.after.tsv")
            require(digest(after)==head["pending_after_sha256"] and digest(tree.read("prepare/pending_samples.tsv"))==digest(after),"pending_drift")
            require(tree.read(protocol+"/HEAD.json")==head_raw,"source_changed")
        finally:
            os.close(lock)  # SH lock released before immutable replay and ANY database work.
        chain=[]; cursor=head["operation_id"]; visited=set(); expected=head["publication_sequence"]
        while cursor is not None:
            require(cursor not in visited and cursor in inventory,"chain_invalid"); visited.add(cursor)
            entry=inventory[cursor]; intent=entry[1]; require(intent["publication_sequence"]==expected,"chain_invalid")
            previous=intent["previous_operation_id"]
            if previous is not None:
                require(previous in inventory and digest(inventory[previous][3])==intent["previous_commit_sha256"],"chain_invalid")
                require(intent["before_exists"] and intent["pending_before"]["sha256"]==inventory[previous][1]["pending_after"]["sha256"],"chain_invalid")
            chain.append(entry); cursor=previous; expected-=1
        require(expected==0 and visited==set(inventory),"chain_invalid")
        operations=[project_operation(tree,*entry,source,secret) for entry in reversed(chain)]
        validate_artifact_ownership(operations)
        return {"sequence":head["publication_sequence"],"head_hash":digest(head_raw),"pending_hash":head["pending_after_sha256"],"operations":operations}
    except SourceError: raise
    except FileNotFoundError: raise SourceError("source_missing") from None
    except PermissionError: raise SourceError("source_permission_denied") from None
    except (OSError,ValueError,KeyError,TypeError,ImportError): raise SourceError("source_invalid") from None
    finally:
        if tree: tree.close()
