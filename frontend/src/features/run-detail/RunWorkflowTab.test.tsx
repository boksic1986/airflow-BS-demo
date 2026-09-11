import "@testing-library/jest-dom/vitest";

import {fireEvent, render, screen, within} from "@testing-library/react";
import {describe, expect, it, vi} from "vitest";

import type {RuleEvent, RunProgressResponse} from "../../api";
import {RunWorkflowTab} from "./RunWorkflowTab";

describe("RunWorkflowTab", () => {
  it("expands group member rules, including members outside the current page", () => {
    render(<RunWorkflowTab progress={null} rules={[{rule: "mapping", status: "planned", execution_group: "master:group", execution_group_members: [{rule: "mapping", snakemake_jobid: "1"}, {rule: "Dedup", snakemake_jobid: "2"}]}]} />);
    const detail = screen.getByText("master:group").closest("details")!;
    expect(within(detail).getByText("Dedup")).toBeInTheDocument();
  });

  it("summarizes completed and canceled terminal members as canceled", () => {
    render(<RunWorkflowTab progress={null} rules={[{rule: "a", phase: "Mapping", status: "success"}, {rule: "b", phase: "Mapping", status: "canceled"}]} />);
    const summary = screen.getByRole("table", {name: /Pipeline phase summary/i});
    expect(within(summary).getByText("canceled").closest(".status-badge")).toBeInTheDocument();
  });
  it("keeps duplicate rule instances attached to their own expanded evidence after reordering", () => {
    const a = {attempt: 2, rule_instance_id: "a", rule: "mapping", sample_id: "S1", sequence: 1, status: "running", execution_group: "group-a"};
    const b = {...a, rule_instance_id: "b", execution_group: "group-b"};
    const {rerender} = render(<RunWorkflowTab progress={null} rules={[a, b]} />);
    const original = screen.getByText("group-a").closest("details")!;
    original.open = true;
    rerender(<RunWorkflowTab progress={null} rules={[b, a]} />);
    expect(screen.getByText("group-a").closest("details")).toBe(original);
    expect(screen.getByText("group-a").closest("details")).toHaveAttribute("open");
    expect(screen.getByText("group-b").closest("details")).not.toHaveAttribute("open");
  });

  it("filters samples and families independently with exact identifiers", () => {
    render(<RunWorkflowTab progress={null} rules={[
      {rule: "sample-match", sample_id: "S1", family_id: "F1", status: "running"},
      {rule: "family-only", sample_id: "S2", family_id: "S1", status: "running"},
      {rule: "prefix-only", sample_id: "S10", family_id: "F1", status: "running"},
    ]} />);
    fireEvent.change(screen.getByLabelText("Sample"), {target: {value: "S1"}});
    const table = screen.getByRole("table", {name: "Pipeline rule instances"});
    expect(within(table).getByText("sample-match")).toBeInTheDocument();
    expect(within(table).queryByText("family-only")).not.toBeInTheDocument();
    expect(within(table).queryByText("prefix-only")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Family"), {target: {value: "S1"}});
    expect(within(table).queryByText("sample-match")).not.toBeInTheDocument();
  });

  it("groups adapter-projected rule phases", () => {
    const rules: RuleEvent[] = [
      {rule: "align", phase: "Mapping", sample_id: "S001", status: "success"},
      {rule: "call", phase: "Variant calling", sample_id: "S001", status: "running"},
    ];

    render(<RunWorkflowTab progress={null} rules={rules} />);

    const summary = screen.getByRole("table", {name: /Pipeline phase summary/i});
    expect(within(summary).getByText("Mapping")).toBeInTheDocument();
    expect(within(summary).getByText("Variant calling")).toBeInTheDocument();
    expect(screen.getByRole("table", {name: "Pipeline rule instances"})).toBeInTheDocument();
  });

  it("shows adapter orchestration stages instead of raw Airflow task ids", () => {
    const progress = {
      pipeline: "wgs",
      airflow_tasks: [
        {task_id: "validate_request", state: "success"},
        {task_id: "submit_step2_master", state: "running"},
      ],
      orchestration_stages: [
        {stage_code: "step1_upload", step_number: 1, label: "Uploading FASTQ", status: "success", progress_available: true, completed_units: 1024 ** 3, total_units: 2 * 1024 ** 3, unit: "bytes"},
        {stage_code: "step2_master", step_number: 2, label: "Starting workflow", status: "running"},
      ],
    } as RunProgressResponse;

    render(<RunWorkflowTab progress={progress} rules={[]} />);

    const graph = screen.getByLabelText("Pipeline stage dependency graph");
    expect(within(graph).getByText("Uploading FASTQ")).toBeInTheDocument();
    expect(within(graph).getByText("Starting workflow")).toBeInTheDocument();
    expect(within(graph).getByText("1.0 GiB / 2.0 GiB")).toBeInTheDocument();
    expect(screen.queryByLabelText("Selected Airflow execution path")).not.toBeInTheDocument();
  });

  it("uses a registry-neutral Airflow path when no stage projection exists", () => {
    const progress = {
      pipeline: "synthetic",
      airflow_tasks: [
        {task_id: "validate_request", state: "success"},
        {task_id: "run_analysis", state: "running"},
      ],
    } as RunProgressResponse;

    render(<RunWorkflowTab progress={progress} rules={[]} />);

    const path = screen.getByLabelText("Selected Airflow execution path");
    expect(within(path).getByText("Validate run request")).toBeInTheDocument();
    expect(within(path).getByText("Run Analysis")).toBeInTheDocument();
  });

  it("opens the registered analysis log from a rule", () => {
    const openLog = vi.fn();
    render(<RunWorkflowTab progress={{pipeline: "wgs"} as RunProgressResponse} onOpenLog={openLog} rules={[{
      rule: "pre_process_mapping",
      phase: "Pre-calling",
      sample_id: "S001",
      status: "running",
      analysis_log_key: "opaque-analysis-log",
    }]} />);

    fireEvent.click(screen.getByRole("button", {name: "Open log for pre_process_mapping"}));
    expect(openLog).toHaveBeenCalledWith("opaque-analysis-log");
  });

  it("renders canceled rule events as terminal phase work", () => {
    render(<RunWorkflowTab progress={null} rules={[
      {rule: "align", phase: "Mapping", sample_id: "S1", status: "failed"},
      {rule: "align", phase: "Mapping", sample_id: "S2", status: "canceled"},
    ]} />);

    const phaseTable = screen.getByRole("table", {name: /Pipeline phase summary/i});
    const row = within(phaseTable).getByText("Mapping").closest("tr");
    expect(row?.querySelectorAll("td")[6]).toHaveTextContent("1");
  });
});
