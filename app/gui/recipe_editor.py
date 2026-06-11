import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QScrollArea, QFrame,
    QGroupBox, QSpinBox, QMessageBox, QStackedWidget, QCompleter,
)
from PySide6.QtCore import Signal, Qt, QStringListModel
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from app.models import Recipe, minutes_to_duration, parse_duration


def _strip_prefix(line: str) -> str:
    """Remove leading bullets or numbers: '1. ', '• ', '- ', '* '"""
    return re.sub(r'^[\d]+[.)]\s*|^[•\-\*]\s*', '', line)


class _ClickableStar(QLabel):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__("☆", parent)
        self.setFixedSize(26, 26)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("font-size: 18px; color: #94a3b8;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class _TagCompleter(QCompleter):
    """Completes the last comma-separated token in the keywords field."""

    def splitPath(self, path: str) -> list[str]:
        return [path.split(",")[-1].strip()]

    def pathFromIndex(self, index) -> str:
        return index.data()


class _DynamicList(QWidget):
    """Editable list of single-line entries with bulk-paste support."""

    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self._ph = placeholder
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Button bar
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(4)
        add_btn = QPushButton("+ Add")
        add_btn.setFixedWidth(72)
        add_btn.clicked.connect(lambda: self._add_row(""))
        self._bulk_btn = QPushButton("Bulk edit")
        self._bulk_btn.setFixedWidth(80)
        self._bulk_btn.clicked.connect(self._toggle_bulk)
        btn_bar.addWidget(add_btn)
        btn_bar.addWidget(self._bulk_btn)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        # Stack: page 0 = individual rows, page 1 = bulk textarea
        self._stack = QStackedWidget()

        rows_page = QWidget()
        rows_layout = QVBoxLayout(rows_page)
        rows_layout.setContentsMargins(0, 0, 0, 0)
        rows_layout.setSpacing(2)
        self._rows = rows_layout
        self._stack.addWidget(rows_page)

        bulk_page = QWidget()
        bulk_layout = QVBoxLayout(bulk_page)
        bulk_layout.setContentsMargins(0, 0, 0, 0)
        self._bulk_area = QTextEdit()
        self._bulk_area.setPlaceholderText(
            "One item per line — paste a list here.\n"
            "Leading numbers and bullets are stripped automatically."
        )
        self._bulk_area.setMinimumHeight(160)
        bulk_layout.addWidget(self._bulk_area)
        self._stack.addWidget(bulk_page)

        layout.addWidget(self._stack)

    def _toggle_bulk(self):
        if self._stack.currentIndex() == 0:
            self._bulk_area.setPlainText('\n'.join(self.get_values()))
            self._stack.setCurrentIndex(1)
            self._bulk_btn.setText("Done")
            self._bulk_area.setFocus()
        else:
            self._apply_bulk()
            self._stack.setCurrentIndex(0)
            self._bulk_btn.setText("Bulk edit")

    def _apply_bulk(self):
        lines = [
            _strip_prefix(l).strip()
            for l in self._bulk_area.toPlainText().splitlines()
        ]
        self.set_values([l for l in lines if l])

    def _make_edit(self, text: str) -> QWidget:
        edit = QLineEdit(text)
        edit.setPlaceholderText(self._ph)
        return edit

    def _add_row(self, text: str):
        row = QWidget()
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 0, 0, 0)
        edit = self._make_edit(text)
        rm = QPushButton("✕")
        rm.setFixedWidth(28)
        rm.clicked.connect(lambda: self._remove(row))
        hl.addWidget(edit)
        hl.addWidget(rm)
        self._rows.addWidget(row)

    def _remove(self, row: QWidget):
        self._rows.removeWidget(row)
        row.deleteLater()

    def get_values(self) -> list[str]:
        # If bulk mode is open, read from there
        if self._stack.currentIndex() == 1:
            lines = [
                _strip_prefix(l).strip()
                for l in self._bulk_area.toPlainText().splitlines()
            ]
            return [l for l in lines if l]
        values = []
        for i in range(self._rows.count()):
            item = self._rows.itemAt(i)
            if item and item.widget():
                edit = item.widget().findChild(QLineEdit)
                if edit:
                    t = edit.text().strip()
                    if t:
                        values.append(t)
        return values

    def set_values(self, values: list[str]):
        # Always switch back to rows mode when loading data
        self._stack.setCurrentIndex(0)
        self._bulk_btn.setText("Bulk edit")
        while self._rows.count():
            item = self._rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for v in values:
            self._add_row(v)


