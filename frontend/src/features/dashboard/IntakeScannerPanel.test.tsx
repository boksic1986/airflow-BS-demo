import "@testing-library/jest-dom/vitest";

import {render, screen} from "@testing-library/react";
import {MemoryRouter} from "react-router-dom";
import {expect, it, vi} from "vitest";

import {IntakeScannerPanel} from "./IntakeScannerPanel";

it("describes waiting batches and reports the neutral scanner item count", () => {
  render(
    <MemoryRouter>
      <IntakeScannerPanel
        scanner={{
          last_scanned_directory_count: 7,
          schedule_seconds: 600,
          auto_dispatch_enabled: false,
        }}
        items={[]}
        total={0}
        limit={10}
        offset={0}
        loading={false}
        error={null}
        onPageChange={vi.fn()}
      />
    </MemoryRouter>,
  );

  expect(screen.getByText("仅显示待下机、待数据就绪、可提交、失败或需要人工复核的测序批次")).toBeInTheDocument();
  expect(screen.getByText("本轮检查 7 个扫描项")).toBeInTheDocument();
  expect(screen.queryByText(/批次目录/)).not.toBeInTheDocument();
});
