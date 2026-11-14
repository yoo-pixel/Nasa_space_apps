import { api } from "./api";
import type { MissionBrief } from "../types";

export const getMissions = async () => (await api.get<Array<MissionBrief & { start_date?: string; description?: string }>>("/missions")).data;