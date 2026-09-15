import "@testing-library/jest-dom/vitest";
import {render, screen, within} from "@testing-library/react";
import {expect, it} from "vitest";

import type {Sample} from "../../api";
import {WgsQcTab} from "./WgsQcTab";

const sample: Sample = {
  sample_id: "SAMPLE-01",
  status: "success",
  qc_status: "pass",
  qc_metrics: {
    clean_q30_percent: 91.2,
    mapped_reads_percent: 99.8,
    average_depth: null,
    coverage_20x_percent: 89.5,
    contamination: "PASS",
  },
  qc_judgments: {
    clean_q30_percent: {value: 91.2, unit: "%", status: "unknown", reason: "Release policy provenance unavailable", provenance: {release_id: "wgs-4.2.1-34bfcbf"}},
    mapped_reads_percent: {value: 99.8, unit: "%", status: "fail", reason: "Outside release criterion", threshold: {min: 99.9, min_inclusive: true}, provenance: {release_id: "wgs-4.2.1-cc9bde3"}},
    average_depth: {value: null, unit: "×", status: "unknown", reason: "Value unavailable", threshold: {min: 20, min_inclusive: true}},
    coverage_20x_percent: {value: 89.5, unit: "%", status: "unknown", reason: "No applicable criterion in this release"},
    contamination: {value: "PASS", unit: "status", status: "unknown", reason: "Value or release provenance unavailable", provenance: {release_id: "wgs-4.2.1-34bfcbf"}},
    raw_gc_percent: {value: 40.1, unit: "%", status: "pass", reason: "Within release criterion", threshold: {min: 39.36, max: 41.48, min_inclusive: true, max_inclusive: true}},
    sex_match: {value: null, unit: "status", status: "unknown", reason: "Individual safe evidence unavailable; retained source aggregate includes this check"},
  },
};

it("keeps source QC separate while showing compact key metric judgments", () => {
  const {container} = render(<WgsQcTab samples={[sample]} />);
  const summary = screen.getByRole("table", {name: "WGS QC summary"});
  const row = within(summary).getByText("SAMPLE-01").closest("tr");

  expect(row).not.toBeNull();
  expect(row!.querySelector("td:nth-child(2) .status-badge[title='pass']")).toBeInTheDocument();
  expect(row!.querySelectorAll(":scope > td > .qc-metric .status-badge[title='unknown']")).toHaveLength(4);
  expect(row!.querySelector(":scope > td:nth-child(4) > .qc-metric .qc-value-fail")).toHaveTextContent("99.8 %");
  expect(row!.querySelector(":scope > td:nth-child(5) > .qc-metric .qc-value-unknown")).toHaveTextContent("-");
  expect(container.querySelectorAll(".qc-metric details")).toHaveLength(0);
});

it("uses one sample disclosure for friendly complete details and isolates raw diagnostics", () => {
  render(<WgsQcTab samples={[sample]} />);

  const disclosure = screen.getByText("Review all metrics").closest("details");
  expect(disclosure).not.toBeNull();
  const detailsTable = within(disclosure!).getByRole("table", {name: "QC metric details for SAMPLE-01"});
  expect(within(detailsTable).getByText("Raw GC")).toBeInTheDocument();
  expect(within(detailsTable).getByText("Sex consistency")).toBeInTheDocument();
  expect(within(detailsTable).getByText("当前流程版本暂无已审核 QC 判定策略")).toBeInTheDocument();
  expect(within(detailsTable).getByText("当前版本不适用此判定")).toBeInTheDocument();
  expect(within(detailsTable).getByText("个体级安全证据不可用；来源汇总 QC 仍包含此项检查")).toBeInTheDocument();
  expect(within(detailsTable).getByText("≥ 99.9 %")).toBeInTheDocument();
  expect(within(detailsTable).getAllByText(/wgs-4\.2\.1-34bfcbf/).length).toBeGreaterThan(0);

  const diagnostics = within(disclosure!).getByText("Raw diagnostic fields").closest("details");
  expect(diagnostics).not.toBeNull();
  expect(within(diagnostics!).getByText(/clean_q30_percent/)).toBeInTheDocument();
  expect(within(diagnostics!).getByText(/Release policy provenance unavailable/)).toBeInTheDocument();
  expect(within(detailsTable).queryByText("clean_q30_percent")).toBeNull();
});
