import {useState} from "react";
import {createPortal} from "react-dom";
import {cancelSubmission, previewSubmissionCancel, type RunDetail, type SubmissionCancelPreview} from "../../api";
import {errorMessage} from "../../lib/errors";

export function CancelSubmission({run, onCancelled}: {run: RunDetail; onCancelled: () => void}) {
  const [open,setOpen]=useState(false);
  const [preview,setPreview]=useState<SubmissionCancelPreview|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState<string|null>(null);
  const phase=String(run.params?.submission_phase || "");
  if (!["config_review","cancelling_submission"].includes(phase) || run.params?.config_approved_at || run.params?.submission_mode==="auto_dispatch") return null;
  async function show() {
    setOpen(true);setBusy(true);setError(null);setPreview(null);
    try {setPreview(await previewSubmissionCancel(run.analysis_id,run.attempt || 1));}
    catch(e){setError(errorMessage(e));} finally {setBusy(false);}
  }
  async function confirm() {
    if (!preview || preview.analysis_id!==run.analysis_id || preview.attempt!==(run.attempt || 1)) return;
    setBusy(true);setError(null);
    try {
      const result=await cancelSubmission(preview.analysis_id,preview.attempt);
      if(result.status!=="cancelled") throw new Error("取消尚未确认，请重试。");
      setOpen(false);onCancelled();window.dispatchEvent(new Event("focus"));
    } catch(e){setError(errorMessage(e));} finally {setBusy(false);}
  }
  return <><button type="button" className="button" onClick={()=>void show()}>{phase==="cancelling_submission"?"重试取消提交":"取消提交"}</button>{open?createPortal(<div className="modal-backdrop"><section className="modal-panel" role="dialog" aria-modal="true" aria-label="取消提交确认"><h2>取消提交确认</h2><p>{run.analysis_id} · attempt {run.attempt}</p>{preview?.effects?.map(effect=><p key={effect}>{effect}</p>)}{busy?<p role="status">正在核验／处理，请稍候…</p>:null}{error?<p className="inline-error" role="alert">{error}</p>:null}<div className="execution-modal-actions"><button type="button" className="button" disabled={busy} onClick={()=>setOpen(false)}>返回</button><button type="button" className="button danger" disabled={busy || !preview} onClick={()=>void confirm()}>确认取消提交</button></div></section></div>,document.body):null}</>;
}
