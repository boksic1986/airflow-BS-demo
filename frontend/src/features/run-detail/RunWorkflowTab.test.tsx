import "@testing-library/jest-dom/vitest";

import {render, screen, within} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {describe, expect, it} from "vitest";

import type {RuleEvent} from "../../api";
import {RunWorkflowTab} from "./RunWorkflowTab";

describe("RunWorkflowTab", () => {
  it("groups NIPT rules into operator phases and paginates large job sets", async () => {
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
    const jobsTable = screen.getByRole("table", {name: /Pipeline rule jobs/i});
    expect(within(jobsTable).getAllByRole("row")).toHaveLength(51);
    expect(within(jobsTable).getByText("S061")).toBeInTheDocument();
    expect(within(jobsTable).queryByText("S060")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", {name: /Next rule jobs/i}));

    expect(within(jobsTable).getByText("S060")).toBeInTheDocument();
  });
});
