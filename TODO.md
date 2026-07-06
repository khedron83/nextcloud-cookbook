# Nextcloud Cookbook TODO

## Import / Export
- [x] Import ZIP — File > Import ZIP…, parses JSON-LD recipe files from ZIP, creates via API
- [x] Export ZIP — File > Export ZIP…, fetches all recipes, writes Nextcloud-compatible JSON-LD ZIP
- [ ] Batch URL import — dialog to paste multiple URLs, import sequentially with progress

## Meal Planning
- [ ] Shopping list — generate combined + deduplicated ingredient list from the week's meal plan entries; show in dialog with copy-to-clipboard
  - Current dedup is exact lowercase string match only ("2 cups flour" vs "1 cup flour" stay separate lines) — needs quantity-aware merging
  - Dialog is a read-only QTextEdit; add checkable list items so it's usable while actually shopping
- [ ] Export meal plan — copy week as plain text (day: breakfast/lunch/dinner recipe names) to clipboard
- [ ] Meal planner grid doesn't reflow at small window sizes — `MealCell` fixed 150×84 thumbnails × 7 day-columns need ~1150px+, but `MainWindow.setMinimumSize(900, 600)` allows narrower; no responsive logic like `RecipeGrid._relayout_grid` has
- [ ] `RecipePicker` (meal_planner.py) is a bare QListWidget of recipe names — no thumbnails/card styling, inconsistent with `RecipeGrid` used everywhere else recipes are browsed

## Offline & Sync
- [ ] Pending badge on recipe cards — small indicator on cards that were created/edited offline and haven't synced yet
- [ ] Sync status in statusbar — show last successful sync time

## Known Bugs
- Empty strip on the right side of the recipe grid — Qt's icon mode spacing is unpredictable; multiple approaches (responsive `resizeEvent` + `_relayout_grid` with correct `CARD_W + 2*sp` slot formula, deferred `QTimer.singleShot(0, ...)`) have not fully resolved it. Investigate whether `setUniformItemSizes`, viewport margins, or a `QGridLayout`-based approach would give more control.

## Navigation
- [ ] Keyboard navigation in grid — arrow keys move focus between cards, Enter opens, Escape goes back

## Cooking Mode
- [ ] Implement cooking_mode.py — fullscreen step-by-step view; ingredient list left, instruction navigation right, built-in timer
- [ ] "Start Cooking" button in recipe view action bar to launch it
- [ ] Even before full cooking_mode.py exists, `RecipeView`'s ingredient/instruction lists (recipe_view.py) are static QLabels — session-only checkboxes to tick off ingredients/steps while cooking would be a cheap intermediate win

## Recipe Management
- [ ] Recipe duplication — "Duplicate" button in recipe view; copy current recipe into editor as a new recipe
- [ ] Recipe image upload/change in editor — currently no way to set or replace a recipe photo from the desktop
- [ ] Recipe editor has no nutrition fields at all (recipe_view.py renders a full nutrition grid, recipe_editor.py has none) — manually-created recipes permanently look worse than imported ones; add a collapsible "Nutrition" QGroupBox mirroring the view
- [ ] Recipe title (RecipeView._title) isn't pinned — scrolling a long recipe loses all visible context of which recipe you're viewing; pin into the #actionBar or a sticky sub-header

## UI/UX Polish
- [x] No empty/first-run state — `RecipeGrid` now has a `QStackedWidget` (content/empty pages); `show_no_server()` shows an icon + heading + "Open Settings" button, wired via new `open_settings_requested` signal from `MainWindow._init()`
- [x] No empty-search-results state — `RecipeGrid._show_empty(query)` shows a centered "No recipes found — No recipes match '…'" message with a "Clear Filter" button when a filter yields zero results, or "No recipes here" (no action) when the whole view is empty
- [x] No loading state — `RecipeGrid.show_loading()` shown from `MainWindow._load()` on first load (only when `_all_recipes` is empty, to avoid flicker on background refreshes); also fixed the offline-with-no-cache path that previously left the grid stuck on this state forever
- [x] Save/sync confirmation is too subtle — added a top-right auto-dismissing toast (`MainWindow._show_toast`/`_make_toast`/`_position_toast`) for `_save_recipe`, `_on_saved_fetched`, and `_sync_pending`'s completion (green/highlight for success, red for sync failures); statusbar still used for ambient/progress messages
- [x] Category sidebar item count styling — `CategorySidebar` now renders rows via a `_CategoryRow` item-widget (icon + name + muted pill-style count), replacing the old single-string `QListWidgetItem` text; selection/hover contrast handled manually via `set_selected()` since item-widgets don't auto-recolor on selection
- [x] Emoji-based functional icons — added `app/gui/icons.py::theme_icon()` helper; converted back buttons (recipe_grid.py, recipe_view.py), remove-row buttons (recipe_editor.py, meal_planner.py), the update-banner dismiss button and offline-banner warning icon (main_window.py), and meal planner prev/next week buttons to `QIcon.fromTheme()` Breeze icons, falling back to the original emoji glyph when no icon theme is present (e.g. non-Linux). Decorative emoji (recipe meta-row icons, placeholder thumbnail) intentionally left as-is per the review's own guidance
- [x] Category rename discoverability — `_CategoryRow` now has a hover-reveal pencil button (via `enterEvent`/`leaveEvent`) next to the count pill for category rows, in addition to the existing right-click "Rename…" menu

## Performance
- [x] Persist ingredient index to disk — currently rebuilt from API on every launch; serialize alongside recipe cache, invalidate on sync
- [x] Search debounce — 150 ms QTimer singleShot on textChanged to avoid re-filtering on every keystroke

## Cleanup
- [x] Delete recipe_list_panel.py — dead file, replaced by recipe_grid.py, never imported
