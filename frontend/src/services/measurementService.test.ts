import AxiosMockAdapter from "axios-mock-adapter";
import { afterEach, describe, expect, it } from "vitest";
import { api } from "./api";
import { submitMeasurement } from "./measurementService";

const mock = new AxiosMockAdapter(api);
afterEach(() => mock.reset());

describe("measurement API service", () => {
  it("posts validated manual readings to the astronaut endpoint", async () => {
    mock.onPost("/astronauts/crew-7/measurements").reply(201, {
      id: "m-1", astronaut_id: "crew-7", metric: "spo2", value: 97, unit: "%",
      source_type: "manual", symptoms: [], notes: "", measured_at: "2026-01-01T10:00:00Z", data_source_id: null,
    });
    const saved = await submitMeasurement("crew-7", { metric: "spo2", value: 97, unit: "%", source_type: "manual" });
    expect(saved.id).toBe("m-1");
    expect(saved.source_type).toBe("manual");
  });
});