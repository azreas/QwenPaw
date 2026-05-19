import { describe, it, expect } from "vitest";
import { formatFailureRate, classifyTraceOwner, ROLE_LABELS } from "../userModel";

describe("formatFailureRate", () => {
  it("returns 0% for zero total", () => {
    expect(formatFailureRate(0, 0)).toBe("0%");
  });
  it("calculates percentage", () => {
    expect(formatFailureRate(1, 4)).toBe("25%");
  });
  it("returns 0% for zero failures", () => {
    expect(formatFailureRate(0, 100)).toBe("0%");
  });
  it("returns 100% when all fail", () => {
    expect(formatFailureRate(5, 5)).toBe("100%");
  });
});

describe("classifyTraceOwner", () => {
  it("classifies permission errors", () => {
    expect(classifyTraceOwner("permission_denied:mcp:call")).toBe(
      "permission_config",
    );
  });
  it("classifies timeout as platform", () => {
    expect(classifyTraceOwner("timeout")).toBe("platform_runtime");
  });
  it("classifies unreachable as platform", () => {
    expect(classifyTraceOwner("ConnectionError: unreachable")).toBe(
      "platform_runtime",
    );
  });
  it("defaults to platform_runtime", () => {
    expect(classifyTraceOwner("unknown error")).toBe("platform_runtime");
  });
});

describe("ROLE_LABELS", () => {
  it("has all roles", () => {
    expect(ROLE_LABELS.platform_admin).toBeDefined();
    expect(ROLE_LABELS.tenant_admin).toBeDefined();
    expect(ROLE_LABELS.tenant_member).toBeDefined();
    expect(ROLE_LABELS.tenant_readonly).toBeDefined();
  });
});
