import type {RuleEvent, RunDetail, RunProgressResponse, RunSummary} from "../api";

import {isActiveStatus, isFailedStatus, normalizeStatus} from "./status";

export type RunProgress = {
  percent: number;
  label: string;
  currentStep: string;
  note: string;
  notInAirflow: boolean;
  failedStep?: string;
};

const terminalRuleStatuses = new Set(["success", "failed", "fail", "error", "skipped", "canceled", "cancelled", "terminated"]);

export function getProjectDisplayName(run: RunSummary, detail?: RunDetail | null): string {
  const projectName = detail?.params?.project_name;
  if (typeof projectName === "string" && projectName.trim()) return projectName.trim();
  return run.analysis_id;
}

export function computeRunProgress(run: RunSummary, detail?: RunDetail | null, rules: RuleEvent[] = []): RunProgress {
  const status = normalizeStatus(detail?.status || run.status);
  const failedRule = rules.find((rule) => isFailedStatus(rule.status));
  const activeRule = rules.find((rule) => isActiveStatus(rule.status));

  if (status === "created") {
    return {
      percent: 0,
      label: "0%",
      currentStep: "Created only",
      note: "Created in backend only",
      notInAirflow: true,
    };
  }

  if (["submitted", "queued", "scheduled"].includes(status)) {
    return {
      percent: status === "submitted" ? 10 : 5,
      label: `${status === "submitted" ? 10 : 5}%`,
      currentStep: "Airflow handoff",
      note: detail?.dag_run_id ? "DAG run created" : "Waiting for dag_run_id",
      notInAirflow: !detail?.dag_run_id,
    };
  }

  if (status === "success") {
    return {
      percent: 100,
      label: "100%",
      currentStep: "Workflow complete",
      note: "Airflow success",
      notInAirflow: false,
    };
  }

  if (isFailedStatus(status)) {
    const percent = rules.length ? Math.max(10, Math.round((terminalRuleCount(rules) / rules.length) * 100)) : 50;
    return {
      percent,
      label: `${percent}%`,
      currentStep: failedRule?.rule || "Failed",
      note: failedRule?.message || "Failed in workflow",
      notInAirflow: false,
      failedStep: failedRule?.rule,
    };
  }

  if (status === "running") {
    if (rules.length) {
      const percent = Math.max(15, Math.round((terminalRuleCount(rules) / rules.length) * 100));
      return {
        percent,
        label: `${percent}%`,
        currentStep: activeRule?.rule || latestRule(rules)?.rule || "Running",
        note: activeRule ? "Rule running" : "Rule events received",
        notInAirflow: false,
      };
    }
    return {
      percent: 15,
      label: "15%",
      currentStep: "Waiting for workflow events",
      note: "No rule events yet",
      notInAirflow: false,
    };
  }

  return {
    percent: rules.length ? Math.round((terminalRuleCount(rules) / rules.length) * 100) : 0,
    label: rules.length ? `${Math.round((terminalRuleCount(rules) / rules.length) * 100)}%` : "0%",
    currentStep: latestRule(rules)?.rule || "Unknown",
    note: "Progress estimate",
    notInAirflow: false,
  };
}

export function progressFromResponse(progress: RunProgressResponse): RunProgress {
  return {
    percent: Math.max(0, Math.min(100, Math.round(progress.percent))),
    label: `${Math.max(0, Math.min(100, Math.round(progress.percent)))}%`,
    currentStep: progress.current_step || "Unknown",
    note: progress.note || `Progress source: ${progress.progress_source}`,
    notInAirflow: progress.not_in_airflow,
    failedStep: progress.rule_events.find((rule) => isFailedStatus(rule.status))?.rule,
  };
}

function terminalRuleCount(rules: RuleEvent[]): number {
  return rules.filter((rule) => terminalRuleStatuses.has(normalizeStatus(rule.status))).length;
}

function latestRule(rules: RuleEvent[]): RuleEvent | undefined {
  return [...rules].reverse().find((rule) => rule.rule);
}
