import type {RecoveryView} from '../api';
import type {RunProgress} from '../lib/runProgress';
import {formatDate, formatPercent} from '../lib/format';

export function recoveryPending(value?: RecoveryView | null) {
  return Boolean(value && value.state !== 'recovering' && value.state !== 'completed_degraded');
}

export function recoveryProgress(progress: RunProgress): RunProgress {
  return {...progress, status:'unknown', estimated:true, failedStep:undefined,
    label:progress.available === false ? '最后确认进度未采集' : `最后确认进度 ${formatPercent(progress.percent)}`,
    note:'保留最后确认进度；不表示当前执行已失败或完成'};
}

export function RecoveryNotice({value}: {value?: RecoveryView | null}) {
  if (!value) return null;
  return <div className="current-stage-cell" role="status">
    <strong>{value.message}</strong>
    {value.reason ? <small>{value.reason}</small> : null}
    {value.next_retry_at ? <small>下次核对：{formatDate(value.next_retry_at)}</small> : null}
    {value.last_confirmed_at ? <small>最后确认：{formatDate(value.last_confirmed_at)}</small> : null}
  </div>;
}
