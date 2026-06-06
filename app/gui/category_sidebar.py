from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QMenu
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QFont, QColor, QPainter, QIcon, QPixmap
from app.models import RecipeSummary

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
        self._list.addItem(self._make_item("All recipes", None, self._total, "special", bold=True))
        # Only show Uncategorised if the server reports recipes without a category
        if getattr(self, "_uncategorised_count", 0) > 0:
            self._list.addItem(self._make_item("Uncategorised", "*", self._uncategorised_count, "special"))

        # Categories section
        if self._categories:
            self._list.addItem(self._make_item("Categories", None, 0, "header"))
            color = self._list.palette().text().color()
            icon = _folder_icon(color)
            for name, count in self._categories:
                cat_item = self._make_item(name, name, count, "category")
                cat_item.setIcon(icon)
                self._list.addItem(cat_item)

        # Restore selection
        for i in range(self._list.count()):
            if self._list.item(i).data(_ROLE_KEY) == selected_key:
                self._list.setCurrentRow(i)
                break
        else:
            self._list.setCurrentRow(0)

        self._list.blockSignals(False)

    def _make_item(self, label: str, key, count: int, item_type: str,
                   bold: bool = False) -> QListWidgetItem:
        item = QListWidgetItem()
        item.setData(_ROLE_KEY, key)
        item.setData(_ROLE_COUNT, count)
        item.setData(_ROLE_TYPE, item_type)

        if item_type == "header":
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            f = QFont()
            f.setPointSize(8)
            f.setBold(True)
            item.setFont(f)
            item.setForeground(QColor("#888"))
            item.setText(f"  {label.upper()}")
            item.setSizeHint(QSize(0, 28))
        else:
            suffix = f"  {count}" if count else ""
            item.setText(f"  {label}{suffix}")
            f = QFont()
            f.setBold(bold)
            item.setFont(f)
            item.setSizeHint(QSize(0, 36))

        return item

    def _current_key(self):
        item = self._list.currentItem()
        return item.data(_ROLE_KEY) if item else None

    def _on_change(self, item: QListWidgetItem | None, _prev):
        if item and item.data(_ROLE_TYPE) != "header":
            self.category_selected.emit(item.data(_ROLE_KEY))

    def _on_context_menu(self, pos):
        item = self._list.itemAt(pos)
        if not item or item.data(_ROLE_TYPE) != "category":
            return
        name = item.data(_ROLE_KEY)
        menu = QMenu(self)
        rename_act = menu.addAction("Rename…")
        if menu.exec(self._list.mapToGlobal(pos)) == rename_act:
            self.rename_requested.emit(name)
