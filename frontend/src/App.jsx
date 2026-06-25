import React, { useState, useEffect, useCallback, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import SettingsDialog from "./SettingsDialog.jsx";
import RecipeEditor from "./RecipeEditor.jsx";
import MealPlanner from "./MealPlanner.jsx";

const thumbCache = new Map();

function RecipeCard({ recipe, onClick }) {
  const [imgSrc, setImgSrc] = useState(thumbCache.get(recipe.recipe_id) ?? null);
  const ref = useRef(null);

  useEffect(() => {
    if (imgSrc || !recipe.recipe_id) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      obs.disconnect();
      invoke("get_recipe_image", { id: recipe.recipe_id, thumb: true })
        .then((bytes) => {
          const url = URL.createObjectURL(new Blob([new Uint8Array(bytes)]));
          thumbCache.set(recipe.recipe_id, url);
          setImgSrc(url);
        })
        .catch(() => {});
    }, { rootMargin: "100px" });
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, [recipe.recipe_id, imgSrc]);

  return (
    <div className="recipe-card" onClick={onClick} ref={ref}>
      <div className="recipe-card-img">
        {imgSrc ? <img src={imgSrc} alt={recipe.name} /> : "🍽"}
      </div>
      <div className="recipe-card-body">
        <div className="recipe-card-name">{recipe.name}</div>
        {recipe.category && <div className="recipe-card-cat">{recipe.category}</div>}
      </div>
    </div>
  );
}

function fmtDuration(iso) {
  if (!iso) return "";
  const m = iso.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
  if (!m) return iso;
  const h = parseInt(m[1] || 0);
  const min = parseInt(m[2] || 0);
  if (h && min) return `${h}h ${min}m`;
  if (h) return `${h}h`;
  return `${min}m`;
}

function scaleIngredient(ing, factor) {
  return ing.replace(/^(\d+(?:[.,]\d+)?(?:\/\d+)?)/, (m) => {
    const n = parseFloat(m.replace(",", "."));
    const scaled = n * factor;
    return Number.isInteger(scaled) ? String(scaled) : scaled.toFixed(1).replace(/\.0$/, "");
  });
}

