import type {IntakeDiscovery, IntakeScannerStateResponse, IntakeView} from "../../api";

import {IntakeDiscoveryTable} from "../../components/IntakeDiscoveryTable";

export function IntakeScannerPanel({scanner, items, total, limit, offset, loading, error, view, onViewChange, onPageChange}: {
  scanner?: IntakeScannerStateResponse | null;
  items: IntakeDiscovery[];
  total: number;
  limit: number;
  offset: number;
  loading: boolean;
  error: string | null;
  view: Exclude<IntakeView, "all">;
  onViewChange: (view: Exclude<IntakeView, "all">) => void;
  onPageChange: (offset: number) => void;
}) {
  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + limit, total);
  const intervalMinutes = Math.max(1, Math.round((scanner?.schedule_seconds ?? 600) / 60));
  return (
    <section className="panel intake-scanner-panel" aria-busy={loading}>
      <div className="section-heading split">
        <div>
          <h2>T7自动扫描</h2>
          <p title="扫描记录不会创建分析任务。">每{intervalMinutes}分钟检查 BarcodeStat.txt；自动分析关闭</p>
          {scanner ? <p className="muted">
            本轮扫描 {scanner.last_scanned_directory_count ?? 0} 个目录
            {scanner.last_scan_at ? `；最近扫描 ${new Date(scanner.last_scan_at).toLocaleString()}` : "；尚未建立扫描基线"}
          </p> : null}
          {scanner?.last_error ? <p className="error-text" role="alert">扫描错误：{scanner.last_error}</p> : null}
        </div>
        <div className="tracker-filters" aria-label="Intake scanner views">
          <button className={view === "pending" ? "active" : ""} type="button" onClick={() => onViewChange("pending")}>Pending &amp; errors</button>
          <button className={view === "history" ? "active" : ""} type="button" onClick={() => onViewChange("history")}>History</button>
        </div>
      </div>
      <IntakeDiscoveryTable
        ariaLabel="Intake discovery records"
        error={error ? `Intake unavailable: ${error}` : null}
        items={items}
        loading={loading}
      />
      <div className="pagination-controls" aria-label="Intake scanner pagination">
        <span>{pageStart}-{pageEnd} of {total}</span>
        <div>
          <button aria-label="Previous intake page" disabled={offset === 0 || loading} type="button" onClick={() => onPageChange(Math.max(0, offset - limit))}>Previous intake</button>
          <button aria-label="Next intake page" disabled={offset + limit >= total || loading} type="button" onClick={() => onPageChange(offset + limit)}>Next intake</button>
        </div>
      </div>
    </section>
  );
}
