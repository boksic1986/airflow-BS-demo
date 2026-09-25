import {useRef, useState} from 'react';
import {resumeStage, type RunDetail} from '../../api';

export function monitorReconnectAvailable(detail: RunDetail | null, canResume: boolean) {
  return Boolean(detail && canResume && ['wgs','gatk'].includes(detail.pipeline)
    && (detail.execution_dispatch?.desired_mode || detail.execution_mode) === 'cce'
    && detail.recovery?.state === 'needs_attention' && detail.recovery.stage_code === 'step3_monitor'
    && detail.recovery.limit === 6);
}

export function ResumeStagePanel({analysisId, attempt, stage, canOperate, onAccepted, reconnect = false}: {
  analysisId: string; attempt: number; stage: string; canOperate: boolean; onAccepted: () => void; reconnect?: boolean;
}) {
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const key = useRef('');
  if (!key.current) key.current = Array.from(crypto.getRandomValues(new Uint8Array(16)), value => value.toString(16).padStart(2, '0')).join('');
  async function submit() {
    setBusy(true);
    setError('');
    try {
      const result = await resumeStage(analysisId, {attempt, stage, idempotency_key: key.current});
      if (result.status === 'uncertain') {
        setError('提交结果尚未确认，请重试查询同一次恢复操作。');
      } else {
        setConfirmed(false);
        onAccepted();
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '恢复请求未确认，请重试。');
    } finally {
      setBusy(false);
    }
  }
  return <section className="panel">
    <h2>{reconnect ? '恢复监控' : '继续当前阶段'}</h2>
    <p>从 {stage} 继续本次分析，不重新准备；保留原 attempt、版本、配置、工作目录及已有结果。</p>
    {reconnect ? <p>先核对原执行：仍在运行则接回监控；无法确认时不重复启动。计算自动重试额度及原截止时间不重置。</p> : null}
    <label><input type="checkbox" checked={confirmed} disabled={busy || !canOperate} onChange={event => setConfirmed(event.target.checked)}/>确认继续当前阶段及必要后续阶段</label>
    <button className="button primary" type="button" disabled={!canOperate || !confirmed || busy} onClick={() => void submit()}>{reconnect ? '恢复监控' : '继续当前阶段'}</button>
    {error ? <p role="alert">{error}</p> : null}
  </section>;
}
