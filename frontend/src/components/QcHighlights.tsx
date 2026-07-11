import type {QcHighlight} from "../api";

const labels: Record<string, string> = {
  clean_read_pairs: "Clean pairs",
  mapped_reads: "Mapped reads",
  mapping_rate: "Map rate",
  estimated_depth_x: "Depth",
  cnv_qc_decision: "CNV QC",
  read_count: "Reads",
  Q30: "Q30",
  unique_mapping_rate: "Unique map",
  fetal_fraction: "Fetal fraction",
};

export function QcHighlights({items}: {items?: QcHighlight[] | null}) {
  if (!items?.length) return <span className="muted">QC metrics pending</span>;
  return (
    <div className="qc-highlight-strip">
      {items.map((item) => (
        <span className={`qc-highlight qc-${item.status || "unknown"}`} key={item.key}>
          <small>{labels[item.key] || item.key}</small>
          <strong>{formatQcValue(item)}</strong>
        </span>
      ))}
    </div>
  );
}

function formatQcValue(item: QcHighlight): string {
  if (item.value == null || item.value === "") return "not captured";
  if (typeof item.value === "string") return item.value;
  if (item.unit === "fraction") return `${(item.value * 100).toFixed(1)}%`;
  if (item.unit === "percent") return `${item.value.toFixed(1)}%`;
  if (item.unit === "x") return `${item.value.toFixed(2)}x`;
  if (item.unit === "reads") return compactNumber(item.value);
  return Number.isInteger(item.value) ? String(item.value) : item.value.toFixed(2);
}

function compactNumber(value: number): string {
  if (Math.abs(value) >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return String(Math.round(value));
}
