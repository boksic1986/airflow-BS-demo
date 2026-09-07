import "@testing-library/jest-dom/vitest";

import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {afterEach, describe, expect, it, vi} from "vitest";

import * as api from "../../api";
import type {RunDetail, WgsTransfer} from "../../api";
import {WgsTransfersTab} from "./WgsTransfersTab";

afterEach(() => vi.restoreAllMocks());

describe("WgsTransfersTab", () => {
  it("loads privacy-safe per-file SDK progress only after expansion", async () => {
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
    }];

    render(<WgsTransfersTab detail={detail} transfers={transfers} />);
    expect(files).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", {name: /File progress/i}));

    await waitFor(() => expect(files).toHaveBeenCalledWith("WGS_TRANSFER-a1-input", {limit: 50, offset: 0}));
    expect(screen.getByText("S1_R1.fastq.gz")).toBeInTheDocument();
    expect(screen.getByText(/50.0%/)).toBeInTheDocument();
    expect(screen.getByText("64.0 MiB/s")).toBeInTheDocument();
  });
});
