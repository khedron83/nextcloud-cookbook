from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QComboBox, QLineEdit, QLabel,
)
from PySide6.QtCore import Signal, Qt
from app.models import RecipeSummary


class RecipeListPanel(QWidget):
    recipe_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._recipes: list[RecipeSummary] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter recipes…")
        self._search.textChanged.connect(self._apply_filter)
        layout.addWidget(self._search)

        self._category = QComboBox()
        self._category.addItem("All Categories")
        self._category.currentTextChanged.connect(self._apply_filter)
        layout.addWidget(self._category)

        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_selection)
        layout.addWidget(self._list)

        self._count_label = QLabel()
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._count_label)

    def set_recipes(self, recipes: list[RecipeSummary]):
        self._recipes = recipes
        self._apply_filter()

    def set_categories(self, categories: list[str]):
        current = self._category.currentText()
        self._category.blockSignals(True)
        self._category.clear()
        self._category.addItem("All Categories")
        for cat in sorted(categories):
            self._category.addItem(cat)
        idx = self._category.findText(current)
        self._category.setCurrentIndex(max(idx, 0))
        self._category.blockSignals(False)

    def _apply_filter(self):
        query = self._search.text().lower()
        category = self._category.currentText()

        self._list.clear()
        for r in self._recipes:
            if query and query not in r.name.lower():
                continue
            if category != "All Categories" and r.category != category:
                continue
            item = QListWidgetItem(r.name)
            item.setData(Qt.ItemDataRole.UserRole, r.recipe_id)
            self._list.addItem(item)

        n = self._list.count()
        self._count_label.setText(f"{n} recipe{'s' if n != 1 else ''}")

    def _on_selection(self, item: QListWidgetItem | None, _prev):
        if item:
            self.recipe_selected.emit(item.data(Qt.ItemDataRole.UserRole))

    def select_recipe(self, recipe_id: int):
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == recipe_id:
                self._list.setCurrentItem(item)
                return
