import "@testing-library/jest-dom/vitest";

import {render, screen} from "@testing-library/react";
import {describe, expect, it} from "vitest";

import type {RunDetail} from "../../api";
import {CurrentProgressPanel} from "./CurrentProgressPanel";

describe("CurrentProgressPanel", () => {
  it("labels an estimate separately and never replaces observed progress", () => {
    const detail = {analysis_id: "E", pipeline: "wgs", status: "running"} as RunDetail;
    const {rerender} = render(<CurrentProgressPanel detail={detail} progress={{percent: 0, available: false, label: "", currentStep: "Publish", note: "", notInAirflow: false}} stage={{estimated_progress_percent: 62.6, estimate_overrun: true}} />);
    expect(screen.getByText("Estimated 62.6%")).toBeInTheDocument();
    expect(screen.getByText(/Still executing/)).toBeInTheDocument();
    rerender(<CurrentProgressPanel detail={detail} progress={{percent: 25, available: true, label: "25%", currentStep: "Publish", note: "", notInAirflow: false}} stage={{estimated_progress_percent: 62.6}} />);
    expect(screen.queryByText("Estimated 62.6%")).not.toBeInTheDocument();
  });
  it("formats byte-based transfer progress in readable units", () => {
    const detail = {
      analysis_id: "WGS_TRANSFER",
      pipeline: "wgs",
      status: "running",
    } as RunDetail;

    const {container} = render(<CurrentProgressPanel
      detail={detail}
      progress={{percent: 25, available: true, label: "25%", currentStep: "Uploading FASTQ", note: "Uploading", notInAirflow: false}}
      stage={{completed_units: 1024 ** 3, total_units: 2 * 1024 ** 3, unit: "bytes"}}
    />);

    expect(screen.getByText("1.0 GiB / 2.0 GiB")).toBeInTheDocument();
    expect(screen.queryByText(/1073741824\/2147483648 bytes/)).not.toBeInTheDocument();
    expect(container.querySelector(".current-progress-hero")).toHaveClass("current-progress-content-centered");
  });

  it("does not mix the global heavy IO quota into run progress", () => {
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

    expect(screen.queryByText("7 / 25 heavy work pods")).not.toBeInTheDocument();
    expect(screen.queryByText("2 waiting / monitor only")).not.toBeInTheDocument();
  });
});
