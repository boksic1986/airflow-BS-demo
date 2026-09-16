import {useCallback, useState} from 'react';
import {getNativeRunView, type NativeRunView, type RunDetail} from '../../api';
import {StatusBadge} from '../../components/StatusBadge';
import {LogViewer} from '../../components/LogViewer';
import {useSilentRefresh} from '../../lib/useSilentRefresh';
import {formatDate} from '../../lib/format';

const tabs = ['Samples', 'Rules', 'Logs', 'QC'] as const;
const metrics = {clean_q30_percent: 'Clean Q30 (%)', mapped_reads_percent: 'Mapped (%)', average_depth: 'Average depth', coverage_20x_percent: '≥20X (%)', contamination: 'Contamination'};

/** Native view in the existing run route; no cloud control actions. */
export function NativeExecutionPanel({detail}: {detail: RunDetail}) {
  const [execution, setExecution] = useState('');
  const [tab, setTab] = useState<typeof tabs[number]>('Samples');
  const [offset, setOffset] = useState(0);
  const [historyOffset, setHistoryOffset] = useState(0);
  const [query, setQuery] = useState('');
  const [matchIndex, setMatchIndex] = useState(0);
  const search = useCallback((value: string, index: number) => {setQuery(value); setMatchIndex(index);}, []);
  const [loaded, setLoaded] = useState<{key: string; value: NativeRunView} | null>(null);
  const key = JSON.stringify([detail.analysis_id, execution, tab, offset, historyOffset, query, matchIndex]);
  const {loading, error} = useSilentRefresh(async ({isCurrent}) => {
    const value = await getNativeRunView(detail.analysis_id, {execution_id: execution, section: tab.toLowerCase(), offset, history_offset: historyOffset, query, match_index: matchIndex});
    if (isCurrent()) setLoaded({key, value});
  }, key);
  const view = loaded?.key === key ? loaded.value : null;
  // Keep selector choices while loading, never stale table rows from another execution.
  const choices = loaded?.value.executions || [];
  const selected = view?.selected;
  const total = tab === 'Samples' ? view?.sample_total || 0 : view?.rule_total || 0;
  return <div className="page-stack run-detail-page">
    <section className="run-summary-header"><div><p className="eyebrow">WGS Local / SGE</p><h1>{detail.analysis_id}</h1><p>Operator: {detail.submitted_by || '-'}</p></div>
      <StatusBadge status={selected?.status || detail.status} size="lg" /></section>
    <section className="panel">
      <div className="section-heading"><h2>Execution history</h2></div>
      <div className="rule-filters">
        <label className="field"><span>Execution</span><select aria-label="Execution" value={execution} onChange={event => {setExecution(event.target.value); setOffset(0); setQuery('');}}>
          <option value="">Current execution</option>
          {choices.map(item => <option key={item.execution_id} value={item.execution_id}>Execution {item.generation} · {item.status}</option>)}
        </select></label>
        <button className="button ghost" disabled={historyOffset === 0} onClick={() => setHistoryOffset(Math.max(0, historyOffset - 50))}>Previous executions</button>
        <button className="button ghost" disabled={historyOffset + 50 >= (loaded?.value.history_total || 0)} onClick={() => setHistoryOffset(historyOffset + 50)}>Older executions</button>
      </div>
      {selected ? <dl className="definition-grid"><div><dt>Execution</dt><dd>{selected.execution_id}</dd></div>
        <div><dt>Execution operator</dt><dd>{selected.registered_by}</dd></div><div><dt>Started</dt><dd>{formatDate(selected.started_at)}</dd></div>
        <div><dt>Finished</dt><dd>{formatDate(selected.ended_at)}</dd></div><div><dt>Configured samples</dt><dd>{selected.sample_count}</dd></div></dl> : null}
      {view?.configuration ? <div className="definition-grid"><div><dt>Linux user / target</dt><dd>{view.configuration.execution_user || '-'} / {view.configuration.execution_target || '-'}</dd></div>
        <div><dt>Frozen analysis parameters</dt><dd>{Object.entries(view.configuration.parameters).map(([name, value]) => `${name}: ${value}`).join(' · ') || '-'}</dd></div></div> : null}
      {view?.monitoring?.monitoring_health === 'degraded' ? <p role="alert">监控异常，保留最后可靠执行状态。</p> : null}
      <div className="tabs" role="tablist" aria-label="Native run tabs">{tabs.map(name => <button type="button" role="tab" aria-selected={tab === name} className={tab === name ? 'active' : ''} key={name} onClick={() => {setTab(name); setOffset(0); setQuery('');}}>{name}</button>)}</div>
      {error ? <p className="inline-error" role="alert">{error}</p> : null}
      {tab === 'Logs' ? <LogViewer key={execution} stream="stdout" onStreamChange={() => {}} log={view?.log || null} error={null} sources={[{key: 'native', label: 'Native Step1 stdout / stderr', stream: 'stdout', source: 'native'}]} activeKey="native" onKeyChange={() => {}} onSearch={search} /> : null}
      {!view ? <p className="muted">{loading ? 'Loading execution...' : 'Loading selected view...'}</p> : <>
        {view.evidence_health === 'unavailable' ? <p role="alert">项目证据不可用或目录身份已改变；未读取其他项目。</p> : null}
        {tab === 'Samples' ? <><p className="muted">本次冻结配置范围；不代表所有样本均重新执行。</p><div className="table-wrap"><table className="data-table" aria-label="Execution samples"><thead><tr><th>Data ID</th><th>Sample</th><th>Family</th></tr></thead><tbody>
          {view.samples.map(row => <tr key={row.data_id}><td>{row.data_id}</td><td>{row.sample_id}</td><td>{row.family_id || '-'}</td></tr>)}
          {!view.samples.length ? <tr><td colSpan={3}>尚无执行样本快照</td></tr> : null}</tbody></table></div></> : null}
        {tab === 'Rules' ? <><p className="muted">仅本次主日志中明确记录的 Rule；未采集的状态和时间不作推断。{view.rules_incomplete ? ' 日志扫描未覆盖全部内容。' : ''}</p><div className="table-wrap"><table className="data-table"><thead><tr><th>Rule</th><th>Job</th><th>Sample</th><th>Family</th><th>Status</th><th>Log line</th></tr></thead><tbody>
          {view.rules.map(row => <tr key={`${selected?.execution_id}:${row.source_line}`}><td>{row.rule}</td><td>{row.job_id}</td><td>{row.sample_id || '-'}</td><td>{row.family_id || '-'}</td><td><StatusBadge status={row.status} size="sm" /></td><td>{row.source_line}</td></tr>)}
          {!view.rules.length ? <tr><td colSpan={6}>尚无可确认的 Rule 记录</td></tr> : null}</tbody></table></div></> : null}
        {tab === 'QC' ? <><p>本 run 最新 QC · {formatDate(view.qc.updated_at)}</p><p className="muted">续跑共用，不随历史 execution 切换；未重新生成时保留已有结果。</p>
          {view.qc.health !== 'available' ? <p role="alert">{view.qc.health === 'stale' ? 'QC 当前不可读或尚未完整写入，展示上次可靠结果。' : '尚无可读取的 QC。'}</p> : null}
          <div className="table-wrap"><table className="data-table" aria-label="Latest run QC"><thead><tr><th>Sample</th><th>Source QC status</th>{Object.values(metrics).map(label => <th key={label}>{label}</th>)}</tr></thead><tbody>
            {view.qc.items.map(row => <tr key={row.sample_id}><td>{row.sample_id}</td><td><StatusBadge status={row.qc_status || 'unknown'} size="sm" /></td>{Object.keys(metrics).map(metric => <td key={metric}>{String(row.qc_metrics?.[metric] ?? '-')}</td>)}</tr>)}
          </tbody></table></div></> : null}
        {tab === 'Samples' || tab === 'Rules' ? <div className="table-pagination"><button className="button ghost" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 25))}>Previous</button><span>{total ? offset + 1 : 0}–{Math.min(offset + 25, total)} of {total}</span><button className="button ghost" disabled={offset + 25 >= total} onClick={() => setOffset(offset + 25)}>Next</button></div> : null}
      </>}
    </section>
  </div>;
}
