import { useState, useEffect, useMemo, useCallback } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

function formatDate(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
}

function getWeekLabel(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days < 7) return "This Week";
  if (days < 14) return "Last Week";
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function startOfWeek(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  d.setDate(diff);
  return d.toISOString().slice(0, 10);
}

const PADDING = { top: 20, right: 20, bottom: 28, left: 52 };
const CHART_WIDTH = 740;
const CHART_HEIGHT = 220;

function buildPath(points) {
  if (points.length === 0) return "";
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const cp1x = prev.x + (points[i].x - prev.x) / 2;
    const cp1y = prev.y;
    const cp2x = points[i].x - (points[i].x - prev.x) / 2;
    const cp2y = points[i].y;
    d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${points[i].x} ${points[i].y}`;
  }
  return d;
}

function SVGLineChart({ data, color, fillColor, formatValue, height }) {
  if (!data || data.length < 2) return null;

  const max = Math.max(...data.map((d) => d.value));
  const min = 0;
  const range = max - min || 1;
  const w = CHART_WIDTH;
  const h = height || CHART_HEIGHT;
  const chartW = w - PADDING.left - PADDING.right;
  const chartH = h - PADDING.top - PADDING.bottom;

  const points = data.map((d, i) => ({
    x: PADDING.left + (i / (data.length - 1)) * chartW,
    y: PADDING.top + chartH - ((d.value - min) / range) * chartH,
    value: d.value,
    label: d.label,
  }));

  const linePath = buildPath(points);
  const areaPath = linePath + ` L ${points[points.length - 1].x} ${PADDING.top + chartH} L ${points[0].x} ${PADDING.top + chartH} Z`;

  const yTicks = 4;
  const tickValues = Array.from({ length: yTicks + 1 }, (_, i) => min + (range / yTicks) * i);

  return (
    <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} style={{ display: "block", overflow: "visible" }}>
      {tickValues.map((v, i) => {
        const y = PADDING.top + chartH - ((v - min) / range) * chartH;
        return (
          <g key={i}>
            <line x1={PADDING.left} y1={y} x2={w - PADDING.right} y2={y}
              stroke="var(--border)" strokeWidth="1" strokeDasharray="4 4" />
            <text x={PADDING.left - 8} y={y + 4} textAnchor="end" fontSize="11"
              fill="var(--text-dim)" fontVariantNumeric="tabular-nums">
              {formatValue ? formatValue(v) : Math.round(v)}
            </text>
          </g>
        );
      })}

      <path d={areaPath} fill={fillColor || "var(--accent-light)"} />
      <path d={linePath} fill="none" stroke={color || "var(--accent)"} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

      {points.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r="5" fill={color || "var(--accent)"} stroke="var(--bg-card)" strokeWidth="2" />
          <circle cx={p.x} cy={p.y} r="1.5" fill="var(--bg-card)" />
          <text x={p.x} y={PADDING.top + chartH + 18} textAnchor="middle" fontSize="11"
            fill="var(--text-muted)">
            {p.label}
          </text>
        </g>
      ))}

      {points.length > 0 && (
        <text x={points[points.length - 1].x + 12} y={points[points.length - 1].y + 4}
          fontSize="12" fontWeight="700" fill={color || "var(--accent)"}
          fontVariantNumeric="tabular-nums">
          {formatValue ? formatValue(points[points.length - 1].value) : points[points.length - 1].value}
        </text>
      )}
    </svg>
  );
}

function MiniLineChart({ data, color }) {
  if (!data || data.length < 2) return null;

  const w = 160;
  const h = 48;
  const pad = { top: 4, right: 4, bottom: 4, left: 4 };
  const chartW = w - pad.left - pad.right;
  const chartH = h - pad.top - pad.bottom;
  const max = Math.max(...data.map((d) => d.weight));
  const min = 0;
  const range = max - min || 1;

  const points = data.map((d, i) => ({
    x: pad.left + (i / (data.length - 1)) * chartW,
    y: pad.top + chartH - ((d.weight - min) / range) * chartH,
  }));

  const path = buildPath(points);
  const area = path + ` L ${points[points.length - 1].x} ${pad.top + chartH} L ${points[0].x} ${pad.top + chartH} Z`;

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{ flexShrink: 0 }}>
      <path d={area} fill={(color || "var(--accent)").replace(")", "0.12)")} />
      <path d={path} fill="none" stroke={color || "var(--accent)"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={points[points.length - 1].x} cy={points[points.length - 1].y} r="3" fill={color || "var(--accent)"} />
    </svg>
  );
}

function Trend({ value }) {
  if (value === 0) return <span className="trend trend--flat">&ndash;</span>;
  if (value > 0) return <span className="trend trend--up">&#8593; {value}</span>;
  return <span className="trend trend--down">&#8595; {Math.abs(value)}</span>;
}

function CollapsibleSection({ title, defaultOpen = true, children, badge }) {
  const [open, setOpen] = useState(defaultOpen);
  const toggle = useCallback(() => setOpen((o) => !o), []);
  return (
    <div className="card collapsible-section">
      <div className="collapsible-header" onClick={toggle} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } }} role="button" tabIndex={0} aria-expanded={open}>
        <h2>{title}</h2>
        <div className="collapsible-header-right">
          {badge && <span className="badge">{badge}</span>}
          <svg className={`chevron ${open ? "chevron--open" : ""}`} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </div>
      <div className={`collapsible-content ${open ? "collapsible-content--open" : ""}`}>
        {children}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [tab, setTab] = useState("analytics");
  const [days, setDays] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/days/").then(async (dayList) => {
      const details = await Promise.all(
        dayList.map((d) => api.get(`/days/${d.id}/`))
      );
      setDays(details);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const now = useMemo(() => new Date(), []);

  const weeksWithWorkouts = useMemo(() => {
    return [...new Set(days.map((d) => startOfWeek(d.date)))].sort().reverse();
  }, [days]);

  const thisWeekStart = useMemo(() => startOfWeek(now.toISOString().slice(0, 10)), [now]);

  const streak = useMemo(() => {
    let count = 0;
    for (let i = 0; i < weeksWithWorkouts.length; i++) {
      const expected = new Date(now);
      expected.setDate(expected.getDate() - expected.getDay() + 1 - i * 7);
      if (weeksWithWorkouts[i] === startOfWeek(expected.toISOString().slice(0, 10))) count++;
      else break;
    }
    return count;
  }, [weeksWithWorkouts, now]);

  const stats = useMemo(() => {
    if (!days.length) return null;
    let totalSets = 0;
    let totalVolume = 0;
    let bestSet = null;
    let thisWeekWorkouts = 0;
    let thisMonthWorkouts = 0;
    let lastWeekWorkouts = 0;
    let bestDay = null;

    const lastWeekStart = new Date(now);
    lastWeekStart.setDate(lastWeekStart.getDate() - lastWeekStart.getDay() + 1 - 7);
    const lastWeekStartStr = startOfWeek(lastWeekStart.toISOString().slice(0, 10));
    const thisMonth = now.getMonth();
    const thisYear = now.getFullYear();

    for (const day of days) {
      const week = startOfWeek(day.date);
      if (week === thisWeekStart) thisWeekWorkouts++;
      if (week === lastWeekStartStr) lastWeekWorkouts++;
      const d = new Date(day.date + "T00:00:00");
      if (d.getMonth() === thisMonth && d.getFullYear() === thisYear) thisMonthWorkouts++;

      let dayVol = 0;
      for (const we of day.exercises || []) {
        for (const s of we.sets || []) {
          if (s.weight_unit !== "kg") continue;
          totalSets++;
          const vol = parseFloat(s.weight) * s.reps;
          dayVol += vol;
          totalVolume += vol;
          if (!bestSet || vol > bestSet.volume) {
            bestSet = { exercise: we.exercise_name, weight: parseFloat(s.weight), reps: s.reps, volume: vol };
          }
        }
      }
      if (!bestDay || dayVol > bestDay.volume) {
        bestDay = { date: day.date, volume: Math.round(dayVol) };
      }
    }

    const weeklyTrend = thisWeekWorkouts - lastWeekWorkouts;

    return {
      totalWorkouts: days.length,
      totalSets,
      totalVolume: Math.round(totalVolume),
      bestSet,
      thisWeek: thisWeekWorkouts,
      thisMonth: thisMonthWorkouts,
      weeklyTrend,
      streak,
      bestDay,
      avgWorkoutsPerWeek: (days.length / Math.max(weeksWithWorkouts.length, 1)).toFixed(1),
    };
  }, [days, thisWeekStart, now, weeksWithWorkouts, streak]);

  const weeklyVolume = useMemo(() => {
    if (!days.length) return [];
    const map = {};
    for (const day of days) {
      const week = startOfWeek(day.date);
      if (!map[week]) map[week] = 0;
      for (const we of day.exercises || []) {
        for (const s of we.sets || []) {
          if (s.weight_unit !== "kg") continue;
          map[week] += parseFloat(s.weight) * s.reps;
        }
      }
    }
    return Object.entries(map)
      .map(([week, value]) => ({ label: getWeekLabel(week), value: Math.round(value) }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [days]);

  const exerciseProgress = useMemo(() => {
    if (!days.length) return [];
    const map = {};
    const sorted = [...days].sort((a, b) => a.date.localeCompare(b.date));
    const exFrequency = {};
    const exWeeks = {};
    for (const day of sorted) {
      const week = startOfWeek(day.date);
      for (const we of day.exercises || []) {
        if (!exFrequency[we.exercise_name]) exFrequency[we.exercise_name] = 0;
        if (!exWeeks[we.exercise_name]) exWeeks[we.exercise_name] = new Set();
        if (!exWeeks[we.exercise_name].has(week)) {
          exFrequency[we.exercise_name]++;
          exWeeks[we.exercise_name].add(week);
        }
        if (!map[we.exercise_name]) {
          map[we.exercise_name] = { name: we.exercise_name, progress: [] };
        }
        for (const s of we.sets || []) {
          if (s.weight_unit !== "kg") continue;
          const existing = map[we.exercise_name].progress;
          const last = existing[existing.length - 1];
          const w = parseFloat(s.weight);
          if (!last || last.weight !== w) {
            existing.push({ weight: w, reps: s.reps });
          }
        }
      }
    }
    return Object.values(map)
      .filter((ex) => ex.progress.length > 1)
      .map((ex) => ({
        ...ex,
        frequency: exFrequency[ex.name] || 0,
      }));
  }, [days]);

  const prs = useMemo(() => {
    if (!days.length) return [];
    const bestPerEx = {};
    for (const day of days) {
      for (const we of day.exercises || []) {
        for (const s of we.sets || []) {
          if (s.weight_unit !== "kg") continue;
          const w = parseFloat(s.weight);
          const vol = w * s.reps;
          const key = we.exercise_name;
          if (!bestPerEx[key] || vol > bestPerEx[key].volume) {
            bestPerEx[key] = { exercise: key, weight: w, reps: s.reps, volume: vol };
          }
        }
      }
    }
    return Object.values(bestPerEx).sort((a, b) => b.volume - a.volume);
  }, [days]);

  if (loading) {
    return (
      <>
        <div className="skeleton skeleton-text" style={{ height: 32, width: 180, marginBottom: 24 }} />
        <div className="skeleton skeleton-card" />
        <div className="skeleton skeleton-card" />
        <div className="skeleton skeleton-card" />
      </>
    );
  }

  return (
    <>
      <div className="page-header">
        <h1>Dashboard</h1>
        <div className="flex gap-sm">
          <Link to="/day/new" className="btn btn-primary">+ Log Workout</Link>
        </div>
      </div>

      <div className="tabs">
        <button className={`tab ${tab === "analytics" ? "tab--active" : ""}`} onClick={() => setTab("analytics")}>Analytics</button>
        <button className={`tab ${tab === "workouts" ? "tab--active" : ""}`} onClick={() => setTab("workouts")}>Past Workouts</button>
      </div>

      {tab === "analytics" && (
        days.length > 0 ? (
          <>
            <div className="analytics-stats">
              <div className="analytics-stat-card">
                <div className="analytics-stat-value">{stats.thisWeek}</div>
                <div className="analytics-stat-label">This Week</div>
                <div className="analytics-stat-sub">
                  workouts <Trend value={stats.weeklyTrend} />
                </div>
              </div>
              <div className="analytics-stat-card">
                <div className="analytics-stat-value">{stats.thisMonth}</div>
                <div className="analytics-stat-label">This Month</div>
                <div className="analytics-stat-sub">workouts logged</div>
              </div>
              <div className="analytics-stat-card">
                <div className="analytics-stat-value">{stats.streak}</div>
                <div className="analytics-stat-label">Streak</div>
                <div className="analytics-stat-sub">consecutive weeks</div>
              </div>
              <div className="analytics-stat-card">
                <div className="analytics-stat-value">{stats.avgWorkoutsPerWeek}</div>
                <div className="analytics-stat-label">Avg / Week</div>
                <div className="analytics-stat-sub">{stats.totalWorkouts} total workouts</div>
              </div>
            </div>

            {weeklyVolume.length > 1 && (
              <CollapsibleSection title="Volume Trend" badge={`${weeklyVolume[weeklyVolume.length - 1].value.toLocaleString()} kg`}>
                <div className="svg-chart-wrap">
                  <SVGLineChart data={weeklyVolume} formatValue={(v) => `${(v / 1000).toFixed(1)}K`} />
                </div>
              </CollapsibleSection>
            )}

            {exerciseProgress.length > 0 && (
              <CollapsibleSection title="Strength Progression" defaultOpen={false}>
                <div className="analytics-exercise-list">
                  {exerciseProgress.map((ex) => {
                    const first = ex.progress[0].weight;
                    const last = ex.progress[ex.progress.length - 1].weight;
                    const change = ((last - first) / first * 100).toFixed(0);
                    return (
                      <div key={ex.name} className="analytics-exercise">
                        <div className="analytics-exercise-header">
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <strong>{ex.name}</strong>
                            <div className="text-muted" style={{ fontSize: "0.75rem", marginTop: 2 }}>
                              {first} kg &rarr; {last} kg &middot; <Trend value={Number(change)} />
                              <span style={{ marginLeft: 10 }}>{ex.frequency} week{ex.frequency !== 1 ? "s" : ""}</span>
                            </div>
                          </div>
                          <MiniLineChart data={ex.progress} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CollapsibleSection>
            )}

            {prs.length > 0 && (
              <CollapsibleSection title="Personal Records" defaultOpen={false}>
                <div className="analytics-pr-list">
                  {prs.map((pr, i) => (
                    <div key={i} className="analytics-pr-row">
                      <span className="analytics-pr-rank">#{i + 1}</span>
                      <span className="analytics-pr-exercise">{pr.exercise}</span>
                      <span className="analytics-pr-value">{pr.weight} kg &times; {pr.reps}</span>
                      <span className="analytics-pr-volume">{pr.volume.toLocaleString()} kg</span>
                    </div>
                  ))}
                </div>
                {stats.bestDay && (
                  <div className="text-muted" style={{ marginTop: 12, fontSize: "0.8rem", textAlign: "center" }}>
                    Best day: {formatDate(stats.bestDay.date)} &middot; {stats.bestDay.volume.toLocaleString()} kg
                  </div>
                )}
              </CollapsibleSection>
            )}
          </>
        ) : (
          <div className="empty-state">
            <p style={{ fontSize: "1.2rem", marginBottom: "8px" }}>No data yet</p>
            <p style={{ marginBottom: "24px" }}>Log some workouts to see your progress here.</p>
            <Link to="/day/new" className="btn btn-primary">Log Your First Workout</Link>
          </div>
        )
      )}

      {tab === "workouts" && (
        days.length > 0 ? (
          <div className="stagger-enter">
            {days.map((day) => (
              <Link to={`/day/${day.id}`} key={day.id} style={{ textDecoration: "none", color: "inherit" }}>
                <div className="card">
                  <div className="flex-between">
                    <div>
                      <strong style={{ fontSize: "1.1rem" }}>{formatDate(day.date)}</strong>
                      {day.preset_name && <span className="preset-badge">{day.preset_name}</span>}
                      <div className="text-muted" style={{ marginTop: 6 }}>
                        {day.exercise_count} exercise{day.exercise_count !== 1 ? "s" : ""}
                      </div>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <p style={{ fontSize: "1.2rem", marginBottom: "8px" }}>No workouts logged yet</p>
            <p style={{ marginBottom: "24px" }}>Start by logging your first workout day!</p>
            <Link to="/day/new" className="btn btn-primary">Log Your First Workout</Link>
          </div>
        )
      )}
    </>
  );
}
