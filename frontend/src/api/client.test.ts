import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, getAppPassword, setAppPassword } from "./client";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(body === undefined ? "" : JSON.stringify(body), { status });
}

describe("api()", () => {
  beforeEach(() => {
    localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("attaches the X-App-Password header when a password is stored", async () => {
    setAppPassword("hunter2");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await api("/api/x");

    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("X-App-Password")).toBe("hunter2");
  });

  it("omits the auth header when no password is set", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(null));
    vi.stubGlobal("fetch", fetchMock);

    await api("/api/x");

    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("X-App-Password")).toBeNull();
  });

  it("sets Content-Type when a body is supplied", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(null));
    vi.stubGlobal("fetch", fetchMock);

    await api("/api/x", { method: "POST", body: JSON.stringify({ a: 1 }) });

    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("throws ApiError carrying the status and parsed body on non-2xx", async () => {
    // A fresh Response per call: a Response body can only be read once.
    const fetchMock = vi
      .fn()
      .mockImplementation(() => Promise.resolve(jsonResponse({ detail: "nope" }, 401)));
    vi.stubGlobal("fetch", fetchMock);

    let caught: unknown;
    try {
      await api("/api/x");
    } catch (e) {
      caught = e;
    }
    expect(caught).toBeInstanceOf(ApiError);
    expect((caught as ApiError).status).toBe(401);
    expect((caught as ApiError).body).toEqual({ detail: "nope" });
  });

  it("returns the parsed JSON body on success", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ value: 42 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await api<{ value: number }>("/api/x");
    expect(result.value).toBe(42);
  });
});

describe("app password storage", () => {
  beforeEach(() => localStorage.clear());

  it("round-trips and clears the password", () => {
    expect(getAppPassword()).toBeNull();
    setAppPassword("abc");
    expect(getAppPassword()).toBe("abc");
    setAppPassword(null);
    expect(getAppPassword()).toBeNull();
  });

  it("treats an empty string as clearing", () => {
    setAppPassword("abc");
    setAppPassword("");
    expect(getAppPassword()).toBeNull();
  });
});
