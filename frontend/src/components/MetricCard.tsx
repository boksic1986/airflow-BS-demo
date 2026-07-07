import {StatusBadge} from "./StatusBadge";

export function MetricCard({
  title,
  value,
  unit,
  trend,
  description,
  status,
}: {
  title: string;
  value: string | number;
  unit?: string;
  trend?: string;
  description?: string;
  status?: string;
}) {
  return (
    <article className="metric-card">
      <div className="metric-card-header">
        <span>{title}</span>
        {status ? <StatusBadge status={status} size="sm" /> : null}
      </div>
      <div className="metric-value">
        <strong>{value}</strong>
        {unit ? <span>{unit}</span> : null}
      </div>
      {trend ? <p className="metric-trend">{trend}</p> : null}
      {description ? <p className="muted">{description}</p> : null}
    </article>
  );
}
