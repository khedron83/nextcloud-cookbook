from urllib.parse import urlparse
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QPushButton, QFrame, QGroupBox, QLayout, QSizePolicy,
    QGridLayout, QSpinBox,
)
from PySide6.QtCore import Signal, Qt, QRect, QSize, QPoint, QUrl
from PySide6.QtGui import QPixmap, QFont, QDesktopServices, QKeySequence, QShortcut
from app.models import Recipe, parse_duration
from app.gui.unit_converter import convert_ingredient, convert_instruction, scale_ingredient
import re


# ── Flow layout for keyword chips ─────────────────────────────────────────────

class _FlowLayout(QLayout):
    def __init__(self, parent=None, h_gap=6, v_gap=4):
        super().__init__(parent)
        self._items = []
        self._h_gap = h_gap
        self._v_gap = v_gap

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._layout(QRect(0, 0, width, 0), dry_run=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._layout(rect, dry_run=False)

    def sizeHint(self):
        return QSize(200, self.heightForWidth(200))

    def minimumSize(self):
        return QSize(50, 20)

    def _layout(self, rect, dry_run):
        m = self.contentsMargins()
        x, y = rect.x() + m.left(), rect.y() + m.top()
        line_h = 0
        for item in self._items:
            w = item.sizeHint().width()
            h = item.sizeHint().height()
            if x + w > rect.right() - m.right() and line_h:
                x = rect.x() + m.left()
                y += line_h + self._v_gap
                line_h = 0
            if not dry_run:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x += w + self._h_gap
            line_h = max(line_h, h)
        return y + line_h - rect.y() + m.bottom()


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()


# ── Scaled image label ────────────────────────────────────────────────────────

class _ScaledImage(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._source: QPixmap | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background: palette(midlight); border-radius: 6px;")

    def set_pixmap(self, px: QPixmap):
        self._source = px
        self._rescale()

    def clear_pixmap(self):
        self._source = None
        self.clear()
        self.setStyleSheet("background: palette(midlight); border-radius: 6px;")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self):
        if self._source and not self._source.isNull():
            scaled = self._source.scaled(
                self.width(), self.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setStyleSheet("background: #000; border-radius: 6px;")
            super().setPixmap(scaled)


# ── Recipe view ───────────────────────────────────────────────────────────────

class RecipeView(QWidget):
    back_requested   = Signal()
    edit_requested   = Signal()
    delete_requested = Signal()
    keyword_clicked  = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._recipe_data: Recipe | None = None
        self._converted = False
        self._orig_servings: int | None = None
        self._scale_factor: float = 1.0
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Action bar ────────────────────────────────────────────────────────
        bar = QWidget()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(8, 4, 8, 4)
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self.back_requested)
        bl.addWidget(back_btn)
        bl.addStretch()
        self._servings_label = QLabel("Servings:")
        self._servings_spin = QSpinBox()
        self._servings_spin.setRange(1, 999)
        self._servings_spin.setFixedWidth(60)
        self._servings_spin.valueChanged.connect(self._on_servings_changed)
        bl.addWidget(self._servings_label)
        bl.addWidget(self._servings_spin)
        bl.addSpacing(12)
        self._edit_btn = QPushButton("Edit")
        self._edit_btn.clicked.connect(self.edit_requested)
        self._del_btn = QPushButton("Delete")
        self._del_btn.setStyleSheet("color: #c0392b;")
        self._del_btn.clicked.connect(self.delete_requested)
        self._convert_btn = QPushButton("Convert to Metric")
        self._convert_btn.setCheckable(True)
        self._convert_btn.toggled.connect(self._on_convert_toggled)
        for btn in (self._edit_btn, self._convert_btn, self._del_btn):
            bl.addWidget(btn)
        outer.addWidget(bar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        outer.addWidget(sep)

        # ── Scroll area ───────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        cl = QVBoxLayout(content)
        cl.setContentsMargins(16, 16, 16, 24)
        cl.setSpacing(16)

        # ── Top row: image left, info right ───────────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(20)

        self._img = _ScaledImage()
        self._img.setMinimumWidth(260)
        self._img.setMaximumWidth(560)
        top_row.addWidget(self._img, 5)

        info_col = QVBoxLayout()
        info_col.setSpacing(10)
        info_col.setContentsMargins(0, 0, 0, 0)

        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        self._title = QLabel()
        self._title.setFont(title_font)
        self._title.setWordWrap(True)
        self._title.setAlignment(Qt.AlignmentFlag.AlignTop)
        info_col.addWidget(self._title)

        # Keyword chips container
        self._chip_container = QWidget()
        self._chip_container.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self._chip_layout = _FlowLayout(self._chip_container, h_gap=5, v_gap=5)
        self._chip_container.setLayout(self._chip_layout)
        info_col.addWidget(self._chip_container)

        # Meta grid (yield, times, dates, source)
        self._meta_frame = QFrame()
        self._meta_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self._meta_frame.setStyleSheet(
            "QFrame { border-radius: 6px; background: palette(alternateBase); "
            "border: 1px solid palette(mid); } "
            "QLabel { border: none; background: transparent; }"
        )
        self._meta_grid = QGridLayout(self._meta_frame)
        self._meta_grid.setContentsMargins(12, 10, 12, 10)
        self._meta_grid.setHorizontalSpacing(16)
        self._meta_grid.setVerticalSpacing(6)
        self._meta_grid.setColumnStretch(1, 1)
        info_col.addWidget(self._meta_frame)

        info_col.addStretch()
        top_row.addLayout(info_col, 4)
        cl.addLayout(top_row)

        # ── Description ───────────────────────────────────────────────────────
        self._desc = QLabel()
        self._desc.setWordWrap(True)
        self._desc.setStyleSheet("color: palette(windowText); font-size: 13px;")
        cl.addWidget(self._desc)

        # ── Bottom: ingredients + instructions side by side ───────────────────
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)

        self._ing_box = QGroupBox("Ingredients")
        self._ing_layout = QVBoxLayout(self._ing_box)
        self._ing_layout.setSpacing(4)
        bottom_row.addWidget(self._ing_box, 1)

        self._ins_box = QGroupBox("Instructions")
        self._ins_layout = QVBoxLayout(self._ins_box)
        self._ins_layout.setSpacing(6)
        bottom_row.addWidget(self._ins_box, 2)

        cl.addLayout(bottom_row)

        self._tools_box = QGroupBox("Tools")
        self._tools_layout = QVBoxLayout(self._tools_box)
        cl.addWidget(self._tools_box)

        self._nutr_box = QGroupBox("Nutrition")
        self._nutr_grid = QGridLayout(self._nutr_box)
        self._nutr_grid.setHorizontalSpacing(24)
        self._nutr_grid.setVerticalSpacing(4)
        cl.addWidget(self._nutr_box)

        cl.addStretch()

        # ── Keyboard shortcuts ────────────────────────────────────────────────
        for key, slot in (
            (Qt.Key.Key_Escape, self.back_requested),
            (Qt.Key.Key_E,      self.edit_requested),
            (Qt.Key.Key_Delete, self.delete_requested),
        ):
            sc = QShortcut(QKeySequence(key), self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(slot)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _chip(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(
            "QPushButton { background: palette(button); color: palette(buttonText);"
            "  border: 1px solid palette(mid); border-radius: 10px;"
            "  padding: 2px 9px; font-size: 11px; }"
            "QPushButton:hover { background: palette(highlight); color: palette(highlightedText); border-color: palette(highlight); }"
        )
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _=False, kw=text: self.keyword_clicked.emit(kw))
        return btn

    def _meta_row(self, grid, row, icon, label, value):
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 13px; color: palette(windowText);")
        key_lbl = QLabel(label)
        key_lbl.setStyleSheet("font-weight: bold; font-size: 12px;")
        val_lbl = QLabel(value)
        val_lbl.setWordWrap(True)
        val_lbl.setStyleSheet("font-size: 12px;")
        grid.addWidget(icon_lbl, row, 0)
        grid.addWidget(key_lbl, row, 1)
        grid.addWidget(val_lbl, row, 2)

    # ── Data binding ──────────────────────────────────────────────────────────

    def set_recipe(self, recipe: Recipe):
        self._recipe_data = recipe
        self._converted = False
        self._scale_factor = 1.0
        self._convert_btn.blockSignals(True)
        self._convert_btn.setChecked(False)
        self._convert_btn.setText("Convert to Metric")
        self._convert_btn.blockSignals(False)
        self._title.setText(recipe.name)

        # Servings spinbox
        m = re.search(r'\d+', recipe.recipe_yield or "")
        self._orig_servings = int(m.group()) if m else None
        self._servings_spin.blockSignals(True)
        self._servings_spin.setValue(self._orig_servings or 1)
        self._servings_spin.blockSignals(False)
        has_yield = self._orig_servings is not None
        self._servings_label.setVisible(has_yield)
        self._servings_spin.setVisible(has_yield)

        # Chips
        _clear_layout(self._chip_layout)
        keywords = [k.strip() for k in recipe.keywords.split(",") if k.strip()]
        for kw in keywords:
            self._chip_layout.addWidget(self._chip(kw))
        self._chip_container.setVisible(bool(keywords))
        self._chip_container.updateGeometry()

        # Meta grid
        _clear_layout(self._meta_grid)
        row = 0
        prep = parse_duration(recipe.prep_time)
        cook = parse_duration(recipe.cook_time)
        total = parse_duration(recipe.total_time)
        if prep:
            self._meta_row(self._meta_grid, row, "🥣", "Prep", f"{prep} min"); row += 1
        if cook:
            self._meta_row(self._meta_grid, row, "🔥", "Cook", f"{cook} min"); row += 1
        if total:
            self._meta_row(self._meta_grid, row, "⏱", "Total", f"{total} min"); row += 1
        if recipe.recipe_category:
            self._meta_row(self._meta_grid, row, "📂", "Category", recipe.recipe_category); row += 1
        created = recipe.date_created[:10] if recipe.date_created else ""
        modified = recipe.date_modified[:10] if recipe.date_modified else ""
        if created:
            self._meta_row(self._meta_grid, row, "📅", "Added", created); row += 1
        if modified and modified != created:
            self._meta_row(self._meta_grid, row, "✏", "Edited", modified); row += 1
        if recipe.url:
            display = urlparse(recipe.url).netloc or recipe.url
            url_lbl = QLabel(f'<a href="{recipe.url}">{display}</a>')
            url_lbl.setOpenExternalLinks(True)
            url_lbl.setWordWrap(True)
            url_lbl.setStyleSheet("font-size: 11px;")
            src_lbl = QLabel("🔗")
            key_lbl = QLabel("Source")
            key_lbl.setStyleSheet("font-weight: bold; font-size: 12px;")
            self._meta_grid.addWidget(src_lbl, row, 0)
            self._meta_grid.addWidget(key_lbl, row, 1)
            self._meta_grid.addWidget(url_lbl, row, 2)
            row += 1
        self._meta_frame.setVisible(row > 0)

        # Description
        self._desc.setText(recipe.description)
        self._desc.setVisible(bool(recipe.description))

        # Ingredients
        _clear_layout(self._ing_layout)
        for ing in recipe.recipe_ingredient:
            lbl = QLabel(f"• {ing}")
            lbl.setWordWrap(True)
            self._ing_layout.addWidget(lbl)
        self._ing_box.setVisible(bool(recipe.recipe_ingredient))

        # Instructions
        _clear_layout(self._ins_layout)
        for i, step in enumerate(recipe.recipe_instructions, 1):
            lbl = QLabel(f"<b>{i}.</b>  {step}")
            lbl.setWordWrap(True)
            lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
            self._ins_layout.addWidget(lbl)
        self._ins_box.setVisible(bool(recipe.recipe_instructions))

        # Tools
        _clear_layout(self._tools_layout)
        for tool in recipe.tools:
            self._tools_layout.addWidget(QLabel(f"• {tool}"))
        self._tools_box.setVisible(bool(recipe.tools))

        # Nutrition
        _clear_layout(self._nutr_grid)
        n = recipe.nutrition
        nutr_items = []
        if n:
            nutr_items = [
                ("Energy",       n.calories),
                ("Carbs",        n.carbohydrate_content),
                ("Sugar",        n.sugar_content),
                ("Fat",          n.fat_content),
                ("Sat. fat",     n.saturated_fat_content),
                ("Fibre",        n.fiber_content),
                ("Protein",      n.protein_content),
                ("Sodium",       n.sodium_content),
                ("Serving size", n.serving_size),
            ]
            nutr_items = [(k, v) for k, v in nutr_items if v]
        for idx, (key, val) in enumerate(nutr_items):
            col = (idx % 3) * 2
            row_n = idx // 3
            k_lbl = QLabel(key)
            k_lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            v_lbl = QLabel(val)
            v_lbl.setStyleSheet("font-size: 11px;")
            self._nutr_grid.addWidget(k_lbl, row_n, col)
            self._nutr_grid.addWidget(v_lbl, row_n, col + 1)
        self._nutr_box.setVisible(bool(nutr_items))

        self._img.clear_pixmap()

    def _on_servings_changed(self, value: int):
        if self._orig_servings:
            self._scale_factor = value / self._orig_servings
        if self._recipe_data:
            self._refresh_ingredients_instructions()

    def _on_convert_toggled(self, checked: bool):
        self._converted = checked
        self._convert_btn.setText("Show Original" if checked else "Convert to Metric")
        if self._recipe_data:
            self._refresh_ingredients_instructions()

    def _refresh_ingredients_instructions(self):
        r = self._recipe_data
        convert = self._converted
        factor = self._scale_factor

        _clear_layout(self._ing_layout)
        for ing in r.recipe_ingredient:
            text = scale_ingredient(ing, factor) if abs(factor - 1.0) > 0.001 else ing
            if convert:
                text = convert_ingredient(text)
            lbl = QLabel(f"• {text}")
            lbl.setWordWrap(True)
            self._ing_layout.addWidget(lbl)

        _clear_layout(self._ins_layout)
        for i, step in enumerate(r.recipe_instructions, 1):
            text = convert_instruction(step) if convert else step
            lbl = QLabel(f"<b>{i}.</b>  {text}")
            lbl.setWordWrap(True)
            lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
            self._ins_layout.addWidget(lbl)

    def set_image(self, data: bytes):
        px = QPixmap()
        px.loadFromData(data)
        if not px.isNull():
            self._img.set_pixmap(px)

    def clear_image(self):
        self._img.clear_pixmap()
