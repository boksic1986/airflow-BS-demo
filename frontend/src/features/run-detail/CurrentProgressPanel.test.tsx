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

    expect(screen.getByText("1.0 GB / 2.0 GB")).toBeInTheDocument();
    expect(screen.queryByText(/1073741824\/2147483648 bytes/)).not.toBeInTheDocument();
  });
});
