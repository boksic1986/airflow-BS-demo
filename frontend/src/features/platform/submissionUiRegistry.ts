import type {PipelineCapability} from "../../api";

const submissionUiAdapters = new Set(["wgs"]);

export function hasRegisteredSubmissionUi(
  pipeline: PipelineCapability,
  isDeployed: (pipelineId: string) => boolean,
) {
  return submissionUiAdapters.has(pipeline.id)
    && isDeployed(pipeline.id)
    && pipeline.enabled
    && pipeline.submit_enabled
    && pipeline.capabilities.includes("submit");
}
