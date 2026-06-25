import React, { useState, useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";

const MEALS = ["Breakfast", "Lunch", "Dinner"];

function mondayOf(d) {
  const day = new Date(d);
  day.setHours(0, 0, 0, 0);
  const diff = (day.getDay() + 6) % 7;
  day.setDate(day.getDate() - diff);
  return day;
}

function addDays(d, n) {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

function RecipePicker({ recipes, onPick, onClose }) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);
  const filtered = recipes.filter((r) => r.name.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="dialog-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="picker-dialog">
        <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 8 }}>Pick a Recipe</h2>
        <input
          className="search-bar"
          style={{ width: "100%" }}
          placeholder="Search…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />
        <div className="picker-list" style={{ flex: 1 }}>
          {filtered.map((r) => (
            <div
              key={r.recipe_id}
              className={`picker-item ${selected?.recipe_id === r.recipe_id ? "active" : ""}`}
              onClick={() => setSelected(r)}
              onDoubleClick={() => { onPick(r); onClose(); }}
            >
              {r.name}
              {r.category && <span style={{ color: "var(--text-muted)", fontSize: 11 }}> — {r.category}</span>}
            </div>
          ))}
          {filtered.length === 0 && (
            <div style={{ padding: 12, color: "var(--text-muted)", fontSize: 13 }}>No results</div>
          )}
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn" disabled={!selected} onClick={() => { onPick(selected); onClose(); }}>Add</button>
        </div>
      </div>
    </div>
  );
}

export default function MealPlanner({ recipes, onRecipeClick }) {
  const [week, setWeek] = useState(() => mondayOf(new Date()));
  const [entries, setEntries] = useState([]);
  const [picker, setPicker] = useState(null);
  const [dragging, setDragging] = useState(null);
  const [dragOver, setDragOver] = useState(null);

  const days = Array.from({ length: 7 }, (_, i) => addDays(week, i));

  const load = useCallback(async () => {
    try {
      setEntries(await invoke("get_meal_plan"));
    } catch (_) {}
  }, []);

  useEffect(() => { load(); }, [load]);

  const entryAt = (date, meal) => entries.find((e) => e.date === date && e.meal === meal) ?? null;

  const persist = async (newEntries) => {
    setEntries(newEntries);
    await invoke("save_meal_plan", { entries: newEntries }).catch(() => {});
  };

  const assign = (date, meal, recipe) => {
    const without = entries.filter((e) => !(e.date === date && e.meal === meal));
    persist([...without, { date, meal, recipeId: recipe.recipe_id, recipeName: recipe.name }]);
  };

  const remove = (date, meal) => persist(entries.filter((e) => !(e.date === date && e.meal === meal)));

  const swap = (srcDate, srcMeal, dstDate, dstMeal) => {
    if (srcDate === dstDate && srcMeal === dstMeal) return;
    const src = entryAt(srcDate, srcMeal);
    const dst = entryAt(dstDate, dstMeal);
    let updated = entries.filter(
      (e) => !((e.date === srcDate && e.meal === srcMeal) || (e.date === dstDate && e.meal === dstMeal))
    );
    if (src) updated.push({ ...src, date: dstDate, meal: dstMeal });
    if (dst) updated.push({ ...dst, date: srcDate, meal: srcMeal });
    persist(updated);
  };

  const weekLabel = () => {
    const end = addDays(week, 6);
    if (week.getMonth() === end.getMonth()) {
      return `${week.getDate()}–${end.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })}`;
    }
    return `${week.toLocaleDateString(undefined, { day: "numeric", month: "short" })} – ${end.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}`;
  };

  const today = isoDate(new Date());

  return (
    <div className="planner">
      <div className="planner-nav">
        <button className="btn-ghost" onClick={() => setWeek(addDays(week, -7))}>← Prev</button>
        <span className="week-label">{weekLabel()}</span>
        <button className="btn-ghost" onClick={() => setWeek(addDays(week, 7))}>Next →</button>
        <button className="btn-ghost" style={{ marginLeft: 12 }} onClick={() => setWeek(mondayOf(new Date()))}>Today</button>
        <button className="btn-ghost" onClick={load} title="Refresh from server">↺</button>
      </div>

      <div className="planner-grid">
        {days.map((day) => {
          const date = isoDate(day);
          const dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
          const dayIdx = (day.getDay() + 6) % 7;
          return (
            <div key={date} className="day-col">
              <div className={`day-header ${date === today ? "today" : ""}`}>
                {dayNames[dayIdx]}<br />
                <span style={{ fontSize: 10 }}>{day.toLocaleDateString(undefined, { day: "numeric", month: "short" })}</span>
              </div>
              {MEALS.map((meal) => {
                const entry = entryAt(date, meal);
                const key = `${date}-${meal}`;
                return (
                  <div
                    key={meal}
                    className={`meal-cell ${dragOver === key ? "drag-over" : ""}`}
                    draggable={!!entry}
                    onDragStart={() => entry && setDragging({ date, meal })}
                    onDragEnd={() => { setDragging(null); setDragOver(null); }}
                    onDragOver={(e) => { e.preventDefault(); setDragOver(key); }}
                    onDrop={(e) => { e.preventDefault(); if (dragging) swap(dragging.date, dragging.meal, date, meal); setDragOver(null); setDragging(null); }}
                  >
                    <div className="meal-label">{meal}</div>
                    {entry ? (
                      <>
                        <div
                          className="meal-name"
                          style={{ cursor: "pointer", textDecoration: "underline" }}
                          onClick={() => onRecipeClick(entry.recipeId)}
                        >
                          {entry.recipeName}
                        </div>
                        <div className="meal-cell-actions">
                          <button className="meal-btn" onClick={() => setPicker({ date, meal })}>Change</button>
                          <button className="meal-btn meal-btn-rm" onClick={() => remove(date, meal)}>✕</button>
                        </div>
                      </>
                    ) : (
                      <button className="meal-btn" style={{ marginTop: "auto" }} onClick={() => setPicker({ date, meal })}>
                        + Add
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>

      {picker && (
        <RecipePicker
          recipes={recipes}
          onPick={(r) => assign(picker.date, picker.meal, r)}
          onClose={() => setPicker(null)}
        />
      )}
    </div>
  );
}
