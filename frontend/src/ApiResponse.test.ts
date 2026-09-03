import {afterEach, describe, expect, it, vi} from "vitest";

import {ApiError, getPlatformCapabilities} from "./api";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  delete window.__AIRFLOW_DEMO_CONFIG__;
});

describe("API response parsing", () => {
  it("retries one transient network failure for an idempotent GET", async () => {
    window.__AIRFLOW_DEMO_CONFIG__ = {apiBaseUrl: "/api"};
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        environment: "WGS production",
        deployed_pipelines: ["wgs"],
        airflow_url: null,
      }), {status: 200, headers: {"Content-Type": "application/json"}}));
    vi.stubGlobal("fetch", fetchMock);

    await expect(getPlatformCapabilities()).resolves.toMatchObject({
      environment: "WGS production",
      deployed_pipelines: ["wgs"],
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("reports an HTML success response as a proxy contract error", async () => {
    window.__AIRFLOW_DEMO_CONFIG__ = {apiBaseUrl: "/api"};
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(new Response(
      "<!doctype html><html><body><div id=\"root\"></div></body></html>",
      {status: 200, headers: {"Content-Type": "text/html"}},
    ))));

    await expect(getPlatformCapabilities()).rejects.toMatchObject({
      name: "ApiError",
      status: 200,
      code: "INVALID_API_RESPONSE",
    });
    await expect(getPlatformCapabilities()).rejects.toThrow(/HTML instead of JSON.*\/platform\/capabilities/i);
  });

  it("reports an HTML 403 without exposing a JSON parser exception", async () => {
    window.__AIRFLOW_DEMO_CONFIG__ = {apiBaseUrl: "/api"};
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      "<html><title>403 Forbidden</title></html>",
      {status: 403, statusText: "Forbidden", headers: {"Content-Type": "text/html"}},
    )));

    const request = getPlatformCapabilities();
    await expect(request).rejects.toBeInstanceOf(ApiError);
    await expect(request).rejects.toThrow(/403 Forbidden.*gateway returned HTML/i);
    await expect(request).rejects.not.toThrow(/Unexpected token|JSON/i);
  });

  it("reports an empty successful response with endpoint context", async () => {
    window.__AIRFLOW_DEMO_CONFIG__ = {apiBaseUrl: "/api"};
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(new Response(null, {status: 204}))));

    await expect(getPlatformCapabilities()).rejects.toMatchObject({
      name: "ApiError",
      status: 204,
      code: "EMPTY_API_RESPONSE",
    });
    await expect(getPlatformCapabilities()).rejects.toThrow(/empty response.*\/platform\/capabilities/i);
  });
});
