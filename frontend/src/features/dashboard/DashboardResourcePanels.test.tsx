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
        logical_cpu_count: 128,
        node_load1: 103.6,
        node_load5: 109.3,
        node_load15: 107.5,
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
        logical_cpu_count: 128,
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
      history: [
        {at: "2026-09-02T14:58:00Z", read_bps: 1024, write_bps: 2048, iops: 10},
        {at: "2026-09-02T14:59:00Z", read_bps: 4096, write_bps: 8192, iops: 12},
      ],
      current: {
        capacity_used_percent: 25,
        capacity_used_bytes: 25 * 1024 ** 3,
        read_bps: 4096,
        write_bps: 8192,
        iops: 12,
        client_connections: 42,
      },
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

it("shows compact node and SFS utilization bars with updated times in the headings", () => {
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
  expect(screen.getByText("11.0%")).toBeInTheDocument();
  expect(screen.getByText("103.6 / 109.3 / 107.5")).toBeInTheDocument();
  expect(screen.queryByText("22.0%")).not.toBeInTheDocument();
  expect(screen.queryByText("Disk read / write")).not.toBeInTheDocument();
  expect(screen.queryByText("Read / write IOPS")).not.toBeInTheDocument();
  expect(screen.queryByText("Network receive / transmit")).not.toBeInTheDocument();
  expect(screen.getByRole("progressbar", {name: "CPU utilization"})).toHaveAttribute("aria-valuenow", "11");
  expect(screen.getByRole("progressbar", {name: "Memory utilization"})).toHaveAttribute("aria-valuenow", "25");
  expect(screen.getByRole("progressbar", {name: "Load 1 / 5 / 15"})).toHaveAttribute("aria-valuenow", "85");
  expect(screen.getByRole("progressbar", {name: "Load 1 / 5 / 15"})).toHaveClass("warning");
  expect(screen.getByRole("progressbar", {name: "SFS capacity utilization"})).toHaveAttribute("aria-valuenow", "25");
  expect(screen.getByText("25.0 GB / 100.0 GB")).toBeInTheDocument();
  const nodePanel = screen.getByRole("heading", {name: "Analysis Node Health"}).closest("section");
  const cloudPanel = screen.getByRole("heading", {name: "Cloud Resources"}).closest("section");
  expect(within(nodePanel!).getByText(/Updated/)).toBeInTheDocument();
  expect(within(cloudPanel!).getByText(/Updated/)).toBeInTheDocument();

  fireEvent.click(within(tabs).getByRole("tab", {name: "172.17.61.97"}));

  expect(within(tabs).getByRole("tab", {name: "172.17.61.97"})).toHaveAttribute("aria-selected", "true");
  expect(screen.getByText("22.0%")).toBeInTheDocument();
  expect(screen.getByText("4 / 5 / 6")).toBeInTheDocument();
  expect(screen.queryByText("11.0%")).not.toBeInTheDocument();
  expect(screen.getByText("sfs-turbo-clinical")).toHaveClass("resource-tag");
  expect(screen.queryByText("OBS Cloud Eye")).not.toBeInTheDocument();
  expect(screen.queryByText("SFS capacity and I/O snapshot")).not.toBeInTheDocument();
  expect(screen.queryByText("Client connections")).not.toBeInTheDocument();
  expect(screen.queryByText("node-96")).not.toBeInTheDocument();
});

it("replaces workflow activity with the SFS read and write history", () => {
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

  expect(screen.queryByRole("heading", {name: "Workflow Activity"})).not.toBeInTheDocument();
  expect(screen.getByRole("heading", {name: "SFS I/O"})).toBeInTheDocument();
  expect(screen.getByRole("tab", {name: "24h"})).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("tab", {name: "1d"})).toBeInTheDocument();
  expect(screen.getByRole("tab", {name: "7d"})).toBeInTheDocument();
  expect(screen.queryByText("Read and write bandwidth, latest 60 samples")).not.toBeInTheDocument();
  expect(screen.getByRole("img", {name: "SFS read and write bandwidth history"})).toBeInTheDocument();
  const yAxis = screen.getByLabelText("SFS bandwidth Y axis");
  expect(within(yAxis).getByText("8.0 KB/s")).toBeInTheDocument();
  expect(within(yAxis).getByText("4.0 KB/s")).toBeInTheDocument();
  expect(within(yAxis).getByText("0 B/s")).toBeInTheDocument();
  expect(screen.getByText("Read")).toBeInTheDocument();
  expect(screen.getByText("Write")).toBeInTheDocument();
  expect(screen.getByText("Current IOPS")).toBeInTheDocument();
  expect(screen.getByText("12")).toBeInTheDocument();
});

it("does not report zero utilization when a metric is unavailable", () => {
  render(
    <MemoryRouter>
      <DashboardResourcePanels
        resources={{
          status: "stale",
          updated_at: "2026-09-02T15:00:00Z",
          items: [{
            resource_key: "sfs-clinical",
            resource_type: "sfs",
            display_name: "sfs-turbo-clinical",
            status: "stale",
            source_updated_at: null,
            history: [],
            current: {},
          }],
        }}
        resourceTab="all"
        overview={null}
        rows={[]}
        loading={false}
        error={null}
        onResourceTabChange={() => undefined}
      />
    </MemoryRouter>,
  );

  expect(screen.getByRole("progressbar", {name: "SFS capacity utilization"})).not.toHaveAttribute("aria-valuenow");
  expect(screen.getAllByText("not reported").length).toBeGreaterThan(0);
});
