import {afterEach, describe, expect, it, vi} from "vitest";

import {ApiError, getPlatformCapabilities, getRunWorkspace, listRuns, submitRun} from "./api";

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  delete window.__AIRFLOW_DEMO_CONFIG__;
});

describe("GET request lifetime", () => {
  const readWorkspace = getRunWorkspace as (analysisId: string, options: {
    signal?: AbortSignal;
    timeoutMs?: number;
  }) => ReturnType<typeof getRunWorkspace>;

  it("times out a GET whose response body never finishes", async () => {
    vi.useFakeTimers();
    window.__AIRFLOW_DEMO_CONFIG__ = {apiBaseUrl: "/api"};
    const response = new Response("{}", {status: 200});
    vi.spyOn(response, "text").mockImplementation(() => new Promise<string>(() => {}));
    const fetchMock = vi.fn().mockResolvedValue(response);
    vi.stubGlobal("fetch", fetchMock);
    let failure: unknown;
    void readWorkspace("SYNTHETIC", {timeoutMs: 100}).catch((error) => { failure = error; });

    await vi.advanceTimersByTimeAsync(99);
    expect(failure).toBeUndefined();
    await vi.advanceTimersByTimeAsync(1);
    expect(failure).toMatchObject({name: "TimeoutError"});
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][1]?.signal?.aborted).toBe(true);
  });

  it("shares the GET deadline across the existing network retry", async () => {
    vi.useFakeTimers();
    window.__AIRFLOW_DEMO_CONFIG__ = {apiBaseUrl: "/api"};
    const response = new Response("{}", {status: 200});
    vi.spyOn(response, "text").mockImplementation(() => new Promise<string>(() => {}));
    const fetchMock = vi.fn()
      .mockImplementationOnce(() => new Promise<Response>((_resolve, reject) => {
        window.setTimeout(() => reject(new TypeError("Failed to fetch")), 200);
      }))
      .mockResolvedValueOnce(response);
    vi.stubGlobal("fetch", fetchMock);
    let failure: unknown;
    void readWorkspace("SYNTHETIC", {timeoutMs: 500}).catch((error) => { failure = error; });

    await vi.advanceTimersByTimeAsync(499);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(failure).toBeUndefined();
    await vi.advanceTimersByTimeAsync(1);
    expect(failure).toMatchObject({name: "TimeoutError"});
    expect(fetchMock.mock.calls[1][1]?.signal?.aborted).toBe(true);
  });

  it("does not issue a second GET when aborted during retry backoff", async () => {
    vi.useFakeTimers();
    window.__AIRFLOW_DEMO_CONFIG__ = {apiBaseUrl: "/api"};
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();
    let failure: unknown;
    void readWorkspace("SYNTHETIC", {signal: controller.signal, timeoutMs: 1000})
      .catch((error) => { failure = error; });

    await vi.advanceTimersByTimeAsync(100);
    controller.abort();
    await vi.advanceTimersByTimeAsync(250);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(failure).toMatchObject({name: "AbortError"});
  });

  it("passes Batch Runs cancellation through to the fetch signal", async () => {
    vi.useFakeTimers();
    window.__AIRFLOW_DEMO_CONFIG__ = {apiBaseUrl: "/api"};
    let fetchSignal: AbortSignal | null | undefined;
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      fetchSignal = init?.signal;
      return new Promise<Response>(() => {});
    });
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();
    const failure = listRuns({pipeline: "wgs", limit: 20}, {signal: controller.signal, timeoutMs: 1000})
      .catch((error: unknown) => error);
    await vi.advanceTimersByTimeAsync(0);
    expect(fetchSignal?.aborted).toBe(false);

    controller.abort();
    await expect(failure).resolves.toMatchObject({name: "AbortError"});
    expect(fetchSignal?.aborted).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("does not retry a POST network failure", async () => {
    vi.useFakeTimers();
    window.__AIRFLOW_DEMO_CONFIG__ = {apiBaseUrl: "/api"};
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchMock);
    let failure: unknown;
    void submitRun("SYNTHETIC").catch((error) => { failure = error; });

    await vi.advanceTimersByTimeAsync(500);
    expect(failure).toBeInstanceOf(TypeError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][1]?.method).toBe("POST");
  });
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
