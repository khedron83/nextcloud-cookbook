from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QMenu, QLabel, QPushButton,
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QFont, QColor, QPainter, QPalette, QIcon, QPixmap
from app.models import RecipeSummary
from app.gui.icons import theme_icon

_ROLE_KEY = Qt.ItemDataRole.UserRole       # None=all, str=category name
_ROLE_COUNT = Qt.ItemDataRole.UserRole + 1
_ROLE_TYPE = Qt.ItemDataRole.UserRole + 2  # "special" | "header" | "category"


def _folder_icon(color: QColor) -> QIcon:
    px = QPixmap(16, 16)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(color)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 6, 16, 10, 2, 2)
    p.drawRoundedRect(0, 3, 8, 6, 2, 2)
    p.end()
    return QIcon(px)


class _CategoryRow(QWidget):
    """Row widget for a sidebar entry: optional icon + name + muted count pill,
    plus a hover-reveal rename button for renameable categories."""

    def __init__(self, label: str, count: int, bold: bool = False,
                 icon: QIcon | None = None, on_rename=None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 6, 0)
        layout.setSpacing(8)

        if icon is not None:
            icon_lbl = QLabel()
            icon_lbl.setPixmap(icon.pixmap(16, 16))
            layout.addWidget(icon_lbl)

        self._name_lbl = QLabel(label)
        f = self._name_lbl.font()
        f.setBold(bold)
        self._name_lbl.setFont(f)
        layout.addWidget(self._name_lbl, 1)

        self._count_lbl = QLabel(str(count))
        self._count_lbl.setVisible(bool(count))
        cf = self._count_lbl.font()
        cf.setPointSize(max(8, cf.pointSize() - 1))
        self._count_lbl.setFont(cf)
        layout.addWidget(self._count_lbl, 0)

        self._rename_btn = None
        if on_rename is not None:
            self._rename_btn = QPushButton()
            pencil = theme_icon("document-edit", "edit-rename")
            if pencil:
                self._rename_btn.setIcon(pencil)
            else:
                self._rename_btn.setText("✎")
            self._rename_btn.setFixedSize(20, 20)
            self._rename_btn.setToolTip("Rename category")
            self._rename_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._rename_btn.setStyleSheet(
                "QPushButton { border: none; background: transparent; padding: 0; }"
                "QPushButton:hover { background: rgba(127,127,127,0.25); border-radius: 4px; }"
            )
            self._rename_btn.clicked.connect(on_rename)
            self._rename_btn.setVisible(False)
            layout.addWidget(self._rename_btn)

        self.set_selected(False)

    def enterEvent(self, event):
        if self._rename_btn:
            self._rename_btn.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._rename_btn:
            self._rename_btn.setVisible(False)
        super().leaveEvent(event)

    def set_selected(self, selected: bool) -> None:
        if selected:
            self._name_lbl.setStyleSheet("color: palette(highlightedText); background: transparent;")
            self._count_lbl.setStyleSheet(
                "color: palette(highlightedText); background: rgba(255,255,255,0.25);"
                " border-radius: 8px; padding: 1px 7px;"
            )
        else:
            self._name_lbl.setStyleSheet("color: palette(windowText); background: transparent;")
            self._count_lbl.setStyleSheet(
                "color: palette(placeholderText); background: rgba(127,127,127,0.18);"
                " border-radius: 8px; padding: 1px 7px;"
            )


class CategorySidebar(QWidget):
    """Emits category_selected(None) for All Recipes, or category_selected(str) for a category."""
    category_selected = Signal(object)
    rename_requested  = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._total = 0
        self._categories: list[tuple[str, int]] = []  # (name, count)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._list = QListWidget()
        self._list.setFrameShape(self._list.frameShape().NoFrame)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setSpacing(1)
        self._list.currentItemChanged.connect(self._on_change)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self._list)

    def set_total(self, n: int):
        self._total = n
        self._rebuild()

    def set_categories(self, data: list):
        """Accepts list of str or list of dicts with 'name' (and optional 'recipe_count')."""
        cats: list[tuple[str, int]] = []
        self._uncategorised_count = 0
        for item in data:
            if isinstance(item, str):
                if item == "*":
                    self._uncategorised_count = 1
                else:
                    cats.append((item, 0))
            elif isinstance(item, dict):
                name = item.get("name", "")
                count = int(item.get("recipe_count", item.get("recipeCount", 0)) or 0)
                if name == "*":
                    self._uncategorised_count = count
                elif name:
                    cats.append((name, count))
        self._categories = sorted(cats, key=lambda x: x[0].lower())
        self._rebuild()

    def _rebuild(self):
        selected_key = self._current_key()

        self._list.blockSignals(True)
        self._list.clear()

        # All recipes
        self._add_row("All recipes", None, self._total, "special", bold=True)
        # Only show Uncategorised if the server reports recipes without a category
        if getattr(self, "_uncategorised_count", 0) > 0:
            self._add_row("Uncategorised", "*", self._uncategorised_count, "special")

        # Categories section
        if self._categories:
            self._add_header("Categories")
            color = self._list.palette().text().color()
            icon = _folder_icon(color)
            for name, count in self._categories:
                self._add_row(
                    name, name, count, "category", icon=icon,
                    on_rename=lambda checked=False, n=name: self.rename_requested.emit(n),
                )

        # Restore selection
        for i in range(self._list.count()):
            if self._list.item(i).data(_ROLE_KEY) == selected_key:
                self._list.setCurrentRow(i)
                break
        else:
            self._list.setCurrentRow(0)

        self._list.blockSignals(False)
        self._refresh_row_selection()

    def _add_header(self, label: str) -> None:
        item = QListWidgetItem()
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setData(_ROLE_TYPE, "header")
        f = QFont()
        f.setPointSize(8)
        f.setBold(True)
        item.setFont(f)
        item.setForeground(self._list.palette().color(QPalette.ColorRole.PlaceholderText))
        item.setText(f"  {label.upper()}")
        item.setSizeHint(QSize(0, 28))
        self._list.addItem(item)

    def _add_row(self, label: str, key, count: int, item_type: str,
                 bold: bool = False, icon: QIcon | None = None, on_rename=None) -> None:
        item = QListWidgetItem()
        item.setData(_ROLE_KEY, key)
        item.setData(_ROLE_COUNT, count)
        item.setData(_ROLE_TYPE, item_type)
        item.setSizeHint(QSize(0, 36))
        self._list.addItem(item)
        row = _CategoryRow(label, count, bold=bold, icon=icon, on_rename=on_rename)
        self._list.setItemWidget(item, row)

    def _current_key(self):
        item = self._list.currentItem()
        return item.data(_ROLE_KEY) if item else None

    def _on_change(self, item: QListWidgetItem | None, _prev):
        self._refresh_row_selection()
        if item and item.data(_ROLE_TYPE) != "header":
            self.category_selected.emit(item.data(_ROLE_KEY))

    def _refresh_row_selection(self) -> None:
        current = self._list.currentItem()
        for i in range(self._list.count()):
            item = self._list.item(i)
            row = self._list.itemWidget(item)
            if isinstance(row, _CategoryRow):
                row.set_selected(item is current)

    def _on_context_menu(self, pos):
        item = self._list.itemAt(pos)
        if not item or item.data(_ROLE_TYPE) != "category":
            return
        name = item.data(_ROLE_KEY)
        menu = QMenu(self)
        rename_act = menu.addAction("Rename…")
        if menu.exec(self._list.mapToGlobal(pos)) == rename_act:
            self.rename_requested.emit(name)
