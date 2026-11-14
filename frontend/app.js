const $ = (selector) => document.querySelector(selector);
const form = $("#forecast-form");
const status = $("#forecast-status");
const button = $("#run-forecast");

const SYSTEMS = [
  { key: "heart", title: "Heart & cardiovascular", metric: "resting_hr_bpm", unit: "bpm" },
  { key: "nervous_system", title: "Nervous system & cognition", metric: "winscat_rt_ms", unit: "ms" },
  { key: "radiation_immune", title: "Radiation & immune", metric: "nlr_ratio", unit: "ratio" },
  { key: "bone_loss", title: "Bone & musculoskeletal", metric: "bmd_drift_pct", unit: "%" },
];

function card(label, value, note) {
  const article = document.createElement("article");
  article.className = "pipeline-card";
  const caption = document.createElement("span");
  caption.className = "label";
  caption.textContent = label;
  const strong = document.createElement("strong");
  strong.textContent = value;
  const detail = document.createElement("small");
  detail.textContent = note;
  article.append(caption, strong, detail);
  return article;
}

async function loadDataStatus() {
  const indicator = $("#connection-status");
  const container = $("#pipeline-status");
  try {
    const response = await fetch("/api/v1/ml/data-status");
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    const payload = await response.json();
    const stages = payload.stages;
    const metrics = stages.training.metrics;
    const metricSummary = metrics
      ? `Synthetic-only grouped CV: heart rate t+1 MAE ${Number(metrics.groupkfold_mae).toFixed(2)} bpm; not clinical accuracy.`
      : "Validation metrics not available.";
    container.replaceChildren(
      card("Collection", `${stages.collection.osdr_cached_files.length} OSDR · ${stages.collection.nlsp_local_files.length} NLSP files`, "Raw research inputs are cached separately; nothing is assumed to be an ML label."),
      card("Processing", `${stages.processing.astronaut_count} demo crewmembers · ${stages.processing.daily_rows} daily rows`, `${stages.processing.mission_day_range[0]} to ${stages.processing.mission_day_range[1]} mission days · synthetic input`),
      card("Training & serving", `${stages.training.models_loaded.length} model artifacts loaded`, `${stages.training.dataset_available ? "Training dataset present" : "Training dataset missing"} · ${metricSummary}`),
    );
    indicator.textContent = "API connected";
    indicator.className = "pill ready";
    const ids = stages.processing.astronaut_ids;
    const select = $("#astronaut-id");
    const prior = select.value;
    select.replaceChildren(...ids.map((id) => {
      const option = document.createElement("option");
      option.value = id;
      option.textContent = id;
      return option;
    }));
    if (ids.includes(prior)) select.value = prior;
    const [, maximum] = stages.processing.mission_day_range;
    $("#mission-day").max = String(maximum);
    if (Number($("#mission-day").value) > maximum) $("#mission-day").value = String(maximum);
  } catch (error) {
    indicator.textContent = "API unavailable";
    indicator.className = "pill error";
    container.replaceChildren(card("Connection", "Could not load pipeline status", String(error.message || error)));
  }
}

function formatValue(value, unit) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
  const digits = Math.abs(Number(value)) < 10 ? 2 : 1;
  return `${Number(value).toFixed(digits)} ${unit}`;
}

function renderSystem(system, definition) {
  const article = document.createElement("article");
  article.className = "system-card";
  const top = document.createElement("div");
  top.className = "system-top";
  const titleWrap = document.createElement("div");
  const title = document.createElement("h3");
  title.textContent = definition.title;
  const metric = document.createElement("div");
  metric.className = "metric";
  metric.textContent = `${definition.metric} · next 7 days`;
  titleWrap.append(title, metric);
  top.append(titleWrap);
  if (system.trajectory?.length) {
    const tag = document.createElement("span");
    tag.className = `risk-tag ${system.trajectory[0].risk_level}`;
    tag.textContent = system.trajectory[0].risk_level.replace("demo_", "");
    top.append(tag);
  }
  article.append(top);

  const trajectory = document.createElement("div");
  trajectory.className = "trajectory";
  for (const point of system.trajectory || []) {
    const row = document.createElement("div");
    row.className = "forecast-row";
    const day = document.createElement("span");
    day.textContent = `DAY +${point.day}`;
    const track = document.createElement("span");
    track.className = "bar-track";
    const fill = document.createElement("span");
    fill.className = "bar-fill";
    fill.style.display = "block";
    fill.style.width = `${Math.max(2, Math.min(100, Number(point.demo_score) * 100))}%`;
    track.append(fill);
    const value = document.createElement("span");
    value.className = "value";
    value.textContent = formatValue(point.predicted_value, definition.unit);
    row.append(day, track, value);
    trajectory.append(row);
  }
  article.append(trajectory);
  const coverage = document.createElement("p");
  coverage.className = "driver";
  coverage.textContent = `Observed input coverage: ${system.input_coverage_pct ?? 0}% · primary feature: ${system.primary_driver || "not available"}`;
  article.append(coverage);
  return article;
}

function renderAlerts(alerts) {
  const box = $("#alerts");
  box.replaceChildren();
  box.hidden = false;
  const heading = document.createElement("h3");
  heading.textContent = alerts.length ? "Demo threshold flags" : "No demo threshold flags";
  box.append(heading);
  if (alerts.length) {
    const list = document.createElement("ul");
    for (const alert of alerts) {
      const item = document.createElement("li");
      item.textContent = `${alert.sensor}: ${alert.trigger} · observed ${formatValue(alert.observed_value, alert.unit || "")}`;
      list.append(item);
    }
    box.append(list);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const astronautId = $("#astronaut-id").value;
  const day = Number($("#mission-day").value);
  const systemContainer = $("#systems");
  button.disabled = true;
  systemContainer.replaceChildren();
  $("#data-quality").hidden = true;
  $("#alerts").hidden = true;
  status.textContent = "Loading normalized observations and generating the synthetic forecast…";
  try {
    const response = await fetch(`/api/v1/ml/forecast-from-dataset/${encodeURIComponent(astronautId)}?mission_day=${encodeURIComponent(day)}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || `API returned ${response.status}`);
    status.textContent = `${payload.astronaut_id} · mission day ${payload.mission_day} · source: ${payload.data_origin}`;
    const missing = payload.data_quality?.source_dataset?.latest_missing_fields || payload.data_quality?.latest_missing_fields || [];
    const quality = $("#data-quality");
    quality.textContent = `${payload.data_quality?.latest_observed_field_count ?? 0}/${payload.data_quality?.expected_field_count ?? 21} expected fields observed today. ${missing.length ? `Missing: ${missing.slice(0, 8).join(", ")}${missing.length > 8 ? "…" : ""}.` : ""} Missing values are imputed for this demonstration.`;
    quality.hidden = false;
    renderAlerts(payload.acute_alerts || []);
    for (const definition of SYSTEMS) {
      const system = payload.systems?.[definition.key];
      if (system?.available) systemContainer.append(renderSystem(system, definition));
    }
  } catch (error) {
    status.textContent = `Forecast failed: ${error.message || error}`;
  } finally {
    button.disabled = false;
  }
});

loadDataStatus();
