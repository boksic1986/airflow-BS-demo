import "@testing-library/jest-dom/vitest";

import {render, screen, within} from "@testing-library/react";
import {describe, expect, it} from "vitest";

import type {RuleEvent, RunProgressResponse} from "../../api";
import {RunWorkflowTab} from "./RunWorkflowTab";

describe("RunWorkflowTab", () => {
  it("groups NIPT rules into operator phases without rendering the raw rule-job table", () => {
    const rules: RuleEvent[] = Array.from({length: 60}, (_, index) => ({
      rule: "map",
      sample_id: `S${String(index + 1).padStart(3, "0")}`,
      status: "success",
      snakemake_jobid: String(index + 1),
      return_code: 0,
    }));
    rules.push({
      rule: "aneuscreen_predict",
      sample_id: "S061",
      status: "running",
      snakemake_jobid: "61",
      return_code: null,
    });

    render(<RunWorkflowTab progress={null} rules={rules} />);

    expect(screen.getByRole("heading", {name: /Pipeline phase summary/i})).toBeInTheDocument();
    expect(screen.getAllByText("Mapping").length).toBeGreaterThan(0);
    expect(screen.getAllByText("T21 classifier").length).toBeGreaterThan(0);
    expect(screen.queryByRole("table", {name: /Pipeline rule jobs/i})).not.toBeInTheDocument();
  });

  it("shows only the PGT-A Predict execution path and hides skipped legacy branches", () => {
    const progress = {
      airflow_tasks: [
        {task_id: "validate_request", state: "success"},
        {task_id: "pgta_predict.run_pgta_mapping", state: "success"},
        {task_id: "pgta_pipeline.run_pgta_mapping", state: "skipped"},
        {task_id: "run_pgta_target", state: "skipped"},
      ],
    } as RunProgressResponse;

    render(<RunWorkflowTab progress={progress} rules={[]} />);

    const selectedPath = screen.getByLabelText("Selected Airflow execution path");
    expect(within(selectedPath).getByText("Mapping reads")).toBeInTheDocument();
    expect(within(selectedPath).queryByText("Run PGT-A workflow")).not.toBeInTheDocument();
    expect(screen.queryByText(/Alternate paths/i)).not.toBeInTheDocument();
    expect(screen.queryByText("run_pgta_target")).not.toBeInTheDocument();
    expect(screen.queryByText("pgta_pipeline.run_pgta_mapping")).not.toBeInTheDocument();
  });

  it("renders canceled rule events as terminal phase work", () => {
    render(<RunWorkflowTab progress={null} rules={[
      {rule: "map", sample_id: "S1", status: "failed"},
      {rule: "map", sample_id: "S2", status: "canceled"},
    ]} />);

    const phaseTable = screen.getByRole("table", {name: /Pipeline phase summary/i});
    expect(within(phaseTable).getByText("Canceled")).toBeInTheDocument();
    const mappingRow = within(phaseTable).getByText("Mapping").closest("tr");
    expect(mappingRow?.querySelectorAll("td")[6]).toHaveTextContent("1");
  });
});
