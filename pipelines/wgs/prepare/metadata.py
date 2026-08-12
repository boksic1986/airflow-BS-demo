from __future__ import annotations

import copy
from collections import defaultdict
from typing import Any, Callable, Dict, Iterable, List, Sequence


WGS_ITEM_NAMES = {
    "Q0045": "全基因组测序（单先证者）",
    "Q0046": "全基因组测序（家系）",
    "Q0056": "全基因组测序（双人家系）",
    "E0040": "儿童快速全基因组基因检测",
    "Q0061": "快速全基因组基因检测",
    "C0017": "快速全基因组测序（产前）",
    "Q0202": "罕与光-全基因组基因检测（家系）",
    "Q0203": "博爱-全基因组测序（单先证者）",
    "Q0204": "博爱-全基因组测序（双人）",
    "Q0205": "博爱-全基因组测序（家系）",
    "Q0206": "博爱-快速全基因组测序（家系）",
    "Q2045": "科研-全基因组测序（单先证者）",
    "Q2046": "科研-全基因组测序（家系）",
    "C2017": "快速全基因组测序（产前）（协和课题）",
    "C0018": "极速全基因组测序（产前）",
    "Q0079": "罕见病项目全基因组测序检测（先证者）",
    "Q0080": "罕见病项目全基因组测序检测（双人家系）",
    "Q0081": "罕见病项目全基因组测序检测（三人家系）",
    "Q0082": "罕见病项目全基因组测序检测（多人家系）",
    "C0517": "快速全基因组测序（产前）",
    "Q0545": "全基因组测序（单先证者）",
    "Q0546": "全基因组测序（家系）",
    "Q0556": "全基因组测序（双人家系）",
    "Q0561": "快速全基因组测序（家系）",
}


def first_nonempty(*values: Any) -> str:
    for value in values:
        text = "" if value is None else str(value).strip()
        if text not in {"", "nan", "None"}:
            return text
    return ""


def record_sample_id(row: Dict[str, Any]) -> str:
    return first_nonempty(row.get("originalID"), row.get("sampleID"), row.get("sampleNo"))


def record_order_key(row: Dict[str, Any]) -> str:
    return first_nonempty(row.get("_order_key"), row.get("analysisTaskId"), row.get("orderCode"))


