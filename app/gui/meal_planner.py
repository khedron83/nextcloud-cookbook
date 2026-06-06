import json
from datetime import date, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QDialog, QLineEdit,
    QListWidget, QListWidgetItem, QDialogButtonBox, QTextEdit,
    QSizePolicy,
)
from PySide6.QtCore import Signal, Qt, QSettings
from PySide6.QtGui import QFont

from app.models import RecipeSummary

_MEALS = ["Breakfast", "Lunch", "Dinner"]


def _week_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _slot_key(d: date, meal: str) -> str:
    return f"mealplan/{d.isoformat()}/{meal.lower()}"


def _load_slot(d: date, meal: str) -> tuple[int, str] | None:
    """Returns (recipe_id, name) or None."""
    raw = QSettings().value(_slot_key(d, meal))
    if raw:
        try:
            data = json.loads(raw)
            return data["id"], data["name"]
        except Exception:
            pass
    return None


def _save_slot(d: date, meal: str, recipe_id: int, name: str):
    QSettings().setValue(_slot_key(d, meal), json.dumps({"id": recipe_id, "name": name}))


def _clear_slot(d: date, meal: str):
    QSettings().remove(_slot_key(d, meal))


def _all_local_entries() -> list[dict]:
    """Read all meal plan entries from QSettings."""
    settings = QSettings()
    settings.beginGroup("mealplan")
    entries = []
    for date_key in settings.childGroups():
        settings.beginGroup(date_key)
        for meal_key in settings.childKeys():
            raw = settings.value(meal_key)
            if raw:
                try:
                    data = json.loads(raw)
                    entries.append({
                        "date": date_key,
                        "meal": meal_key.capitalize(),
                        "recipeId": data["id"],
                        "recipeName": data["name"],
                    })
                except Exception:
                    pass
        settings.endGroup()
    settings.endGroup()
    return entries


def _apply_remote_entries(entries: list[dict]):
    """Write remote entries into QSettings (merge — remote wins)."""
    for e in entries:
        try:
            d = date.fromisoformat(e["date"])
            meal = e["meal"]
            _save_slot(d, meal, e["recipeId"], e["recipeName"])
        except Exception:
            pass


# ── Recipe picker dialog ──────────────────────────────────────────────────────

class RecipePicker(QDialog):
    def __init__(self, recipes: list[RecipeSummary], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pick a Recipe")
        self.setMinimumSize(360, 420)
        self.selected: RecipeSummary | None = None
        self._all = recipes
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search recipes…")
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._pick)
        layout.addWidget(self._list)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._pick)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._filter("")

    def _filter(self, query: str):
        self._list.clear()
        q = query.lower()
        for r in self._all:
            if q and q not in r.name.lower():
                continue
            item = QListWidgetItem(r.name)
            item.setData(Qt.ItemDataRole.UserRole, r)
            self._list.addItem(item)

    def _pick(self):
        item = self._list.currentItem()
        if item:
            self.selected = item.data(Qt.ItemDataRole.UserRole)
            self.accept()


# ── Single meal cell ──────────────────────────────────────────────────────────

