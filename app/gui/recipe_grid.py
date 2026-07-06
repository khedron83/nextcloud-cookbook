from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QStyledItemDelegate,
    QStyle, QLabel, QPushButton, QComboBox, QStackedWidget,
)
from PySide6.QtCore import Signal, Qt, QSize, QRect, QTimer
from PySide6.QtGui import QPixmap, QFont, QPen, QColor, QPainter, QPalette, QKeySequence, QShortcut

from app.models import RecipeSummary
from app.gui.icons import theme_icon

_ROLE_ID    = Qt.ItemDataRole.UserRole
_ROLE_DATE  = Qt.ItemDataRole.UserRole + 1
_ROLE_THUMB = Qt.ItemDataRole.UserRole + 2

CARD_W  = 200
CARD_H  = 260
THUMB_H = 150   # image portion height


class _CardDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._w = CARD_W

    def set_cell_width(self, w: int):
        self._w = w

    def sizeHint(self, option, index):
        return QSize(self._w, CARD_H)

    def paint(self, painter: QPainter, option, index):
        painter.save()
        r = option.rect
        w, h = r.width(), r.height()
        selected = bool(option.state & QStyle.StateFlag.State_Selected)

        # Card background + border
        pal    = option.palette
        bg     = pal.color(QPalette.ColorRole.Highlight if selected else QPalette.ColorRole.AlternateBase)
        border = pal.color(QPalette.ColorRole.Highlight if selected else QPalette.ColorRole.Mid)
        painter.fillRect(r, pal.color(QPalette.ColorRole.Base))
        painter.fillRect(r.adjusted(2, 2, -2, -2), bg)
        painter.setPen(QPen(border, 1))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawRoundedRect(r.adjusted(2, 2, -3, -3), 8, 8)

        # Image area (top portion)
        img_rect = QRect(r.x() + 2, r.y() + 2, w - 4, THUMB_H)
        thumb: QPixmap | None = index.data(_ROLE_THUMB)
        if thumb and not thumb.isNull():
            scaled = thumb.scaled(
                img_rect.width(), img_rect.height(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.setClipRect(img_rect)
            ox = img_rect.x() + (img_rect.width()  - scaled.width())  // 2
            oy = img_rect.y() + (img_rect.height() - scaled.height()) // 2
            painter.drawPixmap(ox, oy, scaled)
            painter.setClipping(False)
        else:
            painter.fillRect(img_rect, pal.color(QPalette.ColorRole.Mid))
            f = QFont()
            f.setPointSize(28)
            painter.setFont(f)
            painter.setPen(pal.color(QPalette.ColorRole.Midlight))
            painter.drawText(img_rect, Qt.AlignmentFlag.AlignCenter, "🍽")

        # Text area (below image)
        text_color  = pal.color(QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.Text)
        muted_color = pal.color(QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.PlaceholderText)

        text_y = r.y() + THUMB_H + 8
        name = index.data(Qt.ItemDataRole.DisplayRole) or ""

        nf = QFont()
        nf.setBold(True)
        nf.setPointSize(10)
        painter.setFont(nf)
        painter.setPen(text_color)
        name_rect = QRect(r.x() + 8, text_y, w - 16, h - THUMB_H - 30)
        painter.drawText(name_rect,
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                         name)

        date = index.data(_ROLE_DATE) or ""
        if date:
            df = QFont()
            df.setPointSize(8)
            painter.setFont(df)
            painter.setPen(muted_color)
            painter.drawText(
                QRect(r.x() + 8, r.y() + h - 22, w - 16, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                date,
            )

        painter.restore()


class RecipeGrid(QWidget):
    recipe_selected = Signal(int)
    back_requested  = Signal()
    open_settings_requested = Signal()

    _CONTENT, _EMPTY = 0, 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all: list[RecipeSummary] = []
        self._index = None
        self._thumb_cache: dict[int, QPixmap] = {}
        self._cell_w = CARD_W
        self._delegate = _CardDelegate()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._back_btn = QPushButton()
        self._back_icon = theme_icon("go-previous", "arrow-left")
        if self._back_icon:
            self._back_btn.setIcon(self._back_icon)
        self._back_btn.setVisible(False)
        self._back_btn.clicked.connect(self.back_requested)
        layout.addWidget(self._back_btn)

        self._bar_widget = QWidget()
        bar = QHBoxLayout(self._bar_widget)
        bar.setContentsMargins(8, 6, 8, 4)
        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter…")
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(150)
        self._debounce.timeout.connect(self._apply_filter)
        self._search.textChanged.connect(lambda _: self._debounce.start())
        self._mode = QComboBox()
        self._mode.addItems(["Name", "Ingredient"])
        self._mode.setToolTip("Search by recipe name or ingredient")
        self._mode.currentIndexChanged.connect(self._on_mode_changed)
        self._sort = QComboBox()
        self._sort.addItems(["Name A→Z", "Name Z→A", "Newest", "Oldest"])
        self._sort.setToolTip("Sort order")
        self._sort.currentIndexChanged.connect(self._apply_filter)
        self._count_label = QLabel()
        self._count_label.setObjectName("countLabel")
        bar.addWidget(self._search)
        bar.addWidget(self._mode)
        bar.addWidget(self._sort)
        bar.addWidget(self._count_label)
        layout.addWidget(self._bar_widget)

        self._list = QListWidget()
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setFlow(QListWidget.Flow.LeftToRight)
        self._list.setWrapping(True)
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setUniformItemSizes(True)
        self._list.setSpacing(10)
        self._list.setItemDelegate(self._delegate)
        self._list.setMouseTracking(True)
        self._list.itemClicked.connect(lambda item: self.recipe_selected.emit(item.data(_ROLE_ID)))
        self._list.itemActivated.connect(lambda item: self.recipe_selected.emit(item.data(_ROLE_ID)))

        self._content_stack = QStackedWidget()
        self._content_stack.addWidget(self._list)                    # _CONTENT = 0
        self._empty_widget = self._make_empty_widget()
        self._content_stack.addWidget(self._empty_widget)            # _EMPTY = 1
        layout.addWidget(self._content_stack)

        focus_search = QShortcut(QKeySequence("Ctrl+F"), self)
        focus_search.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        focus_search.activated.connect(lambda: (self._search.setFocus(), self._search.selectAll()))

    def _make_empty_widget(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setSpacing(6)

        self._empty_icon = QLabel()
        self._empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_icon.setStyleSheet("font-size: 40px;")

        self._empty_title = QLabel()
        self._empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_title.setStyleSheet("font-size: 15px; font-weight: 600; color: palette(windowText);")

        self._empty_subtitle = QLabel()
        self._empty_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_subtitle.setWordWrap(True)
        self._empty_subtitle.setMaximumWidth(320)
        self._empty_subtitle.setStyleSheet("color: palette(placeholderText); font-size: 12px;")

        self._empty_action = QPushButton()
        self._empty_action.setFixedWidth(160)
        self._empty_action.setVisible(False)
        self._empty_action_connected = False

        v.addWidget(self._empty_icon)
        v.addWidget(self._empty_title)
        v.addWidget(self._empty_subtitle)
        v.addSpacing(4)
        v.addWidget(self._empty_action, 0, Qt.AlignmentFlag.AlignHCenter)
        return w

    def _connect_empty_action(self, slot) -> None:
        if self._empty_action_connected:
            self._empty_action.clicked.disconnect()
        self._empty_action.clicked.connect(slot)
        self._empty_action_connected = True

    def show_no_server(self) -> None:
        """Shown when no Nextcloud server is configured yet."""
        self._bar_widget.setVisible(False)
        self._back_btn.setVisible(False)
        self._empty_icon.setText("⚙")
        self._empty_title.setText("No server configured")
        self._empty_subtitle.setText("Connect to your Nextcloud instance to start browsing recipes.")
        self._empty_action.setText("Open Settings")
        self._empty_action.setVisible(True)
        self._connect_empty_action(self.open_settings_requested)
        self._content_stack.setCurrentIndex(self._EMPTY)

    def show_loading(self) -> None:
        """Shown briefly while the first fetch of recipes is in flight."""
        self._empty_icon.setText("⏳")
        self._empty_title.setText("Loading recipes…")
        self._empty_subtitle.setText("")
        self._empty_action.setVisible(False)
        self._content_stack.setCurrentIndex(self._EMPTY)

    def _show_empty(self, query: str) -> None:
        if query:
            self._empty_icon.setText("🔍")
            self._empty_title.setText("No recipes found")
            self._empty_subtitle.setText(f'No recipes match "{query}".')
            self._empty_action.setText("Clear Filter")
            self._empty_action.setVisible(True)
            self._connect_empty_action(self._clear_filter)
        else:
            self._empty_icon.setText("🍽")
            self._empty_title.setText("No recipes here")
            self._empty_subtitle.setText("Try a different category, or import/create a recipe to get started.")
            self._empty_action.setVisible(False)
        self._content_stack.setCurrentIndex(self._EMPTY)

    def _clear_filter(self) -> None:
        self._search.clear()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Defer so the list viewport has its final size before we measure it
        QTimer.singleShot(0, self._relayout_grid)

    def _relayout_grid(self):
        vw = self._list.viewport().width()
        if vw <= 0:
            return
        sp = self._list.spacing()
        # Qt pads `sp` on each side of every item, so each slot = CARD_W + 2*sp
        cols = max(1, vw // (CARD_W + 2 * sp))
        cell_w = max(1, vw // cols - 2 * sp)
        if cell_w == self._cell_w:
            return
        self._cell_w = cell_w
        self._delegate.set_cell_width(cell_w)
        sz = QSize(cell_w, CARD_H)
        for i in range(self._list.count()):
            self._list.item(i).setSizeHint(sz)

    def set_ingredient_index(self, index):
        self._index = index
        if self._mode.currentText() == "Ingredient":
            self._apply_filter()

    def _on_mode_changed(self):
        mode = self._mode.currentText()
        if mode == "Ingredient" and not self._index:
            self._search.setPlaceholderText("Building index…")
            self._search.setEnabled(False)
        else:
            self._search.setPlaceholderText("Filter…")
            self._search.setEnabled(True)
        self._apply_filter()

    def set_back_label(self, label: str):
        """Show a back button with the given label, or hide it if label is empty."""
        if label:
            self._back_btn.setText(label if self._back_icon else f"← {label}")
            self._back_btn.setVisible(True)
        else:
            self._back_btn.setVisible(False)

    def set_recipes(self, recipes: list[RecipeSummary]):
        self._all = recipes
        self._bar_widget.setVisible(True)
        self._apply_filter()

    def _apply_filter(self):
        query = self._search.text().lower()
        mode  = self._mode.currentText()

        if mode == "Ingredient" and self._index and query:
            matching_ids = self._index.search(query)
        else:
            matching_ids = None

        filtered = []
        for r in self._all:
            if matching_ids is not None:
                if r.recipe_id not in matching_ids:
                    continue
            elif query and query not in r.name.lower():
                continue
            filtered.append(r)

        sort_key = self._sort.currentText()
        if sort_key == "Name A→Z":
            filtered.sort(key=lambda r: r.name.lower())
        elif sort_key == "Name Z→A":
            filtered.sort(key=lambda r: r.name.lower(), reverse=True)
        elif sort_key == "Newest":
            filtered.sort(key=lambda r: r.date_modified or "", reverse=True)
        elif sort_key == "Oldest":
            filtered.sort(key=lambda r: r.date_modified or "")

        self._list.clear()
        for r in filtered:
            item = QListWidgetItem(r.name)
            item.setData(_ROLE_ID, r.recipe_id)
            date = r.date_modified[:10] if r.date_modified else ""
            item.setData(_ROLE_DATE, date)
            if r.recipe_id in self._thumb_cache:
                item.setData(_ROLE_THUMB, self._thumb_cache[r.recipe_id])
            item.setSizeHint(QSize(self._cell_w, CARD_H))
            self._list.addItem(item)
        n = self._list.count()
        self._count_label.setText(f"{n} recipe{'s' if n != 1 else ''}")
        if n == 0:
            self._show_empty(self._search.text().strip())
        else:
            self._content_stack.setCurrentIndex(self._CONTENT)
        QTimer.singleShot(0, self._relayout_grid)

    def set_thumbnail(self, recipe_id: int, data: bytes):
        px = QPixmap()
        px.loadFromData(data)
        if px.isNull():
            return
        self._thumb_cache[recipe_id] = px
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(_ROLE_ID) == recipe_id:
                item.setData(_ROLE_THUMB, px)
                return

    def refresh_recipe(self, recipe_id, name: str, keywords: str = ""):
        """Update a card's text in-place without rebuilding the list (preserves thumbnails)."""
        rid = int(recipe_id)
        for r in self._all:
            try:
                if int(r.recipe_id) == rid:
                    r.name = name
                    r.keywords = keywords
                    break
            except (TypeError, ValueError):
                pass
        for i in range(self._list.count()):
            item = self._list.item(i)
            try:
                if int(item.data(_ROLE_ID) or 0) == rid:
                    item.setText(name)
                    break
            except (TypeError, ValueError):
                pass

    def remap_recipe_id(self, old_id: int, new_id: int):
        """Swap a local negative ID for the real server ID after sync."""
        for r in self._all:
            try:
                if int(r.recipe_id) == old_id:
                    r.recipe_id = new_id
                    break
            except (TypeError, ValueError):
                pass
        for i in range(self._list.count()):
            item = self._list.item(i)
            try:
                if int(item.data(_ROLE_ID) or 0) == old_id:
                    item.setData(_ROLE_ID, new_id)
                    break
            except (TypeError, ValueError):
                pass

    def insert_recipe(self, summary: RecipeSummary):
        """Append a new card without rebuilding the list."""
        self._all.append(summary)
        item = QListWidgetItem(summary.name)
        item.setData(_ROLE_ID, summary.recipe_id)
        item.setData(_ROLE_DATE, "")
        item.setSizeHint(QSize(self._cell_w, CARD_H))
        self._list.addItem(item)
        n = self._list.count()
        self._count_label.setText(f"{n} recipe{'s' if n != 1 else ''}")
        self._content_stack.setCurrentIndex(self._CONTENT)

    def recipe_ids(self) -> list[int]:
        return [r.recipe_id for r in self._all]

    def set_category_title(self, title: str):
        pass
