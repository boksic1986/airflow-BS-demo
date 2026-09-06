import "@testing-library/jest-dom/vitest";

import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {describe, expect, it, vi} from "vitest";

import type {WgsExecutionDispatch} from "../../api";
import {ExecutionTargetSelector} from "./ExecutionTargetSelector";

const dispatch: WgsExecutionDispatch = {
  desired_mode: "cce",
  desired_target: "cce",
  dispatch_state: "waiting_resource",
  dispatch_revision: 4,
  allow_switch: true,
  committed_at: null,
  committed_attempt: null,
  blocking_reason: "Waiting for CCE upload slot",
  targets: [
    {mode: "cce", target: "cce", label: "CCE", status: "available", available: true},
    {
      mode: "local",
      target: "node-97",
      label: "Local .97",
      status: "available",
      available: true,
      metrics: {
        cpu_percent: 8.5,
        load1: 4,
        load5: 5,
        load15: 6,
        memory_percent: 32,
        logical_cpu_count: 192,
        updated_at: "2026-09-06T10:00:00Z",
      },
    },
    {mode: "local", target: "node-96", label: "Local .96", status: "high_load", available: false, reason: "CPU is above 25%"},
    {mode: "sge", target: "sge-default", label: "SGE", status: "unsupported", available: false, reason: "SGE runner has not passed production acceptance"},
  ],
};

describe("ExecutionTargetSelector", () => {
  it("shows target state, blocks inadmissible nodes, and confirms an atomic switch", async () => {
    const onSwitch = vi.fn().mockResolvedValue(undefined);
    render(
      <ExecutionTargetSelector
        attempt={2}
        batch="20260906A"
        sampleCount={8}
        dispatch={dispatch}
        onSwitch={onSwitch}
      />,
    );

    expect(screen.getByRole("button", {name: "CCE · waiting upload slot"})).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", {name: "Local .96 · high CPU"})).toBeDisabled();
    expect(screen.getByRole("button", {name: "Local .96 · high CPU"})).toHaveAttribute("title", "CPU is above 25%");

    await userEvent.click(screen.getByRole("button", {name: "Local .97 · available"}));
    expect(screen.getByRole("dialog", {name: "Confirm execution target"})).toBeInTheDocument();
    expect(screen.getByText("CCE → Local .97")).toBeInTheDocument();
    expect(screen.getByText("20260906A · 8 samples · attempt 2")).toBeInTheDocument();
    expect(screen.getByText("CPU 8.5% · Load 4 / 5 / 6 · Memory 32% · 192 CPUs")).toBeInTheDocument();
    expect(screen.getByText(/may start immediately/i)).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Audit reason"), "Move to accepted local runner");
    await userEvent.click(screen.getByRole("button", {name: "Confirm switch"}));
    expect(onSwitch).toHaveBeenCalledWith({
      desired_mode: "local",
      desired_target: "node-97",
      expected_revision: 4,
      reason: "Move to accepted local runner",
    });
  });

  it("is read-only after commit and explains the freeze point", () => {
    render(
      <ExecutionTargetSelector
        attempt={2}
        batch="20260906A"
        sampleCount={8}
        dispatch={{...dispatch, dispatch_state: "committed", allow_switch: false, committed_attempt: 2}}
        onSwitch={vi.fn()}
      />,
    );

    expect(screen.getByText("Locked · Step1 started")).toBeInTheDocument();
    expect(screen.getAllByRole("button").every((button) => button.hasAttribute("disabled"))).toBe(true);
  });
});
