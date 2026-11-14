import { api } from "./api";
import type { Alert } from "../types";

export const getAlerts = async (status?: string) =>
  (await api.get<Alert[]>("/alerts", { params: status && status !== "all" ? { status } : {} })).data;
export const getAlert = async (id: string) => (await api.get<Alert>("/alerts/" + id)).data;
export const updateAlert = async (id: string, payload: Partial<Pick<Alert, "status" | "reviewer_notes" | "reviewed_by">>) =>
  (await api.patch<Alert>("/alerts/" + id, payload)).data;