function RecipeView({ recipe, image, onBack, onEdit, onDelete, onKeywordClick }) {
  const [servings, setServings] = useState(null);
  const origServings = recipe.recipe_yield ? parseInt(recipe.recipe_yield.match(/\d+/)?.[0]) : null;
  useEffect(() => { setServings(origServings); }, [recipe.id]);
  const scale = origServings && servings ? servings / origServings : 1;
  const keywords = (recipe.keywords || "").split(",").map((k) => k.trim()).filter(Boolean);
  const stars = recipe.rating ? Array.from({ length: 5 }, (_, i) => i < recipe.rating) : null;
  const metaRows = [
    recipe.prep_time && ["🥣", "Prep", fmtDuration(recipe.prep_time)],
    recipe.cook_time && ["🔥", "Cook", fmtDuration(recipe.cook_time)],
    recipe.total_time && ["⏱", "Total", fmtDuration(recipe.total_time)],
    recipe.recipe_category && ["📂", "Category", recipe.recipe_category],
    recipe.date_created && ["📅", "Added", recipe.date_created.slice(0, 10)],
    recipe.url && ["🔗", "Source", recipe.url],
  ].filter(Boolean);

  return (
    <div className="recipe-view">
      <div className="recipe-view-bar">
        <button className="btn-ghost" onClick={onBack}>← Back</button>
        <div style={{ flex: 1 }} />
        {origServings && (
          <>
            <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Servings</label>
            <input
              type="number" min={1} max={999}
              value={servings ?? origServings}
              onChange={(e) => setServings(parseInt(e.target.value) || origServings)}
              style={{ width: 60, background: "var(--surface2)", border: "1px solid var(--border)", color: "var(--text)", borderRadius: 4, padding: "3px 6px", marginLeft: 6 }}
            />
          </>
        )}
        <button className="btn-ghost" onClick={onEdit}>Edit</button>
        <button className="btn-danger" onClick={onDelete}>Delete</button>
      </div>

      <div className="recipe-view-content">
        <div className="recipe-top-row">
          <div className="recipe-img-wrap">
            {image ? <img src={image} alt={recipe.name} /> : "🍽"}
          </div>
          <div className="recipe-info">
            <div className="recipe-title">{recipe.name}</div>
            {keywords.length > 0 && (
              <div className="chips">
                {keywords.map((kw) => (
                  <span key={kw} className="chip" onClick={() => onKeywordClick(kw)}>{kw}</span>
                ))}
              </div>
            )}
            {stars && (
              <div className="stars" style={{ marginBottom: 10 }}>
                {stars.map((on, i) => (
                  <span key={i} className={on ? "star-on" : "star-off"}>★</span>
                ))}
              </div>
            )}
            {metaRows.length > 0 && (
              <table className="meta-table">
                <tbody>
                  {metaRows.map(([icon, label, val]) => (
                    <tr key={label}>
                      <td>{icon}</td>
                      <td>{label}</td>
                      <td style={{ wordBreak: "break-all" }}>
                        {label === "Source"
                          ? <a href={val} target="_blank" rel="noreferrer" style={{ color: "var(--accent)", fontSize: 11 }}>{(() => { try { return new URL(val).hostname; } catch { return val; } })()}</a>
                          : val}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {recipe.description && <p className="recipe-desc">{recipe.description}</p>}

        <div className="recipe-columns">
          {recipe.recipe_ingredient?.length > 0 && (
            <div className="ing-box">
              <div className="box-title">Ingredients</div>
              {recipe.recipe_ingredient.map((ing, i) => (
                <div key={i} className="ing-item">• {scale !== 1 ? scaleIngredient(ing, scale) : ing}</div>
              ))}
            </div>
          )}
          {recipe.recipe_instructions?.length > 0 && (
            <div className="ins-box">
              <div className="box-title">Instructions</div>
              {recipe.recipe_instructions.map((step, i) => (
                <div key={i} className="step">
                  <span className="step-num">{i + 1}.</span>
                  <span>{step}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {recipe.nutrition && Object.values(recipe.nutrition).some(Boolean) && (
          <div style={{ marginTop: 16 }}>
            <div className="box-title">Nutrition</div>
            <div className="nutr-grid">
              {[
                ["Energy", recipe.nutrition.calories],
                ["Carbs", recipe.nutrition.carbohydrate_content],
                ["Fat", recipe.nutrition.fat_content],
                ["Sat. fat", recipe.nutrition.saturated_fat_content],
                ["Fibre", recipe.nutrition.fiber_content],
                ["Protein", recipe.nutrition.protein_content],
                ["Sodium", recipe.nutrition.sodium_content],
                ["Sugar", recipe.nutrition.sugar_content],
                ["Serving", recipe.nutrition.serving_size],
              ].filter(([, v]) => v).map(([label, val]) => (
                <React.Fragment key={label}>
                  <span className="nutr-item-label">{label}</span>
                  <span className="nutr-item-val">{val}</span>
                </React.Fragment>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [settings, setSettings] = useState(null);
  const [recipes, setRecipes] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCat, setSelectedCat] = useState(null);
  const [search, setSearch] = useState("");
  const [view, setView] = useState("grid");
  const [currentRecipe, setCurrentRecipe] = useState(null);
  const [currentImage, setCurrentImage] = useState(null);
  const [offline, setOffline] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [importUrl, setImportUrl] = useState("");
  const [showImport, setShowImport] = useState(false);

  useEffect(() => {
    invoke("get_settings").then(setSettings).catch(() => {});
    invoke("get_cached_recipes").then((r) => { if (r.length) setRecipes(r); }).catch(() => {});
    invoke("get_categories").then(setCategories).catch(() => {});
    invoke("get_pending_count").then(setPendingCount).catch(() => {});
  }, []);

  useEffect(() => {
    if (settings?.url) refresh();
  }, [settings?.url]);

  useEffect(() => {
    const t = setInterval(() => {
      invoke("sync_pending").then((n) => { if (n > 0) { setPendingCount(0); refresh(); } }).catch(() => {});
    }, 5 * 60 * 1000);
    return () => clearInterval(t);
  }, []);

  const refresh = useCallback(async () => {
    setBusy(true);
    try {
      const r = await invoke("get_recipes");
      setRecipes(r);
      const cats = [...new Set(r.map((x) => x.category).filter(Boolean))].sort();
      setCategories(cats);
      setOffline(false);
    } catch (_) {
      setOffline(true);
      setStatus("Offline — showing cached recipes");
    } finally {
      setBusy(false);
    }
  }, []);

  const openRecipe = useCallback(async (id) => {
    setBusy(true);
    try {
      const recipe = await invoke("get_recipe", { id });
      setCurrentRecipe(recipe);
      setCurrentImage(null);
      setView("view");
      invoke("get_recipe_image", { id, thumb: false })
        .then((bytes) => {
          setCurrentImage(URL.createObjectURL(new Blob([new Uint8Array(bytes)])));
        })
        .catch(() => {});
    } catch (e) {
      setStatus("Error: " + e);
    } finally {
      setBusy(false);
    }
  }, []);

  const handleDelete = async () => {
    if (!currentRecipe?.id || !confirm(`Delete "${currentRecipe.name}"?`)) return;
    setBusy(true);
    try {
      await invoke("delete_recipe", { id: currentRecipe.id });
      setRecipes((prev) => prev.filter((r) => r.recipe_id !== currentRecipe.id));
      setView("grid");
      setStatus(`"${currentRecipe.name}" deleted.`);
    } catch (e) {
      setStatus("Error: " + e);
    } finally {
      setBusy(false);
    }
  };

  const handleSaveRecipe = async (recipe) => {
    setBusy(true);
    try {
      if (recipe.id) {
        const updated = await invoke("update_recipe", { id: recipe.id, recipe });
        setCurrentRecipe(updated);
        setRecipes((prev) => prev.map((r) => r.recipe_id === recipe.id
          ? { ...r, name: updated.name, category: updated.recipe_category, keywords: updated.keywords }
          : r
        ));
        setStatus("Recipe saved.");
        setView("view");
      } else {
        const created = await invoke("create_recipe", { recipe });
        setCurrentRecipe(created);
        await refresh();
        setStatus("Recipe created.");
        setView(created.id ? "view" : "grid");
      }
      setPendingCount(await invoke("get_pending_count"));
    } catch (e) {
      setStatus("Error: " + e);
    } finally {
      setBusy(false);
    }
  };

  const handleImport = async () => {
    if (!importUrl.trim()) return;
    setBusy(true); setStatus("Importing…");
    try {
      const recipe = await invoke("import_recipe_url", { url: importUrl.trim() });
      setCurrentRecipe(recipe);
      setView("edit");
      setShowImport(false);
      setImportUrl("");
      setStatus("Recipe imported — review and save.");
    } catch (e) {
      setStatus("Import failed: " + e);
    } finally {
      setBusy(false);
    }
  };

  const handleSync = async () => {
    setBusy(true); setStatus("Syncing…");
    try {
      const n = await invoke("sync_pending");
      setPendingCount(0);
      await refresh();
      setStatus(n > 0 ? `Synced ${n} pending change${n !== 1 ? "s" : ""}.` : "All up to date.");
    } catch (e) {
      setStatus("Sync failed: " + e);
    } finally {
      setBusy(false);
    }
  };

  const filtered = recipes.filter((r) => {
    if (selectedCat && r.category !== selectedCat) return false;
    if (search) {
      const q = search.toLowerCase();
      return r.name.toLowerCase().includes(q) || r.keywords.toLowerCase().includes(q);
    }
    return true;
  });

  const showSidebar = view === "grid" || view === "planner";
  const defaultSettings = { url: "", username: "", password: "", verify_ssl: true };

  return (
    <div className="app">
      {offline && <div className="offline-banner">Offline — showing cached data</div>}

      <div className="toolbar">
        <span className="toolbar-title" style={{ cursor: "pointer" }} onClick={() => setView("grid")}>
          🍽 Cookbook
        </span>
        <input
          className="search-bar"
          placeholder="Search recipes…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); if (view !== "grid") setView("grid"); }}
        />
        <button className="btn-ghost" onClick={() => { setCurrentRecipe(null); setView("edit"); }}>+ New</button>
        <button className="btn-ghost" onClick={() => setShowImport(true)}>Import URL</button>
        <button className="btn-ghost" onClick={() => setView("planner")}>📅 Planner</button>
        <button className="btn-ghost" onClick={handleSync} disabled={busy} title={pendingCount > 0 ? `${pendingCount} pending` : "Sync"}>
          ↺{pendingCount > 0 ? ` (${pendingCount})` : ""}
        </button>
        <button className="btn-ghost" onClick={refresh} disabled={busy}>Refresh</button>
        <button className="btn-ghost" onClick={() => setShowSettings(true)}>⚙</button>
      </div>

      <div className="app-body">
        {showSidebar && (
          <aside className="sidebar">
            <div className="sidebar-heading">Categories</div>
            <div className={`cat-item ${!selectedCat ? "active" : ""}`} onClick={() => setSelectedCat(null)}>
              All recipes
            </div>
            {categories.map((cat) => (
              <div
                key={cat}
                className={`cat-item ${selectedCat === cat ? "active" : ""}`}
                onClick={() => setSelectedCat(cat)}
              >{cat}</div>
            ))}
          </aside>
        )}

        <div className="main">
          {view === "view" && currentRecipe && (
            <RecipeView
              recipe={currentRecipe}
              image={currentImage}
              onBack={() => setView("grid")}
              onEdit={() => setView("edit")}
              onDelete={handleDelete}
              onKeywordClick={(kw) => { setSearch(kw); setView("grid"); }}
            />
          )}
          {view === "edit" && (
            <RecipeEditor
              recipe={currentRecipe}
              onSave={handleSaveRecipe}
              onCancel={() => setView(currentRecipe?.id ? "view" : "grid")}
              busy={busy}
            />
          )}
          {view === "planner" && (
            <MealPlanner recipes={recipes} onRecipeClick={openRecipe} />
          )}
          {view === "grid" && (
            <div className="recipe-grid">
              {filtered.map((r) => (
                <RecipeCard key={r.recipe_id} recipe={r} onClick={() => openRecipe(r.recipe_id)} />
              ))}
              {filtered.length === 0 && (
                <div style={{ color: "var(--text-muted)", fontSize: 13, gridColumn: "1/-1", padding: 24 }}>
                  {recipes.length === 0
                    ? (settings?.url ? "No recipes found. Try Refresh." : "Configure Nextcloud server in ⚙ Settings.")
                    : "No recipes match."}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="statusbar">{status || (busy ? "Loading…" : "")}</div>

      {showImport && (
        <div className="dialog-overlay" onClick={(e) => e.target === e.currentTarget && setShowImport(false)}>
          <div className="dialog" style={{ width: 500 }}>
            <h2>Import Recipe from URL</h2>
            <div className="form-group">
              <label>Recipe URL</label>
              <input
                value={importUrl}
                onChange={(e) => setImportUrl(e.target.value)}
                placeholder="https://example.com/recipe/…"
                onKeyDown={(e) => e.key === "Enter" && handleImport()}
                autoFocus
              />
              <span className="dialog-path" style={{ display: "block", marginTop: 4 }}>
                Tries the Nextcloud server first, then falls back to JSON-LD scraping.
              </span>
            </div>
            <div className="dialog-row">
              <button className="btn-ghost" onClick={() => setShowImport(false)}>Cancel</button>
              <button className="btn" onClick={handleImport} disabled={busy || !importUrl.trim()}>
                {busy ? "Importing…" : "Import"}
              </button>
            </div>
          </div>
        </div>
      )}

      {showSettings && (
        <SettingsDialog
          settings={settings ?? defaultSettings}
          onClose={() => setShowSettings(false)}
          onSaved={(s) => { setSettings(s); setShowSettings(false); refresh(); }}
        />
      )}
    </div>
  );
}
