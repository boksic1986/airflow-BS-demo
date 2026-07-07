import {PipelineCard} from "../components/PipelineCard";
import {WorkflowTimeline} from "../components/WorkflowTimeline";
import {workflowTemplates} from "../mocks/platform";

export function WorkflowsPage() {
  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Workflow templates</p>
          <h1>Workflows</h1>
          <p>DAG/rule templates, implementation status, expected inputs, and outputs for each bioinformatics pipeline.</p>
        </div>
      </section>
      <section className="card-grid">
        {workflowTemplates.map((pipeline) => (
          <PipelineCard key={pipeline.id} pipeline={pipeline} />
        ))}
      </section>
      <section className="card-grid">
        {workflowTemplates.map((pipeline) => (
          <WorkflowTimeline key={pipeline.id} title={`${pipeline.name} DAG/rule structure`} steps={pipeline.steps} />
        ))}
      </section>
    </div>
  );
}
