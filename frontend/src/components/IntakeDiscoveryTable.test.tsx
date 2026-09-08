import "@testing-library/jest-dom/vitest";

import {cleanup, render, screen} from "@testing-library/react";
import {afterEach, expect, it} from "vitest";

import type {IntakeDiscovery} from "../api";
import {IntakeDiscoveryTable} from "./IntakeDiscoveryTable";

afterEach(cleanup);

it("labels the shared scanner timestamp as the most recent check", () => {
  render(<IntakeDiscoveryTable
    ariaLabel="Intake discovery records"
    items={[{
      pipeline: "wgs",
      chip_id: "2243th_20260906B",
      batch_id: "20260906B",
      sequencing_batch: "20260906B",
      ready_state: "ready",
      submit_state: "ready",
      eligible_pair_count: 9,
      excluded_addon_pair_count: 0,
      pair_issue_count: 0,
      last_seen_at: "2026-09-08T12:33:22Z",
    }] satisfies IntakeDiscovery[]}
  />);

  expect(screen.getByRole("columnheader", {name: "最近检查"})).toBeInTheDocument();
  expect(screen.queryByRole("columnheader", {name: "最近扫描"})).not.toBeInTheDocument();
});
