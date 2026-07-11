import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api } from "../api";

export default function PresetDetail({ showFlash }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [preset, setPreset] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get(`/presets/${id}/`).then(setPreset).catch(() => {}).finally(() => setLoading(false));
  }, [id]);

  const handleDelete = async () => {
    if (!confirm(`Delete preset "${preset.name}"?`)) return;
    await api.del(`/presets/${id}/`);
    showFlash(`Preset "${preset.name}" deleted.`);
    navigate("/presets");
  };

  if (loading) {
    return (
      <>
        <div className="skeleton skeleton-text" style={{ height: 32, width: 200, marginBottom: 8 }} />
        <div className="skeleton skeleton-text short" style={{ marginBottom: 24 }} />
        <div className="skeleton" style={{ height: 48, borderRadius: "var(--radius-sm)", marginBottom: 6 }} />
        <div className="skeleton" style={{ height: 48, borderRadius: "var(--radius-sm)", marginBottom: 6 }} />
        <div className="skeleton" style={{ height: 48, borderRadius: "var(--radius-sm)", marginBottom: 6 }} />
      </>
    );
  }

  if (!preset) return null;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>{preset.name}</h1>
          <p className="text-muted">{preset.exercises.length} exercise{preset.exercises.length !== 1 ? "s" : ""}</p>
        </div>
        <div className="flex gap-sm">
          <Link to={`/day/new?preset=${preset.id}`} className="btn btn-primary">Use for Workout</Link>
          <Link to={`/presets/${preset.id}/edit`} className="btn btn-secondary">Edit</Link>
          <button className="btn btn-danger" onClick={handleDelete}>Delete</button>
        </div>
      </div>

      {preset.exercises.map((pe, i) => (
        <div className="exercise-chip" style={{ display: "flex", alignItems: "center", gap: "8px", padding: "12px 16px", marginBottom: "6px" }} key={pe.id}>
          <span style={{ color: "var(--text-muted)", fontWeight: 600 }}>{i + 1}.</span>
          <span style={{ flex: 1 }}>{pe.exercise_name}</span>
          <span className="body-part-badge">{pe.exercise_body_part}</span>
        </div>
      ))}

      {preset.exercises.length === 0 && (
        <div className="empty-state">
          <p>This preset has no exercises yet.</p>
        </div>
      )}

      <div className="text-center mt-md">
        <Link to="/presets" className="btn btn-secondary">Back to Presets</Link>
      </div>
    </>
  );
}
