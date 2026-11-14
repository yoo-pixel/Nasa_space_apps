import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DataNotice, StatusPill, prettyMetric } from "./Ui";

describe("shared interface components", () => {
  it("labels demo values and explains the review boundary", () => {
    render(<DataNotice />);
    expect(screen.getByText(/synthetic and not NASA observations/i)).toBeInTheDocument();
    expect(screen.getByText(/not diagnoses/i)).toBeInTheDocument();
  });

  it("renders a readable status", () => {
    render(<StatusPill status="acknowledged" />);
    expect(screen.getByText("acknowledged")).toBeInTheDocument();
  });

  it("formats physiological metric keys", () => {
    expect(prettyMetric("heart_rate")).toBe("Heart rate");
  });
});