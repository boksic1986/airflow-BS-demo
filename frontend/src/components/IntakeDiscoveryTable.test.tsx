import "@testing-library/jest-dom/vitest";

import {render, screen, within} from "@testing-library/react";
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

it("renders an unbound Samplelist batch as waiting for sequencing without invented pair counts", () => {
  render(
    <MemoryRouter>
      <IntakeDiscoveryTable
        ariaLabel="Intake discovery records"
        items={[{
          pipeline: "wgs",
          intake_id: 41,
          discovery_mode: "samplelist_batches",
          project_id: "WGS_Clinical",
          platform_id: "T7",
          batch_id: "intake:41",
          chip_id: null,
          sequencing_batch: "20990101A",
          ready_state: "waiting_sequencing",
          submit_state: "disabled",
          reason_code: "sequencing_directory_pending",
          eligible_pair_count: null,
          excluded_addon_pair_count: null,
          pair_issue_count: null,
          last_seen_at: "2099-01-01T01:02:03Z",
        }]}
      />
    </MemoryRouter>,
  );

  const row = screen.getByText("待绑定").closest("tr");
  expect(row).not.toBeNull();
  expect(within(row!).getByText("待下机")).toBeInTheDocument();
  expect(within(row!).getAllByText("-")).toHaveLength(3);
  expect(within(row!).queryByRole("link")).not.toBeInTheDocument();
  expect(screen.queryByText("Intake validation failed")).not.toBeInTheDocument();
  expect(screen.queryByText(/0 samples/)).not.toBeInTheDocument();
});

it("keeps the Samplelist row identity when binding appears on silent refresh", () => {
  const waiting = {
    pipeline: "wgs",
    intake_id: 42,
    discovery_mode: "samplelist_batches",
    project_id: "WGS_Clinical",
    platform_id: "T7",
    batch_id: "intake:42",
    chip_id: null,
    sequencing_batch: "20990102B",
    ready_state: "waiting_sequencing",
    submit_state: "disabled",
    reason_code: "sequencing_directory_pending",
    eligible_pair_count: null,
    excluded_addon_pair_count: null,
    pair_issue_count: null,
    last_seen_at: "2099-01-02T01:02:03Z",
  } as const;
  const {rerender} = render(
    <MemoryRouter>
      <IntakeDiscoveryTable ariaLabel="Intake discovery records" items={[waiting]} />
    </MemoryRouter>,
  );
  const originalRow = screen.getByText("待绑定").closest("tr");

  rerender(
    <MemoryRouter>
      <IntakeDiscoveryTable
        ariaLabel="Intake discovery records"
        items={[{
          ...waiting,
          chip_id: "2th_20990102B_SYN",
          ready_state: "waiting_data",
          reason_code: "barcode_pending",
          last_seen_at: "2099-01-02T01:12:03Z",
        }]}
      />
    </MemoryRouter>,
  );

  const boundRow = screen.getByText("2th_20990102B_SYN").closest("tr");
  expect(boundRow).toBe(originalRow);
  expect(within(boundRow!).getByText("待数据就绪")).toBeInTheDocument();
  expect(within(boundRow!).getAllByText("-")).toHaveLength(3);
});

it("preserves the linked operations rendering for non-WGS intake rows", () => {
  render(
    <MemoryRouter>
      <IntakeDiscoveryTable
        ariaLabel="Intake discovery records"
        items={[{
          pipeline: "nipt",
          root_path: "synthetic",
          batch_id: "NIPT_BATCH_2099",
          ready_state: "ready",
          submit_state: "submitted",
          analysis_id: "NIPT_2099",
          project_name: "Synthetic NIPT",
          sample_count: 2,
          file_count: 4,
          total_bytes: 1024,
          analysis_status: "running",
        }]}
      />
    </MemoryRouter>,
  );

  expect(screen.getByRole("columnheader", {name: "Project / Batch"})).toBeInTheDocument();
  expect(screen.getByRole("link", {name: "Synthetic NIPT"})).toHaveAttribute("href", "/runs/NIPT_2099");
  expect(screen.getByRole("link", {name: "NIPT_2099"})).toHaveAttribute("href", "/runs/NIPT_2099");
});
