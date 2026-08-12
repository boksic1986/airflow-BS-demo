import "@testing-library/jest-dom/vitest";

import {render, screen} from "@testing-library/react";
import {afterEach, expect, it, vi} from "vitest";

import App from "./App";

afterEach(() => {
  vi.unstubAllGlobals();
  window.history.pushState({}, "", "/");
});

it("requires sign-in before showing the WGS control tower", async () => {
  window.__AIRFLOW_DEMO_CONFIG__ = {apiBaseUrl: "/api"};
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
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
  expect(screen.queryByText("WGS Control Tower")).not.toBeInTheDocument();
});
