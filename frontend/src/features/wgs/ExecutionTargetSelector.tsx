import {useState} from "react";

import {ApiError, type WgsExecutionChoiceRequest, type WgsExecutionDispatch, type WgsExecutionTargetState} from "../../api";

export function ExecutionTargetSelector({attempt, batch, sampleCount, dispatch, onSwitch, onRefresh}: {
  attempt: number;
  batch: string;
  sampleCount: number;
  dispatch: WgsExecutionDispatch;
  onSwitch: (payload: WgsExecutionChoiceRequest) => Promise<void>;
  onRefresh?: () => Promise<void> | void;
}) {
  const [candidate, setCandidate] = useState<WgsExecutionTargetState | null>(null);
  const [reason, setReason] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const locked = !dispatch.allow_switch || ["committed", "running", "terminal", "needs_recovery"].includes(dispatch.dispatch_state);
  const current = dispatch.targets.find((target) => target.target === dispatch.desired_target);

  async function confirmSwitch() {
    if (!candidate || !reason.trim()) return;
    setPending(true);
    setError(null);
    try {
      await onSwitch({
        desired_mode: candidate.mode,
        desired_target: candidate.target,
        expected_revision: dispatch.dispatch_revision,
        reason: reason.trim(),
      });
      setCandidate(null);
      setReason("");
    } catch (switchError) {
      if (switchError instanceof ApiError && switchError.code === "EXECUTION_ALREADY_COMMITTED") {
        setError("CCE Step1 已启动，执行目标不能再修改");
      } else if (switchError instanceof ApiError && switchError.code === "STALE_EXECUTION_CHOICE") {
        setError("Execution target changed after this page loaded. Refreshing the latest state.");
      } else if (switchError instanceof Error) {
        setError(switchError.message);
      } else {
        setError("Execution target could not be changed.");
      }
      await onRefresh?.();
    } finally {
      setPending(false);
    }
  }

  return <section className="execution-target-panel" aria-label="Execution target">
    <div className="execution-target-heading">
      <div><h2>Execution target</h2><p>{locked ? "The target is frozen for this attempt." : dispatch.blocking_reason || "Choose the backend before execution is committed."}</p></div>
      {locked ? <strong className="execution-lock">Locked · Step1 started</strong> : <span className="muted">Revision {dispatch.dispatch_revision}</span>}
    </div>
    <div className="execution-target-segments" role="group" aria-label="WGS execution target">
      {dispatch.targets.map((target) => {
        const selected = target.target === dispatch.desired_target;
        const label = `${target.label} · ${targetStatus(target, dispatch)}`;
        return <button
          aria-pressed={selected}
          className={selected ? "active" : ""}
          disabled={locked || selected || !target.available}
          key={target.target}
          onClick={() => { setCandidate(target); setReason(""); setError(null); }}
          title={target.reason || target.warning || label}
          type="button"
        >{label}</button>;
      })}
    </div>
    {error ? <div className="inline-error" role="alert">{error}</div> : null}
    {candidate ? <div className="modal-backdrop">
      <section aria-label="Confirm execution target" aria-modal="true" className="modal-panel execution-target-modal" role="dialog">
        <div className="section-heading split"><div><h2>Confirm execution target</h2><p>This updates the current DagRun and attempt; neither is recreated.</p></div><button className="button ghost" disabled={pending} onClick={() => setCandidate(null)} type="button">Close</button></div>
        <div className="execution-switch-summary">
          <strong>{current?.label || dispatch.desired_target} → {candidate.label}</strong>
          <span>{batch} · {sampleCount} samples · attempt {attempt}</span>
          {candidate.metrics ? <span>{formatMetrics(candidate)}</span> : null}
          {candidate.warning ? <span className="warning-text">{candidate.warning}</span> : null}
          <p>After confirmation, the selected backend may start immediately when its admission checks still pass.</p>
        </div>
        <label className="field"><span>Audit reason</span><textarea aria-label="Audit reason" maxLength={500} onChange={(event) => setReason(event.target.value)} rows={3} value={reason} /></label>
        <div className="execution-modal-actions"><button className="button ghost" disabled={pending} onClick={() => setCandidate(null)} type="button">Cancel</button><button className="button primary" disabled={pending || !reason.trim()} onClick={() => void confirmSwitch()} type="button">{pending ? "Switching..." : "Confirm switch"}</button></div>
      </section>
    </div> : null}
  </section>;
}

function targetStatus(target: WgsExecutionTargetState, dispatch: WgsExecutionDispatch): string {
  if (target.target === dispatch.desired_target && dispatch.dispatch_state === "waiting_resource" && target.target === "cce") return "waiting upload slot";
  return {
    available: "available",
    waiting_upload_slot: "waiting upload slot",
    busy: "busy",
    high_load: "high CPU",
    stale: "stale metrics",
    manual: "manual",
    unsupported: "unavailable",
  }[target.status];
}

function formatMetrics(target: WgsExecutionTargetState): string {
  const metrics = target.metrics;
  if (!metrics) return "";
  return `CPU ${formatNumber(metrics.cpu_percent)}% · Load ${formatNumber(metrics.load1)} / ${formatNumber(metrics.load5)} / ${formatNumber(metrics.load15)} · Memory ${formatNumber(metrics.memory_percent)}% · ${formatNumber(metrics.logical_cpu_count)} CPUs`;
}

function formatNumber(value?: number | null): string {
  if (value == null) return "-";
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}
