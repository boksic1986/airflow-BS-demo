import type {DeployedPipeline} from "../api";

export function deployedPipelineFilter(
  requested: string | null,
  deployed: readonly DeployedPipeline[],
): "all" | DeployedPipeline {
  if (!requested || requested === "all") return "all";
  return deployed.includes(requested as DeployedPipeline) ? requested as DeployedPipeline : "all";
}
