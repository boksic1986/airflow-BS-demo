import {getStatusMeta} from "../lib/status";

export function StatusBadge({status, size = "md"}: {status?: string | null; size?: "sm" | "md" | "lg"}) {
  const meta = getStatusMeta(status);
  const Icon = meta.Icon;
  return (
    <span className={`status-badge status-${meta.tone} status-${size}`} title={meta.label}>
      <Icon aria-hidden="true" size={size === "lg" ? 16 : 14} />
      <span>{meta.label}</span>
    </span>
  );
}
