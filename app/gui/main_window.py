from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QMessageBox, QStackedWidget,
    QStatusBar, QInputDialog, QLabel, QFrame, QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QPixmap, QKeySequence
import json
from pathlib import Path

_CACHE_PATH = Path.home() / ".local" / "share" / "nextcloud-cookbook" / "cache.json"

from app.api.client import CookbookClient
from app.models import Recipe, RecipeSummary
from app.workers import Worker, ThumbnailLoader
from app.gui.category_sidebar import CategorySidebar
from app.gui.recipe_grid import RecipeGrid
from app.gui.recipe_view import RecipeView
from app.gui.recipe_editor import RecipeEditor
from app.gui.settings_dialog import SettingsDialog
from app.gui.import_export import ExportDialog, ImportDialog
from app.gui.ingredient_index import IngredientIndex
from app.gui.meal_planner import MealPlannerView

_GRID, _VIEW, _EDIT, _PLANNER = 0, 1, 2, 3


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nextcloud Cookbook")
        self.setMinimumSize(900, 600)
        self.resize(1280, 780)
        self._client: CookbookClient | None = None
        self._current: Recipe | None = None
        self._all_recipes: list[RecipeSummary] = []
        self._workers: list[Worker] = []
        self._thumb_loader: ThumbnailLoader | None = None
        self._ing_index: IngredientIndex | None = None
        self._active_category: object = None
        self._offline: bool = False
        self._build_ui()
        self._init()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        mb = self.menuBar()

        # ── File ──────────────────────────────────────────────────────────────
        file_menu = mb.addMenu("&File")

        new_act = QAction("&New Recipe", self)
        new_act.setShortcut(QKeySequence.StandardKey.New)
        new_act.triggered.connect(self._new_recipe)
        file_menu.addAction(new_act)

        file_menu.addSeparator()

        import_url_act = QAction("Import from &URL…", self)
        import_url_act.setShortcut("Ctrl+I")
        import_url_act.triggered.connect(lambda: self._import_url())
        file_menu.addAction(import_url_act)

        import_zip_act = QAction("Import &ZIP…", self)
        import_zip_act.triggered.connect(self._import_zip)
        file_menu.addAction(import_zip_act)

        file_menu.addSeparator()

        export_act = QAction("&Export ZIP…", self)
        export_act.triggered.connect(self._export_zip)
        file_menu.addAction(export_act)

        file_menu.addSeparator()

        settings_act = QAction("&Settings…", self)
        settings_act.setShortcut(QKeySequence.StandardKey.Preferences)
        settings_act.triggered.connect(self._open_settings)
        file_menu.addAction(settings_act)

        # ── Library ───────────────────────────────────────────────────────────
        lib_menu = mb.addMenu("&Library")

        refresh_act = QAction("&Refresh", self)
        refresh_act.setShortcut(QKeySequence.StandardKey.Refresh)
        refresh_act.triggered.connect(self._load)
        lib_menu.addAction(refresh_act)

        reindex_act = QAction("Re&index", self)
        reindex_act.triggered.connect(self._reindex)
        lib_menu.addAction(reindex_act)

        lib_menu.addSeparator()

        self._planner_act = QAction("&Meal Planner", self)
        self._planner_act.setCheckable(True)
        self._planner_act.setShortcut("Ctrl+M")
        self._planner_act.triggered.connect(self._toggle_planner)
        lib_menu.addAction(self._planner_act)

        # ── Help ──────────────────────────────────────────────────────────────
        help_menu = mb.addMenu("&Help")

        about_act = QAction("&About Nextcloud Cookbook", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._offline_banner = self._make_offline_banner()
        root.addWidget(self._offline_banner)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # Left: category sidebar
        self._sidebar = CategorySidebar()
        self._sidebar.setMinimumWidth(180)
        self._sidebar.setMaximumWidth(280)
        self._sidebar.category_selected.connect(self._on_category)
        self._sidebar.rename_requested.connect(self._rename_category)
        splitter.addWidget(self._sidebar)

        # Right: stacked (grid / view / editor)
        self._stack = QStackedWidget()

        self._grid = RecipeGrid()
        self._grid.recipe_selected.connect(self._on_recipe_selected)
        self._grid.back_requested.connect(self._back_from_keyword)
        self._stack.addWidget(self._grid)           # _GRID = 0

        self._view = RecipeView()
        self._view.back_requested.connect(self._back_to_grid)
        self._view.edit_requested.connect(self._edit_current)
        self._view.delete_requested.connect(self._delete_current)
        self._view.keyword_clicked.connect(self._on_keyword_filter)
        self._stack.addWidget(self._view)           # _VIEW = 1

        self._editor = RecipeEditor()
        self._editor.save_requested.connect(self._save_recipe)
        self._editor.cancel_requested.connect(self._cancel_edit)
        self._editor.import_requested.connect(self._import_url)
        self._stack.addWidget(self._editor)         # _EDIT = 2

        self._planner = MealPlannerView()
        self._stack.addWidget(self._planner)        # _PLANNER = 3

        splitter.addWidget(self._stack)
        splitter.setSizes([220, 1060])

        self.setStatusBar(QStatusBar())

    # ── Bootstrap ─────────────────────────────────────────────────────────────

    def _init(self):
        self._client = SettingsDialog.get_client()
        if not self._client:
            self.statusBar().showMessage("Configure your Nextcloud server in Settings.")
            self._open_settings()
        else:
            self._load()

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load(self):
        if not self._client:
            return
        self.statusBar().showMessage("Loading…")
        client = self._client

        def _fetch():
            import requests as _req
            try:
                recipes    = client.get_recipes()
                categories = client.get_categories()
                return {'ok': True, 'recipes': recipes, 'categories': categories}
            except (_req.exceptions.ConnectionError, _req.exceptions.Timeout, OSError):
                return {'ok': False}

        def _on_fetched(result):
            if result['ok']:
                self._set_offline(False)
                self._save_cache(result['recipes'], result['categories'])
                self._on_recipes_loaded(result['recipes'])
                self._on_categories_loaded(result['categories'])
            else:
                self._set_offline(True)
                cached = self._load_cache()
                if cached:
                    self._on_recipes_loaded(cached.get('recipes', []))
                    self._on_categories_loaded(cached.get('categories', []))
                else:
                    self.statusBar().showMessage("Offline — no cached data available.")

        self._run(_fetch, _on_fetched)

    def _on_recipes_loaded(self, data: list):
        self._all_recipes = [
            RecipeSummary(
                recipe_id=item.get("recipe_id", item.get("id", 0)),
                name=item.get("name", ""),
                keywords=item.get("keywords", ""),
                date_modified=item.get("dateModified", ""),
            )
            for item in data
        ]
        self._sidebar.set_total(len(self._all_recipes))
        self._on_category(self._active_category)
        self._planner.set_recipes(self._all_recipes)
        self.statusBar().showMessage(f"Loaded {len(self._all_recipes)} recipes.")
        self._start_ingredient_index()

    def _start_ingredient_index(self):
        if self._ing_index and self._ing_index.isRunning():
            self._ing_index.stop()
        ids = [r.recipe_id for r in self._all_recipes]
        self._ing_index = IngredientIndex(self._client, ids)
        self._ing_index.progress.connect(self._on_index_progress)
        self._ing_index.ready.connect(self._on_index_ready)
        self._ing_index.start()

    def _on_index_progress(self, loaded: int, total: int):
        self._grid.set_ingredient_index(None)   # not ready yet
        if self._stack.currentIndex() == _GRID:
            self.statusBar().showMessage(f"Indexing ingredients… {loaded}/{total}")

    def _on_index_ready(self):
        self._grid.set_ingredient_index(self._ing_index)
        self._planner.set_ingredient_index(self._ing_index)
        self.statusBar().showMessage("Ingredient index ready.")

    def _on_categories_loaded(self, data: list):
        self._sidebar.set_categories(data)

    def _on_category(self, key):
        self._active_category = key
        if key is None:
            # All recipes — use cached list
            self._show_summaries(self._all_recipes)
        else:
            # Server-side category filter
            self._run(self._client.get_category_recipes, self._on_category_recipes, key)

    def _on_category_recipes(self, data: list):
        summaries = [
            RecipeSummary(
                recipe_id=item.get("recipe_id", item.get("id", 0)),
                name=item.get("name", ""),
                keywords=item.get("keywords", ""),
                date_modified=item.get("dateModified", ""),
            )
            for item in data
        ]
        self._show_summaries(summaries)

    def _show_summaries(self, recipes: list):
        self._grid.set_recipes(recipes)
        self._planner_act.setChecked(False)
        self._stack.setCurrentIndex(_GRID)
        self._start_thumbnail_loader([r.recipe_id for r in recipes])

    def _start_thumbnail_loader(self, ids: list[int]):
        if self._thumb_loader and self._thumb_loader.isRunning():
            self._thumb_loader.stop()
            self._thumb_loader.wait()
        if not ids:
            return
        self._thumb_loader = ThumbnailLoader(self._client, ids)
        self._thumb_loader.thumbnail_ready.connect(self._on_thumbnail)
        self._thumb_loader.start()

    def _on_thumbnail(self, recipe_id: int, data: bytes):
        self._grid.set_thumbnail(recipe_id, data)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _on_recipe_selected(self, recipe_id: int):
        if not self._client:
            return
        if self._offline:
            cached = self._load_cache()
            detail = cached.get('details', {}).get(str(recipe_id)) if cached else None
            if detail:
                self._on_recipe_loaded(detail)
            else:
                self.statusBar().showMessage("Recipe not available offline.")
            return
        self.statusBar().showMessage("Loading recipe…")
        self._run(self._client.get_recipe, self._on_recipe_loaded, recipe_id)

    def _on_recipe_loaded(self, data: dict):
        self._save_recipe_detail(data)
        self._current = Recipe.from_api(data)
        self._view.set_recipe(self._current)
        self._stack.setCurrentIndex(_VIEW)
        self.statusBar().showMessage(self._current.name)
        if self._current.id and not self._offline:
            self._run_silent(
                self._client.get_recipe_image,
                self._view.set_image,
                self._current.id,
            )

    def _toggle_planner(self, checked: bool):
        if checked:
            self._planner.set_client(self._client)
            self._stack.setCurrentIndex(_PLANNER)
        else:
            self._stack.setCurrentIndex(_GRID)

    def _back_to_grid(self):
        self._grid.set_back_label("")
        self._planner_act.setChecked(False)
        self._stack.setCurrentIndex(_GRID)

    def _on_keyword_filter(self, keyword: str):
        kw = keyword.lower()
        matches = [r for r in self._all_recipes if kw in (r.keywords or "").lower()]
        self._show_summaries(matches)
        self._grid.set_back_label(f"Back to {self._current.name}" if self._current else "Back")
        self.statusBar().showMessage(f"Tag: {keyword}  ({len(matches)} recipes)")

    def _back_from_keyword(self):
        self._grid.set_back_label("")
        if self._current:
            self._stack.setCurrentIndex(_VIEW)
        else:
            self._on_category(self._active_category)

    # ── Recipe actions ────────────────────────────────────────────────────────

    def _new_recipe(self):
        self._editor.load_new()
        self._stack.setCurrentIndex(_EDIT)

    def _edit_current(self):
        if self._current:
            self._editor.load_recipe(self._current)
            self._stack.setCurrentIndex(_EDIT)

    def _cancel_edit(self):
        if self._current:
            self._stack.setCurrentIndex(_VIEW)
        else:
            self._stack.setCurrentIndex(_GRID)

    def _delete_current(self):
        if not self._current or not self._client:
            return
        reply = QMessageBox.question(
            self, "Delete Recipe",
            f'Delete "{self._current.name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        rid = self._current.id
        self._current = None
        self._run(self._client.delete_recipe, lambda _: self._load(), rid)
        self._stack.setCurrentIndex(_GRID)

    def _save_recipe(self, recipe: Recipe):
        if not self._client:
            return
        self.statusBar().showMessage("Saving…")
        if recipe.id is None:
            self._run(self._client.create_recipe, self._on_saved, recipe.to_api())
        else:
            self._run(self._client.update_recipe, self._on_saved, recipe.id, recipe.to_api())

    def _on_saved(self, data):
        # create returns a dict; update returns the recipe ID as an int
        if isinstance(data, int):
            self._run(self._client.get_recipe, self._on_saved_fetched, data)
        else:
            self._on_saved_fetched(data)

    def _on_saved_fetched(self, data: dict):
        self._current = Recipe.from_api(data)
        self._view.set_recipe(self._current)
        self._stack.setCurrentIndex(_VIEW)
        self._load()
        self.statusBar().showMessage(f"Saved: {self._current.name}")
        if self._current.id:
            self._run_silent(
                self._client.get_recipe_image,
                self._view.set_image,
                self._current.id,
            )

    # ── Import / Export ───────────────────────────────────────────────────────

    def _import_url(self, url: str = ""):
        if not self._client:
            return
        if not url:
            url, ok = QInputDialog.getText(self, "Import Recipe", "Enter recipe URL:")
            if not ok or not url.strip():
                return
            url = url.strip()
        self.statusBar().showMessage(f"Importing from {url}…")
        self._run(self._client.import_recipe, self._on_saved, url)

    def _export_zip(self):
        if not self._client:
            return
        ExportDialog(self._client, self).exec()

    def _import_zip(self):
        if not self._client:
            return
        dlg = ImportDialog(self._client, self)
        dlg.imported.connect(self._load)
        dlg.exec()

    def _reindex(self):
        if not self._client:
            return
        self._run(self._client.reindex, lambda _: self._load())
        self.statusBar().showMessage("Reindexing…")

    def _show_about(self):
        from pathlib import Path
        icon_path = Path(__file__).parent.parent / "resources" / "icon.svg"
        from PySide6.QtGui import QIcon
        dlg = QMessageBox(self)
        dlg.setWindowTitle("About Nextcloud Cookbook")
        if icon_path.exists():
            dlg.setIconPixmap(QIcon(str(icon_path)).pixmap(64, 64))
        dlg.setText("<b>Nextcloud Cookbook</b>")
        dlg.setInformativeText(
            "Version 1.0\n\n"
            "A desktop client for the Nextcloud Cookbook app.\n\n"
            "Manage, browse, and plan your recipes directly\n"
            "from your Nextcloud instance."
        )
        dlg.exec()

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self._client = SettingsDialog.get_client()
            self._load()

    # ── Category rename ───────────────────────────────────────────────────────

    def _rename_category(self, old_name: str):
        if not self._client:
            return
        new_name, ok = QInputDialog.getText(
            self, "Rename Category", f'Rename "{old_name}" to:', text=old_name
        )
        if not ok or not new_name.strip() or new_name.strip() == old_name:
            return
        self._run(self._client.rename_category, lambda _: self._load(), old_name, new_name.strip())
        self.statusBar().showMessage(f'Renaming "{old_name}"…')

    # ── Offline banner & cache ────────────────────────────────────────────────

    def _make_offline_banner(self) -> QFrame:
        banner = QFrame()
        banner.setStyleSheet(
            "QFrame { background: #856404; border: none; }"
            "QLabel { color: #fff; font-weight: bold; border: none; }"
            "QPushButton { color: #fff; border: 1px solid #fff;"
            "  border-radius: 4px; padding: 2px 10px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.15); }"
        )
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.addWidget(QLabel("⚠  Offline — showing cached data"))
        layout.addStretch()
        retry_btn = QPushButton("Retry")
        retry_btn.clicked.connect(self._load)
        layout.addWidget(retry_btn)
        banner.setVisible(False)
        return banner

    def _set_offline(self, offline: bool):
        self._offline = offline
        self._offline_banner.setVisible(offline)
        if offline:
            self.statusBar().showMessage("Offline — showing cached data.")
        else:
            self._offline_banner.setVisible(False)

    def _save_cache(self, recipes: list, categories: list):
        try:
            existing = self._load_cache() or {}
            existing['recipes']    = recipes
            existing['categories'] = categories
            _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _CACHE_PATH.write_text(json.dumps(existing), encoding='utf-8')
        except Exception:
            pass

    def _save_recipe_detail(self, data: dict):
        try:
            rid = data.get('id')
            if rid is None:
                return
            existing = self._load_cache() or {}
            existing.setdefault('details', {})[str(rid)] = data
            _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _CACHE_PATH.write_text(json.dumps(existing), encoding='utf-8')
        except Exception:
            pass

    def _load_cache(self) -> dict | None:
        try:
            return json.loads(_CACHE_PATH.read_text(encoding='utf-8'))
        except Exception:
            return None

    # ── Worker helpers ────────────────────────────────────────────────────────

    def _run(self, fn, callback, *args):
        worker = Worker(fn, *args)
        worker.result.connect(callback)
        worker.error.connect(self._on_error)
        self._workers.append(worker)
        worker.finished.connect(
            lambda: self._workers.remove(worker) if worker in self._workers else None
        )
        worker.start()

    def _run_silent(self, fn, callback, *args):
        worker = Worker(fn, *args)
        worker.result.connect(callback)
        self._workers.append(worker)
        worker.finished.connect(
            lambda: self._workers.remove(worker) if worker in self._workers else None
        )
        worker.start()

    def _on_error(self, msg: str):
        self.statusBar().showMessage(f"Error: {msg}")
        QMessageBox.critical(self, "Error", msg)