class MealCell(QFrame):
    assign_requested = Signal(date, str)   # date, meal
    cleared          = Signal(date, str)

    def __init__(self, day: date, meal: str, parent=None):
        super().__init__(parent)
        self._day  = day
        self._meal = meal
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "MealCell { border: 1px solid palette(mid); border-radius: 5px;"
            " background: palette(base); }"
        )
        self.setMinimumHeight(70)
        self._build()
        self.refresh()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        meal_lbl = QLabel(self._meal)
        meal_lbl.setStyleSheet("font-size: 10px; color: palette(placeholderText); font-weight: bold;")
        layout.addWidget(meal_lbl)

        self._name_lbl = QLabel()
        self._name_lbl.setWordWrap(True)
        self._name_lbl.setStyleSheet("font-size: 11px;")
        layout.addWidget(self._name_lbl)

        btn_row = QHBoxLayout()
        self._add_btn = QPushButton("+ Add")
        self._add_btn.setStyleSheet(
            "QPushButton { font-size: 10px; padding: 2px 6px; border-radius: 3px;"
            " border: 1px solid palette(mid); background: palette(button); }"
            "QPushButton:hover { background: palette(highlight); color: palette(highlightedText); }"
        )
        self._add_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._add_btn.clicked.connect(lambda: self.assign_requested.emit(self._day, self._meal))

        self._rm_btn = QPushButton("✕")
        self._rm_btn.setStyleSheet(
            "QPushButton { font-size: 10px; padding: 2px 6px; color: #c0392b;"
            " border: none; background: transparent; }"
            "QPushButton:hover { background: palette(alternateBase); }"
        )
        self._rm_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._rm_btn.clicked.connect(self._remove)

        btn_row.addWidget(self._add_btn)
        btn_row.addWidget(self._rm_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def refresh(self):
        assigned = _load_slot(self._day, self._meal)
        if assigned:
            rid, name = assigned
            self._name_lbl.setText(name)
            self._name_lbl.setVisible(True)
            self._add_btn.setText("Change")
            self._rm_btn.setVisible(True)
        else:
            self._name_lbl.setVisible(False)
            self._add_btn.setText("+ Add")
            self._rm_btn.setVisible(False)

    def _remove(self):
        _clear_slot(self._day, self._meal)
        self.refresh()
        self.cleared.emit(self._day, self._meal)

    def assigned_id(self) -> int | None:
        slot = _load_slot(self._day, self._meal)
        return slot[0] if slot else None


# ── Shopping list dialog ──────────────────────────────────────────────────────

class ShoppingListDialog(QDialog):
    def __init__(self, ingredients: list[str], missing: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shopping List")
        self.setMinimumSize(400, 500)
        layout = QVBoxLayout(self)

        if missing:
            note = QLabel(f"Note: {missing} recipe(s) not yet indexed — their ingredients are missing.")
            note.setStyleSheet("color: palette(placeholderText); font-size: 11px;")
            note.setWordWrap(True)
            layout.addWidget(note)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setPlainText("\n".join(f"• {i}" for i in ingredients) if ingredients
                                else "No recipes assigned this week.")
        layout.addWidget(self._text)

        btn_row = QHBoxLayout()
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self._copy)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(copy_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _copy(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._text.toPlainText())


# ── Meal planner view ─────────────────────────────────────────────────────────

class MealPlannerView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._week  = _week_monday(date.today())
        self._recipes: list[RecipeSummary] = []
        self._index = None
        self._cells: list[MealCell] = []
        self._client = None
        self._build_ui()

    def set_client(self, client):
        self._client = client
        self._sync_from_server()

    def set_recipes(self, recipes: list[RecipeSummary]):
        self._recipes = recipes

    def set_ingredient_index(self, index):
        self._index = index

    def _sync_from_server(self):
        if not self._client:
            return
        try:
            remote = self._client.get_meal_plan()
            if remote:
                _apply_remote_entries(remote)
                self._rebuild_grid()
        except Exception:
            pass

    def _push_to_server(self):
        if not self._client:
            return
        try:
            self._client.save_meal_plan(_all_local_entries())
        except Exception:
            pass

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        # Nav bar
        nav = QHBoxLayout()
        prev_btn = QPushButton("← Prev")
        prev_btn.clicked.connect(self._prev_week)
        next_btn = QPushButton("Next →")
        next_btn.clicked.connect(self._next_week)
        self._week_lbl = QLabel()
        f = self._week_lbl.font(); f.setBold(True); f.setPointSize(13)
        self._week_lbl.setFont(f)
        self._week_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        today_btn = QPushButton("Today")
        today_btn.clicked.connect(self._go_today)
        shop_btn = QPushButton("Shopping List")
        shop_btn.clicked.connect(self._show_shopping)
        nav.addWidget(prev_btn)
        nav.addWidget(self._week_lbl, 1)
        nav.addWidget(next_btn)
        nav.addSpacing(20)
        nav.addWidget(today_btn)
        nav.addWidget(shop_btn)
        outer.addLayout(nav)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        outer.addWidget(sep)

        # Scrollable grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        self._grid_widget = QWidget()
        scroll.setWidget(self._grid_widget)
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setSpacing(8)

        self._rebuild_grid()

    def _rebuild_grid(self):
        # Clear
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cells.clear()

        today = date.today()
        days = [self._week + timedelta(days=i) for i in range(7)]
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        # Header row
        for col, (name, day) in enumerate(zip(day_names, days)):
            lbl = QLabel(f"{name}\n{day.strftime('%-d %b')}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                "font-weight: bold; font-size: 12px; padding: 4px;"
                + (" background: palette(highlight); color: palette(highlightedText); border-radius: 4px;"
                   if day == today else "")
            )
            self._grid.addWidget(lbl, 0, col)

        # Meal rows
        for row, meal in enumerate(_MEALS, 1):
            for col, day in enumerate(days):
                cell = MealCell(day, meal)
                cell.assign_requested.connect(self._on_assign)
                cell.cleared.connect(lambda _d, _m: self._push_to_server())
                self._cells.append(cell)
                self._grid.addWidget(cell, row, col)

        self._update_week_label()

    def _update_week_label(self):
        end = self._week + timedelta(days=6)
        if self._week.month == end.month:
            label = f"{self._week.strftime('%-d')}–{end.strftime('%-d %B %Y')}"
        else:
            label = f"{self._week.strftime('%-d %b')} – {end.strftime('%-d %b %Y')}"
        self._week_lbl.setText(label)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _prev_week(self):
        self._week -= timedelta(weeks=1)
        self._rebuild_grid()

    def _next_week(self):
        self._week += timedelta(weeks=1)
        self._rebuild_grid()

    def _go_today(self):
        self._week = _week_monday(date.today())
        self._rebuild_grid()

    # ── Assignment ────────────────────────────────────────────────────────────

    def _on_assign(self, day: date, meal: str):
        if not self._recipes:
            return
        dlg = RecipePicker(self._recipes, self)
        if dlg.exec() and dlg.selected:
            r = dlg.selected
            _save_slot(day, meal, r.recipe_id, r.name)
            for cell in self._cells:
                if cell._day == day and cell._meal == meal:
                    cell.refresh()
                    break
            self._push_to_server()

    # ── Shopping list ─────────────────────────────────────────────────────────

    def _show_shopping(self):
        days = [self._week + timedelta(days=i) for i in range(7)]
        assigned_ids = set()
        for day in days:
            for meal in _MEALS:
                slot = _load_slot(day, meal)
                if slot:
                    assigned_ids.add(slot[0])

        if not assigned_ids:
            ShoppingListDialog([], 0, self).exec()
            return

        missing = 0
        ingredients: list[str] = []
        seen: set[str] = set()

        if self._index:
            for rid in assigned_ids:
                ings = self._index._data.get(rid)
                if ings is None:
                    missing += 1
                else:
                    for ing in ings:
                        key = ing.strip().lower()
                        if key not in seen:
                            seen.add(key)
                            ingredients.append(ing.strip())
        else:
            missing = len(assigned_ids)

        ingredients.sort()
        ShoppingListDialog(ingredients, missing, self).exec()
