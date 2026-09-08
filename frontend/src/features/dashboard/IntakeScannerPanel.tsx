import type {IntakeDiscovery, IntakeScannerStateResponse} from "../../api";

import {IntakeDiscoveryTable} from "../../components/IntakeDiscoveryTable";

export function IntakeScannerPanel({scanner, items, total, limit, offset, loading, error, onPageChange}: {
  scanner?: IntakeScannerStateResponse | null;
  items: IntakeDiscovery[];
  total: number;
  limit: number;
  offset: number;
  loading: boolean;
  error: string | null;
  onPageChange: (offset: number) => void;
}) {
  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + limit, total);
  const intervalMinutes = Math.max(1, Math.round((scanner?.schedule_seconds ?? 600) / 60));
  return (
    <section className="panel intake-scanner-panel" aria-busy={loading}>
      <div className="section-heading split">
        <div>
          <h2>WGS Intake Queue</h2>
          <p>仅显示可提交、失败或需要人工复核的测序批次</p>
          {scanner ? <div className="intake-scanner-metadata" aria-label="T7 scan status">
            <span>扫描周期 {intervalMinutes}分钟</span>
            <span>本轮检查 {scanner.last_scanned_directory_count ?? 0} 个批次目录</span>
            <span>{scanner.last_scan_at ? `最近更新 ${new Date(scanner.last_scan_at).toLocaleString()}` : "尚未建立扫描基线"}</span>
          </div> : null}
          {scanner?.last_error ? <p className="error-text" role="alert">扫描错误：{scanner.last_error}</p> : null}
        </div>
      </div>
      <IntakeDiscoveryTable
        ariaLabel="Intake discovery records"
        error={error ? `Intake unavailable: ${error}` : null}
        items={items}
        loading={loading}
        emptyMessage="No WGS batches currently require attention."
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
