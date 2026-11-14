export type Status = "stable" | "monitoring" | "review" | "open" | "acknowledged" | "resolved";
export type MissionBrief = { id: string; name: string; status: string; destination: string };
export type Astronaut = {
  id: string; mission_id: string; full_name: string; callsign: string; role: string; nationality: string;
  avatar_color: string; monitoring_status: string; notes: string; mission: MissionBrief;
};
export type Measurement = {
  id: string; astronaut_id: string; data_source_id: string | null; metric: string; value: number; unit: string;
  measured_at: string; source_type: string; symptoms: string[]; notes: string;
};
export type Baseline = {
  id: string; astronaut_id: string; metric: string; unit: string; median: number; lower_bound: number;
  upper_bound: number; sample_count: number; method: string; updated_at: string;
};
export type MedicalHistory = {
  id: string; astronaut_id: string; category: string; summary: string; recorded_at: string; recorded_by: string;
  source: string; verification_status: "unverified" | "verified" | "not_verified"; review_notes: string;
  reviewed_by: string; reviewed_at: string | null;
};
export type LearningRequirement = { key: string; label: string; required: number; actual: number; met: boolean };
export type LearningTimelineItem = { label: string; days: string; complete: boolean; current: boolean };
export type LearningSnapshot = {
  astronaut_id: string; session_id: string | null; started_at: string | null; started_by: string | null; day_number: number;
  elapsed_days: number; status: "not_started" | "collecting" | "needs_more_data" | "ready_for_review" | "profile_active";
  phase: string; distinct_days: number; reading_count: number; metric_count: number;
  requirements: LearningRequirement[]; timeline: LearningTimelineItem[]; profile_id: string | null; profile_status: string | null;
};
export type BoneAssessment = {
  id: string; astronaut_id: string; assessment_type: "scan" | "turnover_marker" | "exercise" | "nutrition";
  metric: string; value: number; unit: string; recorded_at: string; source: string; source_verified: boolean; notes: string;
};
export type RadiationRecord = {
  id: string; astronaut_id: string; dosimeter_id: string; exposure_type: "absorbed" | "equivalent" | "effective" | "dose_rate";
  measurement_basis: "interval" | "cumulative" | "rate"; value: number; unit: string; measured_at: string; source: string; mission_phase: string; event: string;
  shielding: string; source_verified: boolean; notes: string;
};
export type HealthDomain = { key: string; label: string; status: "data_available" | "insufficient" | "unavailable" | "not_monitored" | "awaiting_medical_review"; record_count: number; detail: string };
export type MonitoringSummary = { sessions_collecting: number; sessions_ready_for_review: number; histories_awaiting_review: number; bone_record_count: number; radiation_record_count: number; active_profile_count: number };
export type Alert = {
  id: string; astronaut_id: string; analysis_id: string | null; measurement_id: string | null; title: string;
  metric: string; observed_value: number; unit: string; baseline_value: number | null; explanation: string;
  priority: string; status: string; reviewer_notes: string; reviewed_by: string; created_at: string;
  reviewed_at: string | null;
};
export type Analysis = {
  id: string; astronaut_id: string; model_name: string; model_version: string; summary: string;
  findings: Array<{ metric: string; value: number; unit: string; baseline: number; lower_bound: number; upper_bound: number; anomaly_score: number; is_flagged: boolean; explanation: string }>;
  anomaly_score: number | null; needs_review: boolean; created_at: string;
};
export type DataSource = {
  id: string; name: string; organization: string; description: string; dataset_version: string;
  url: string; is_simulated: boolean; status: string;
};
export type DashboardSummary = {
  astronaut_count: number; measurement_count: number; active_alert_count: number; review_count: number;
  mission_name: string; mission_start_date: string | null;
  recent_measurements: Array<{ id: string; astronaut_id: string; astronaut: string; metric: string; value: number; unit: string; measured_at: string; source_type: string }>;
  recent_alerts: Array<{ id: string; astronaut_id: string; astronaut: string; title: string; metric: string; observed_value: number; unit: string; priority: string; status: string; created_at: string }>;
};
