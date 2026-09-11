import "@testing-library/jest-dom/vitest";

import {act, fireEvent, render, screen, waitFor} from "@testing-library/react";
import {afterEach, describe, expect, it, vi} from "vitest";

import * as api from "../../api";
import type {RunDetail, WgsTransfer} from "../../api";
import {WgsTransfersTab} from "./WgsTransfersTab";

afterEach(() => vi.restoreAllMocks());

describe("WgsTransfersTab", () => {
  it("loads privacy-safe per-file obsutil progress only after expansion", async () => {
    const files = vi.spyOn(api, "getTransferFiles").mockResolvedValue({
      items: [{
        file_key: "a".repeat(64),
        display_name: "S1_R1.fastq.gz",
        status: "running",
        bytes_total: 2 * 1024 ** 3,
        bytes_transferred: 1024 ** 3,
        progress_percent: 50,
        speed_bps: 64 * 1024 ** 2,
        checksum_status: "pending",
        started_at: "2026-09-08T01:00:00Z",
        ended_at: null,
      }],
      total: 1,
      limit: 50,
      offset: 0,
    });
    const detail = {analysis_id: "WGS_TRANSFER", pipeline: "wgs", status: "running", params: {batch_no: "B1"}} as RunDetail;
    const transfers: WgsTransfer[] = [{
      transfer_id: "WGS_TRANSFER-a1-input",
      direction: "upload",
      status: "running",
      progress_detail_available: true,
      progress_percent: 50,
      bytes_total: 2 * 1024 ** 3,
      bytes_transferred: 1024 ** 3,
      files_total: 1,
      files_completed: 0,
      started_at: "2026-09-08T01:00:00Z",
      ended_at: null,
      transfer_engine: "obsutil",
    }];

    render(<WgsTransfersTab detail={detail} transfers={transfers} />);
    expect(files).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", {name: /File progress/i}));

    await waitFor(() => expect(files).toHaveBeenCalledWith("WGS_TRANSFER-a1-input", {limit: 50, offset: 0}));
    expect(screen.getByText("S1_R1.fastq.gz")).toBeInTheDocument();
    expect(screen.getAllByText(/50.0%/)).toHaveLength(2);
    expect(screen.getByRole("progressbar", {name: "S1_R1.fastq.gz progress"})).toHaveAttribute("value", "50");
    expect(screen.getAllByText(/2026-09-08/).length).toBeGreaterThan(0);
    expect(screen.getByTitle("Pending")).toBeInTheDocument();
    expect(screen.getByText("64.0 MiB/s")).toBeInTheDocument();
    expect(screen.getByText("obsutil")).toBeInTheDocument();
  });

  it("labels an accepted file without checkpoint bytes as waiting", async () => {
    vi.spyOn(api, "getTransferFiles").mockResolvedValue({
      items: [{
        file_key: "b".repeat(64),
        display_name: "S2_R1.fastq.gz",
        status: "accepted",
        bytes_total: 1024,
        bytes_transferred: 0,
        progress_percent: 0,
        speed_bps: 0,
        checksum_status: "pending",
      }],
      total: 1,
      limit: 50,
      offset: 0,
    });
    const detail = {analysis_id: "WGS_TRANSFER", pipeline: "wgs", status: "running", params: {batch_no: "B1"}} as RunDetail;
    const transfers: WgsTransfer[] = [{
      transfer_id: "WGS_TRANSFER-a1-input",
      direction: "upload",
      status: "running",
      progress_detail_available: true,
      transfer_engine: "obsutil",
    }];

    render(<WgsTransfersTab detail={detail} transfers={transfers} />);
    fireEvent.click(screen.getByRole("button", {name: /File progress/i}));

    expect(await screen.findByText("Waiting for checkpoint")).toBeInTheDocument();
  });

  it("keeps the existing file table visible while a live snapshot refreshes", async () => {
    const files = vi.spyOn(api, "getTransferFiles")
      .mockResolvedValueOnce({
        items: [{file_key: "active", display_name: "active.cram", status: "running", bytes_total: 100, bytes_transferred: 25, progress_percent: 25, speed_bps: 10}],
        total: 1,
        limit: 50,
        offset: 0,
      })
      .mockImplementationOnce(() => new Promise(() => {}));
    const detail = {analysis_id: "WGS_TRANSFER", pipeline: "wgs", status: "downloading", params: {batch_no: "B1"}} as RunDetail;
    const transfers: WgsTransfer[] = [{transfer_id: "result", direction: "download", status: "running", progress_detail_available: true, progress_percent: 25}];
    const {rerender} = render(<WgsTransfersTab detail={detail} transfers={transfers} refreshKey="snapshot-1" />);
    fireEvent.click(screen.getByRole("button", {name: /File progress/i}));
    await screen.findByText("active.cram");
    const previousTable = screen.getByRole("table");

    rerender(<WgsTransfersTab detail={detail} transfers={transfers} refreshKey="snapshot-2" />);
    expect(files).toHaveBeenCalledTimes(1);
    await act(async () => { window.dispatchEvent(new Event("focus")); });

    expect(files).toHaveBeenCalledTimes(2);
    expect(screen.getByText("active.cram")).toBeInTheDocument();
    expect(screen.getByRole("table")).toBe(previousTable);
    expect(screen.queryByText("Loading file progress...")).not.toBeInTheDocument();
  });
});
