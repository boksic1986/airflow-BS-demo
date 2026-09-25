import "@testing-library/jest-dom/vitest";

import {render, screen} from "@testing-library/react";
import {describe, expect, it} from "vitest";

import type {RunDetail} from "../../api";
import {CurrentProgressPanel} from "./CurrentProgressPanel";

describe("CurrentProgressPanel", () => {
  it("keeps last measured progress during recovery without claiming live progress or ETA", () => {
    const detail = {analysis_id: 'RECOVERY',pipeline:'wgs',status:'running',recovery:{state:'waiting',message:'自动续跑等待中（1/2）',reason:'等待现有 Worker 自然结束',next_retry_at:'2026-09-25T02:00:00Z'}} as RunDetail;
    const {rerender} = render(<CurrentProgressPanel detail={detail} progress={{percent:35,available:true,label:'35%',currentStep:'Analysis',note:'',notInAirflow:false}} stage={{estimate_model:'stage_median_linear_v1',estimated_progress_percent:70}} />);
    expect(screen.getByRole('status')).toHaveTextContent('自动续跑等待中（1/2）');
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow','35');
    expect(screen.getByText('最后确认进度 35.0%')).toBeInTheDocument();
    expect(screen.queryByText(/ETA based|70.0%/)).not.toBeInTheDocument();
    rerender(<CurrentProgressPanel detail={{...detail,recovery:null}} progress={{percent:40,available:true,label:'40%',currentStep:'Analysis',note:'',notInAirflow:false}} />);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow','40');
  });

  it("shows uncertainty even before any progress exists", () => {
    render(<CurrentProgressPanel detail={{analysis_id:'R',pipeline:'gatk',status:'failed',recovery:{state:'checking',message:'正在核对原执行，勿重复提交'}} as RunDetail} progress={null} />);
    expect(screen.getByRole('status')).toHaveTextContent('勿重复提交');
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  });
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
