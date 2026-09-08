import "@testing-library/jest-dom/vitest";

import {render, screen} from "@testing-library/react";
import {MemoryRouter} from "react-router-dom";
import {expect, it} from "vitest";

import {IntakeDiscoveryTable} from "./IntakeDiscoveryTable";

it("labels the shared T7 cycle timestamp as the most recent check", () => {
  render(
    <MemoryRouter>
      <IntakeDiscoveryTable
        ariaLabel="Intake discovery records"
        items={[{
          pipeline: "wgs",
          batch_id: "2243th_20260906B_E250209844",
          chip_id: "2243th_20260906B_E250209844",
          sequencing_batch: "20260906B",
          ready_state: "ready",
          submit_state: "disabled",
          eligible_pair_count: 9,
          excluded_addon_pair_count: 0,
          pair_issue_count: 0,
          last_seen_at: "2026-09-08T05:03:24Z",
        }]}
      />
    </MemoryRouter>,
  );

  expect(screen.getByRole("columnheader", {name: "最近检查"})).toBeInTheDocument();
  expect(screen.queryByRole("columnheader", {name: "最近扫描"})).not.toBeInTheDocument();
});
