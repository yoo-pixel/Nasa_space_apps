import { api } from "./api";
import type { Analysis, Baseline, DashboardSummary, Measurement } from "../types";

export const getDashboard = async () => (await api.get<DashboardSummary>("/dashboard/summary")).data;
export const getMeasurements = async (id: string, metric?: string) =>
  (await api.get<Measurement[]>("/astronauts/" + id + "/measurements", { params: { metric, limit: 1000 } })).data;
export const getBaselines = async (id: string) =>
  (await api.get<Baseline[]>("/astronauts/" + id + "/baseline")).data;
export const submitMeasurement = async (id: string, payload: Record<string, unknown>) =>
  (await api.post<Measurement>("/astronauts/" + id + "/measurements", payload)).data;
export const analyzeAstronaut = async (id: string) =>
  (await api.post<Analysis>("/astronauts/" + id + "/analysis")).data;
export const getAnalyses = async (id: string) =>
  (await api.get<Analysis[]>("/astronauts/" + id + "/analysis")).data;