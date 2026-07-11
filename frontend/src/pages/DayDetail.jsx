import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api } from "../api";

function formatDate(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" });
}

export default function DayDetail({ showFlash }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [day, setDay] = useState(null);
  const [loading, setLoading] = useState(true);
  const [allExercises, setAllExercises] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get(`/days/${id}/`),
      api.get("/exercises/"),
    ]).then(([dayData, exData]) => {
      setDay(dayData);
      setAllExercises(exData);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const handleDeleteDay = async () => {
    if (!confirm("Delete this entire workout day?")) return;
    await api.del(`/days/${id}/`);
    showFlash("Workout day deleted.");
    navigate("/dashboard");
  };

  const handleAddExercise = async (exerciseId) => {
    await api.post(`/days/${id}/add-exercise/`, { exercise_id: exerciseId });
    const ex = allExercises.find((e) => e.id === exerciseId);
    showFlash(`"${ex.name}" added.`);
    setShowAddForm(false);
    load();
  };

  const handleRemoveExercise = async (weId, name) => {
    if (!confirm("Remove this exercise?")) return;
    await api.del(`/days/${id}/remove-exercise/${weId}/`);
    showFlash("Exercise removed.");
    load();
  };

  const handleAddSet = async (weId, weight, weightUnit, reps) => {
    await api.post(`/sets/${weId}/add/`, { weight, weight_unit: weightUnit, reps });
    load();
  };

  const handleDeleteSet = async (setId) => {
    if (!confirm("Delete this set?")) return;
    await api.del(`/sets/${setId}/delete/`);
    load();
  };

  if (loading) {
    return (
      <>
        <div className="skeleton skeleton-text" style={{ height: 32, width: 280, marginBottom: 24 }} />
        <div className="skeleton skeleton-card" />
        <div className="skeleton skeleton-card" />
        <div className="skeleton skeleton-card" />
      </>
    );
  }

  if (!day) return null;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>{formatDate(day.date)}</h1>
          {day.preset_name && <span className="preset-badge">{day.preset_name}</span>}
          {day.notes && <p className="text-muted" style={{ marginTop: 6 }}>{day.notes}</p>}
        </div>
        <div className="flex gap-sm">
          <button className="btn btn-secondary" onClick={() => setShowAddForm(!showAddForm)} aria-label="Add exercise">+ Add Exercise</button>
          <button className="btn btn-danger" onClick={handleDeleteDay} aria-label="Delete this workout day">Delete Day</button>
        </div>
      </div>

      {showAddForm && (
        <div className="card" style={{ animation: "slideDown 0.2s ease-out" }}>
          <h2>Add Exercise</h2>
          <div className="form-row">
            <div className="form-group" style={{ flex: 3 }}>
                <select defaultValue="" onChange={(e) => e.target.value && handleAddExercise(Number(e.target.value))}>
                <option value="">— Select exercise —</option>
                {allExercises.map((ex) => (
                  <option key={ex.id} value={ex.id}>{ex.name} ({ex.body_part})</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {day.exercises.length > 0 ? (
        day.exercises.map((we) => (
          <div className="exercise-item" key={we.id}>
            <div className="exercise-header"
              onClick={(e) => {
                const s = e.currentTarget.nextElementSibling;
                if (s) s.classList.toggle("hidden");
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  const s = e.currentTarget.nextElementSibling;
                  if (s) s.classList.toggle("hidden");
                }
              }}
              tabIndex={0}
              role="button"
              aria-label={`Toggle ${we.exercise_name} sets`}
            >
              <div className="flex-center">
                <h3>{we.exercise_name}</h3>
                <span className="badge">{we.sets.length} set{we.sets.length !== 1 ? "s" : ""}</span>
              </div>
              <div className="flex-center">
                <button className="btn btn-danger btn-sm" onClick={(e) => { e.stopPropagation(); handleRemoveExercise(we.id, we.exercise_name); }} aria-label={`Remove ${we.exercise_name}`}>Remove</button>
              </div>
            </div>

            <div className="exercise-sets">
              {we.sets.length > 0 && (
                <>
                  <div className="set-row" style={{ fontWeight: 600, fontSize: "0.8rem", color: "var(--text-muted)", borderBottom: "2px solid var(--border)" }}>
                    <span className="set-num">#</span>
                    <span style={{ width: "80px" }}>Weight</span>
                    <span style={{ width: "60px" }}>Unit</span>
                    <span style={{ width: "80px" }}>Reps</span>
                    <span style={{ width: "36px" }}></span>
                  </div>
                  {we.sets.map((s) => (
                    <div className="set-row" key={s.id}>
                      <span className="set-num">{s.set_number}</span>
                      <span style={{ fontVariantNumeric: "tabular-nums" }}>{s.weight}</span>
                      <span className="text-muted">{s.weight_unit}</span>
                      <span style={{ fontVariantNumeric: "tabular-nums" }}>{s.reps} reps</span>
                      <button className="btn btn-danger btn-sm btn-icon"
                        style={{ width: "28px", height: "28px", fontSize: "0.7rem" }}
                        onClick={() => handleDeleteSet(s.id)} aria-label={`Delete set ${s.set_number}`}>✕</button>
                    </div>
                  ))}
                </>
              )}

              <AddSetForm weId={we.id} onAdd={handleAddSet} />
            </div>
          </div>
        ))
      ) : (
        <div className="empty-state">
          <p>No exercises in this workout yet</p>
          <button className="btn btn-primary mt-md" onClick={() => setShowAddForm(true)}>Add Exercise</button>
        </div>
      )}

      <div style={{ textAlign: "center", marginTop: "20px" }}>
        <Link to="/dashboard" className="btn btn-secondary">Back to Dashboard</Link>
      </div>
    </>
  );
}

function AddSetForm({ weId, onAdd }) {
  const [weight, setWeight] = useState("");
  const [weightUnit, setWeightUnit] = useState("kg");
  const [reps, setReps] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!weight || !reps) return;
    setSubmitting(true);
    await onAdd(weId, weight, weightUnit, reps);
    setWeight("");
    setReps("");
    setSubmitting(false);
  };

  return (
    <form onSubmit={handleSubmit} className="set-add-form">
      <div className="form-group">
        <label htmlFor={`weight-${weId}`}>Weight</label>
        <input id={`weight-${weId}`} type="number" step="0.5" min="0" placeholder="0" required
          value={weight} onChange={(e) => setWeight(e.target.value)} />
      </div>
      <div className="form-group">
        <label htmlFor={`unit-${weId}`}>Unit</label>
        <select id={`unit-${weId}`} value={weightUnit} onChange={(e) => setWeightUnit(e.target.value)}>
          <option value="kg">kg</option>
          <option value="lbs">lbs</option>
        </select>
      </div>
      <div className="form-group">
        <label htmlFor={`reps-${weId}`}>Reps</label>
        <input id={`reps-${weId}`} type="number" min="1" placeholder="0" required
          value={reps} onChange={(e) => setReps(e.target.value)} />
      </div>
      <div className="form-group">
        <label>&nbsp;</label>
        <button type="submit" className="btn btn-primary w-full" disabled={submitting}>
          {submitting ? <><span className="spinner spinner--white" /> Adding…</> : "+ Set"}
        </button>
      </div>
    </form>
  );
}
