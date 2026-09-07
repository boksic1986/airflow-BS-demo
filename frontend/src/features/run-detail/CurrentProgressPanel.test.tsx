import "@testing-library/jest-dom/vitest";

import {render, screen} from "@testing-library/react";
import {describe, expect, it} from "vitest";

import type {RunDetail} from "../../api";
import {CurrentProgressPanel} from "./CurrentProgressPanel";

describe("CurrentProgressPanel", () => {
  it("formats byte-based transfer progress in readable units", () => {
    const detail = {
      analysis_id: "WGS_TRANSFER",
      pipeline: "wgs",
      status: "running",
    } as RunDetail;

    render(<CurrentProgressPanel
      detail={detail}
      progress={{percent: 25, available: true, label: "25%", currentStep: "Uploading FASTQ", note: "Uploading", notInAirflow: false}}
      stage={{completed_units: 1024 ** 3, total_units: 2 * 1024 ** 3, unit: "bytes"}}
    />);

    expect(screen.getByText("1.0 GiB / 2.0 GiB")).toBeInTheDocument();
    expect(screen.queryByText(/1073741824\/2147483648 bytes/)).not.toBeInTheDocument();
  });

  it("shows heavy IO work pod quota separately from CPU capacity", () => {
    const detail = {
      analysis_id: "WGS_HEAVY",
      pipeline: "wgs",
      status: "running",
    } as RunDetail;

    render(<CurrentProgressPanel
      detail={detail}
      progress={{percent: 40, available: true, label: "40%", currentStep: "Mapping", note: "Mapping", notInAirflow: false}}
      slotUsage={{pool: "wgs-heavy-io", used: 7, limit: 25, waiting: 2, mode: "monitor-only"}}
    />);

    expect(screen.getByText("7 / 25 heavy work pods")).toBeInTheDocument();
    expect(screen.getByText("2 waiting / monitor only")).toBeInTheDocument();
  });
});
