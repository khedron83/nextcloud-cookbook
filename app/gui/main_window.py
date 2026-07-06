from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QMessageBox, QStackedWidget,
    QStatusBar, QInputDialog, QLabel, QFrame, QPushButton,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QPixmap, QKeySequence
from datetime import datetime
import json
from pathlib import Path

_CACHE_PATH = Path.home() / ".local" / "share" / "nextcloud-cookbook" / "cache.json"

from app.api.client import CookbookClient
from app.models import Recipe, RecipeSummary
from app.workers import Worker, ThumbnailLoader, UpdateCheckWorker, APP_VERSION
from app.gui.category_sidebar import CategorySidebar
from app.gui.recipe_grid import RecipeGrid
from app.gui.recipe_view import RecipeView
from app.gui.recipe_editor import RecipeEditor
from app.gui.settings_dialog import SettingsDialog
from app.gui.import_export import ExportDialog, ImportDialog, ObsidianExportDialog
from app.gui.ingredient_index import IngredientIndex
from app.gui.meal_planner import MealPlannerView
from app.gui.icons import theme_icon

_GRID, _VIEW, _EDIT, _PLANNER = 0, 1, 2, 3

_STYLE = """
/* ── Base ────────────────────────────────────────────────────────── */
QMainWindow, QDialog { background: palette(window); color: palette(windowText); }
QWidget { color: palette(windowText); font-size: 13px; }
QLabel  { background: transparent; color: palette(windowText); }

/* ── Sidebar ─────────────────────────────────────────────────────── */
QWidget#sidebar { background: palette(alternateBase); }
QWidget#sidebar QListWidget {
    background: transparent; border: none;
    color: palette(text); padding: 4px 8px; outline: 0;
}
QWidget#sidebar QListWidget::item {
    padding: 9px 10px; border-radius: 6px; margin: 1px 0;
}
QWidget#sidebar QListWidget::item:selected { background: palette(highlight); color: palette(highlightedText); }
QWidget#sidebar QListWidget::item:hover:!selected { background: rgba(127,127,127,0.12); }

/* ── Splitter ────────────────────────────────────────────────────── */
QSplitter::handle:horizontal { background: palette(mid); width: 1px; }

/* ── Action bar ──────────────────────────────────────────────────── */
QWidget#actionBar { background: palette(alternateBase); border-bottom: 1px solid palette(mid); }

/* ── Recipe grid list ────────────────────────────────────────────── */
QListWidget { background: palette(base); border: none; outline: 0; color: palette(windowText); }
QListWidget::item:selected       { background: palette(highlight); color: palette(highlightedText); }
QListWidget::item:hover:!selected { background: palette(alternateBase); }

/* ── Buttons ─────────────────────────────────────────────────────── */
QPushButton {
    background: palette(highlight); color: palette(highlightedText); border: 1px solid transparent;
    border-radius: 7px; padding: 6px 15px;
    font-size: 13px; font-weight: 500;
}
QPushButton:hover   { border-color: palette(highlightedText); }
QPushButton:pressed { background: palette(midlight); color: palette(text); border-color: transparent; }
QPushButton:disabled { background: palette(mid); color: palette(placeholderText); border: 1px solid palette(midlight); }
/* ponytail: keep semantic green for active cooking-timer toggle */
QPushButton:checked       { background: #15803d; color: white; }
QPushButton:checked:hover { background: #16a34a; color: white; border-color: white; }
QPushButton#backBtn { background: transparent; color: palette(placeholderText); border: 1px solid palette(mid); }
QPushButton#backBtn:hover { background: palette(alternateBase); color: palette(windowText); border-color: palette(mid); }
QPushButton#editBtn { background: palette(highlight); color: palette(highlightedText); }
/* ponytail: keep semantic red for destructive delete actions */
QPushButton#deleteBtn       { background: #b91c1c; color: white; }
QPushButton#deleteBtn:hover { background: #dc2626; color: white; }

/* ── Inputs ──────────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background: palette(base); border: 1px solid palette(mid); border-radius: 6px;
    padding: 6px 10px; color: palette(text); selection-background-color: palette(highlight);
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus { border-color: palette(highlight); }
QSpinBox, QDoubleSpinBox {
    background: palette(base); border: 1px solid palette(mid); border-radius: 6px;
    padding: 4px 8px; color: palette(text);
}
QSpinBox:focus, QDoubleSpinBox:focus { border-color: palette(highlight); }
QSpinBox::up-button, QSpinBox::down-button { background: palette(mid); border: none; width: 18px; }
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: palette(midlight); }
QComboBox {
    background: palette(base); border: 1px solid palette(mid); border-radius: 6px;
    padding: 5px 10px; color: palette(text);
}
QComboBox:focus { border-color: palette(highlight); }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background: palette(base); border: 1px solid palette(mid); color: palette(text);
    selection-background-color: palette(highlight); outline: 0;
}

/* ── Group boxes ─────────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid palette(mid); border-radius: 8px;
    margin-top: 12px; padding-top: 8px;
    color: palette(windowText); background: transparent;
}
QGroupBox::title {
    subcontrol-origin: margin; left: 12px; padding: 0 6px;
    color: palette(placeholderText); font-size: 11px; font-weight: bold;
}

/* ── Scroll bars ─────────────────────────────────────────────────── */
QScrollBar:vertical   { background: transparent; width: 8px;  margin: 0; border: none; }
QScrollBar:horizontal { background: transparent; height: 8px; margin: 0; border: none; }
QScrollBar::handle:vertical   { background: palette(mid); border-radius: 3px; min-height: 24px; margin: 0 2px; }
QScrollBar::handle:horizontal { background: palette(mid); border-radius: 3px; min-width:  24px; margin: 2px 0; }
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: palette(midlight); }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }

/* ── Menus ───────────────────────────────────────────────────────── */
QMenuBar { background: palette(alternateBase); color: palette(text); padding: 2px; border-bottom: 1px solid palette(mid); }
QMenuBar::item:selected { background: palette(mid); border-radius: 4px; }
QMenu { background: palette(alternateBase); color: palette(text); border: 1px solid palette(mid); border-radius: 6px; padding: 4px; }
QMenu::item { padding: 6px 24px 6px 12px; border-radius: 4px; }
QMenu::item:selected { background: palette(highlight); color: palette(highlightedText); }
QMenu::separator { background: palette(mid); height: 1px; margin: 4px 8px; }

/* ── Status bar ──────────────────────────────────────────────────── */
QStatusBar { background: palette(alternateBase); color: palette(placeholderText); border-top: 1px solid palette(mid); font-size: 12px; padding: 2px 8px; }
QStatusBar::item { border: none; }

/* ── Misc ────────────────────────────────────────────────────────── */
QCheckBox { color: palette(text); spacing: 8px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid palette(mid); border-radius: 4px; background: palette(base); }
QCheckBox::indicator:checked { background: palette(highlight); border-color: palette(highlight); }
QFrame[frameShape="4"], QFrame[frameShape="5"] { color: palette(mid); }
QScrollArea { background: palette(window); border: none; }
QScrollArea > QWidget > QWidget { background: palette(window); }
QLabel#countLabel { color: palette(placeholderText); }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nextcloud Cookbook")
        self.setMinimumSize(900, 600)
        self.resize(1280, 780)
        self.setStyleSheet(_STYLE)
        self._client: CookbookClient | None = None
        self._current: Recipe | None = None
        self._all_recipes: list[RecipeSummary] = []
        self._workers: list[Worker] = []
        self._thumb_loader: ThumbnailLoader | None = None
        self._ing_index: IngredientIndex | None = None
        self._active_category: object = None
        self._offline: bool = False
        self._stay_on_view: bool = False
        self._category_names: list[str] = []
        self._pending: list[dict] = []
        self._syncing: bool = False
        self._last_sync: str = ""
        self._update_worker = None
        self._sync_timer = QTimer(self)
        self._sync_timer.timeout.connect(self._sync_pending)
        self._build_ui()
        self._init()
        self._check_for_update()

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

        obsidian_act = QAction("Export to &Obsidian…", self)
        obsidian_act.triggered.connect(self._export_obsidian)
        file_menu.addAction(obsidian_act)

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

        sync_now_act = QAction("Sync &Now", self)
        sync_now_act.setShortcut("Ctrl+Shift+S")
        sync_now_act.triggered.connect(self._sync_pending)
        lib_menu.addAction(sync_now_act)

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

        self._update_banner = self._make_update_banner()
        root.addWidget(self._update_banner)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # Left: category sidebar
        self._sidebar = CategorySidebar()
        self._sidebar.setObjectName("sidebar")
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
        self._grid.open_settings_requested.connect(self._open_settings)
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
        self._sync_label = QLabel()
        self._sync_label.setStyleSheet("padding: 0 10px; font-size: 12px;")
        self.statusBar().addPermanentWidget(self._sync_label)

        self._toast = self._make_toast()

    # ── Toast (save/sync confirmation) ─────────────────────────────────────────

    def _make_toast(self) -> QLabel:
        lbl = QLabel(self)
        lbl.setWordWrap(True)
        lbl.setVisible(False)
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(lbl.hide)
        return lbl

    def _show_toast(self, text: str, error: bool = False):
        color = "#b91c1c" if error else "palette(highlight)"
        text_color = "white" if error else "palette(highlightedText)"
        self._toast.setStyleSheet(
            f"QLabel {{ background: {color}; color: {text_color}; border-radius: 8px;"
            " padding: 8px 16px; font-size: 12px; font-weight: 500; }"
        )
        self._toast.setText(text)
        self._toast.adjustSize()
        self._position_toast()
        self._toast.show()
        self._toast.raise_()
        self._toast_timer.start(2800)

    def _position_toast(self):
        margin = 16
        top = self.menuBar().height() + margin
        if self._offline_banner.isVisible():
            top += self._offline_banner.height()
        if self._update_banner.isVisible():
            top += self._update_banner.height()
        x = max(0, self.width() - self._toast.width() - margin)
        self._toast.move(x, top)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._toast.isVisible():
            self._position_toast()

    # ── Bootstrap ─────────────────────────────────────────────────────────────

    def _init(self):
        self._load_pending()
        self._update_sync_label()
        self._client = SettingsDialog.get_client()
        if not self._client:
            self.statusBar().showMessage("Configure your Nextcloud server in Settings.")
            self._grid.show_no_server()
            self._open_settings()
        else:
            self._load()
            self._restart_sync_timer()
            if self._pending:
                self._sync_pending()

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load(self):
        if not self._client:
            return
        self.statusBar().showMessage("Loading…")
        if not self._all_recipes:
            self._grid.show_loading()
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
                    self._grid.set_recipes([])

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
        # Re-add locally created but not yet synced recipes
        for entry in self._pending:
            if entry["op"] == "create":
                d = entry["data"]
                self._all_recipes.append(RecipeSummary(
                    recipe_id=entry["local_id"],
                    name=d.get("name", ""),
                    keywords=d.get("keywords", ""),
                    category=d.get("recipeCategory", ""),
                ))
        self._sidebar.set_total(len(self._all_recipes))
        self._on_category(self._active_category)
        self._planner.set_recipes(self._all_recipes)
        self.statusBar().showMessage(f"Loaded {len(self._all_recipes)} recipes.")
        self._start_ingredient_index()
        all_tags: set[str] = set()
        for r in self._all_recipes:
            if r.keywords:
                for tag in r.keywords.split(","):
                    t = tag.strip()
                    if t:
                        all_tags.add(t)
        self._editor.set_keyword_suggestions(list(all_tags))

    def _start_ingredient_index(self):
        if self._ing_index and self._ing_index.isRunning():
            self._ing_index.stop()
            self._ing_index.wait()
        ids = [r.recipe_id for r in self._all_recipes]
        cached = self._load_ingredient_cache(ids)
        self._ing_index = IngredientIndex(self._client, ids, cached_data=cached)
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
        if not self._ing_index._from_cache:
            self.statusBar().showMessage("Ingredient index ready.")
            self._save_ingredient_cache()

    def _on_categories_loaded(self, data: list):
        self._sidebar.set_categories(data)
        self._category_names = [
            (item.get("name") if isinstance(item, dict) else item)
            for item in data
            if (item.get("name") if isinstance(item, dict) else item) not in ("", "*", None)
        ]

    def _on_category(self, key):
        self._active_category = key
        if key is None:
            self._show_summaries(self._all_recipes)
        elif key == "*":
            self._load_uncategorised()
        else:
            self._run(self._client.get_category_recipes, self._on_category_recipes, key)

    def _load_uncategorised(self):
        """Fetch all named category recipe IDs then show what's left."""
        all_recipes = list(self._all_recipes)
        categories = list(self._category_names)
        client = self._client
        self.statusBar().showMessage("Loading uncategorised…")

        def _fetch():
            categorised_ids: set[int] = set()
            for cat in categories:
                try:
                    for item in client.get_category_recipes(cat):
                        rid = item.get("recipe_id", item.get("id", 0))
                        categorised_ids.add(rid)
                except Exception:
                    pass
            return [r for r in all_recipes if r.recipe_id not in categorised_ids]

        self._run(_fetch, self._show_summaries)

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
        if not self._stay_on_view:
            self._stack.setCurrentIndex(_GRID)
        self._stay_on_view = False
        self._start_thumbnail_loader([r.recipe_id for r in recipes])

    def _start_thumbnail_loader(self, ids: list[int]):
        ids = [i for i in ids if i > 0]
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
        if recipe_id < 0 or self._offline:
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
        if self._current.id is not None and int(self._current.id) > 0 and not self._offline:
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
        self._all_recipes = [r for r in self._all_recipes if int(r.recipe_id) != int(rid)]
        if rid is not None and int(rid) < 0:
            # Local-only: cancel the pending create, nothing to sync
            self._pending = [e for e in self._pending
                             if not (e["op"] == "create" and e["local_id"] == int(rid))]
            self._save_pending()
        else:
            self._queue_op({"op": "delete", "recipe_id": int(rid)})
        self._on_category(self._active_category)
        self._stack.setCurrentIndex(_GRID)
        self._update_sync_label()

    def _save_recipe(self, recipe: Recipe):
        if not self._client:
            return
        name_lower = recipe.name.strip().lower()
        current_id = int(recipe.id) if recipe.id is not None else None
        for r in self._all_recipes:
            if current_id is not None and int(r.recipe_id) == current_id:
                continue
            if r.name.strip().lower() == name_lower:
                reply = QMessageBox.question(
                    self, "Duplicate Recipe",
                    f'A recipe named "{r.name}" already exists. Save anyway?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
                break

        data = recipe.to_api()

        if recipe.id is None or (recipe.id is not None and int(recipe.id) < 0):
            # New recipe or edit of an unsynced local recipe
            local_id = int(recipe.id) if recipe.id is not None else self._next_local_id()
            data["id"] = local_id
            self._save_recipe_detail(data)
            if recipe.id is None:
                self._all_recipes.append(RecipeSummary(
                    recipe_id=local_id,
                    name=recipe.name,
                    keywords=recipe.keywords,
                    category=recipe.recipe_category,
                ))
            else:
                for r in self._all_recipes:
                    if int(r.recipe_id) == local_id:
                        r.name = recipe.name
                        r.keywords = recipe.keywords
                        break
            self._queue_op({"op": "create", "local_id": local_id, "data": data})
        else:
            # Edit of a synced recipe
            self._save_recipe_detail(data)
            for r in self._all_recipes:
                if int(r.recipe_id) == int(recipe.id):
                    r.name = recipe.name
                    r.keywords = recipe.keywords
                    break
            self._queue_op({"op": "update", "recipe_id": int(recipe.id), "data": data})

        self._current = Recipe.from_api(data)
        self._view.set_recipe(self._current)
        self._stack.setCurrentIndex(_VIEW)
        if self._current.id is not None and int(self._current.id) > 0 and not self._offline:
            self._run_silent(
                self._client.get_recipe_image,
                self._view.set_image,
                self._current.id,
            )

        if recipe.id is None:
            # Brand-new recipe: add a card only if the grid is showing all recipes
            if self._active_category is None:
                self._grid.insert_recipe(RecipeSummary(
                    recipe_id=local_id,
                    name=recipe.name,
                    keywords=recipe.keywords,
                    category=recipe.recipe_category,
                ))
        else:
            # Edit: update the existing card in-place (thumbnail untouched)
            self._grid.refresh_recipe(int(recipe.id), recipe.name, recipe.keywords)

        if self._ing_index:
            rid = int(data.get("id", 0))
            if rid:
                self._ing_index._data[rid] = recipe.recipe_ingredient

        self._update_sync_label()
        self._show_toast(f"Saved locally: {recipe.name}")

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
        self._stay_on_view = True
        self._load()
        self._show_toast(f"Saved: {self._current.name}")
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
        self._run(self._client.import_recipe_with_fallback, self._on_imported, url)

    def _on_imported(self, data: dict):
        recipe_id = data.get("recipeId") or data.get("id")
        if recipe_id:
            self._run(self._client.get_recipe, self._on_saved_fetched, recipe_id)
        else:
            self._load()
            self.statusBar().showMessage("Recipe imported.")

    def _export_zip(self):
        if not self._client:
            return
        ExportDialog(self._client, self).exec()

    def _export_obsidian(self):
        if not self._client:
            return
        ObsidianExportDialog(self._client, self).exec()

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
            f"Version {APP_VERSION}\n\n"
            "A desktop client for the Nextcloud Cookbook app.\n\n"
            "Manage, browse, and plan your recipes directly\n"
            "from your Nextcloud instance."
        )
        dlg.exec()

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self._client = SettingsDialog.get_client()
            self._restart_sync_timer()
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

    def _make_update_banner(self) -> QFrame:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        banner = QFrame()
        banner.setStyleSheet(
            "QFrame { background: palette(highlight); border: none; }"
            "QLabel { color: palette(highlightedText); border: none; }"
            "QPushButton { color: palette(highlightedText); border: 1px solid palette(highlightedText);"
            "  border-radius: 4px; padding: 2px 10px; background: transparent; }"
            "QPushButton:hover { background: rgba(255,255,255,0.15); }"
        )
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(12, 6, 12, 6)
        self._update_label = QLabel()
        layout.addWidget(self._update_label)
        layout.addStretch()
        dl_btn = QPushButton("Download")
        dl_btn.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl("https://github.com/khedron83/nextcloud-cookbook/releases/latest")
        ))
        layout.addWidget(dl_btn)
        dismiss_btn = QPushButton()
        dismiss_icon = theme_icon("window-close", "dialog-close")
        if dismiss_icon:
            dismiss_btn.setIcon(dismiss_icon)
        else:
            dismiss_btn.setText("✕")
        dismiss_btn.setFixedWidth(28)
        dismiss_btn.clicked.connect(banner.hide)
        layout.addWidget(dismiss_btn)
        banner.setVisible(False)
        return banner

    def _check_for_update(self):
        self._update_worker = UpdateCheckWorker()
        self._update_worker.update_available.connect(self._show_update_banner)
        self._update_worker.start()

    def _show_update_banner(self, tag: str):
        self._update_label.setText(f"Update available: {tag}")
        self._update_banner.show()

    def _make_offline_banner(self) -> QFrame:
        banner = QFrame()
        # ponytail: amber hex is intentional — no "warning" role in QPalette
        banner.setStyleSheet(
            "QFrame { background: #856404; border: none; }"
            "QLabel { color: #fff; font-weight: bold; border: none; }"
            "QPushButton { color: #fff; border: 1px solid #fff;"
            "  border-radius: 4px; padding: 2px 10px; background: transparent; }"
            "QPushButton:hover { background: rgba(255,255,255,0.15); }"
        )
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(12, 6, 12, 6)
        warning_icon = theme_icon("dialog-warning", "emblem-warning")
        if warning_icon:
            icon_lbl = QLabel()
            icon_lbl.setPixmap(warning_icon.pixmap(16, 16))
            layout.addWidget(icon_lbl)
            layout.addWidget(QLabel("Offline — showing cached data"))
        else:
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
        self._update_sync_label()

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

    def _load_ingredient_cache(self, current_ids: list[int]) -> dict | None:
        cached = self._load_cache() or {}
        idx = cached.get("ingredient_index")
        if not idx:
            return None
        if sorted(idx.get("ids", [])) != sorted(current_ids):
            return None
        return idx.get("data")

    def _save_ingredient_cache(self):
        if not self._ing_index:
            return
        try:
            existing = self._load_cache() or {}
            existing["ingredient_index"] = {
                "ids": [r.recipe_id for r in self._all_recipes],
                "data": self._ing_index.to_dict(),
            }
            _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _CACHE_PATH.write_text(json.dumps(existing), encoding="utf-8")
        except Exception:
            pass

    # ── Local-first sync ─────────────────────────────────────────────────────

    def _next_local_id(self) -> int:
        local_ids = [e["local_id"] for e in self._pending if e["op"] == "create"]
        return min(local_ids + [0]) - 1

    def _queue_op(self, entry: dict):
        self._pending.append(entry)
        self._save_pending()

    def _squash_queue(self, ops: list[dict]) -> list[dict]:
        state: dict[str, dict] = {}
        for entry in ops:
            op = entry["op"]
            if op == "create":
                key = f"local:{entry['local_id']}"
                state[key] = entry
            elif op == "update":
                key = f"recipe:{entry['recipe_id']}"
                state[key] = entry
            elif op == "delete":
                rid = entry["recipe_id"]
                update_key = f"recipe:{rid}"
                if update_key in state:
                    del state[update_key]
                state[f"recipe:{rid}"] = entry
        return list(state.values())

    def _sync_pending(self):
        if not self._pending or not self._client or self._syncing or self._offline:
            return
        self._syncing = True
        self.statusBar().showMessage("Syncing…")
        ops = self._squash_queue(list(self._pending))
        client = self._client

        def _do_sync():
            synced, failed, id_map = [], [], {}
            for entry in ops:
                try:
                    op = entry["op"]
                    if op == "create":
                        result = client.create_recipe(entry["data"])
                        real_id = result if isinstance(result, int) else int(result.get("id") or result.get("recipeId"))
                        id_map[entry["local_id"]] = real_id
                        synced.append(entry)
                    elif op == "update":
                        client.update_recipe(entry["recipe_id"], entry["data"])
                        synced.append(entry)
                    elif op == "delete":
                        client.delete_recipe(entry["recipe_id"])
                        synced.append(entry)
                except Exception as e:
                    failed.append((entry, str(e)))
            return synced, failed, id_map

        def _on_done(result):
            self._syncing = False
            synced, failed, id_map = result

            # Replace temp local IDs with real server IDs
            for local_id, real_id in id_map.items():
                for r in self._all_recipes:
                    if int(r.recipe_id) == local_id:
                        r.recipe_id = real_id
                        break
                cached = self._load_cache() or {}
                details = cached.get("details", {})
                if str(local_id) in details:
                    d = details.pop(str(local_id))
                    d["id"] = real_id
                    details[str(real_id)] = d
                    cached["details"] = details
                    try:
                        _CACHE_PATH.write_text(json.dumps(cached), encoding="utf-8")
                    except Exception:
                        pass
                if self._current and self._current.id == local_id:
                    self._current = Recipe.from_api({**self._current.to_api(), "id": real_id})
                    if self._stack.currentIndex() == _VIEW:
                        self._view.set_recipe(self._current)

            # Remove synced ops from the queue
            synced_keys = set()
            for entry in synced:
                if entry["op"] == "create":
                    synced_keys.add(f"local:{entry['local_id']}")
                else:
                    synced_keys.add(f"recipe:{entry['recipe_id']}")
            self._pending = [
                e for e in self._pending
                if (f"local:{e['local_id']}" if e["op"] == "create" else f"recipe:{e['recipe_id']}") not in synced_keys
            ]

            self._last_sync = datetime.now().strftime("%H:%M")
            self._save_pending()
            self._update_sync_label()
            for local_id, real_id in id_map.items():
                self._grid.remap_recipe_id(local_id, real_id)

            if failed:
                errors = "; ".join(msg for _, msg in failed[:2])
                self._show_toast(f"Sync: {len(synced)} ok — {errors}", error=True)
            else:
                self._show_toast(f"Synced {len(synced)} change(s) at {self._last_sync}.")

        self._run(_do_sync, _on_done)

    def _restart_sync_timer(self):
        from PySide6.QtCore import QSettings
        interval = QSettings().value("sync/interval_minutes", 5, type=int)
        if interval > 0:
            self._sync_timer.start(interval * 60 * 1000)
        else:
            self._sync_timer.stop()

    def _update_sync_label(self):
        n = len(self._pending)
        if self._offline:
            suffix = f" · {self._last_sync}" if self._last_sync else ""
            self._sync_label.setText(f"Offline{suffix}")
            self._sync_label.setStyleSheet("color: palette(placeholderText); padding: 0 10px; font-size: 12px;")
        elif n:
            self._sync_label.setText(f"● {n} pending")
            self._sync_label.setStyleSheet("color: palette(highlight); padding: 0 10px; font-size: 12px;")
        elif self._last_sync:
            self._sync_label.setText(f"✓ {self._last_sync}")
            self._sync_label.setStyleSheet("color: palette(placeholderText); padding: 0 10px; font-size: 12px;")
        else:
            self._sync_label.setText("")

    def _save_pending(self):
        try:
            existing = self._load_cache() or {}
            existing["pending"] = self._pending
            existing["last_sync"] = self._last_sync
            _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _CACHE_PATH.write_text(json.dumps(existing), encoding="utf-8")
        except Exception:
            pass

    def _load_pending(self):
        cached = self._load_cache() or {}
        self._pending = cached.get("pending", [])
        self._last_sync = cached.get("last_sync", "")

    def closeEvent(self, event):
        self._sync_timer.stop()
        if self._pending and self._client and not self._offline:
            self.statusBar().showMessage("Syncing before close…")
            ops = self._squash_queue(list(self._pending))
            succeeded_keys: set[str] = set()
            for entry in ops:
                try:
                    op = entry["op"]
                    if op == "create":
                        self._client.create_recipe(entry["data"])
                        succeeded_keys.add(f"local:{entry['local_id']}")
                    elif op == "update":
                        self._client.update_recipe(entry["recipe_id"], entry["data"])
                        succeeded_keys.add(f"recipe:{entry['recipe_id']}")
                    elif op == "delete":
                        self._client.delete_recipe(entry["recipe_id"])
                        succeeded_keys.add(f"recipe:{entry['recipe_id']}")
                except Exception:
                    pass
            self._pending = [
                e for e in self._pending
                if (f"local:{e['local_id']}" if e["op"] == "create" else f"recipe:{e['recipe_id']}") not in succeeded_keys
            ]
            self._save_pending()
        event.accept()

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
