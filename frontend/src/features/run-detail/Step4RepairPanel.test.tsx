import "@testing-library/jest-dom/vitest";

import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {afterEach, expect, it, vi} from "vitest";

import {Step4RepairPanel} from "./Step4RepairPanel";


afterEach(() => vi.restoreAllMocks());


it("shows the disabled runtime reason without exposing a repair action", () => {
  render(<Step4RepairPanel capability={{linkage_group: "cram", available: false, reason: "runtime_unavailable", latest_action: null}} canOperate />);

  expect(screen.getByText("运行环境尚不可用")).toBeInTheDocument();
  expect(screen.queryByRole("button", {name: "修复CRAM联动并继续"})).not.toBeInTheDocument();
});


it("requires operator role and a second confirmation before repairing cram", async () => {
  const repair = vi.fn();
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
  const capability = {linkage_group: "cram", available: true, reason: null, latest_action: null} as const;
  const {rerender} = render(<Step4RepairPanel capability={capability} canOperate={false} onRepair={repair} />);

  expect(screen.queryByRole("button", {name: "修复CRAM联动并继续"})).not.toBeInTheDocument();
  rerender(<Step4RepairPanel capability={capability} canOperate onRepair={repair} />);
  await userEvent.click(screen.getByRole("button", {name: "修复CRAM联动并继续"}));

  expect(confirm).toHaveBeenCalledWith("确认修复本次分析的 CRAM 联动并继续？该操作只处理固定 cram 组。");
  expect(repair).toHaveBeenCalledTimes(1);
});
