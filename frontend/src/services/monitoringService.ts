import { api } from "./api";
import type { BoneAssessment, HealthDomain, LearningSnapshot, MonitoringSummary, RadiationRecord } from "../types";

export const getMonitoringSummary = async () => (await api.get<MonitoringSummary>("/dashboard/monitoring-summary")).data;
export const getLearning = async (id: string) => (await api.get<LearningSnapshot>(`/astronauts/${id}/learning`)).data;
export const startLearning = async (id: string, startedBy: string) => (await api.post<LearningSnapshot>(`/astronauts/${id}/learning`, { started_by: startedBy })).data;
export const approveLearningProfile = async (sessionId: string, approvedBy: string) =>
  (await api.post<LearningSnapshot>(`/learning/${sessionId}/approve`, { approved_by: approvedBy })).data;
export const getHealthDomains = async (id: string) => (await api.get<HealthDomain[]>(`/astronauts/${id}/health-domains`)).data;
export const getBoneAssessments = async (id: string) => (await api.get<BoneAssessment[]>(`/astronauts/${id}/bone-health`)).data;
export const createBoneAssessment = async (id: string, payload: Omit<BoneAssessment, "id" | "astronaut_id" | "recorded_at"> & { recorded_at?: string }) =>
  (await api.post<BoneAssessment>(`/astronauts/${id}/bone-health`, payload)).data;
export const getRadiationRecords = async (id: string) => (await api.get<RadiationRecord[]>(`/astronauts/${id}/radiation`)).data;
export const createRadiationRecord = async (id: string, payload: Omit<RadiationRecord, "id" | "astronaut_id" | "measured_at"> & { measured_at?: string }) =>
  (await api.post<RadiationRecord>(`/astronauts/${id}/radiation`, payload)).data;
