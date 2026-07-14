import "@testing-library/jest-dom/vitest";

import {render, screen, within} from "@testing-library/react";
import {describe, expect, it} from "vitest";

import {RunQcTab} from "./RunQcTab";


describe("RunQcTab", () => {
  it("ignores informational unknown metrics when computing the sample QC status", () => {
    render(
      <RunQcTab
        qc={{
          summary: {pass: 1, warn: 0, fail: 0, unknown: 1},
          sample_summary: {pass: 1, warn: 0, fail: 0, unknown: 0},
          items: [
            {
              sample_id: "NIPT26040001.A01",
              metric_name: "read_count",
              metric_value: "6000000",
              metric_numeric: 6000000,
              threshold: "reported",
              status: "unknown",
              decision_metric: false,
            },
            {
              sample_id: "NIPT26040001.A01",
              metric_name: "Q30",
              metric_value: "95.2",
              metric_numeric: 95.2,
              threshold: ">=85",
              status: "pass",
              decision_metric: true,
            },
          ],
        }}
      />,
    );

    const matrix = screen.getByRole("table", {name: "QC decision matrix"});
    const row = within(matrix).getByText("NIPT26040001.A01").closest("tr");
    expect(row).not.toBeNull();
    expect(row).toHaveTextContent("pass");
    expect(row).not.toHaveTextContent("unknown");
  });

  it("shows QC unavailable after workflow failure and keeps informational metrics separate", () => {
    render(
      <RunQcTab
        runStatus="failed"
        qc={{
          summary: {pass: 0, warn: 0, fail: 0, unknown: 1},
          sample_summary: {pass: 0, warn: 0, fail: 0, unknown: 1},
          items: [{sample_id: "S1", metric_name: "read_count", metric_value: "100000", status: "unknown", threshold: "reported", decision_metric: false}],
        }}
      />,
    );

    expect(screen.getByText("QC unavailable")).toBeInTheDocument();
    expect(screen.getByRole("heading", {name: "Informational"})).toBeInTheDocument();
    expect(screen.getByText("read_count")).toBeInTheDocument();
  });

  it("formats NIPT percentages, fetal fraction, PGT-A decimals, and read counts consistently", () => {
    render(
      <RunQcTab
        runStatus="success"
        qc={{
          summary: {pass: 1, warn: 0, fail: 0, unknown: 0},
          sample_summary: {pass: 1, warn: 0, fail: 0, unknown: 0},
          items: [
            {sample_id: "S1", metric_name: "read_count", metric_value: "12600000", metric_numeric: 12600000, threshold: "reported", status: "pass", decision_metric: false},
            {sample_id: "S1", metric_name: "unique_mapping_rate", metric_value: "%74.3", threshold: ">=60", status: "pass", decision_metric: true},
            {sample_id: "S1", metric_name: "pcr_duplication_rate", metric_value: "11.2%", threshold: "<=30", status: "pass", decision_metric: true},
            {sample_id: "S1", metric_name: "fetal_fraction", metric_value: "0.16947", threshold: ">=0.04", status: "pass", decision_metric: true},
            {sample_id: "S1", metric_name: "mapped_fragments", metric_numeric: 842300, threshold: ">=100000", status: "pass", decision_metric: true},
            {sample_id: "S1", metric_name: "total_counts", metric_numeric: 38264612, threshold: ">=100000", status: "pass", decision_metric: true},
            {sample_id: "S1", metric_name: "pearson_r", metric_numeric: 0.987654, threshold: ">=0.9", status: "pass", decision_metric: true},
          ],
        }}
      />,
    );

    expect(screen.getByText("12.6M")).toBeInTheDocument();
    expect(screen.getByText("74.30%")).toBeInTheDocument();
    expect(screen.getByText("11.20%")).toBeInTheDocument();
    expect(screen.getByText("0.1695")).toBeInTheDocument();
    expect(screen.getByText("842.3K")).toBeInTheDocument();
    expect(screen.getByText("38.3M")).toBeInTheDocument();
    expect(screen.getByText("0.9877")).toBeInTheDocument();
  });
});
