import { api } from "./api";
import type { Astronaut, MedicalHistory } from "../types";

export const listAstronauts = async (params?: { q?: string; status?: string }) =>
  (await api.get<Astronaut[]>("/astronauts", { params })).data;
export const getAstronaut = async (id: string) => (await api.get<Astronaut>("/astronauts/" + id)).data;
export const createAstronaut = async (payload: Record<string, unknown>) =>
  (await api.post<Astronaut>("/astronauts", payload)).data;
export const getMedicalHistory = async (id: string) =>
  (await api.get<MedicalHistory[]>("/astronauts/" + id + "/medical-history")).data;
export const createMedicalHistory = async (id: string, payload: { category: string; summary: string; source: string; recorded_by: string }) =>
  (await api.post<MedicalHistory>(`/astronauts/${id}/medical-history`, payload)).data;
export const reviewMedicalHistory = async (id: string, payload: { verification_status: "verified" | "not_verified"; review_notes?: string; reviewed_by: string }) =>
  (await api.patch<MedicalHistory>(`/medical-history/${id}`, payload)).data;
