import {useState} from "react";
import {Link} from "react-router-dom";
import {listIncompleteWgsSubmissions, WGS_SUBMISSION_PHASES, type RunDetail} from "../../api";
import {useSilentRefresh} from "../../lib/useSilentRefresh";
import {usePlatformCapabilities} from "../platform/PlatformCapabilitiesContext";
import {CancelSubmission} from "./CancelSubmission";

export function useIncompleteWgsSubmissions(enabled = true) {
  const capabilities = usePlatformCapabilities();
  const available = enabled && !capabilities.loading && capabilities.isDeployed("wgs");
  const [items, setItems] = useState<RunDetail[]>([]);
  const result = useSilentRefresh(async ({isCurrent}) => {
    const next = await listIncompleteWgsSubmissions();
    if (isCurrent()) setItems(next);
  }, "incomplete-wgs-submissions", available);
  return {...result, items: available ? items : []};
}

export function SubmissionResumeCard({run}: {run: RunDetail}) {
  const [cancelled,setCancelled]=useState(false);
  if(cancelled) return null;
  const batch = String(run.params?.sequencing_batch || run.params?.analysis_batch || run.params?.batch_no || run.analysis_id);
  const phase = WGS_SUBMISSION_PHASES[String(run.params?.submission_phase || "")];
  return <div className="submission-resume-row"><Link className="attention-item submission-resume-card" to={`/submit?pipeline=wgs&analysis_id=${encodeURIComponent(run.analysis_id)}`}>
    <span className="attention-marker warning" aria-hidden="true" />
    <span><strong>{batch} · 未完成提交</strong><small>{phase} · attempt {run.attempt || 1}</small><small>{run.analysis_id}{run.created_at ? ` · 创建于 ${new Date(run.created_at).toLocaleString()}` : ""}</small></span>
    <span className="attention-actions">继续提交 →</span>
  </Link><CancelSubmission run={run} onCancelled={()=>setCancelled(true)} /></div>;
}

export function IncompleteSubmissionsPanel() {
  const {items, loading, error} = useIncompleteWgsSubmissions();
  return <section className="panel" aria-label="未完成提交">
    <h2>未完成提交</h2><p>任务已保存在服务器；点击继续原任务，不会重复创建或自动启动分析。</p>
    <div className="attention-list">{items.map(run => <SubmissionResumeCard key={run.analysis_id} run={run} />)}</div>
    {loading && !items.length ? <p>正在查找未完成提交…</p> : null}
    {!loading && !items.length && !error ? <p>没有待继续的手动提交。</p> : null}
    {error ? <small role="status">未完成提交刷新失败，保留上次结果；稍后自动重试。</small> : null}
  </section>;
}
