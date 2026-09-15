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

it("keeps source QC separate and shows only available source judgments", () => {
  const {container} = render(<WgsQcTab samples={[sample]} />);
  const summary = screen.getByRole("table", {name: "WGS QC summary"});
  const row = within(summary).getByText("SAMPLE-01").closest("tr");

  expect(row).not.toBeNull();
  expect(row!.querySelector("td:nth-child(2) .status-badge[title='pass']")).toBeInTheDocument();
  expect(row!.querySelectorAll(".status-badge[title='unknown']")).toHaveLength(0);
  expect(row!.querySelector(":scope > td > .qc-metric .qc-value-fail")).toHaveTextContent("99.8 %");
  expect(within(summary).queryByRole("columnheader", {name: "Average depth"})).toBeNull();
  expect(within(summary).queryByRole("columnheader", {name: "Clean Q30"})).toBeNull();
  expect(container.querySelectorAll(".qc-metric details")).toHaveLength(0);
});

it("uses one sample disclosure for friendly complete details and isolates raw diagnostics", () => {
  render(<WgsQcTab samples={[sample]} />);

  const disclosure = screen.getByText("Review all metrics").closest("details");
  expect(disclosure).not.toBeNull();
  const detailsTable = within(disclosure!).getByRole("table", {name: "QC metric details for SAMPLE-01"});
  expect(within(detailsTable).getByText("Raw GC")).toBeInTheDocument();
  expect(within(detailsTable).queryByText("Sex consistency")).toBeNull();
  expect(within(detailsTable).queryByText("Coverage ≥20X")).toBeNull();
  expect(within(detailsTable).getAllByRole("row")).toHaveLength(3);
  expect(within(detailsTable).getByText("≥ 99.9 %")).toBeInTheDocument();

  const diagnostics = within(disclosure!).getByText("Raw diagnostic fields").closest("details");
  expect(diagnostics).not.toBeNull();
  expect(within(diagnostics!).getByText(/mapped_reads_percent/)).toBeInTheDocument();
  expect(within(diagnostics!).queryByText(/clean_q30_percent/)).toBeNull();
  expect(within(diagnostics!).queryByText(/Release policy provenance unavailable/)).toBeNull();
  expect(within(detailsTable).queryByText("clean_q30_percent")).toBeNull();
});

it("retains zero and explicit source results without inventing missing sample judgments", () => {
  render(<WgsQcTab samples={[
    {...sample, qc_metrics: {average_depth: 0, contamination: "WARNING"}, qc_judgments: {
      average_depth: {value: 0, status: "fail", unit: "×"},
      contamination: {value: "WARNING", status: "warn", unit: "status"},
      raw_gc_percent: {value: " ", status: "pass"},
    }},
    {sample_id: "SAMPLE-02", status: "success", qc_status: "pass", qc_metrics: {raw_gc_percent: 40}},
  ]} />);
  const summary = screen.getByRole("table", {name: "WGS QC summary"});
  expect(within(summary).getByRole("columnheader", {name: "Average depth"})).toBeInTheDocument();
  expect(within(summary).getAllByText("0 ×").length).toBeGreaterThan(0);
  expect(within(summary).getAllByText("WARNING").length).toBeGreaterThan(0);
  expect(within(summary).queryByText("Raw GC")).toBeNull();
  const missingRow = within(summary).getByText("SAMPLE-02").closest("tr")!;
  expect(within(missingRow).getByText("暂无可展示的质控判定指标")).toBeInTheDocument();
  expect(missingRow.querySelector(".status-badge[title='unknown']")).toBeNull();
});
