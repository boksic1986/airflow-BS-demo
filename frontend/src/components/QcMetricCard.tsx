import type {QcMetric} from "../api";

import {StatusBadge} from "./StatusBadge";

export function QcMetricCard({metric}: {metric: QcMetric}) {
  return (
    <article className="qc-metric-card">
      <div>
        <strong>{metric.metric_name}</strong>
        <span>{metric.sample_id || "project"}</span>
      </div>
      <div className="metric-value compact">
        <strong>{metric.metric_value ?? metric.metric_numeric ?? "not set"}</strong>
      </div>
      <span className="muted">{metric.threshold || "no threshold"}</span>
      <StatusBadge status={metric.status} />
    </article>
  );
}
