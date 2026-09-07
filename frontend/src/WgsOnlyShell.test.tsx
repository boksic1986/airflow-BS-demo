import "@testing-library/jest-dom/vitest";

import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {afterEach, expect, it, vi} from "vitest";

import App from "./App";

afterEach(() => {
  vi.unstubAllGlobals();
  window.history.pushState({}, "", "/");
});

it("requires sign-in before showing the NGS application shell", async () => {
  window.__AIRFLOW_DEMO_CONFIG__ = {apiBaseUrl: "/api"};
  const requests: string[] = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    requests.push(url);
    if (url.endsWith("/api/auth/me")) {
      return Promise.resolve(new Response(JSON.stringify({detail: "Not authenticated"}), {
        status: 401,
        headers: {"Content-Type": "application/json"},
      }));
    }
    return Promise.resolve(new Response(JSON.stringify({
      environment: "WGS production",
      deployed_pipelines: ["wgs"],
      airflow_url: null,
    }), {status: 200, headers: {"Content-Type": "application/json"}}));
  }));

  render(<App />);

  expect(await screen.findByRole("heading", {name: "Sign in"})).toBeInTheDocument();
  expect(screen.queryByRole("navigation", {name: "Primary navigation"})).not.toBeInTheDocument();
  expect(requests).not.toContain("/api/platform/capabilities");
});

it("loads deployment capabilities only after a successful sign-in", async () => {
  window.__AIRFLOW_DEMO_CONFIG__ = {apiBaseUrl: "/api"};
  let authenticated = false;
  const requests: string[] = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    requests.push(url);
    if (url.endsWith("/api/auth/me")) {
      return Promise.resolve(new Response(JSON.stringify({detail: {code: "AUTH_REQUIRED", message: "Login required."}}), {
        status: 401,
        headers: {"Content-Type": "application/json"},
      }));
    }
    if (url.endsWith("/api/auth/login")) {
      authenticated = true;
      return json({username: "operator", role: "operator"});
    }
    if (url.endsWith("/api/platform/capabilities")) {
      if (!authenticated) {
        return Promise.resolve(new Response(JSON.stringify({detail: {code: "AUTH_REQUIRED", message: "Login required."}}), {
          status: 401,
          headers: {"Content-Type": "application/json"},
        }));
      }
      return json({environment: "WGS production", deployed_pipelines: ["wgs"], airflow_url: null});
    }
    return json({items: [], total: 0});
  }));

  render(<App />);
  expect(await screen.findByRole("heading", {name: "Sign in"})).toBeInTheDocument();
  expect(requests.filter((url) => url.endsWith("/api/platform/capabilities"))).toHaveLength(0);

  await userEvent.type(screen.getByLabelText("Username"), "operator");
  await userEvent.type(screen.getByLabelText("Password"), "secret");
  await userEvent.click(screen.getByRole("button", {name: "Sign in"}));

  expect(await screen.findByText("NGS Huawei Cloud")).toBeInTheDocument();
  expect(await screen.findByText("WGS production environment")).toBeInTheDocument();
  expect(screen.queryByText(/Deployment capabilities unavailable/)).not.toBeInTheDocument();
  expect(requests.filter((url) => url.endsWith("/api/platform/capabilities"))).toHaveLength(1);
});

it("hides submission entry points when no deployed pipeline advertises submit capability", async () => {
  window.__AIRFLOW_DEMO_CONFIG__ = {apiBaseUrl: "/api"};
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "operator", role: "operator"});
    if (url.endsWith("/api/platform/capabilities")) {
      return json({
        environment: "NGS",
        deployed_pipelines: ["synthetic"],
        pipelines: [{
          id: "synthetic",
          display_name: "Synthetic",
          dag_id: "bio_synthetic",
          enabled: true,
          submit_enabled: true,
          capabilities: ["submit"],
          execution_targets: ["local"],
        }],
        airflow_url: null,
      });
    }
    return json({items: [], total: 0});
  }));

  render(<App />);

  expect(await screen.findByText("NGS Huawei Cloud")).toBeInTheDocument();
  expect(screen.queryByRole("link", {name: "Submit Run"})).not.toBeInTheDocument();
  expect(screen.queryByRole("link", {name: "Submit run"})).not.toBeInTheDocument();
});

function json(value: unknown): Promise<Response> {
  return Promise.resolve(new Response(JSON.stringify(value), {
    status: 200,
    headers: {"Content-Type": "application/json"},
  }));
}
