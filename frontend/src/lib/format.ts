const displayTimeZone =
  window.__AIRFLOW_DEMO_CONFIG__?.timeZone || import.meta.env.VITE_DISPLAY_TIME_ZONE || "Asia/Shanghai";

export function formatDate(value?: string | null): string {
  if (!value) return "not set";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: displayTimeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find((item) => item.type === type)?.value || "00";
  return `${part("year")}-${part("month")}-${part("day")} ${part("hour")}:${part("minute")}:${part("second")}`;
}

export function formatDuration(start?: string | null, end?: string | null): string {
  if (!start) return "not set";
  const startDate = new Date(start);
  const endDate = end ? new Date(end) : new Date();
  if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) return "not set";
  const seconds = Math.max(0, Math.floor((endDate.getTime() - startDate.getTime()) / 1000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

export function formatSecondsDuration(seconds?: number | null): string {
  if (seconds == null || !Number.isFinite(seconds)) return "not set";
  const normalized = Math.max(0, Math.floor(seconds));
  if (normalized < 60) return `${normalized}s`;
  const minutes = Math.floor(normalized / 60);
  if (minutes < 60) return `${minutes}m ${normalized % 60}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

export function displayTimeZoneLabel(): string {
  return displayTimeZone;
}

export function formatBytes(value?: number | null): string {
  if (value == null) return "not set";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

export function compactPipelineName(pipeline?: string | null): string {
  if (!pipeline) return "unknown";
  if (pipeline === "wes_qsub") return "WES qsub";
  if (pipeline === "nipt_qsub") return "NIPT qsub";
  if (pipeline === "nipt_docker") return "NIPT docker";
  if (pipeline === "pgta") return "PGT-A";
  return pipeline.toUpperCase();
}

export function safeJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
