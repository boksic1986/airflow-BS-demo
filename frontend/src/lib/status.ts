import {
  AlertTriangle,
  Ban,
  CheckCircle2,
  Circle,
  Clock3,
  HelpCircle,
  Loader2,
  PauseCircle,
  XCircle,
} from "lucide-react";

import type {LucideIcon} from "lucide-react";

export type StatusTone = "neutral" | "info" | "success" | "warning" | "danger" | "muted";

export type StatusMeta = {
  label: string;
  tone: StatusTone;
  Icon: LucideIcon;
  active: boolean;
  terminal: boolean;
};

const metaByStatus: Record<string, StatusMeta> = {
  created: {label: "created", tone: "neutral", Icon: Circle, active: false, terminal: false},
  queued: {label: "queued", tone: "info", Icon: Clock3, active: true, terminal: false},
  submitted: {label: "submitted", tone: "info", Icon: Clock3, active: true, terminal: false},
  scheduled: {label: "scheduled", tone: "info", Icon: Clock3, active: true, terminal: false},
  running: {label: "running", tone: "info", Icon: Loader2, active: true, terminal: false},
  success: {label: "success", tone: "success", Icon: CheckCircle2, active: false, terminal: true},
  pass: {label: "pass", tone: "success", Icon: CheckCircle2, active: false, terminal: true},
  warning: {label: "warning", tone: "warning", Icon: AlertTriangle, active: false, terminal: false},
  warn: {label: "warn", tone: "warning", Icon: AlertTriangle, active: false, terminal: false},
  qc_warning: {label: "qc warning", tone: "warning", Icon: AlertTriangle, active: false, terminal: false},
  failed: {label: "failed", tone: "danger", Icon: XCircle, active: false, terminal: true},
  fail: {label: "fail", tone: "danger", Icon: XCircle, active: false, terminal: true},
  error: {label: "error", tone: "danger", Icon: XCircle, active: false, terminal: true},
  canceled: {label: "canceled", tone: "muted", Icon: Ban, active: false, terminal: true},
  cancelled: {label: "canceled", tone: "muted", Icon: Ban, active: false, terminal: true},
  terminated: {label: "terminated", tone: "muted", Icon: Ban, active: false, terminal: true},
  skipped: {label: "skipped", tone: "muted", Icon: PauseCircle, active: false, terminal: true},
  unknown: {label: "unknown", tone: "neutral", Icon: HelpCircle, active: false, terminal: false},
};

export function normalizeStatus(status?: string | null): string {
  return (status || "unknown").trim().toLowerCase() || "unknown";
}

export function getStatusMeta(status?: string | null): StatusMeta {
  const normalized = normalizeStatus(status);
  return metaByStatus[normalized] || {label: normalized, tone: "neutral", Icon: HelpCircle, active: false, terminal: false};
}

export function isActiveStatus(status?: string | null): boolean {
  return getStatusMeta(status).active;
}

export function isFailedStatus(status?: string | null): boolean {
  const normalized = normalizeStatus(status);
  return ["failed", "fail", "error", "terminated"].includes(normalized);
}

export function statusPriority(status?: string | null): number {
  const normalized = normalizeStatus(status);
  if (["failed", "fail", "error"].includes(normalized)) return 0;
  if (["running", "submitted", "queued", "scheduled"].includes(normalized)) return 1;
  if (["warning", "warn", "qc_warning"].includes(normalized)) return 2;
  if (["success", "pass"].includes(normalized)) return 3;
  return 4;
}
