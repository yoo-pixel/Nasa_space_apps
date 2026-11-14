import { api } from "./api";
import type { DataSource } from "../types";

export const getDataSources = async () => (await api.get<DataSource[]>("/data-sources")).data;
export const getApiHealth = async () => (await api.get<{ status: string; database: string }>("/health")).data;

export type RadLabRecord = {
  timestamp: string;
  instrument_id: string;
  absorbed_dose_rate: number | null;
  dose_equivalent_rate: number | null;
  latitude: number | null;
  longitude: number | null;
  altitude: number | null;
  spacecraft: string;
};

export type RadLabResponse = {
  source: string;
  source_url: string;
  spacecraft: string;
  instrument: string;
  start: string;
  end: string;
  retrieved_at: string;
  units: { absorbed_dose_rate: string; dose_equivalent_rate: string; altitude: string; latitude: string; longitude: string };
  rows: RadLabRecord[];
  truncated: boolean;
};

export const getRadLabFeed = async (start: string, end: string, instrument: string) =>
  (await api.get<RadLabResponse>("/research/radlab", { params: { start: `${start}:00`, end: `${end}:00`, instrument } })).data;
