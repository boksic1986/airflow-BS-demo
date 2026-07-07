import {PipelineCard} from "../components/PipelineCard";
import {WorkflowTimeline} from "../components/WorkflowTimeline";
import {deployedWorkflowTemplates} from "../mocks/platform";

export function WorkflowsPage() {
  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Workflow templates</p>
          <h1>Workflows</h1>
          <p>Current deployment exposes only the PGT-A workflow template. Non-PGT-A workflow surfaces are hidden from the demo.</p>
        </div>
      </section>
      <section className="card-grid">
        {deployedWorkflowTemplates.map((pipeline) => (
          <PipelineCard key={pipeline.id} pipeline={pipeline} />
        ))}
      </section>
      <section className="card-grid">
        {deployedWorkflowTemplates.map((pipeline) => (
          <WorkflowTimeline key={pipeline.id} title={`${pipeline.name} DAG/rule structure`} steps={pipeline.steps} />
        ))}
      </section>
    </div>
  );
}
