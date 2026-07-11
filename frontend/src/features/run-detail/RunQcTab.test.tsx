import "@testing-library/jest-dom/vitest";

import {render, screen} from "@testing-library/react";
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

    const row = screen.getByText("NIPT26040001.A01").closest("tr");
    expect(row).not.toBeNull();
    expect(row).toHaveTextContent("pass");
    expect(row).not.toHaveTextContent("unknown");
  });
});
