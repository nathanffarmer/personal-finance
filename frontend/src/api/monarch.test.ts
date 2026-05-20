import { describe, expect, it } from "vitest";
import { formatCurrency } from "./monarch";

describe("formatCurrency", () => {
  it("formats positive amounts as whole-dollar USD", () => {
    expect(formatCurrency(1_234_567)).toBe("$1,234,567");
  });

  it("formats negative amounts", () => {
    expect(formatCurrency(-1500)).toBe("-$1,500");
  });

  it("rounds to whole dollars", () => {
    expect(formatCurrency(99.99)).toBe("$100");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0");
  });
});
