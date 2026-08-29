import type {Step4RepairCapability} from "../../api";


export function Step4RepairPanel({capability, canOperate, acting = false, onRepair}: {
  capability: Step4RepairCapability;
  canOperate: boolean;
  acting?: boolean;
  onRepair?: () => void;
}) {
  const latest = capability.latest_action;
  const runtimeUnavailable = capability.reason === "runtime_unavailable";

  function confirmRepair() {
    if (!window.confirm("确认修复本次分析的 CRAM 联动并继续？该操作只处理固定 cram 组。")) return;
    onRepair?.();
  }

  return (
    <section className="panel validation-review" aria-label="Step4 CRAM repair">
      <div className="section-heading split">
        <div>
          <h2>Step4 CRAM 联动修复</h2>
          <p>仅消费冻结 WGS bundle 的 cram 修复合同；页面不能提交路径、分组或 shell 参数。</p>
        </div>
        {capability.available && canOperate ? (
          <button className="button primary" type="button" disabled={acting} onClick={confirmRepair}>修复CRAM联动并继续</button>
        ) : null}
      </div>
      {runtimeUnavailable ? <div className="inline-error" role="note">运行环境尚不可用</div> : null}
      {!runtimeUnavailable && capability.reason && capability.reason !== "repair_in_progress" ? <p className="muted">当前任务不满足修复条件：{capability.reason}</p> : null}
      {latest ? <p className="muted">最近维护操作：{latest.status} / attempt {latest.attempt} / {latest.action_id}</p> : null}
    </section>
  );
}
