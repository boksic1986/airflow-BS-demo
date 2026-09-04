import "@testing-library/jest-dom/vitest";

import {fireEvent, render, screen, within} from "@testing-library/react";
import {describe, expect, it, vi} from "vitest";

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

  it("shows the WGS business-stage graph without raw Airflow task IDs", () => {
    const progress = {
      pipeline: "wgs",
      airflow_tasks: [
        {task_id: "validate_request", state: "success"},
        {task_id: "prepare_wgs_batch", state: "success"},
        {task_id: "input_transfer.start_step1_upload", state: "success"},
        {task_id: "submit_step2_master", state: "running"},
        {task_id: "start_step3_monitor", state: "queued"},
        {task_id: "submit_master", state: "success"},
        {task_id: "run_nipt_docker", state: "success"},
      ],
      orchestration_stages: [
        {stage_code: "step1_upload", step_number: 1, label: "Uploading FASTQ", status: "success", progress_available: true, completed_units: 1024 ** 3, total_units: 2 * 1024 ** 3, unit: "bytes"},
        {stage_code: "step2_master", step_number: 2, label: "Starting WGS workflow", status: "running"},
        {stage_code: "step3_monitor", step_number: 3, label: "WGS workflow running", status: "pending"},
        {stage_code: "step4_publish", step_number: 4, label: "Publishing WGS results", status: "pending"},
        {stage_code: "step5_download", step_number: 5, label: "Downloading WGS results", status: "pending"},
        {stage_code: "step6_materialize", step_number: 6, label: "Materializing local results", status: "pending"},
      ],
    } as RunProgressResponse;

    render(<RunWorkflowTab progress={progress} rules={[]} />);

    expect(screen.getByRole("heading", {name: "WGS CCE orchestration path"})).toBeInTheDocument();
    const graph = screen.getByLabelText("WGS stage dependency graph");
    expect(within(graph).getByText("Uploading FASTQ")).toBeInTheDocument();
    expect(within(graph).getByText("WGS workflow running")).toBeInTheDocument();
    expect(within(graph).getByText("Downloading WGS results")).toBeInTheDocument();
    expect(within(graph).getByText("1.0 GiB / 2.0 GiB")).toBeInTheDocument();
    expect(screen.queryByText("wait_step3_analysis")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Selected Airflow execution path")).not.toBeInTheDocument();
  });

  it("uses backend orchestration states and keeps ETA history out of the Rule message", () => {
    const progress = {
      analysis_id: "WGS_SUCCESS",
      pipeline: "wgs",
      status: "success",
      current_step: "finalize_run",
      current_source: "biodemo",
      note: "",
      not_in_airflow: false,
      progress_source: "run-stage-state",
      airflow_tasks: [],
      rule_events: [],
      orchestration_stages: [
        {stage_code: "step1_upload", step_number: 1, label: "Uploading FASTQ", status: "success"},
        {stage_code: "step2_master", step_number: 2, label: "Starting WGS workflow", status: "success"},
        {stage_code: "step3_monitor", step_number: 3, label: "WGS workflow running", status: "success"},
        {stage_code: "step4_publish", step_number: 4, label: "Publishing WGS results", status: "success"},
        {stage_code: "step5_download", step_number: 5, label: "Downloading WGS results", status: "success"},
        {stage_code: "step6_materialize", step_number: 6, label: "Materializing local results", status: "success"},
      ],
    } as RunProgressResponse;
    const rules: RuleEvent[] = [
      {
        rule: "pre_process_mapping",
        phase: "Pre-calling",
        phase_order: 10,
        sample_id: "WGS001-WGS",
        family_id: "F001",
        sequence: 12,
        status: "success",
        eta_model: "insufficient_history",
        eta_history_count: 0,
      },
    ];

    render(<RunWorkflowTab progress={progress} rules={rules} />);

    const graph = screen.getByLabelText("WGS stage dependency graph");
    expect(graph.querySelectorAll(".wgs-stage-node.success")).toHaveLength(6);
    expect(screen.getByRole("columnheader", {name: "Execution order"})).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", {name: "Layer / sequence"})).not.toBeInTheDocument();
    const ruleTable = screen.getByRole("table", {name: "WGS rule instances"});
    expect(within(ruleTable).getByText("WGS001-WGS")).toBeInTheDocument();
    expect(within(ruleTable).getByText("F001")).toBeInTheDocument();
    expect(within(ruleTable).getByText("12")).toBeInTheDocument();
    expect(within(ruleTable).queryByText("No reliable ETA (0/3)")).not.toBeInTheDocument();
  });

  it("opens the registered analysis log from a monitored WGS Rule", () => {
    const openLog = vi.fn();
    render(
      <RunWorkflowTab
        progress={{pipeline: "wgs"} as RunProgressResponse}
        onOpenLog={openLog}
        rules={[
          {
            rule: "pre_process_mapping",
            sample_id: "WGS26080568",
            family_id: "JX26G00230117",
            status: "running",
            analysis_log_key: "opaque-analysis-log",
          },
        ]}
      />,
    );

    fireEvent.click(screen.getByRole("button", {name: "Open log for pre_process_mapping"}));

    expect(openLog).toHaveBeenCalledWith("opaque-analysis-log");
  });

  it("shows only the NIPT Docker Airflow path and NIPT rule phases", () => {
    const progress = {
      pipeline: "nipt_docker",
      airflow_tasks: [
        {task_id: "validate_request", state: "success"},
        {task_id: "prepare_nipt_docker_run", state: "success"},
        {task_id: "run_nipt_docker", state: "running"},
        {task_id: "wgs_pipeline.pre_calling", state: "success"},
      ],
    } as RunProgressResponse;

    render(<RunWorkflowTab progress={progress} rules={[{rule: "aneuscreen_predict", sample_id: "N1", status: "running"}]} />);

    expect(screen.getByRole("heading", {name: "NIPT full analysis path"})).toBeInTheDocument();
    const selectedPath = screen.getByLabelText("Selected Airflow execution path");
    expect(within(selectedPath).getByText("Prepare NIPT Docker run")).toBeInTheDocument();
    expect(within(selectedPath).getByText("Run NIPT Docker workflow")).toBeInTheDocument();
    expect(within(selectedPath).queryByText("Pre-calling")).not.toBeInTheDocument();
    expect(screen.getAllByText("T21 classifier").length).toBeGreaterThan(0);
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
