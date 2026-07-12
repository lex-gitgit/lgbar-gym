import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api";
import ExercisePicker from "../components/ExercisePicker";

export default function PresetForm({ showFlash }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  const [name, setName] = useState("");
  const [exercises, setExercises] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.get("/exercises/").then(setExercises);
    if (isEdit) {
      api.get(`/presets/${id}/`).then((data) => {
        setName(data.name);
        setSelected(new Set(data.exercises.map((e) => e.exercise)));
      });
    }
  }, [id, isEdit]);

  const toggle = (exId) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(exId)) next.delete(exId);
      else next.add(exId);
      return next;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || selected.size === 0) {
      showFlash("Please provide a name and select exercises.", "error");
      return;
    }
    setSubmitting(true);
    try {
      const body = { name, exercises: Array.from(selected).join(",") };
      if (isEdit) {
        await api.put(`/presets/${id}/`, body);
        showFlash(`Preset "${name}" updated!`);
        navigate(`/presets/${id}`);
      } else {
        const data = await api.post("/presets/", body);
        showFlash(`Preset "${name}" created!`);
        navigate(`/presets/${data.id}`);
      }
    } catch (err) {
      showFlash(err.message, "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="page-header">
        <h1>{isEdit ? "Edit" : "New"} Preset</h1>
      </div>
      <form onSubmit={handleSubmit}>
        <div className="card">
          <div className="form-group">
            <label htmlFor="name">Preset Name</label>
            <input type="text" id="name" placeholder="e.g. Pull Day" required
              value={name} onChange={(e) => setName(e.target.value)} />
          </div>
        </div>

        <div className="card">
          <h2>Exercises</h2>
          <ExercisePicker exercises={exercises} selected={selected} onToggle={toggle} />
        </div>

        <button type="submit" className="btn btn-primary w-full" style={{ padding: "14px" }} disabled={submitting}>
          {submitting ? <><span className="spinner spinner--white" /> Saving…</> : "Save Preset"}
        </button>
      </form>
    </>
  );
}
