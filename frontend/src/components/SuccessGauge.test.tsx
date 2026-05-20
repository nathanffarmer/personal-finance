import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { SuccessGauge } from "./SuccessGauge";

describe("SuccessGauge", () => {
  it("renders the rate as a rounded percentage", () => {
    render(<SuccessGauge rate={0.923} />);
    expect(screen.getByText("92%")).toBeInTheDocument();
  });

  it("renders the 100% and 0% bounds", () => {
    const { rerender } = render(<SuccessGauge rate={1} />);
    expect(screen.getByText("100%")).toBeInTheDocument();
    rerender(<SuccessGauge rate={0} />);
    expect(screen.getByText("0%")).toBeInTheDocument();
  });

  it("labels the gauge", () => {
    render(<SuccessGauge rate={0.5} />);
    expect(screen.getByText("Probability of success")).toBeInTheDocument();
  });
});
