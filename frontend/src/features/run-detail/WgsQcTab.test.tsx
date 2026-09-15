import "@testing-library/jest-dom/vitest";
import {render, screen, within} from "@testing-library/react";
import {expect, it} from "vitest";
import type {Sample} from "../../api";
import {WgsQcTab} from "./WgsQcTab";

const sample: Sample = {sample_id: "SAMPLE-01", qc_status: "fail", qc_judgments: {
  clean_q30_percent: {value: 84, unit: "%", status: "fail", reason: "Outside release criterion", threshold: {min: 85, min_inclusive: true}},
  raw_gc_percent: {value: 40, unit: "%", status: "pass", threshold: {min: 39, max: 41}},
  average_depth: {value: null, status: "unknown", reason: "Value unavailable"},
  sex_match: {value: "Yes", status: "pass", reason: "Source-produced sex consistency judgment"},
}};

it("shows all available QC columns directly without thresholds and with failure reasons, without diagnostic disclosures", () => {
  const {container} = render(<WgsQcTab samples={[sample]} />);
  const table = screen.getByRole("table", {name: "WGS QC summary"});
  expect(within(table).getByRole("columnheader", {name: "Clean Q30"})).toBeInTheDocument();
  expect(within(table).getByRole("columnheader", {name: /Raw GC/})).toBeInTheDocument();
  expect(within(table).getByRole("columnheader", {name: "Sex consistency"})).toBeInTheDocument();
  expect(within(table).queryByRole("columnheader", {name: /Average depth/})).toBeNull();
  expect(within(table).getAllByRole("columnheader").at(-1)).toHaveTextContent("Reason");
  expect(container.querySelectorAll("details")).toHaveLength(0);
  expect(container.querySelectorAll("table")).toHaveLength(1);
  expect(table.closest(".table-wrap")).toHaveClass("wgs-qc-table-wrap");
  const reason = within(table).getByText("SAMPLE-01").closest("tr")!.lastElementChild!;
  expect(reason).toHaveTextContent("Clean Q30");
  expect(reason).toHaveTextContent("超出当前版本阈值");
  expect(reason).not.toHaveTextContent("Raw GC");
});

it("does not apply one sample's threshold to another and keeps zero and warnings visible", () => {
  const make = (id: string, min: number, value: number): Sample => ({sample_id: id, qc_status: "pass", qc_judgments: {
    average_depth: {value, unit: "×", status: value < min ? "fail" : "pass", threshold: {min}},
    contamination: {value: "CHARR 0.025 / AB 0.12", status: "warn", reason: "Contamination measurements exceed release criterion"},
  }});
  render(<WgsQcTab samples={[make("S1",30,0),make("S2",20,25)]} />);
  expect(screen.getByRole("columnheader", {name: "Average depth"})).toBeInTheDocument();
  const one=screen.getByText("S1").closest("tr")!;
  const two=screen.getByText("S2").closest("tr")!;
  expect(within(one).getByText("0 ×")).toBeInTheDocument();
  expect(within(one).queryByText(/≥|按样本/)).toBeNull();
  expect(within(two).queryByText(/≥|按样本/)).toBeNull();
  expect(screen.getByRole("columnheader", {name: "Contamination"})).toBeInTheDocument();
  expect(one.lastElementChild).toHaveTextContent("污染指标超出当前版本阈值");
});

it("retains failed source QC when metric evidence cannot explain it", () => {
  render(<WgsQcTab samples={[{sample_id:"S0",qc_status:"fail",qc_judgments:{contamination:{value:null,status:"unknown"}}}]} />);
  expect(screen.queryByRole("columnheader",{name:/Contamination/})).toBeNull();
  expect(screen.getByText(/来源汇总 QC 未通过.*缺少可展示的原因证据/)).toBeInTheDocument();
});
