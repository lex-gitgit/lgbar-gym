import { useState, useMemo } from "react";

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

const BODY_PART_ORDER = ["chest", "back", "shoulders", "biceps", "triceps", "legs", "core", "cardio"];

export default function ExercisePicker({ exercises, selected, onToggle }) {
  const [search, setSearch] = useState("");
  const [part, setPart] = useState("all");

  const counts = useMemo(() => {
    const map = {};
    for (const ex of exercises) {
      const key = ex.body_part || "other";
      map[key] = (map[key] || 0) + 1;
    }
    return map;
  }, [exercises]);

  const parts = useMemo(() => {
    const known = BODY_PART_ORDER.filter((p) => counts[p]);
    const extra = Object.keys(counts).filter((p) => !BODY_PART_ORDER.includes(p)).sort();
    return [...known, ...extra];
  }, [counts]);

  const filtered = useMemo(() => {
    let list = exercises;
    if (part !== "all") list = list.filter((ex) => (ex.body_part || "other") === part);
    if (search) {
      const q = search.toLowerCase();
      list = list.filter((ex) => ex.name.toLowerCase().includes(q));
    }
    return list;
  }, [exercises, search, part]);

  const grouped = useMemo(() => {
    const map = {};
    for (const ex of filtered) {
      const key = ex.body_part || "other";
      if (!map[key]) map[key] = [];
      map[key].push(ex);
    }
    return map;
  }, [filtered]);

  // Insertion order, matching the order the user tapped them in.
  const selectedList = useMemo(() => {
    const byId = new Map(exercises.map((ex) => [ex.id, ex]));
    return Array.from(selected).map((id) => byId.get(id) || { id, name: String(id) });
  }, [exercises, selected]);

  return (
    <div className="picker">
      <div className="picker-search">
        <input
          type="text"
          placeholder="Search exercises…"
          aria-label="Search exercises"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {search && (
          <button type="button" className="picker-search-clear" aria-label="Clear search" onClick={() => setSearch("")}>
            ✕
          </button>
        )}
      </div>

      <div className="picker-filters">
        <button
          type="button"
          className={`picker-filter ${part === "all" ? "active" : ""}`}
          aria-pressed={part === "all"}
          onClick={() => setPart("all")}
        >
          All <span className="picker-filter-count">{exercises.length}</span>
        </button>
        {parts.map((p) => (
          <button
            type="button"
            key={p}
            className={`picker-filter ${part === p ? "active" : ""}`}
            aria-pressed={part === p}
            onClick={() => setPart((cur) => (cur === p ? "all" : p))}
          >
            {BODY_PART_LABELS[p] || p} <span className="picker-filter-count">{counts[p]}</span>
          </button>
        ))}
      </div>

      <div className="picker-selected-bar">
        <span className="picker-selected-count">{selected.size} selected</span>
        <div className="picker-selected-chips">
          {selectedList.map((ex) => (
            <button
              type="button"
              key={ex.id}
              className="picker-selected-chip"
              onClick={() => onToggle(ex.id)}
              aria-label={`Remove ${ex.name}`}
            >
              {ex.name} <span aria-hidden="true">✕</span>
            </button>
          ))}
          {selectedList.length === 0 && (
            <span className="picker-selected-hint">Tap exercises below to add them</span>
          )}
        </div>
      </div>

      {Object.keys(grouped).length > 0 ? (
        Object.entries(grouped).map(([p, exs]) => (
          <div key={p} className="picker-group">
            <h3 className="body-part-heading">{BODY_PART_LABELS[p] || p}</h3>
            <div className="exercise-list">
              {exs.map((ex) => (
                <button
                  type="button"
                  key={ex.id}
                  className={`exercise-chip ${selected.has(ex.id) ? "selected" : ""}`}
                  onClick={() => onToggle(ex.id)}
                  aria-pressed={selected.has(ex.id)}
                >
                  {selected.has(ex.id) && <span className="exercise-chip-check" aria-hidden="true">✓</span>}
                  <span>{ex.name}</span>
                </button>
              ))}
            </div>
          </div>
        ))
      ) : (
        <p className="text-muted">
          No exercises found{search ? ` matching "${search}"` : ""}
          {part !== "all" ? ` in ${BODY_PART_LABELS[part] || part}` : ""}.
        </p>
      )}
    </div>
  );
}
