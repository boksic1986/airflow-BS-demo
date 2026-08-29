import type {IntakeDiscovery} from "../api";

import {compactPipelineName, displayTimeZoneLabel, formatBytes, formatDate} from "../lib/format";
import {intakeDisplay} from "../lib/intake";
import {RunProgressBar} from "./RunProgressBar";
import {StatusBadge} from "./StatusBadge";
import {OperationProjectCell, OperationRuntimeCell} from "./OperationCells";

export function IntakeDiscoveryTable({
  items,
  ariaLabel,
  loading = false,
  error = null,
  emptyMessage = "No intake discovery records yet.",
}: {
  items: IntakeDiscovery[];
  ariaLabel: string;
  loading?: boolean;
  error?: string | null;
  emptyMessage?: string;
}) {
  const wgsScanOnly = items.length > 0 && items.every((item) => item.pipeline === "wgs" && Boolean(item.chip_id));
  return (
    <div className="intake-discovery-surface" aria-busy={loading}>
      {error ? <div className="inline-error" role="alert">{error}</div> : null}
      {loading && items.length === 0 ? <p className="muted panel-loading">Loading intake records...</p> : null}
      {items.length && wgsScanOnly ? (
        <WgsT7DiscoveryTable ariaLabel={ariaLabel} items={items} />
      ) : items.length ? (
        <div className="intake-discovery-table-wrap">
          <table aria-label={ariaLabel} className="intake-discovery-table">
            <thead>
              <tr>
                <th scope="col">Project / Batch</th>
                <th scope="col">Pipeline</th>
                <th scope="col">Status</th>
                <th scope="col">Current stage</th>
                <th scope="col">Progress</th>
                <th scope="col">Samples</th>
                <th scope="col">Runtime / ETA</th>
                <th scope="col">Started</th>
                <th scope="col">Finished</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const display = intakeDisplay(item);
                const hasIntakeError = item.ready_state === "error" || item.submit_state === "error";
                return (
                  <tr key={`${item.pipeline}-${item.root_path}-${item.batch_id}`}>
                    <td className="discovery-batch-cell">
                      <OperationProjectCell analysisId={item.analysis_id} fallbackId={item.batch_id} projectName={item.project_name} sampleCount={item.sample_count || Math.floor((item.file_count ?? 0) / 2) || 0} source="intake" sourceBatchId={item.analysis_id ? item.source_batch_id || item.batch_id : null} submittedBy={item.submitted_by} />
                    </td>
                    <td>{compactPipelineName(item.pipeline)}</td>
                    <td>
                      {item.analysis_id ? <StatusBadge status={item.display_status || item.analysis_status || "submitted"} /> : (
                        <span className={`intake-state-pill ${display.tone}`}>{display.label}</span>
                      )}
                    </td>
                    <td>
                      <div className="current-stage-cell">
                        <strong>{hasIntakeError ? "Intake validation failed" : item.current_stage || discoveryStage(item)}</strong>
                        {hasIntakeError ? (
                          <span className="intake-error-reason" title={item.last_error || undefined}>
                            {item.last_error || "Review the scanner configuration and source files."}
                          </span>
                        ) : (
                          <span>{item.analysis_id ? "Pipeline state" : `${item.file_count} files / ${formatBytes(item.total_bytes)}`}</span>
                        )}
                      </div>
                    </td>
                    <td>
                      <RunProgressBar
                        analysisId={item.analysis_id || item.batch_id}
                        compact
                        progress={{
                          percent: item.progress_percent || 0,
                          label: `${Math.round(item.progress_percent || 0)}%`,
                          currentStep: hasIntakeError ? "Intake validation failed" : item.current_stage || discoveryStage(item),
                          note: item.analysis_id ? "Linked pipeline state" : `${item.file_count} files / ${formatBytes(item.total_bytes)}`,
                          notInAirflow: !item.analysis_id,
                          failedStep: hasIntakeError ? "intake" : undefined,
                        }}
                      />
                    </td>
                    <td>{item.sample_count || Math.floor((item.file_count ?? 0) / 2) || 0} samples</td>
                    <td><OperationRuntimeCell elapsedSeconds={item.elapsed_seconds} estimatedRemainingSeconds={item.estimated_remaining_seconds} status={item.analysis_status || item.submit_state} submitted={Boolean(item.submitted_at)} /></td>
                    <td title={`Displayed in ${displayTimeZoneLabel()}`}>{item.submitted_at ? formatDate(item.submitted_at) : "Not submitted"}</td>
                    <td title={`Displayed in ${displayTimeZoneLabel()}`}>{item.pipeline_finished_at ? formatDate(item.pipeline_finished_at) : item.analysis_id ? "In progress" : "-"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : !loading && !error ? <p className="empty-state">{emptyMessage}</p> : null}
    </div>
  );
}

function WgsT7DiscoveryTable({items, ariaLabel}: {items: IntakeDiscovery[]; ariaLabel: string}) {
  return <div className="intake-discovery-table-wrap"><table aria-label={ariaLabel} className="intake-discovery-table"><thead><tr><th>芯片</th><th>上机批次</th><th>状态</th><th>可分析配对</th><th>排除加测</th><th>异常配对</th><th>最近扫描</th></tr></thead><tbody>{items.map((item) => {
    const display = intakeDisplay(item);
    return <tr key={item.chip_id || item.batch_id}><td>{item.chip_id || item.batch_id}</td><td>{item.sequencing_batch || "-"}</td><td><span className={`intake-state-pill ${display.tone}`}>{display.label}</span>{item.last_error ? <span className="intake-error-reason">{item.last_error}</span> : null}</td><td>{item.eligible_pair_count ?? 0}</td><td>{item.excluded_addon_pair_count ?? 0}</td><td>{item.pair_issue_count ?? 0}</td><td>{formatDate(item.last_seen_at)}</td></tr>;
  })}</tbody></table></div>;
}

function discoveryStage(item: IntakeDiscovery): string {
  if (item.submit_state === "bootstrap") return "Bootstrap protected";
  if (item.ready_state === "ready") return "Stable ready";
  if (item.ready_state === "error" || item.submit_state === "error") return "Discovery error";
  return `Observed · ${item.stable_observation_count || 0}/2 checks`;
}
