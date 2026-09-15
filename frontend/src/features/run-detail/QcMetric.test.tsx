import "@testing-library/jest-dom/vitest";
import {render, screen} from "@testing-library/react";
import {expect, it} from "vitest";
import {QcMetric} from "./QcMetric";

it("does not color an unsupported policy source PASS as successful", () => {
  const {container} = render(<QcMetric value="PASS" judgment={{value: "PASS", unit: "status", status: "unknown", reason: "Policy unavailable"}} />);
  expect(screen.getByText("PASS")).toHaveClass("qc-value-unknown");
  expect(container.querySelector(".status-success")).toBeNull();
  expect(screen.getByText("unknown")).toBeInTheDocument();
  expect(container.querySelector("details")).toBeNull();
});

it("renders a numeric value with its unit and compact judgment badge", () => {
  render(<QcMetric value="85%" judgment={{value: 85, unit: "%", status: "fail", reason: "Outside release criterion", threshold: {min: 85, min_inclusive: false}, provenance: {source_commit: "cc9bde3"}}} />);
  expect(screen.getByText("85 %")).toHaveClass("qc-value-fail");
  expect(screen.getByText("fail").closest(".status-badge")).toBeInTheDocument();
});

it("keeps unknown numeric evidence and renders contamination as a status badge", () => {
  render(<><QcMetric judgment={{value: null, status: "unknown", reason: "Value unavailable"}} /><QcMetric value="WARNING" judgment={{value: "WARNING", status: "warn", unit: "status"}} /></>);
  expect(screen.getByText("unknown")).toBeInTheDocument();
  expect(screen.getAllByText("warn").find((node) => node.closest(".status-badge"))).toBeDefined();
});
