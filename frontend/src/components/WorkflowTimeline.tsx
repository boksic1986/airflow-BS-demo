import {StatusBadge} from "./StatusBadge";

export type WorkflowStep = {
  name: string;
  status: string;
  description?: string | null;
  sample?: string | null;
};

export function WorkflowTimeline({steps, title = "Workflow timeline"}: {steps: WorkflowStep[]; title?: string}) {
  return (
    <section className="panel">
      <div className="section-heading">
        <h2>{title}</h2>
      </div>
      <ol className="workflow-timeline">
        {steps.length ? (
          steps.map((step, index) => (
            <li key={`${step.name}-${step.sample || "project"}-${index}`}>
              <div className="timeline-marker">{index + 1}</div>
              <div>
                <div className="timeline-title">
                  <strong>{step.name}</strong>
                  <StatusBadge status={step.status} size="sm" />
                </div>
                <p>{step.sample ? `${step.sample} - ` : ""}{step.description || "No detail provided."}</p>
              </div>
            </li>
          ))
        ) : (
          <li>
            <div className="timeline-marker">0</div>
            <p>No workflow events returned yet.</p>
          </li>
        )}
      </ol>
    </section>
  );
}
