import "@testing-library/jest-dom/vitest";

import {render, screen} from "@testing-library/react";
import {MemoryRouter} from "react-router-dom";
import {expect, it} from "vitest";

import {RunTable} from "./RunTable";

it("uses one typography contract for submitted and started timestamps", () => {
  render(
    <MemoryRouter>
      <RunTable runs={[{
        analysis_id: "WGS_001",
        project_name: "WGS_Clinical",
        batch_no: "20260906B",
        pipeline: "wgs",
        status: "running",
        submitted_at: "2026-09-07T15:26:49Z",
        started_at: "2026-09-07T15:27:00Z",
      }]} />
    </MemoryRouter>,
  );

  expect(screen.getByText(/^Submitted /)).toHaveClass("run-table-time-line");
  expect(screen.getByText(/^Started /)).toHaveClass("run-table-time-line");
  expect(screen.getByText(/^Submitted /).parentElement).toHaveClass("run-table-time-pair");
});
