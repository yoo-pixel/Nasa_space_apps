import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Checkin from "./Checkin";
import { CrewSelectionProvider } from "../state/CrewSelection";

const mocks = vi.hoisted(() => ({
  listAstronauts: vi.fn(),
  submitMeasurement: vi.fn(),
  analyzeAstronaut: vi.fn(),
}));
vi.mock("../services/astronautService", () => ({ listAstronauts: mocks.listAstronauts }));
vi.mock("../services/measurementService", () => ({
  submitMeasurement: mocks.submitMeasurement,
  analyzeAstronaut: mocks.analyzeAstronaut,
}));

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<MemoryRouter><QueryClientProvider client={client}><CrewSelectionProvider><Checkin /></CrewSelectionProvider></QueryClientProvider></MemoryRouter>);
}

describe("health check-in", () => {
  beforeEach(() => {
    mocks.listAstronauts.mockResolvedValue([{
      id: "crew-1", full_name: "Test Crew", callsign: "TEST", role: "Pilot",
      mission: { name: "Asteria-04" },
    }]);
    mocks.submitMeasurement.mockResolvedValue({});
    mocks.analyzeAstronaut.mockResolvedValue({});
  });

  it("requires at least one measurement before submission", async () => {
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /save and analyze/i }));
    expect(await screen.findByText("Enter at least one measurement.")).toBeInTheDocument();
    expect(mocks.submitMeasurement).not.toHaveBeenCalled();
  });

  it("submits a value and runs analysis", async () => {
    renderPage();
    fireEvent.change(await screen.findByLabelText(/Heart rate/), { target: { value: "72" } });
    fireEvent.click(screen.getByRole("button", { name: /save and analyze/i }));
    await waitFor(() => expect(mocks.submitMeasurement).toHaveBeenCalledWith("crew-1", expect.objectContaining({ metric: "heart_rate", value: 72, unit: "bpm", source_type: "manual" })));
    await waitFor(() => expect(mocks.analyzeAstronaut).toHaveBeenCalledWith("crew-1"));
    expect(await screen.findByText(/Check-in saved/)).toBeInTheDocument();
  });
});