class _DynamicTextList(_DynamicList):
    """Editable list of multi-line entries (for instructions)."""

    def _make_edit(self, text: str) -> QWidget:
        edit = QTextEdit(text)
        edit.setPlaceholderText(self._ph)
        edit.setFixedHeight(72)
        return edit

    def get_values(self) -> list[str]:
        if self._stack.currentIndex() == 1:
            lines = [
                _strip_prefix(l).strip()
                for l in self._bulk_area.toPlainText().splitlines()
            ]
            return [l for l in lines if l]
        values = []
        for i in range(self._rows.count()):
            item = self._rows.itemAt(i)
            if item and item.widget():
                edit = item.widget().findChild(QTextEdit)
                if edit:
                    t = edit.toPlainText().strip()
                    if t:
                        values.append(t)
        return values


class RecipeEditor(QWidget):
    save_requested = Signal(Recipe)
    cancel_requested = Signal()
    import_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._recipe: Recipe | None = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header bar
        bar = QWidget()
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(8, 4, 8, 4)
        self._header = QLabel("New Recipe")
        hdr_font = QFont()
        hdr_font.setPointSize(14)
        hdr_font.setBold(True)
        self._header.setFont(hdr_font)
        bar_layout.addWidget(self._header)
        bar_layout.addStretch()
        import_btn = QPushButton("Import from URL")
        import_btn.clicked.connect(self._on_import)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.cancel_requested)
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        for w in (import_btn, cancel_btn, save_btn):
            bar_layout.addWidget(w)
        outer.addWidget(bar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        outer.addWidget(sep)

        # Scrollable form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        form_widget = QWidget()
        scroll.setWidget(form_widget)
        vbox = QVBoxLayout(form_widget)
        vbox.setContentsMargins(20, 12, 20, 20)
        vbox.setSpacing(12)

        # Basic info
        basic = QGroupBox("Basic Info")
        bf = QFormLayout(basic)
        self._name = QLineEdit()
        self._name.setPlaceholderText("Recipe name *")
        bf.addRow("Name:", self._name)
        self._desc = QTextEdit()
        self._desc.setFixedHeight(72)
        self._desc.setPlaceholderText("Short description")
        bf.addRow("Description:", self._desc)
        self._source_url = QLineEdit()
        self._source_url.setPlaceholderText("https://…")
        bf.addRow("Source URL:", self._source_url)
        self._category = QLineEdit()
        bf.addRow("Category:", self._category)
        self._keywords = QLineEdit()
        self._keywords.setPlaceholderText("tag1, tag2, tag3")
        bf.addRow("Keywords:", self._keywords)
        self._tag_model = QStringListModel([], self)
        self._tag_completer = _TagCompleter(self._tag_model, self)
        self._tag_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._tag_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._keywords.setCompleter(self._tag_completer)
        self._tag_completer.activated.connect(self._on_tag_completed)
        self._yield = QLineEdit()
        self._yield.setPlaceholderText("4 servings")
        bf.addRow("Yield:", self._yield)
        self._rating = 0
        self._star_labels: list[_ClickableStar] = []
        star_row = QHBoxLayout()
        star_row.setSpacing(2)
        star_row.setContentsMargins(0, 0, 0, 0)
        for i in range(1, 6):
            star = _ClickableStar()
            star.clicked.connect(lambda n=i: self._set_rating(n))
            self._star_labels.append(star)
            star_row.addWidget(star)
        star_row.addStretch()
        bf.addRow("Rating:", star_row)
        vbox.addWidget(basic)

        # Timing
        timing = QGroupBox("Timing")
        tf = QFormLayout(timing)
        self._prep = QSpinBox()
        self._prep.setRange(0, 9999)
        self._prep.setSuffix(" min")
        tf.addRow("Prep time:", self._prep)
        self._cook = QSpinBox()
        self._cook.setRange(0, 9999)
        self._cook.setSuffix(" min")
        tf.addRow("Cook time:", self._cook)
        vbox.addWidget(timing)

        # Ingredients
        ing_box = QGroupBox("Ingredients")
        self._ingredients = _DynamicList("e.g. 2 cups flour")
        QVBoxLayout(ing_box).addWidget(self._ingredients)
        vbox.addWidget(ing_box)

        # Instructions
        ins_box = QGroupBox("Instructions")
        self._instructions = _DynamicTextList("Describe this step…")
        QVBoxLayout(ins_box).addWidget(self._instructions)
        vbox.addWidget(ins_box)

        # Tools
        tools_box = QGroupBox("Tools")
        self._tools = _DynamicList("e.g. Large mixing bowl")
        QVBoxLayout(tools_box).addWidget(self._tools)
        vbox.addWidget(tools_box)

        vbox.addStretch()

        # ── Keyboard shortcuts ────────────────────────────────────────────────
        save_sc = QShortcut(QKeySequence.StandardKey.Save, self)
        save_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        save_sc.activated.connect(self._on_save)
        cancel_sc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        cancel_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        cancel_sc.activated.connect(self.cancel_requested)

    def _set_rating(self, n: int):
        self._rating = 0 if self._rating == n else n
        self._refresh_stars()

    def _refresh_stars(self):
        for i, star in enumerate(self._star_labels):
            if i < self._rating:
                star.setText("★")
                star.setStyleSheet("font-size: 18px; color: #f59e0b;")
            else:
                star.setText("☆")
                star.setStyleSheet("font-size: 18px; color: #94a3b8;")

    def _on_tag_completed(self, text: str):
        parts = [p.strip() for p in self._keywords.text().split(",")]
        parts[-1] = text
        new_text = ", ".join(p for p in parts if p) + ", "
        self._keywords.setText(new_text)
        self._keywords.setCursorPosition(len(new_text))

    def set_keyword_suggestions(self, tags: list[str]):
        self._tag_model.setStringList(sorted(tags, key=str.casefold))

    def _on_import(self):
        from PySide6.QtWidgets import QInputDialog
        url, ok = QInputDialog.getText(self, "Import Recipe", "Enter recipe URL:")
        if ok and url.strip():
            self.import_requested.emit(url.strip())

    def _on_save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing", "Recipe name is required.")
            return
        recipe = Recipe(
            id=self._recipe.id if self._recipe else None,
            image=self._recipe.image if self._recipe else "",
            name=name,
            description=self._desc.toPlainText().strip(),
            url=self._source_url.text().strip(),
            recipe_yield=self._yield.text().strip(),
            prep_time=minutes_to_duration(self._prep.value()),
            cook_time=minutes_to_duration(self._cook.value()),
            recipe_category=self._category.text().strip(),
            keywords=self._keywords.text().strip(),
            recipe_ingredient=self._ingredients.get_values(),
            recipe_instructions=self._instructions.get_values(),
            tools=self._tools.get_values(),
            rating=self._rating,
        )
        self.save_requested.emit(recipe)

    def load_recipe(self, recipe: Recipe):
        self._recipe = recipe
        self._header.setText(recipe.name or "Edit Recipe")
        self._name.setText(recipe.name)
        self._desc.setPlainText(recipe.description)
        self._source_url.setText(recipe.url)
        self._category.setText(recipe.recipe_category)
        self._keywords.setText(recipe.keywords)
        self._yield.setText(recipe.recipe_yield)
        self._prep.setValue(parse_duration(recipe.prep_time))
        self._cook.setValue(parse_duration(recipe.cook_time))
        self._ingredients.set_values(recipe.recipe_ingredient)
        self._instructions.set_values(recipe.recipe_instructions)
        self._tools.set_values(recipe.tools)
        self._rating = recipe.rating
        self._refresh_stars()

    def load_new(self):
        self._recipe = None
        self._header.setText("New Recipe")
        self._name.clear()
        self._desc.clear()
        self._source_url.clear()
        self._category.clear()
        self._keywords.clear()
        self._yield.clear()
        self._prep.setValue(0)
        self._cook.setValue(0)
        self._ingredients.set_values([])
        self._instructions.set_values([])
        self._tools.set_values([])
        self._rating = 0
        self._refresh_stars()
