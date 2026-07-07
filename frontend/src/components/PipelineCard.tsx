import type {PipelineTemplate} from "../mocks/platform";

import {compactPipelineName} from "../lib/format";
import {StatusBadge} from "./StatusBadge";

export function PipelineCard({pipeline}: {pipeline: PipelineTemplate}) {
  return (
    <article className="pipeline-card">
      <div className="pipeline-card-title">
        <div>
          <h3>{compactPipelineName(pipeline.id)}</h3>
          <p>{pipeline.description}</p>
        </div>
        <StatusBadge status={pipeline.implementationStatus} />
      </div>
      <dl className="definition-grid compact">
        <div>
          <dt>DAG</dt>
          <dd>{pipeline.dagId}</dd>
        </div>
        <div>
          <dt>Version</dt>
          <dd>{pipeline.version}</dd>
        </div>
        <div>
          <dt>Execution</dt>
          <dd>{pipeline.execution}</dd>
        </div>
        <div>
          <dt>Reference</dt>
          <dd>{pipeline.reference}</dd>
        </div>
        <div>
          <dt>Latest run</dt>
          <dd>{pipeline.latestRun}</dd>
        </div>
        <div>
          <dt>Success rate</dt>
          <dd>{pipeline.successRate}</dd>
        </div>
      </dl>
    </article>
  );
}
