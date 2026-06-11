import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/svelte";
import SuccessGauge from "./SuccessGauge.svelte";

describe("SuccessGauge", () => {
  it("renders the rate as a rounded percentage", () => {
    render(SuccessGauge, { props: { rate: 0.923 } });
    expect(screen.getByText("92%")).toBeInTheDocument();
  });

  it("renders the 100% bound", () => {
    render(SuccessGauge, { props: { rate: 1 } });
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("renders the 0% bound", () => {
    render(SuccessGauge, { props: { rate: 0 } });
    expect(screen.getByText("0%")).toBeInTheDocument();
  });

  it("labels the gauge", () => {
    render(SuccessGauge, { props: { rate: 0.5 } });
    expect(screen.getByText("Probability of success")).toBeInTheDocument();
  });
});
