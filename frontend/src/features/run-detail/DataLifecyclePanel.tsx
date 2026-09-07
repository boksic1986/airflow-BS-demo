import type {WgsLifecycle, WgsLifecycleStatus} from "../../api";

import {formatDate} from "../../lib/format";
import {getStatusMeta} from "../../lib/status";


const items: Array<{
  key: keyof WgsLifecycle;
  title: string;
  successLabel: string;
  runningLabel: string;
}> = [
  {key: "workflow", title: "Workflow", successLabel: "Workflow success", runningLabel: "Workflow running"},
  {key: "cloud_release", title: "Cloud release", successLabel: "SFS released", runningLabel: "SFS release running"},
  {key: "raw_fastq_backup", title: "Raw FASTQ backup", successLabel: "FASTQ backed up", runningLabel: "FASTQ backup running"},
  {key: "downstream_release", title: "Result delivery", successLabel: "Delivered", runningLabel: "Delivery running"},
];


export function DataLifecyclePanel({lifecycle}: {lifecycle: WgsLifecycle}) {
  const postRunFailed = [
    lifecycle.cloud_release,
    lifecycle.raw_fastq_backup,
    lifecycle.downstream_release,
  ].some((item) => item.status === "failed");
  return (
    <section className="panel data-lifecycle-panel" aria-labelledby="data-lifecycle-title">
      <div className="section-heading">
        <h2 id="data-lifecycle-title">Data lifecycle</h2>
        <p>Workflow completion and post-run data handling are tracked independently.</p>
      </div>
      <div className="data-lifecycle-grid">
        {items.map((item) => (
          <LifecycleItem
            key={item.key}
            item={lifecycle[item.key]}
            runningLabel={item.runningLabel}
            successLabel={item.successLabel}
            title={item.title}
          />
        ))}
      </div>
      {postRunFailed && lifecycle.workflow.status === "success" ? (
        <div className="inline-warning" role="status">Post-run action failed; workflow results remain successful.</div>
      ) : null}
    </section>
  );
}


export function LifecycleStatusBadge({
  item,
  successLabel,
  runningLabel,
}: {
  item: WgsLifecycleStatus;
  successLabel: string;
  runningLabel: string;
}) {
  const meta = getStatusMeta(item.status);
  const Icon = meta.Icon;
  const label = item.status === "success"
    ? successLabel
    : item.status === "running"
      ? runningLabel
      : meta.label;
  return (
    <span className={`status-badge status-${meta.tone} status-md lifecycle-status-${item.status}`} title={label}>
      <Icon aria-hidden="true" size={14} />
      <span>{label}</span>
    </span>
  );
}


function LifecycleItem({
  title,
  item,
  successLabel,
  runningLabel,
}: {
  title: string;
  item: WgsLifecycleStatus;
  successLabel: string;
  runningLabel: string;
}) {
  return (
    <article className="data-lifecycle-item">
      <div className="data-lifecycle-item-heading">
        <h3>{title}</h3>
        <LifecycleStatusBadge item={item} successLabel={successLabel} runningLabel={runningLabel} />
      </div>
      <dl>
        <div><dt>Updated</dt><dd>{item.updated_at ? formatDate(item.updated_at) : "Not recorded"}</dd></div>
        <div><dt>Operator</dt><dd>{item.updated_by || "-"}</dd></div>
        <div><dt>Note</dt><dd>{item.message || "-"}</dd></div>
      </dl>
    </article>
  );
}
