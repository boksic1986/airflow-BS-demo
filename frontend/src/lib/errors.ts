import {ApiError} from "../api";

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.code ? `${error.code}: ${error.message}` : error.message;
  }
  if (error instanceof Error) return error.message;
  return "Request failed";
}

export type ParsedErrorSummary = {
  failedStep: string;
  exitCode: string;
  errorLogPath: string;
  stderrExcerpt: string;
  possibleReason: string;
  suggestedAction: string;
};

export function parseErrorSummary(summary?: string | null, failedRule?: string | null): ParsedErrorSummary | null {
  if (!summary && !failedRule) return null;
  let parsed: Record<string, unknown> | null = null;
  if (summary) {
    try {
      parsed = JSON.parse(summary) as Record<string, unknown>;
    } catch {
      parsed = null;
    }
  }

  const lines = Array.isArray(parsed?.last_100_lines)
    ? (parsed?.last_100_lines as unknown[]).map(String)
    : summary
      ? [summary]
      : [];
  const excerpt = lines.slice(-8).join("\n") || "No stderr excerpt available.";
  const returnCode = typeof parsed?.return_code === "number" || typeof parsed?.return_code === "string" ? String(parsed.return_code) : "not set";
  const stderrPath = typeof parsed?.stderr_path === "string" ? parsed.stderr_path : "not set";
  const failedStep = failedRule || (typeof parsed?.failed_step === "string" ? parsed.failed_step : "workflow");
  const possibleReason = excerpt.includes("MissingRuleException")
    ? "Snakemake target or rule is not available for this controlled demo target."
    : "Inspect the failed rule stderr and Snakemake command artifact.";

  return {
    failedStep,
    exitCode: returnCode,
    errorLogPath: stderrPath,
    stderrExcerpt: excerpt,
    possibleReason,
    suggestedAction: "Open Logs, confirm stderr, then use resume or rerun_rule only after fixing the root cause.",
  };
}
