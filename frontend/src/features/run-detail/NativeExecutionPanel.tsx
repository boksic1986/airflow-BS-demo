import {useCallback, useState} from 'react';
import {getNativeRunView, type NativeRunView, type RunDetail} from '../../api';
import {StatusBadge} from '../../components/StatusBadge';
import {LogViewer} from '../../components/LogViewer';
import {useSilentRefresh} from '../../lib/useSilentRefresh';
import {formatDate} from '../../lib/format';
import {RunProgressBar} from '../../components/RunProgressBar';
import {RuleInstanceTable} from './RunWorkflowTab';

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
  const [ruleStatus, setRuleStatus] = useState('running');
  const [sampleId, setSampleId] = useState('');
  const [familyId, setFamilyId] = useState('');
  const search = useCallback((value: string, index: number) => {setQuery(value); setMatchIndex(index);}, []);
  const [loaded, setLoaded] = useState<{key: string; value: NativeRunView} | null>(null);
  const key = JSON.stringify([detail.analysis_id, execution, tab, offset, historyOffset, query, matchIndex, ruleStatus, sampleId, familyId]);
  const {loading, error} = useSilentRefresh(async ({isCurrent}) => {
    const value = await getNativeRunView(detail.analysis_id, {execution_id: execution, section: tab.toLowerCase(), offset, history_offset: historyOffset, query, match_index: matchIndex, rule_status: ruleStatus, sample_id: sampleId, family_id: familyId});
    if (isCurrent()) setLoaded({key, value});
  }, key);
  const view = loaded?.key === key ? loaded.value : null;
  // Keep selector choices while loading, never stale table rows from another execution.
  const choices = loaded?.value.executions || [];
  const selected = view?.selected;
  const total = tab === 'Samples' ? view?.sample_total || 0 : view?.rule_total || 0;
  const batch = String(detail.params?.batch_no || detail.analysis_id);
  const mode = view?.configuration?.execution_mode === 'sge' ? 'SGE' : 'Local';
  return <div className="page-stack run-detail-page native-run-page">
    <section className="run-summary-header"><div><p className="eyebrow">WGS · {mode}</p><h1>{batch}</h1><p className="muted">{detail.analysis_id}</p></div>
      <StatusBadge status={selected?.status || detail.status} size="lg" /></section>
    <div className="native-summary-grid">
      <section className="panel"><h2>运行摘要</h2><dl className="definition-grid">
        <div><dt>Platform operator</dt><dd>{selected?.registered_by || detail.submitted_by || '-'}</dd></div>
        <div><dt>Linux user / target</dt><dd>{view?.configuration?.execution_user || '-'} / {view?.configuration?.execution_target || '-'}</dd></div>
        <div><dt>Started</dt><dd>{formatDate(selected?.started_at)}</dd></div>
        <div><dt>Finished</dt><dd>{selected?.ended_at ? formatDate(selected.ended_at) : '尚未结束'}</dd></div>
        <div><dt>Configured samples</dt><dd>{selected?.sample_count ?? '—'}</dd></div>
        <div><dt>Analysis parameters</dt><dd>{Object.entries(view?.configuration?.parameters || {}).map(([name, value]) => `${name}: ${value}`).join(' · ') || '-'}</dd></div>
      </dl></section>
      <section className="panel native-progress-panel"><h2>分析进度</h2>
        <RunProgressBar analysisId={detail.analysis_id} progress={{notInAirflow: false, available: view?.progress?.available ?? false,
          percent: view?.progress?.percent ?? 0, label: `${view?.progress?.percent ?? 0}%`, currentStep: `${mode} analysis`,
          status: selected?.status || detail.status, note: view?.progress?.total_units ? `${view.progress.completed_units ?? 0} / ${view.progress.total_units} rules completed` : `已采集 ${view?.progress?.observed_rules ?? 0} 条 Rule，等待总量证据`}} />
        <p className="muted">仅本次执行日志 · 监控更新 {formatDate(view?.monitoring?.checked_at)}</p>
        {view?.monitoring?.monitoring_health === 'degraded' || view?.evidence_health === 'unavailable' ? <p className="inline-error" role="alert">监控证据暂不可读；不表示分析失败，不要重复启动。</p> : null}
      </section>
    </div>
    <section className="panel native-history"><details><summary>执行历史与技术信息</summary>
      <div className="rule-filters">
        <label className="field"><span>Execution</span><select aria-label="Execution" value={execution} onChange={event => {setExecution(event.target.value); setOffset(0); setQuery('');}}>
          <option value="">Current execution</option>
          {choices.map(item => <option key={item.execution_id} value={item.execution_id}>Execution {item.generation} · {item.status}</option>)}
        </select></label>
        <button className="button ghost" disabled={historyOffset === 0} onClick={() => setHistoryOffset(Math.max(0, historyOffset - 50))}>Previous executions</button>
        <button className="button ghost" disabled={historyOffset + 50 >= (loaded?.value.history_total || 0)} onClick={() => setHistoryOffset(historyOffset + 50)}>Older executions</button>
      </div>
      <dl className="definition-grid"><div><dt>Execution ID</dt><dd>{selected?.execution_id || '-'}</dd></div><div><dt>Generation</dt><dd>{selected?.generation || '-'}</dd></div></dl>
    </details></section>
    <section className="panel native-data-panel">
      <div className="tabs" role="tablist" aria-label="Native run tabs">{tabs.map(name => <button type="button" role="tab" aria-selected={tab === name} className={tab === name ? 'active' : ''} key={name} onClick={() => {setTab(name); setOffset(0); setQuery('');}}>{name}</button>)}</div>
      {error ? <p className="inline-error" role="alert">{error}</p> : null}
      {tab === 'Logs' ? <LogViewer key={execution} stream="stdout" onStreamChange={() => {}} log={view?.log || null} error={null} sources={[{key: 'native', label: 'Native Step1 stdout / stderr', stream: 'stdout', source: 'native'}]} activeKey="native" onKeyChange={() => {}} onSearch={search} /> : null}
      {!view ? <p className="muted">{loading ? 'Loading execution...' : 'Loading selected view...'}</p> : <>
        {tab === 'Samples' ? <><p className="muted">本次冻结配置范围；不代表所有样本均重新执行。</p><div className="table-wrap"><table className="data-table" aria-label="Execution samples"><thead><tr><th>Data ID</th><th>Sample</th><th>Family</th></tr></thead><tbody>
          {view.samples.map(row => <tr key={row.data_id}><td>{row.data_id}</td><td>{row.sample_id}</td><td>{row.family_id || '-'}</td></tr>)}
          {!view.samples.length ? <tr><td colSpan={3}>尚无执行样本快照</td></tr> : null}</tbody></table></div></> : null}
        {tab === 'Rules' ? <><p className="muted">本次日志中的 Rule；时间按执行节点本地时间显示。</p>
          <div className="rule-filters">
            <label>Status<select aria-label="Rule status" value={ruleStatus} onChange={e => {setRuleStatus(e.target.value); setOffset(0);}}><option value="">All</option>{['running','success','failed','unknown'].map(s => <option key={s}>{s}</option>)}</select></label>
            <label>Sample<input aria-label="Exact sample" value={sampleId} onChange={e => {setSampleId(e.target.value); setOffset(0);}} placeholder="Exact sample ID" /></label>
            <label>Family<input aria-label="Exact family" value={familyId} onChange={e => {setFamilyId(e.target.value); setOffset(0);}} placeholder="Exact family ID" /></label>
          </div>
          <RuleInstanceTable key={selected?.execution_id} rules={view.rules} />
        </> : null}
        {tab === 'QC' ? <><p>本 run 最新 QC · {formatDate(view.qc.updated_at)}</p><p className="muted">续跑共用，不随历史 execution 切换；未重新生成时保留已有结果。</p>
          {view.qc.health !== 'available' ? <p role="alert">{view.qc.health === 'stale' ? 'QC 当前不可读或尚未完整写入，展示上次可靠结果。' : '尚无可读取的 QC。'}</p> : null}
          <div className="table-wrap"><table className="data-table" aria-label="Latest run QC"><thead><tr><th>Sample</th><th>Source QC status</th>{Object.values(metrics).map(label => <th key={label}>{label}</th>)}</tr></thead><tbody>
            {view.qc.items.map(row => <tr key={row.sample_id}><td>{row.sample_id}</td><td><StatusBadge status={row.qc_status || 'unknown'} size="sm" /></td>{Object.keys(metrics).map(metric => <td key={metric}>{String(row.qc_metrics?.[metric] ?? '-')}</td>)}</tr>)}
          </tbody></table></div></> : null}
        {tab === 'Samples' || tab === 'Rules' ? <div className="pagination-controls"><span>{total ? offset + 1 : 0}–{Math.min(offset + 25, total)} of {total}</span><div><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 25))}>Previous</button><button disabled={offset + 25 >= total} onClick={() => setOffset(offset + 25)}>Next</button></div></div> : null}
      </>}
    </section>
  </div>;
}
