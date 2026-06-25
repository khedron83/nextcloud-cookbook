import React, { useState } from "react";

function DynList({ items, onChange, multiline = false, placeholder = "Add item…" }) {
  const update = (i, val) => onChange(items.map((x, j) => (j === i ? val : x)));
  const remove = (i) => onChange(items.filter((_, j) => j !== i));
  const add = () => onChange([...items, ""]);

  return (
    <div className="dyn-list">
      {items.map((item, i) =>
        multiline ? (
          <div key={i} className="dyn-item">
            <textarea rows={2} value={item} onChange={(e) => update(i, e.target.value)} placeholder={placeholder} />
            <button className="dyn-rm" onClick={() => remove(i)} title="Remove">✕</button>
          </div>
        ) : (
          <div key={i} className="dyn-item">
            <input value={item} onChange={(e) => update(i, e.target.value)} placeholder={placeholder} />
            <button className="dyn-rm" onClick={() => remove(i)} title="Remove">✕</button>
          </div>
        )
      )}
      <button className="btn-add-item" onClick={add}>+ Add</button>
    </div>
  );
}

function StarRating({ value, onChange }) {
  const [hover, setHover] = useState(0);
  return (
    <div className="rating-stars">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          className={`rating-star ${n <= (hover || value || 0) ? "on" : ""}`}
          onClick={() => onChange(n === value ? null : n)}
          onMouseEnter={() => setHover(n)}
          onMouseLeave={() => setHover(0)}
        >★</button>
      ))}
    </div>
  );
}

export default function RecipeEditor({ recipe, onSave, onCancel, busy }) {
  const [r, setR] = useState({
    name: recipe?.name ?? "",
    description: recipe?.description ?? "",
    url: recipe?.url ?? "",
    recipe_yield: recipe?.recipe_yield ?? "",
    prep_time: recipe?.prep_time ?? "",
    cook_time: recipe?.cook_time ?? "",
    total_time: recipe?.total_time ?? "",
    recipe_category: recipe?.recipe_category ?? "",
    keywords: recipe?.keywords ?? "",
    recipe_ingredient: recipe?.recipe_ingredient?.length ? recipe.recipe_ingredient : [""],
    recipe_instructions: recipe?.recipe_instructions?.length ? recipe.recipe_instructions : [""],
    tools: recipe?.tools ?? [],
    rating: recipe?.rating ?? null,
  });

  const set = (key, val) => setR((prev) => ({ ...prev, [key]: val }));

  const handleSave = () => {
    if (!r.name.trim()) { alert("Recipe name is required."); return; }
    onSave({
      ...r,
      id: recipe?.id ?? null,
      image: recipe?.image ?? "",
      nutrition: recipe?.nutrition ?? null,
      date_created: recipe?.date_created ?? "",
      date_modified: recipe?.date_modified ?? "",
      recipe_ingredient: r.recipe_ingredient.filter((s) => s.trim()),
      recipe_instructions: r.recipe_instructions.filter((s) => s.trim()),
      tools: r.tools.filter((s) => s.trim()),
    });
  };

  return (
    <div className="editor">
      <div className="editor-title">{recipe?.id ? "Edit Recipe" : "New Recipe"}</div>

      <div className="form-group">
        <label>Name *</label>
        <input value={r.name} onChange={(e) => set("name", e.target.value)} placeholder="Recipe name" />
      </div>

      <div className="form-group">
        <label>Description</label>
        <textarea value={r.description} onChange={(e) => set("description", e.target.value)} placeholder="Short description…" />
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Source URL</label>
          <input value={r.url} onChange={(e) => set("url", e.target.value)} placeholder="https://…" />
        </div>
        <div className="form-group">
          <label>Yield / Servings</label>
          <input value={r.recipe_yield} onChange={(e) => set("recipe_yield", e.target.value)} placeholder="4 servings" />
        </div>
      </div>

      <div className="form-row-3">
        <div className="form-group">
          <label>Prep time</label>
          <input value={r.prep_time} onChange={(e) => set("prep_time", e.target.value)} placeholder="PT30M" />
        </div>
        <div className="form-group">
          <label>Cook time</label>
          <input value={r.cook_time} onChange={(e) => set("cook_time", e.target.value)} placeholder="PT1H" />
        </div>
        <div className="form-group">
          <label>Total time</label>
          <input value={r.total_time} onChange={(e) => set("total_time", e.target.value)} placeholder="PT1H30M" />
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Category</label>
          <input value={r.recipe_category} onChange={(e) => set("recipe_category", e.target.value)} placeholder="Dinner" />
        </div>
        <div className="form-group">
          <label>Keywords (comma-separated)</label>
          <input value={r.keywords} onChange={(e) => set("keywords", e.target.value)} placeholder="quick, easy, vegetarian" />
        </div>
      </div>

      <div className="form-group">
        <label>Rating</label>
        <StarRating value={r.rating} onChange={(v) => set("rating", v)} />
      </div>

      <div className="form-group">
        <label>Ingredients</label>
        <DynList items={r.recipe_ingredient} onChange={(v) => set("recipe_ingredient", v)} placeholder="e.g. 200g flour" />
      </div>

      <div className="form-group">
        <label>Instructions</label>
        <DynList items={r.recipe_instructions} onChange={(v) => set("recipe_instructions", v)} multiline placeholder="Describe this step…" />
      </div>

      <div className="form-group">
        <label>Tools</label>
        <DynList items={r.tools.length ? r.tools : [""]} onChange={(v) => set("tools", v)} placeholder="e.g. Stand mixer" />
      </div>

      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 16, paddingBottom: 24 }}>
        <button className="btn-ghost" onClick={onCancel} disabled={busy}>Cancel</button>
        <button className="btn" onClick={handleSave} disabled={busy}>{busy ? "Saving…" : "Save"}</button>
      </div>
    </div>
  );
}
