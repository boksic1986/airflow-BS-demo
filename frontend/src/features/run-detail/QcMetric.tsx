import type {QcJudgment} from "../../api";
import {StatusBadge} from "../../components/StatusBadge";

export function QcMetric({value, judgment}: {value?: string | number | null; judgment?: QcJudgment}) {
  const status = judgment?.status || "unknown";
  const displayed = judgment?.value ?? value;
  const text = displayed == null || displayed === "" ? "-" : String(displayed);
  return <div className="qc-metric">
    {judgment?.unit === "status" && displayed ? <StatusBadge status={String(displayed)} /> : <span className={`qc-value-${status}`}>{text}{judgment?.value != null && judgment.unit ? ` ${judgment.unit}` : ""}</span>}
    <details><summary>{status}</summary><small>{judgment?.reason || "Judgment provenance unavailable"}</small>{judgment?.threshold ? <pre>{JSON.stringify(judgment.threshold)}</pre> : null}{judgment?.provenance ? <pre>{JSON.stringify(judgment.provenance, null, 2)}</pre> : null}</details>
  </div>;
}
