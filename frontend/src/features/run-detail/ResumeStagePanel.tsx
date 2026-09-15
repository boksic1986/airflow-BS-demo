import {useRef, useState} from 'react';
import {resumeStage} from '../../api';

export function ResumeStagePanel({analysisId, attempt, stage, canOperate, onAccepted}: {
  analysisId: string; attempt: number; stage: string; canOperate: boolean; onAccepted: () => void;
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
    <h2>继续当前阶段</h2>
    <p>从 {stage} 继续本次分析，不重新准备；保留原 attempt、版本、配置、工作目录及已有结果。</p>
    <label><input type="checkbox" checked={confirmed} disabled={busy || !canOperate} onChange={event => setConfirmed(event.target.checked)}/>确认继续当前阶段及必要后续阶段</label>
    <button className="button primary" type="button" disabled={!canOperate || !confirmed || busy} onClick={() => void submit()}>继续当前阶段</button>
    {error ? <p role="alert">{error}</p> : null}
  </section>;
}
