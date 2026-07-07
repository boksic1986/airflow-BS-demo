import type {PipelineTemplate} from "../mocks/platform";

import {compactPipelineName} from "../lib/format";
import {StatusBadge} from "./StatusBadge";

export function PipelineSelector({
  pipelines,
  value,
  onChange,
}: {
  pipelines: PipelineTemplate[];
  value: PipelineTemplate["id"];
  onChange: (value: PipelineTemplate["id"]) => void;
}) {
  return (
    <fieldset className="pipeline-selector">
      <legend>Pipeline</legend>
      {pipelines.map((pipeline) => (
        <label key={pipeline.id} className={value === pipeline.id ? "selected" : ""}>
          <input
            checked={value === pipeline.id}
            name="pipeline"
            type="radio"
            value={pipeline.id}
            onChange={() => onChange(pipeline.id)}
          />
          <span>
            <strong>{compactPipelineName(pipeline.id)}</strong>
            <small>{pipeline.description}</small>
          </span>
          <StatusBadge status={pipeline.implementationStatus} size="sm" />
        </label>
      ))}
    </fieldset>
  );
}
