import {getStatusMeta} from "../lib/status";

export function StatusBadge({status, label, size = "md", className = ""}: {status?: string | null; label?: string; size?: "sm" | "md" | "lg"; className?: string}) {
  const meta = getStatusMeta(status);
  const Icon = meta.Icon;
  return (
    <span className={`status-badge status-${meta.tone} status-${size} ${className}`.trim()} title={label ?? meta.label}>
      <Icon aria-hidden="true" size={size === "lg" ? 16 : 14} />
      <span>{label ?? meta.label}</span>
    </span>
  );
}
