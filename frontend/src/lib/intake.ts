import type {IntakeDiscovery} from "../api";

export type IntakeDisplay = {
  label: string;
  tone: "neutral" | "success" | "warning" | "danger" | "muted";
};

export function intakeDisplay(item: IntakeDiscovery): IntakeDisplay {
  const ready = item.ready_state.toLowerCase();
  const submit = item.submit_state.toLowerCase();
  if (ready === "waiting_barcode_stat") return {label: "waiting", tone: "neutral"};
  if (ready === "no_new_wgs") return {label: "no-new-WGS", tone: "muted"};
  if (ready === "needs_review") return {label: "needs-review", tone: "danger"};
  if (ready === "bootstrap_ignored") return {label: "bootstrap-ignored", tone: "neutral"};
  if (item.pipeline === "wgs" && ready === "ready") return {label: "ready", tone: "warning"};
  if (ready === "error" || submit === "error") return {label: "Error", tone: "danger"};
  if (ready === "disabled" || submit === "disabled") return {label: "Disabled", tone: "muted"};
  if (submit === "submitted") return {label: "Auto-submitted", tone: "success"};
  if (submit === "bootstrap") return {label: "Bootstrap observed", tone: "neutral"};
  if (ready === "ready") return {label: "Stable ready", tone: "warning"};
  if (ready === "observed") return {label: "Observed", tone: "neutral"};
  return {label: ready || submit || "Unknown", tone: "neutral"};
}