def _dedupe(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    seen = set()
    for row in rows:
        key = (
            record_sample_id(row),
            record_order_key(row),
            first_nonempty(row.get("projectId")),
            first_nonempty(row.get("taskSampleId")),
        )
        if key not in seen:
            output.append(row)
            seen.add(key)
    return output


class MongoMetadataProvider:
    source_label = "MongoDB"

    def __init__(self, config: Dict[str, Any], test: bool = False, collection: Any = None):
        self.config = config
        self.test = test
        self._collection = collection
        self.active_states = {str(value) for value in config.get("active_project_states", [1, 2])}

    @property
    def collection(self):
        if self._collection is None:
            from pymongo import MongoClient

            host = self.config.get("test_host") if self.test else self.config.get("host")
            port = self.config.get("test_port") if self.test else self.config.get("port")
            client = MongoClient(
                host,
                int(port),
                username=self.config.get("username"),
                password=self.config.get("password"),
                authSource=self.config.get("auth_source", "admin"),
                authMechanism=self.config.get("auth_mechanism", "SCRAM-SHA-1"),
                serverSelectionTimeoutMS=10000,
            )
            client.admin.command("ping")
            self._collection = client[self.config.get("database", "passport")][self.config.get("collection", "inheritance")]
        return self._collection

    def _active_wgs(self, row: Dict[str, Any]) -> bool:
        return str(row.get("projectState", "")).strip() in self.active_states and str(row.get("itemCode", "")) in WGS_ITEM_NAMES

    def _latest_sample_details(self, sample_id: str, item_code: str) -> Dict[str, Any]:
        rows: List[Dict[str, Any]] = []
        for field in ("originalID", "sampleID"):
            rows.extend(self.collection.find({field: sample_id, "itemCode": item_code}))
        active = [dict(row) for row in rows if self._active_wgs(row)]
        if not active:
            return {}
        active.sort(key=lambda row: first_nonempty(row.get("expectedReportDate")), reverse=True)
        return active[0]

    def _prepare(self, rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        prepared: List[Dict[str, Any]] = []
        for raw in rows:
            row = {key: value for key, value in dict(raw).items() if key != "_id"}
            if not self._active_wgs(row):
                continue
            sample_id = record_sample_id(row)
            order_code = first_nonempty(row.get("orderCode"))
            if not sample_id or not order_code:
                continue
            row["originalID"] = sample_id
            row["_order_key"] = order_code
            row.setdefault("itemName", WGS_ITEM_NAMES.get(str(row.get("itemCode", "")), ""))
            if any(first_nonempty(row.get(field)) in {"", "."} for field in ("mainkeyword", "mainkeywordEN", "analysenote")):
                details = self._latest_sample_details(sample_id, str(row.get("itemCode", "")))
                for field in ("mainkeyword", "mainkeywordEN", "analysenote"):
                    if first_nonempty(row.get(field)) in {"", "."} and first_nonempty(details.get(field)):
                        row[field] = details[field]
            row.setdefault("mainkeyword", ".")
            row.setdefault("mainkeywordEN", ".")
            row.setdefault("analysenote", ".")
            prepared.append(row)
        return _dedupe(prepared)

    def records_for_sample(self, sample_id: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for field in ("originalID", "sampleID"):
            rows.extend(self.collection.find({field: sample_id}))
        return self._prepare(rows)

    def records_for_order(self, order_key: str) -> List[Dict[str, Any]]:
        return self._prepare(self.collection.find({"orderCode": order_key}))

    def enrich(self, rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [copy.deepcopy(row) for row in rows]


class HttpMetadataProvider:
    source_label = "HTTP"
    FIELD_MAP = {
        "relationShip": "relationship",
        "sampleState": "projectState",
        "orderId": "orderCode",
        "sampleNo": "originalID",
        "patientName": "username",
        "barCode": "orderBarCode",
        "isSick": "issick",
        "ldtProjectId": "projectId",
        "sex": "gender",
        "birthday": "bornDate",
        "mainKeyWord": "mainkeyword",
        "mainKeyWordEn": "mainkeywordEN",
        "analysisAgain": "analyseAgain",
        "hospitalNo": "healthNum",
    }

    def __init__(
        self,
        config: Dict[str, Any],
        test: bool = False,
        request_func: Callable[[dict, str], Any] | None = None,
    ):
        self.url = config.get("test_url") if test else config.get("url")
        self.stop_states = {str(value).strip() for value in config.get("stop_states", ["0", "STOP", "终止"])}
        self.request_func = request_func or self._default_request
        self.sample_rows: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.order_rows: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.loaded_samples = set()
        self.loaded_orders = set()

    @staticmethod
    def _default_request(data: dict, url: str):
        from .make_requests import make_requests

        return make_requests(data=data, url=url)

    def _request(self, data: dict) -> List[Dict[str, Any]]:
        response = self.request_func(data, self.url)
        if getattr(response, "status_code", None) != 200:
            raise RuntimeError(f"HTTP sample info request failed: {getattr(response, 'status_code', None)}")
        payload = response.json()
        rows = payload.get("data", [])
        if not isinstance(rows, list):
            raise RuntimeError("HTTP sample info response data is not a list")
        return [self._normalize(row) for row in rows]

    def _normalize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        row = dict(raw)
        for source, target in self.FIELD_MAP.items():
            if source in row and not first_nonempty(row.get(target)):
                row[target] = row.get(source)
        row["originalID"] = record_sample_id(row)
        row["_order_key"] = first_nonempty(row.get("analysisTaskId"), row.get("orderCode"))
        row.setdefault("itemName", WGS_ITEM_NAMES.get(str(row.get("itemCode", "")), ""))
        return row

    def _active_wgs(self, row: Dict[str, Any]) -> bool:
        state = str(row.get("projectState", "")).strip()
        return state not in self.stop_states and str(row.get("itemCode", "")) in WGS_ITEM_NAMES

    def _ingest(self, rows: Iterable[Dict[str, Any]]) -> None:
        for row in rows:
            if not self._active_wgs(row):
                continue
            sample_id = record_sample_id(row)
            order_key = record_order_key(row)
            if sample_id and not any(self._same(row, old) for old in self.sample_rows[sample_id]):
                self.sample_rows[sample_id].append(row)
            if order_key and not any(self._same(row, old) for old in self.order_rows[order_key]):
                self.order_rows[order_key].append(row)

    @staticmethod
    def _same(left: Dict[str, Any], right: Dict[str, Any]) -> bool:
        return (
            record_sample_id(left) == record_sample_id(right)
            and record_order_key(left) == record_order_key(right)
            and first_nonempty(left.get("taskSampleId")) == first_nonempty(right.get("taskSampleId"))
        )

    def preload_samples(self, sample_ids: Sequence[str]) -> None:
        ids = [sample_id for sample_id in sample_ids if sample_id and sample_id not in self.loaded_samples]
        if not ids:
            return
        rows = self._request({"sampleNoList": ids})
        self._ingest(rows)
        self.loaded_samples.update(ids)
        task_ids = sorted({record_order_key(row) for row in rows if record_order_key(row)})
        family_codes = sorted({first_nonempty(row.get("familyCode")) for row in rows if first_nonempty(row.get("familyCode"))})
        if task_ids or family_codes:
            family_rows = self._request({"analysisTaskIdList": task_ids, "familyCodeList": family_codes})
            self._ingest(family_rows)
            self.loaded_orders.update(task_ids)

    def records_for_sample(self, sample_id: str) -> List[Dict[str, Any]]:
        self.preload_samples([sample_id])
        return [copy.deepcopy(row) for row in self.sample_rows.get(sample_id, [])]

    def records_for_order(self, order_key: str) -> List[Dict[str, Any]]:
        if order_key not in self.loaded_orders:
            self._ingest(self._request({"analysisTaskIdList": [order_key], "familyCodeList": []}))
            self.loaded_orders.add(order_key)
        return [copy.deepcopy(row) for row in self.order_rows.get(order_key, [])]

    def enrich(self, rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [copy.deepcopy(row) for row in rows]


class HybridMetadataProvider:
    source_label = "MongoDB+HTTP"

    def __init__(self, mongo: MongoMetadataProvider, http: HttpMetadataProvider):
        self.mongo = mongo
        self.http = http

    def records_for_sample(self, sample_id: str) -> List[Dict[str, Any]]:
        return self.mongo.records_for_sample(sample_id)

    def records_for_order(self, order_key: str) -> List[Dict[str, Any]]:
        return self.mongo.records_for_order(order_key)

    def enrich(self, rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sample_ids = sorted({record_sample_id(row) for row in rows if record_sample_id(row)})
        self.http.preload_samples(sample_ids)
        output: List[Dict[str, Any]] = []
        missing: List[str] = []
        for raw in rows:
            row = copy.deepcopy(raw)
            sample_id = record_sample_id(row)
            candidates = self.http.sample_rows.get(sample_id, [])
            order_code = first_nonempty(row.get("orderCode"))
            matched = [candidate for candidate in candidates if first_nonempty(candidate.get("outsideOrderId")) == order_code]
            if len(matched) != 1:
                report_date = first_nonempty(row.get("expectedReportDate"))
                date_matches = [candidate for candidate in candidates if first_nonempty(candidate.get("expectedReportDate")) == report_date]
                matched = date_matches if len(date_matches) == 1 else matched
            if len(matched) == 1:
                row["analysisTaskId"] = first_nonempty(matched[0].get("analysisTaskId"))
                row["taskSampleId"] = first_nonempty(matched[0].get("taskSampleId"))
            else:
                row["analysisTaskId"] = ""
                row["taskSampleId"] = ""
                missing.append(f"{sample_id}/{order_code}")
            output.append(row)
        if missing:
            print("提示：以下样本/订单未能从 HTTP 唯一匹配 analysisTaskId、taskSampleId：" + ",".join(sorted(set(missing))))
        return output


def build_metadata_provider(
    prepare_config: Dict[str, Any],
    source: str,
    test: bool = False,
    mongo_collection: Any = None,
    request_func: Callable[[dict, str], Any] | None = None,
):
    metadata_config = prepare_config["metadata"]
    http = HttpMetadataProvider(metadata_config["http"], test=test, request_func=request_func)
    if source == "http":
        return http
    mongo = MongoMetadataProvider(metadata_config["mongo"], test=test, collection=mongo_collection)
    return HybridMetadataProvider(mongo, http)
