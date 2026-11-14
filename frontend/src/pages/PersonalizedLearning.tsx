import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, CircleAlert, ClipboardCheck, Clock3, HeartPulse, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { createMedicalHistory, getMedicalHistory, listAstronauts, reviewMedicalHistory } from "../services/astronautService";
import { approveLearningProfile, getLearning, startLearning } from "../services/monitoringService";
import { DataNotice, EmptyState, LoadingState, PageTitle, Panel, formatStamp } from "../components/Ui";
import { ApiError, CrewPicker, StateBadge } from "./HealthCommon";
import { useCrewSelection } from "../state/CrewSelection";

export default function PersonalizedLearning() {
  const queryClient = useQueryClient();
  const { activeAstronautId, setActiveAstronautId } = useCrewSelection();
  const [reviewer, setReviewer] = useState("Dr. Rivera");
  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({});
  const [category, setCategory] = useState("Preflight review");
  const [summary, setSummary] = useState("");
  const [source, setSource] = useState("Medical record");
  const crew = useQuery({ queryKey: ["crew"], queryFn: () => listAstronauts() });
  const astronautId = activeAstronautId || crew.data?.[0]?.id || "";
  const history = useQuery({ queryKey: ["history", astronautId], queryFn: () => getMedicalHistory(astronautId), enabled: !!astronautId });
  const learning = useQuery({ queryKey: ["learning", astronautId], queryFn: () => getLearning(astronautId), enabled: !!astronautId, refetchInterval: 60000 });
  const refresh = async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ["history", astronautId] }), queryClient.invalidateQueries({ queryKey: ["learning", astronautId] }), queryClient.invalidateQueries({ queryKey: ["baselines", astronautId] })]); };
  const review = useMutation({ mutationFn: ({ id, verification_status }: { id: string; verification_status: "verified" | "not_verified" }) => reviewMedicalHistory(id, { verification_status, reviewed_by: reviewer.trim() || "Medical reviewer", review_notes: reviewNotes[id] || "" }), onSuccess: refresh });
  const createHistory = useMutation({ mutationFn: () => createMedicalHistory(astronautId, { category, summary: summary.trim(), source: source.trim(), recorded_by: reviewer.trim() || "Medical reviewer" }), onSuccess: async () => { setSummary(""); await refresh(); } });
  const beginLearning = useMutation({ mutationFn: () => startLearning(astronautId, reviewer.trim() || "Medical reviewer"), onSuccess: refresh });
  const approve = useMutation({ mutationFn: () => approveLearningProfile(learning.data!.session_id!, reviewer.trim() || "Medical reviewer"), onSuccess: refresh });
  if (crew.isLoading) return <LoadingState label="Loading crew" />;
  if (crew.error || !crew.data?.length) return <div className="page-stack"><PageTitle title="Personalized learning" /><EmptyState title="No crew profiles available" detail="Add a crew member before starting a learning session." /></div>;
  const current = learning.data;
  const historyItems = history.data || [];
  const awaitingReview = historyItems.filter((item) => item.verification_status === "unverified").length;
  const progress = current?.session_id ? Math.min(100, (current.elapsed_days / 14) * 100) : 0;
  return <div className="page-stack">
    <PageTitle eyebrow="PERSONALIZED HEALTH PROFILE" title="Start with what’s known" subtitle="Review the record, collect a personal baseline, then publish it for medical review." action={<CrewPicker crew={crew.data} value={astronautId} onChange={setActiveAstronautId} />} />
    <DataNotice />
    <div className="flow-strip"><span className="flow-step active"><b>01</b> Review history</span><ArrowRight size={13} /><span className={current?.session_id ? "flow-step active" : "flow-step"}><b>02</b> Learn from observations</span><ArrowRight size={13} /><span className={current?.status === "profile_active" ? "flow-step active" : "flow-step"}><b>03</b> Approve profile</span></div>
    <Panel title="1. Medical history review" detail="Only records you mark verified may be considered in medical review. Unverified entries block a new session." action={<span className="review-count">{awaitingReview ? `${awaitingReview} need review` : "Review complete"}</span>}>
      <div className="history-review-list">
        {historyItems.map((item) => <article className="history-review-item" key={item.id}>
          <div className="history-review-main"><div className="history-review-title"><strong>{item.category}</strong><StateBadge status={item.verification_status} /></div><p>{item.summary}</p><small>{formatStamp(item.recorded_at, false)} · Source: {item.source} · Entered by {item.recorded_by}</small>{item.review_notes && <small className="review-note">Review note: {item.review_notes}</small>}{item.verification_status === "unverified" && <input className="history-review-note-input" value={reviewNotes[item.id] || ""} onChange={(event) => setReviewNotes((current) => ({ ...current, [item.id]: event.target.value }))} placeholder="Optional reviewer note" aria-label={`Reviewer note for ${item.category}`} />}</div>
          {item.verification_status === "unverified" ? <div className="history-review-actions"><button className="outline-button" disabled={review.isPending} onClick={() => review.mutate({ id: item.id, verification_status: "not_verified" })}>Cannot verify</button><button className="primary-button" disabled={review.isPending} onClick={() => review.mutate({ id: item.id, verification_status: "verified" })}><Check size={13} /> Verify</button></div> : <span className="reviewed-stamp"><ShieldCheck size={13} /> Reviewed by {item.reviewed_by || "Medical reviewer"}</span>}
        </article>)}
        {!history.isLoading && historyItems.length === 0 && <div className="history-review-empty"><CircleAlert size={15} /><span>No history has been recorded. You can add the preflight record below, or start a learning session with no history attached.</span></div>}
      </div>
      <form className="history-entry-form" onSubmit={(event: FormEvent) => { event.preventDefault(); createHistory.mutate(); }}>
        <div className="form-section-label"><ClipboardCheck size={14} /> Add a history entry <small>New entries start as unreviewed</small></div>
        <div className="history-entry-grid">
          <label className="form-label">Category<select value={category} onChange={(event) => setCategory(event.target.value)}><option>Preflight review</option><option>Medication</option><option>Allergy</option><option>Prior condition</option><option>Procedure</option><option>Other</option></select></label>
          <label className="form-label">Record source<input required value={source} onChange={(event) => setSource(event.target.value)} placeholder="e.g. flight medical file" /></label>
          <label className="form-label history-summary-field">Summary<textarea required rows={2} value={summary} onChange={(event) => setSummary(event.target.value)} placeholder="Enter the note as documented; avoid inference." /></label>
        </div>
        <div className="form-actions"><label className="form-label reviewer-field">Reviewer<input value={reviewer} onChange={(event) => setReviewer(event.target.value)} /></label><button className="outline-button" disabled={createHistory.isPending || !summary.trim()}>{createHistory.isPending ? "Saving…" : "Save history"}</button></div>
            <ApiError error={createHistory.error || review.error || history.error || learning.error} />
      </form>
    </Panel>
    <Panel title="2. Fourteen-day personal learning" detail="Progress comes from dated observations. Time passing by itself does not create a personal profile." action={current?.session_id && <StateBadge status={current.status} />}>
      {!current ? <LoadingState label="Loading learning status" /> : <>
        {current.status === "not_started" ? <div className="learning-start-row"><div className="learning-start-icon"><Clock3 size={20} /></div><div><strong>Ready when the history review is complete</strong><p>Learning uses records entered after the session starts. Existing demo readings do not count toward this window.</p></div><button className="primary-button" disabled={beginLearning.isPending || awaitingReview > 0 || history.isLoading || history.isError} onClick={() => beginLearning.mutate()}>{beginLearning.isPending ? "Starting…" : "Start 14-day learning"}<ArrowRight size={14} /></button></div> : <>
          <div className="learning-hero"><div><span className="eyebrow">CURRENT PHASE</span><h3>{current.phase}</h3><p>Day {current.day_number} of 14 · started {current.started_at ? formatStamp(current.started_at, false) : "—"}</p></div><div className="learning-progress-number"><strong>{Math.round(progress)}<small>%</small></strong><span>time elapsed</span></div></div>
          <div className="learning-progress"><i style={{ width: `${progress}%` }} /></div>
          <div className="learning-timeline">{current.timeline.map((step, index) => <div className={`learning-phase ${step.complete ? "complete" : ""} ${step.current ? "current" : ""}`} key={step.label}><span className="learning-phase-dot">{step.complete ? <Check size={11} /> : index + 1}</span><strong>{step.label}</strong><small>Days {step.days}</small></div>)}</div>
          <div className="learning-data-grid"><div><span>Separate days</span><strong>{current.distinct_days} <small>/ 10 required</small></strong></div><div><span>Valid readings</span><strong>{current.reading_count} <small>/ 30 required</small></strong></div><div><span>Metrics observed</span><strong>{current.metric_count} <small>/ 2 required</small></strong></div></div>
          {current.status === "ready_for_review" ? <div className="ready-profile"><div><ShieldCheck size={17} /><span><strong>Data collection criteria met</strong><small>A reviewer can publish an observed personal baseline now.</small></span></div><button className="primary-button" disabled={approve.isPending} onClick={() => approve.mutate()}>{approve.isPending ? "Approving…" : "Approve personal profile"}</button></div> : current.status === "profile_active" ? <div className="ready-profile approved"><div><Check size={17} /><span><strong>Personal profile is active</strong><small>Updated from observed readings and approved by {reviewer}.</small></span></div><Link className="outline-button" to={`/crew/${astronautId}`}>View profile</Link></div> : <div className="learning-next"><Clock3 size={14} /><span>{current.status === "needs_more_data" ? "The 14-day window elapsed, but the evidence criteria are not met. Keep recording; no profile was created." : "Continue regular check-ins. Safety flags and medical review remain active throughout learning."}</span><Link to={`/check-in?astronaut=${astronautId}`}><HeartPulse size={13} /> Record check-in</Link></div>}
          <div className="learning-requirements">{current.requirements.map((item) => <div key={item.key} className={item.met ? "met" : ""}><span>{item.met ? <Check size={12} /> : <CircleAlert size={12} />}{item.label}</span><small>{item.actual} / {item.required}</small></div>)}</div>
        </>}
        <ApiError error={beginLearning.error || approve.error} />
      </>}
    </Panel>
    <div className="safety-banner"><ShieldCheck size={15} /><span><strong>Safety monitoring continues during learning.</strong> Existing alert rules remain active. The profile uses observed personal records, not an automatically retrained or clinically validated model.</span><Link to="/alerts">Open alerts</Link></div>
  </div>;
}
