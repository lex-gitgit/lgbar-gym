import { useState, useEffect, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";

const BODY_PART_LABELS = {
  chest: "Chest", back: "Back", shoulders: "Shoulders",
  biceps: "Biceps", triceps: "Triceps", legs: "Legs", core: "Core", cardio: "Cardio",
};

const BTN_PARTS = [
  { key: "chest", label: "Chest" }, { key: "back", label: "Back" },
  { key: "shoulders", label: "Shoulders" }, { key: "biceps", label: "Biceps" },
  { key: "triceps", label: "Triceps" }, { key: "legs", label: "Legs" },
  { key: "core", label: "Core" },
];

function CatalogueTab({ showFlash }) {
  const [exercises, setExercises] = useState([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [bodyPart, setBodyPart] = useState("chest");
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [filterPart, setFilterPart] = useState("");
  const [adding, setAdding] = useState(false);

  const load = () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (filterPart) params.set("body_part", filterPart);
    api.get(`/exercises/?${params.toString()}`).then(setExercises).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [search, filterPart]);

  const grouped = useMemo(() => {
    const map = {};
    for (const ex of exercises) {
      const key = ex.body_part || "other";
      if (!map[key]) map[key] = [];
      map[key].push(ex);
    }
    return map;
  }, [exercises]);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setAdding(true);
    await api.post("/exercises/", { name, body_part: bodyPart });
    setName("");
    setBodyPart("chest");
    setShowForm(false);
    setAdding(false);
    showFlash(`"${name}" added!`);
    load();
  };

  const handleDelete = async (id, n) => {
    if (!confirm(`Delete ${n}?`)) return;
    try {
      await api.del(`/exercises/${id}/`);
      showFlash(`"${n}" deleted.`);
      load();
    } catch (err) {
      showFlash(err.message || "Couldn't delete exercise.", "error");
    }
  };

  return (
    <>
      <div className="card" style={{ marginBottom: 16 }}>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "+ Add Exercise"}
        </button>

        {showForm && (
          <form onSubmit={handleAdd} style={{ marginTop: 12 }}>
            <div className="form-row">
              <div className="form-group" style={{ flex: 2 }}>
                <input type="text" placeholder="Exercise name…" required
                  value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <select value={bodyPart} onChange={(e) => setBodyPart(e.target.value)}>
                  {BTN_PARTS.map((p) => (
                    <option key={p.key} value={p.key}>{p.label}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <button type="submit" className="btn btn-primary w-full" disabled={adding}>
                  {adding ? <><span className="spinner spinner--white" /> Adding…</> : "Add"}
                </button>
              </div>
            </div>
          </form>
        )}
      </div>

      <div className="card" style={{ marginBottom: "16px" }}>
        <div className="form-row">
          <div className="form-group" style={{ flex: 2 }}>
            <input type="text" placeholder="Search exercises…"
              value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <div className="form-group" style={{ flex: 1 }}>
            <select value={filterPart} onChange={(e) => setFilterPart(e.target.value)}>
              <option value="">All body parts</option>
              {BTN_PARTS.map((p) => (
                <option key={p.key} value={p.key}>{p.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="exercise-list">
          {Array.from({ length: 8 }).map((_, i) => (
            <div className="skeleton skeleton-chip" key={i} />
          ))}
        </div>
      ) : Object.keys(grouped).length > 0 ? (
        Object.entries(grouped).map(([part, exs]) => (
          <div key={part} style={{ marginBottom: "20px" }}>
            <h2 className="body-part-heading">{BODY_PART_LABELS[part] || part}</h2>
            <div className="exercise-list stagger-enter">
              {exs.map((ex) => (
                <div className="exercise-chip flex-between" style={{ gap: "8px" }} key={ex.id}>
                  <span>{ex.name}</span>
                  <button className="btn btn-danger btn-sm" style={{ padding: "2px 8px", fontSize: "0.8rem", minWidth: 28 }}
                    onClick={() => handleDelete(ex.id, ex.name)} aria-label={`Delete ${ex.name}`}>✕</button>
                </div>
              ))}
            </div>
          </div>
        ))
      ) : (
        <div className="empty-state">
          <p>No exercises found{search ? ` matching "${search}"` : ""}.</p>
        </div>
      )}
    </>
  );
}

function PresetsTab() {
  const [presets, setPresets] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/presets/").then(setPresets).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="preset-grid">
        {Array.from({ length: 4 }).map((_, i) => (
          <div className="skeleton" key={i} style={{ height: 60, borderRadius: "var(--radius)" }} />
        ))}
      </div>
    );
  }

  return (
    <>
      <div className="flex gap-sm" style={{ marginBottom: 16 }}>
        <Link to="/presets/new" className="btn btn-primary">+ New Preset</Link>
      </div>

      {presets.length > 0 ? (
        <div className="preset-grid stagger-enter">
          {presets.map((p) => (
            <Link to={`/presets/${p.id}`} key={p.id}>
              <div className="preset-card">
                <strong>{p.name}</strong>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <p>No presets yet. Create a preset to quickly log common workouts!</p>
          <Link to="/presets/new" className="btn btn-primary mt-md">Create Preset</Link>
        </div>
      )}
    </>
  );
}

export default function Exercises({ showFlash }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") || "catalogue";

  const setTab = (t) => setSearchParams({ tab: t });

  return (
    <>
      <div className="page-header">
        <h1>Exercises</h1>
      </div>

      <div className="tabs">
        <button className={`tab ${tab === "catalogue" ? "tab--active" : ""}`} onClick={() => setTab("catalogue")}>Catalogue</button>
        <button className={`tab ${tab === "presets" ? "tab--active" : ""}`} onClick={() => setTab("presets")}>Presets</button>
      </div>

      {tab === "catalogue" ? <CatalogueTab showFlash={showFlash} /> : <PresetsTab />}
    </>
  );
}
