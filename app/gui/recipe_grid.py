from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QStyledItemDelegate,
    QStyle, QLabel, QPushButton, QComboBox,
)
from PySide6.QtCore import Signal, Qt, QSize, QRect
from PySide6.QtGui import QPixmap, QFont, QPen, QColor, QPainter, QKeySequence, QShortcut

from app.models import RecipeSummary

_ROLE_ID    = Qt.ItemDataRole.UserRole
_ROLE_DATE  = Qt.ItemDataRole.UserRole + 1
_ROLE_THUMB = Qt.ItemDataRole.UserRole + 2

CARD_W  = 200
CARD_H  = 260
THUMB_H = 150   # image portion height


class _CardDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(CARD_W, CARD_H)

    def paint(self, painter: QPainter, option, index):
        painter.save()
        r = option.rect
        selected = bool(option.state & QStyle.StateFlag.State_Selected)

        # Card background + border
        bg     = QColor("#1d3461") if selected else QColor("#1e2a3a")
        border = QColor("#2563eb") if selected else QColor("#2d3f55")
        painter.fillRect(r, QColor("#111827"))  # gap between cards
        painter.fillRect(r.adjusted(2, 2, -2, -2), bg)
        painter.setPen(QPen(border, 1))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawRoundedRect(r.adjusted(2, 2, -3, -3), 8, 8)

        # Image area (top portion)
        img_rect = QRect(r.x() + 2, r.y() + 2, CARD_W - 4, THUMB_H)
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
            painter.fillRect(img_rect, QColor("#243447"))
            f = QFont()
            f.setPointSize(28)
            painter.setFont(f)
            painter.setPen(QColor("#374151"))
            painter.drawText(img_rect, Qt.AlignmentFlag.AlignCenter, "🍽")

        # Text area (below image)
        text_color  = QColor("#93c5fd") if selected else QColor("#e2e8f0")
        muted_color = QColor("#93c5fd") if selected else QColor("#64748b")

        text_y = r.y() + THUMB_H + 8
        name = index.data(Qt.ItemDataRole.DisplayRole) or ""

        nf = QFont()
        nf.setBold(True)
        nf.setPointSize(10)
        painter.setFont(nf)
        painter.setPen(text_color)
        name_rect = QRect(r.x() + 8, text_y, CARD_W - 16, CARD_H - THUMB_H - 30)
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
                QRect(r.x() + 8, r.y() + CARD_H - 22, CARD_W - 16, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                date,
            )

        painter.restore()


class RecipeGrid(QWidget):
    recipe_selected = Signal(int)
    back_requested  = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all: list[RecipeSummary] = []
        self._index = None
        self._thumb_cache: dict[int, QPixmap] = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._back_btn = QPushButton()
        self._back_btn.setVisible(False)
        self._back_btn.clicked.connect(self.back_requested)
        layout.addWidget(self._back_btn)

        bar = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter…")
        self._search.textChanged.connect(self._apply_filter)
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
        layout.addLayout(bar)

        self._list = QListWidget()
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setFlow(QListWidget.Flow.LeftToRight)
        self._list.setWrapping(True)
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setUniformItemSizes(True)
        self._list.setSpacing(10)
        self._list.setItemDelegate(_CardDelegate())
        self._list.setMouseTracking(True)
        self._list.itemClicked.connect(lambda item: self.recipe_selected.emit(item.data(_ROLE_ID)))
        self._list.itemActivated.connect(lambda item: self.recipe_selected.emit(item.data(_ROLE_ID)))
        layout.addWidget(self._list)

        focus_search = QShortcut(QKeySequence("Ctrl+F"), self)
        focus_search.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        focus_search.activated.connect(lambda: (self._search.setFocus(), self._search.selectAll()))

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
            self._back_btn.setText(f"← {label}")
            self._back_btn.setVisible(True)
        else:
            self._back_btn.setVisible(False)

    def set_recipes(self, recipes: list[RecipeSummary]):
        self._all = recipes
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
            item.setSizeHint(QSize(CARD_W, CARD_H))
            self._list.addItem(item)
        n = self._list.count()
        self._count_label.setText(f"{n} recipe{'s' if n != 1 else ''}")

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

    def recipe_ids(self) -> list[int]:
        return [r.recipe_id for r in self._all]

    def set_category_title(self, title: str):
        pass
