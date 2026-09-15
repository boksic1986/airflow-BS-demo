import type {QcJudgment} from "../../api";
import {StatusBadge} from "../../components/StatusBadge";

export function QcMetric({value, judgment}: {value?: string | number | null; judgment?: QcJudgment}) {
  const status = judgment?.status || "unknown";
  const displayed = judgment?.value ?? value;
  const text = displayed == null || displayed === "" ? "-" : String(displayed);
  return <div className="qc-metric">
    <span className={`qc-value-${status}`}>{text}{displayed != null && judgment?.unit && judgment.unit !== "status" ? ` ${judgment.unit}` : ""}</span>
    <StatusBadge status={status} size="sm" />
  </div>;
}
