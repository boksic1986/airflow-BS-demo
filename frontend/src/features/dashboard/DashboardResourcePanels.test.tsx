import "@testing-library/jest-dom";

import {fireEvent, render, screen, within} from "@testing-library/react";
import {MemoryRouter} from "react-router-dom";

import type {PlatformResourcesResponse} from "../../api";
import {DashboardResourcePanels} from "./DashboardResourcePanels";

const resources: PlatformResourcesResponse = {
  status: "healthy",
  updated_at: "2026-09-02T15:00:00Z",
  items: [
    {
      resource_key: "node-96",
      resource_type: "node",
      display_name: "node-96",
      status: "healthy",
      source_updated_at: "2026-09-02T15:00:00Z",
      history: [],
      current: {
        cpu_used_percent: 11,
        node_load1: 1,
        node_load5: 2,
        node_load15: 3,
        node_memory_MemTotal_bytes: 100,
        node_memory_MemAvailable_bytes: 75,
        disk_read_bps: 1000,
        network_receive_bps: 2000,
      },
    },
    {
      resource_key: "node-97",
      resource_type: "node",
      display_name: "node-97",
      status: "healthy",
      source_updated_at: "2026-09-02T15:00:00Z",
      history: [],
      current: {
        cpu_used_percent: 22,
        node_load1: 4,
        node_load5: 5,
        node_load15: 6,
        node_memory_MemTotal_bytes: 100,
        node_memory_MemAvailable_bytes: 50,
        disk_read_bps: 3000,
        network_receive_bps: 4000,
      },
    },
    {
      resource_key: "sfs-clinical",
      resource_type: "sfs",
      display_name: "sfs-turbo-clinical",
      status: "healthy",
      source_updated_at: "2026-09-02T15:00:00Z",
      history: [],
      current: {capacity_used_percent: 13.86, read_bps: 1024, write_bps: 2048, iops: 12},
    },
    {
      resource_key: "obs-legacy",
      resource_type: "obs",
      display_name: "OBS Cloud Eye",
      status: "healthy",
      source_updated_at: "2026-09-02T15:00:00Z",
      history: [],
      current: {used_bytes: 1024},
    },
  ],
};

it("shows one analysis node at a time and hides disk and network throughput", () => {
  render(
    <MemoryRouter>
      <DashboardResourcePanels
        resources={resources}
        resourceTab="all"
        overview={null}
        rows={[]}
        loading={false}
        error={null}
        onResourceTabChange={() => undefined}
      />
    </MemoryRouter>,
  );

  const tabs = screen.getByRole("tablist", {name: "Analysis node"});
  expect(within(tabs).getByRole("tab", {name: "172.17.61.96"})).toHaveAttribute("aria-selected", "true");
  expect(screen.queryByText("172.17.61.96 and 172.17.61.97")).not.toBeInTheDocument();
  expect(screen.getByText("11% / 1 / 2 / 3")).toBeInTheDocument();
  expect(screen.queryByText("22% / 4 / 5 / 6")).not.toBeInTheDocument();
  expect(screen.queryByText("Disk read / write")).not.toBeInTheDocument();
  expect(screen.queryByText("Read / write IOPS")).not.toBeInTheDocument();
  expect(screen.queryByText("Network receive / transmit")).not.toBeInTheDocument();

  fireEvent.click(within(tabs).getByRole("tab", {name: "172.17.61.97"}));

  expect(within(tabs).getByRole("tab", {name: "172.17.61.97"})).toHaveAttribute("aria-selected", "true");
  expect(screen.getByText("22% / 4 / 5 / 6")).toBeInTheDocument();
  expect(screen.queryByText("11% / 1 / 2 / 3")).not.toBeInTheDocument();
  expect(screen.getByText("sfs-turbo-clinical")).toBeInTheDocument();
  expect(screen.queryByText("OBS Cloud Eye")).not.toBeInTheDocument();
  expect(screen.getByText("SFS capacity and I/O snapshot")).toBeInTheDocument();
});
