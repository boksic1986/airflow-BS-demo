const stageLabels: Record<string, string> = {
  "Workflow complete": "Completed",
  validate_request: "Validate run request",
  __airflow_demo_invalid_target__: "Demo invalid target",
};

export function humanStageLabel(value?: string | null): string {
  if (!value) return "No step captured";
  return stageLabels[value] || prettifyIdentifier(value);
}

export function stageDebugLabel(value?: string | null): string | null {
  if (!value) return null;
  const label = humanStageLabel(value);
  return label === value ? null : value;
}

function prettifyIdentifier(value: string): string {
  return value
    .split(".")
    .pop()!
    .replace(/^run_/, "Run ")
    .replace(/^collect_/, "Collect ")
    .replace(/^prepare_/, "Prepare ")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
