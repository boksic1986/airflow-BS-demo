import {ChevronDown, ChevronRight, RefreshCw} from "lucide-react";
import {useCallback, useEffect, useState} from "react";

import {getTransferFiles} from "../../api";
import type {RunDetail, WgsTransfer, WgsTransferFile} from "../../api";
import {StatusBadge} from "../../components/StatusBadge";
import {errorMessage} from "../../lib/errors";
import {formatBytes, formatDate, formatSecondsDuration} from "../../lib/format";

const PAGE_SIZE = 50;

export function WgsTransfersTab({detail, transfers}: {detail: RunDetail; transfers: WgsTransfer[]}) {
  return <div className="transfer-list">{transfers.map((transfer) => (
    <TransferCard detail={detail} transfer={transfer} key={transfer.transfer_id || `${transfer.source}-${transfer.destination}`} />
  ))}{transfers.length === 0 ? <p className="empty-state">No transfers returned.</p> : null}</div>;
}

function TransferCard({detail, transfer}: {detail: RunDetail; transfer: WgsTransfer}) {
  const hasDetail = transfer.progress_detail_available === true;
  const title = transfer.direction === "download" ? "Results download" : "FASTQ upload";
  const [expanded, setExpanded] = useState(false);
  return <section className="transfer-card">
    <div className="section-heading">
      <div><h3>{title}</h3><p>Batch {String(detail.params?.sequencing_batch || detail.params?.analysis_batch || "-")} · Attempt {transfer.attempt ?? 1}{transfer.progress_basis === "legacy_estimate" ? " · Legacy estimate" : ""}</p></div>
      <StatusBadge status={transfer.status || "unknown"} size="lg" />
    </div>
    {hasDetail ? <>
      <progress className="transfer-progress" max={100} value={transfer.progress_percent ?? 0} aria-label={`${title} progress`} />
      <div className="definition-grid"><div><dt>Progress</dt><dd>{transfer.progress_percent ?? 0}% / {formatBytes(transfer.bytes_transferred)} of {formatBytes(transfer.bytes_total)}</dd></div><div><dt>Speed</dt><dd>{formatBytes(transfer.speed_bps)}/s</dd></div><div><dt>ETA</dt><dd>{transfer.eta_seconds == null ? "-" : formatSecondsDuration(transfer.eta_seconds)}</dd></div><div><dt>Files</dt><dd>{transfer.files_completed ?? "-"} / {transfer.files_total ?? "-"}</dd></div><div><dt>Current file</dt><dd className="path-text">{transfer.current_file || "-"}</dd></div><div><dt>Heartbeat</dt><dd>{formatDate(transfer.heartbeat_at)}</dd></div></div>
      {transfer.transfer_id ? <button className="button ghost transfer-files-toggle" type="button" aria-expanded={expanded} onClick={() => setExpanded((value) => !value)}>
        {expanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />} File progress
      </button> : null}
      {expanded && transfer.transfer_id ? <TransferFiles transferId={transfer.transfer_id} /> : null}
    </> : <div className="transfer-phase-status">
      <p>Stage status is available, but this legacy transfer has no reliable byte or file progress.</p>
      <div className="definition-grid"><div><dt>Stage message</dt><dd>{transfer.message || "Waiting for the next stage status."}</dd></div><div><dt>Heartbeat</dt><dd>{formatDate(transfer.heartbeat_at)}</dd></div></div>
    </div>}
    {transfer.error_message ? <div className="inline-error" role="alert">{transfer.error_message}</div> : null}
  </section>;
}

function TransferFiles({transferId}: {transferId: string}) {
  const [items, setItems] = useState<WgsTransferFile[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getTransferFiles(transferId, {limit: PAGE_SIZE, offset});
      setItems(result.items);
      setTotal(result.total);
    } catch (loadError) {
      setError(errorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [offset, transferId]);

  useEffect(() => { void load(); }, [load]);

  if (loading) return <p className="muted">Loading file progress...</p>;
  if (error) return <div className="inline-error" role="alert">File progress unavailable: {error} <button className="button ghost" type="button" onClick={() => void load()}><RefreshCw size={14} />Retry</button></div>;
  return <div className="transfer-files">
    <div className="table-wrap"><table className="data-table compact"><thead><tr><th>File</th><th>Status</th><th>Progress</th><th>Speed</th><th>Checksum</th></tr></thead><tbody>
      {items.map((item) => <tr key={item.file_key}><td><strong>{item.display_name}</strong>{item.error_message ? <small className="cell-error">{item.error_message}</small> : null}</td><td><StatusBadge status={item.status} /></td><td>{item.progress_percent.toFixed(1)}% · {formatBytes(item.bytes_transferred)} / {formatBytes(item.bytes_total)}</td><td>{item.speed_bps ? `${formatBytes(item.speed_bps)}/s` : "-"}</td><td>{item.checksum_status || "pending"}</td></tr>)}
      {items.length === 0 ? <tr><td className="empty-cell" colSpan={5}>No per-file progress has been imported yet.</td></tr> : null}
    </tbody></table></div>
    <div className="pagination-row"><span>{total ? `${offset + 1}-${Math.min(offset + PAGE_SIZE, total)} of ${total}` : "0 files"}</span><div><button className="button ghost" type="button" disabled={offset === 0} onClick={() => setOffset((value) => Math.max(0, value - PAGE_SIZE))}>Previous</button><button className="button ghost" type="button" disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset((value) => value + PAGE_SIZE)}>Next</button></div></div>
  </div>;
}
