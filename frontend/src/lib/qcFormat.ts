import type {QcMetric} from "../api";

const countMetrics = new Set([
  "clean_read_pairs",
  "fastq_reads",
  "mapped_fragments",
  "mapped_reads",
  "read_count",
  "read_pairs",
  "total_counts",
  "total_reads",
]);

const percentagePointMetrics = new Set([
  "pcr_duplication_rate",
  "unique_mapping_rate",
]);

export function formatQcMetricValue(metric: QcMetric): string {
  const raw = metric.metric_value ?? metric.metric_numeric;
  if (raw === null || raw === undefined || raw === "") return "-";

  const numeric = metric.metric_numeric ?? parseMetricNumber(raw);
  if (numeric === null) return String(raw);

  const metricName = metric.metric_name.trim().toLowerCase();
  if (countMetrics.has(metricName)) return formatCount(numeric);
  if (percentagePointMetrics.has(metricName)) return `${numeric.toFixed(2)}%`;
  if (metricName === "fetal_fraction") return numeric.toFixed(4);
  return numeric.toFixed(4);
}

function parseMetricNumber(raw: string | number): number | null {
  if (typeof raw === "number") return Number.isFinite(raw) ? raw : null;
  const normalized = raw.trim().replaceAll("%", "").replaceAll(",", "");
  if (!normalized) return null;
  const value = Number(normalized);
  return Number.isFinite(value) ? value : null;
}

function formatCount(value: number): string {
  const absolute = Math.abs(value);
  if (absolute >= 1_000_000) return `${trimSingleDecimal(value / 1_000_000)}M`;
  if (absolute >= 1_000) return `${trimSingleDecimal(value / 1_000)}K`;
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function trimSingleDecimal(value: number): string {
  return value.toFixed(1).replace(/\.0$/, "");
}
