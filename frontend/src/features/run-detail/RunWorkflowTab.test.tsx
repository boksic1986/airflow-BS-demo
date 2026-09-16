import "@testing-library/jest-dom/vitest";
import {fireEvent, render, screen, within} from "@testing-library/react";
import {expect, it, vi} from "vitest";
import type {RulePage, RunProgressResponse} from "../../api";
import {RunWorkflowTab} from "./RunWorkflowTab";

it("defaults to running rules, twenty per page, without expanding execution-group inventory", () => {
  const rules=Array.from({length:21},(_,i)=>({rule:`active-${i}`,status:"running",execution_group:"group-a",origin:"master:opaque",execution_group_members:[{rule:"not-started-member"}]}));
  render(<RunWorkflowTab progress={null} rules={[{rule:"done",status:"success"},...rules]} />);
  const table=screen.getByRole("table",{name:"Pipeline rule instances"});
  expect(screen.getByLabelText("Rule status")).toHaveValue("running");
  expect(within(table).getAllByRole("row")).toHaveLength(21);
  expect(within(table).queryByText("done")).toBeNull();
  expect(within(table).queryByText(/Execution group|master:opaque|not-started-member/)).toBeNull();
  fireEvent.click(screen.getByRole("button",{name:"Next"}));
  expect(within(table).getByText("active-20")).toBeInTheDocument();
  expect(within(table).getAllByRole("row")).toHaveLength(2);
  fireEvent.change(screen.getByLabelText("Rule status"),{target:{value:""}});
  expect(within(table).getByText("done")).toBeInTheDocument();
});

it("passes running/twenty-row paging and exact independent filters to the server query", () => {
  const change=vi.fn();
  render(<RunWorkflowTab progress={null} rules={[]} page={{items:[],limit:20,offset:0,total:21,current_attempt:2}} onQueryChange={change} />);
  expect(screen.queryByRole("combobox",{name:"Attempt"})).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Sample"),{target:{value:"S1"}});
  expect(change).toHaveBeenLastCalledWith(expect.objectContaining({sampleId:"S1",status:"running",limit:20,offset:0}));
  fireEvent.click(screen.getByRole("button",{name:"Next"}));
  expect(change).toHaveBeenLastCalledWith(expect.objectContaining({status:"running",limit:20,offset:20}));
});

it("filters sample and family independently without prefix matches", () => {
  render(<RunWorkflowTab progress={null} rules={[
    {rule:"sample-match",sample_id:"S1",family_id:"F1",status:"running"},
    {rule:"family-only",sample_id:"S2",family_id:"S1",status:"running"},
    {rule:"prefix-only",sample_id:"S10",family_id:"F1",status:"running"},
  ]} />);
  fireEvent.change(screen.getByLabelText("Sample"),{target:{value:"S1"}});
  const table=screen.getByRole("table",{name:"Pipeline rule instances"});
  expect(within(table).getByText("sample-match")).toBeInTheDocument();
  expect(within(table).queryByText("family-only")).toBeNull();
  expect(within(table).queryByText("prefix-only")).toBeNull();
  fireEvent.change(screen.getByLabelText("Family"),{target:{value:"S1"}});
  expect(within(table).queryByText("sample-match")).toBeNull();
});

it("keeps full phase summaries independent of running-only rows", () => {
  render(<RunWorkflowTab progress={null} rules={[{rule:"a",phase:"Mapping",status:"success"},{rule:"b",phase:"Mapping",status:"canceled"}]} />);
  expect(within(screen.getByRole("table",{name:"Pipeline phase summary"})).getByText("canceled")).toBeInTheDocument();
});

it("uses attempt-wide server summaries for both phase displays while row status changes", () => {
  const phase_summaries = [{phase:"FASTQ QC",status:"running",total:71,running:20,success:51,failed:0,canceled:0}];
  const renderPage = (status: string, total: number) => {
    const items = total ? [{rule:`row-${status}`,phase:"FASTQ QC",status}] : [];
    const page: RulePage = {items,total,limit:20,offset:0,attempt:1,phase_summaries};
    return <RunWorkflowTab progress={null} rules={items} page={page} query={{status,limit:20,offset:0}} onQueryChange={() => {}} />;
  };
  const view = render(renderPage("running",20));
  for (const [status,total] of [["running",20],["success",51],["failed",0],["",71]] as const) {
    view.rerender(renderPage(status,total));
    const summary = screen.getByRole("table",{name:"Pipeline phase summary"});
    const cells = within(within(summary).getAllByRole("row")[1]).getAllByRole("cell");
    expect(cells.map(cell => cell.textContent)).toEqual(["FASTQ QC","running","71","20","51","0","0"]);
    expect(within(screen.getByLabelText("Layered workflow timeline")).getByText("51/71 jobs complete")).toBeInTheDocument();
    const rows = screen.getByRole("table",{name:"Pipeline rule instances"});
    if (total) expect(within(rows).getByText(`row-${status}`)).toBeInTheDocument();
    else expect(within(rows).getByText("No matching Rule instances.")).toBeInTheDocument();
  }
});

it("shows stage timestamps on hover, with no embedded estimate or missing-history message", () => {
  const progress={pipeline:"wgs",orchestration_stages:[
    {stage_code:"step4_publish",step_number:4,label:"Publishing",status:"success",started_at:"2026-09-15T00:00:00Z",ended_at:"2026-09-15T00:05:00Z",estimate_model:"stage_median_linear_v1"},
    {stage_code:"step6_materialize",step_number:6,label:"Materializing",status:"pending",estimate_model:"stage_median_linear_v1"},
  ]} as RunProgressResponse;
  render(<RunWorkflowTab progress={progress} rules={[]} />);
  const graph=screen.getByLabelText("Pipeline stage dependency graph");
  expect(within(graph).queryByRole("progressbar")).toBeNull();
  expect(within(graph).queryByText(/暂无预估|缺少足够/)).toBeNull();
  expect(within(graph).getByText("Publishing").parentElement).toHaveAttribute("title",expect.stringMatching(/开始.*2026-09-15.*完成.*2026-09-15/s));
  expect(within(graph).getByText("Materializing").parentElement).toHaveAttribute("title","开始：未记录\n完成：未记录");
});

it("opens registered logs for current rules", () => {
  const open=vi.fn();
  render(<RunWorkflowTab progress={null} onOpenLog={open} rules={[{rule:"mapping",status:"running",analysis_log_key:"opaque-log"}]} />);
  fireEvent.click(screen.getByRole("button",{name:"Open log for mapping"}));
  expect(open).toHaveBeenCalledWith("opaque-log");
});
