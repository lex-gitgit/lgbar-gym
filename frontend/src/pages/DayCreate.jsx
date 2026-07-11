import { useState, useEffect, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";

const BODY_PART_LABELS = {
  chest: "Chest",
  back: "Back",
  shoulders: "Shoulders",
  biceps: "Biceps",
  triceps: "Triceps",
  legs: "Legs",
  core: "Core",
  cardio: "Cardio",
};

function daysAgoLabel(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const diffDays = Math.round((now.getTime() - d.getTime()) / 86400000);
  if (diffDays <= 0) return "today";
  if (diffDays === 1) return "yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default function DayCreate({ showFlash }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [exercises, setExercises] = useState([]);
  const [presets, setPresets] = useState([]);
  const [presetExercises, setPresetExercises] = useState({});
  const [days, setDays] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [presetId, setPresetId] = useState(searchParams.get("preset") || "");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState("");
  const [showCustom, setShowCustom] = useState(() => Boolean(searchParams.get("preset")));
  const [quickLoggingId, setQuickLoggingId] = useState(null);

  const filtered = useMemo(() => {
    if (!search) return exercises;
    const q = search.toLowerCase();
    return exercises.filter((ex) => ex.name.toLowerCase().includes(q));
  }, [exercises, search]);

  const grouped = useMemo(() => {
    const map = {};
    for (const ex of filtered) {
      const key = ex.body_part || "other";
      if (!map[key]) map[key] = [];
      map[key].push(ex);
    }
    return map;
  }, [filtered]);

  const lastUsedByPreset = useMemo(() => {
    const map = {};
    for (const d of days) {
      if (d.preset && !(d.preset in map)) map[d.preset] = d.date;
    }
    return map;
  }, [days]);

  useEffect(() => {
    Promise.all([
      api.get("/exercises/"),
      api.get("/presets/"),
      api.get("/days/"),
    ]).then(([exData, presetData, dayData]) => {
      setExercises(exData);
      setPresets(presetData);
      setDays(dayData);
      const pe = {};
      Promise.all(
        presetData.map((p) =>
          api.get(`/presets/${p.id}/`).then((d) => {
            pe[p.id] = d.exercises.map((e) => e.exercise);
          })
        )
      ).then(() => setPresetExercises(pe));
    });
  }, []);

  useEffect(() => {
    if (presetId && presetExercises[presetId]) {
      setSelected(new Set(presetExercises[presetId]));
    } else if (!presetId) {
      setSelected(new Set());
    }
  }, [presetId, presetExercises]);

  const toggle = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const quickLog = async (preset) => {
    if (quickLoggingId) return;
    setQuickLoggingId(preset.id);
    try {
      const data = await api.post(`/presets/${preset.id}/quick-log/`, {
        date: new Date().toISOString().slice(0, 10),
      });
      showFlash(`"${preset.name}" logged — review your sets!`);
      navigate(`/day/${data.id}`);
    } catch (err) {
      showFlash(err.message, "error");
      setQuickLoggingId(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (selected.size === 0) {
      showFlash("Please select at least one exercise.", "error");
      return;
    }
    setSubmitting(true);
    try {
      const data = await api.post("/days/", {
        date,
        preset: presetId || null,
        notes,
        exercises: Array.from(selected).join(","),
      });
      showFlash("Workout logged!");
      navigate(`/day/${data.id}`);
    } catch (err) {
      showFlash(err.message, "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="page-header">
        <h1>Log Workout</h1>
      </div>

      {presets.length > 0 && (
        <>
          <div className="card">
            <h2>Quick Start</h2>
            <div className="preset-quick-grid">
              {presets.map((p) => {
                const count = (presetExercises[p.id] || []).length;
                const lastDate = lastUsedByPreset[p.id];
                const busy = quickLoggingId === p.id;
                return (
                  <button
                    type="button"
                    key={p.id}
                    className={`preset-quick-btn ${busy ? "preset-quick-btn--busy" : ""}`}
                    onClick={() => quickLog(p)}
                    disabled={Boolean(quickLoggingId)}
                  >
                    {busy ? (
                      <span className="spinner" />
                    ) : (
                      <>
                        <span className="preset-quick-name">{p.name}</span>
                        <span className="preset-quick-meta">
                          {count} exercise{count !== 1 ? "s" : ""}
                          {lastDate ? ` · last ${daysAgoLabel(lastDate)}` : ""}
                        </span>
                      </>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          <button
            type="button"
            className="btn btn-secondary w-full mb-md"
            onClick={() => setShowCustom((s) => !s)}
          >
            {showCustom ? "Hide Custom Workout" : "+ Custom Workout"}
          </button>
        </>
      )}

      {(showCustom || presets.length === 0) && (
        <form onSubmit={handleSubmit}>
          <div className="card">
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="date">Date</label>
                <input type="date" id="date" value={date} onChange={(e) => setDate(e.target.value)} required />
              </div>
              <div className="form-group">
                <label htmlFor="preset">Preset (optional)</label>
                <select id="preset" value={presetId} onChange={(e) => setPresetId(e.target.value)}>
                  <option value="">— Custom Day —</option>
                  {presets.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label htmlFor="notes">Notes</label>
              <textarea id="notes" rows="2" placeholder="Optional notes…" value={notes}
                onChange={(e) => setNotes(e.target.value)} />
            </div>
          </div>

          <div className="card">
            <h2>Choose Exercises</h2>
            <div style={{ marginBottom: 12 }}>
              <input type="text" placeholder="Search exercises…"
                value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
            {Object.keys(grouped).length > 0 ? (
              Object.entries(grouped).map(([part, exs]) => (
                <div key={part} style={{ marginBottom: 16 }}>
                  <h3 className="body-part-heading">{BODY_PART_LABELS[part] || part}</h3>
                  <div className="exercise-list">
                    {exs.map((ex) => (
                      <button
                        type="button"
                        key={ex.id}
                        className={`exercise-chip ${selected.has(ex.id) ? "selected" : ""}`}
                        onClick={() => toggle(ex.id)}
                        aria-pressed={selected.has(ex.id)}
                      >
                        <span>{ex.name}</span>
                        <span className="body-part-badge">{ex.body_part}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-muted">No exercises found{search ? ` matching "${search}"` : ""}.</p>
            )}
          </div>

          <div className="card">
            <h2>Selected Exercises</h2>
            {selected.size > 0 ? (
              Array.from(selected).map((id) => {
                const ex = exercises.find((e) => e.id === id);
                return (
                  <div className="exercise-chip flex-between" style={{ marginBottom: "4px", cursor: "default" }} key={id}>
                    <span>{ex ? ex.name : id}</span>
                    <button type="button" className="chip-remove" onClick={() => toggle(id)} aria-label={`Remove ${ex ? ex.name : "exercise"}`}>✕</button>
                  </div>
                );
              })
            ) : (
              <p className="text-muted">No exercises selected yet — tap any above to add it.</p>
            )}
          </div>

          <button type="submit" className="btn btn-primary w-full" style={{ padding: "14px", marginBottom: 16 }} disabled={submitting}>
            {submitting ? <><span className="spinner spinner--white" /> Saving…</> : "Start Logging"}
          </button>
        </form>
      )}
    </>
  );
}
