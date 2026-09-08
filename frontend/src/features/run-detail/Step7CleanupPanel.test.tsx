import "@testing-library/jest-dom/vitest";

import {fireEvent, render, screen} from "@testing-library/react";
import {expect, it, vi} from "vitest";

import {Step7CleanupPanel} from "./Step7CleanupPanel";


it("shows queued Step7 maintenance progress without inventing a percentage", () => {
  render(
    <Step7CleanupPanel
      capability={{
        available: false,
        reason: "cleanup_in_progress",
        required_batch: "20260825A",
        latest_action: {
          action_id: "step7-sfs-abcdef123456",
          analysis_id: "WGS_20260903_062828_0858DC",
          attempt: 7,
          action_type: "cleanup_step7_sfs",
          linkage_group: "sfs",
          status: "queued",
          requested_by: "admin",
          created_at: "2026-09-07T03:48:21Z",
        },
      }}
      onCleanup={vi.fn()}
    />,
  );

  expect(screen.getByRole("heading", {name: "Step7 progress"})).toBeInTheDocument();
  expect(screen.getByText("Waiting for Step7 worker")).toBeInTheDocument();
  expect(screen.getByText(/Generation 1/)).toBeInTheDocument();
  expect(screen.queryByText(/%/)).not.toBeInTheDocument();
});

it("submits a failed Step7 action as an explicit retry generation", () => {
  const cleanup = vi.fn();
  render(
    <Step7CleanupPanel
      capability={{
        available: true,
        reason: null,
        retry_available: true,
        required_batch: "20260905A",
        latest_action: {
          action_id: "step7-old",
          analysis_id: "WGS_RETRY",
          attempt: 1,
          action_type: "cleanup_step7_sfs",
          linkage_group: "sfs",
          status: "failed",
          generation: 1,
          requested_by: "admin",
          created_at: "2026-09-08T01:00:00Z",
          error_message: "runtime root was not configured",
        },
      }}
      onCleanup={cleanup}
    />,
  );

  fireEvent.click(screen.getByText("Retry SFS release"));
  fireEvent.click(screen.getByLabelText("Acknowledge SFS cleanup"));
  fireEvent.change(screen.getByLabelText("Step7 Batch confirmation"), {target: {value: "20260905A"}});
  fireEvent.click(screen.getByRole("button", {name: "Retry Step7 SFS cleanup"}));

  expect(screen.getByText(/Generation 1/)).toBeInTheDocument();
  expect(cleanup).toHaveBeenCalledWith("20260905A", true);
});
