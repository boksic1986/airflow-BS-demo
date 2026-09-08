import {getStatusMeta} from "../lib/status";

export function StatusBadge({status, size = "md", className = ""}: {status?: string | null; size?: "sm" | "md" | "lg"; className?: string}) {
  const meta = getStatusMeta(status);
  const Icon = meta.Icon;
  return (
    <span className={`status-badge status-${meta.tone} status-${size}${className ? ` ${className}` : ""}`} title={meta.label}>
      <Icon aria-hidden="true" size={size === "lg" ? 16 : 14} />
      <span>{meta.label}</span>
    </span>
  );
}
