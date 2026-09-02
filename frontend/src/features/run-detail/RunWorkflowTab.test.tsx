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
    } as RunProgressResponse;

    render(<RunWorkflowTab progress={progress} rules={[]} />);

    expect(screen.getByRole("heading", {name: "WGS CCE orchestration path"})).toBeInTheDocument();
    const graph = screen.getByLabelText("WGS stage dependency graph");
    expect(within(graph).getByText("Uploading FASTQ")).toBeInTheDocument();
    expect(within(graph).getByText("WGS workflow running")).toBeInTheDocument();
    expect(within(graph).getByText("Downloading WGS results")).toBeInTheDocument();
    expect(screen.queryByText("wait_step3_analysis")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Selected Airflow execution path")).not.toBeInTheDocument();
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
