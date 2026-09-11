import "@testing-library/jest-dom/vitest";
import {render, screen} from "@testing-library/react";
import {it, expect} from "vitest";
import {EstimatedStageProgress} from "./EstimatedStageProgress";

it("does not describe a frozen terminal estimate as still executing", () => {
  render(<EstimatedStageProgress stage={{estimated_progress_percent: 62.6, estimate_overrun: true, estimate_frozen: true}} />);
  expect(screen.queryByText(/Still executing/)).not.toBeInTheDocument();
  expect(screen.getByText(/Estimate frozen/)).toBeInTheDocument();
});
