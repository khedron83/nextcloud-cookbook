from PySide6.QtCore import QThread, Signal


class IngredientIndex(QThread):
    """Loads all recipes in the background and builds an ingredient search index."""
    progress = Signal(int, int)   # loaded, total
    ready    = Signal()

    def __init__(self, client, recipe_ids: list[int]):
        super().__init__()
        self._client  = client
        self._ids     = list(recipe_ids)
        self._stop    = False
        self._data: dict[int, list[str]] = {}   # recipe_id → ingredient strings

    def stop(self):
        self._stop = True

    @property
    def is_ready(self) -> bool:
        return not self.isRunning() and bool(self._data)

    def loaded_count(self) -> int:
        return len(self._data)

    def search(self, query: str) -> set[int]:
        q = query.strip().lower()
        if not q:
            return set()
        return {
            rid for rid, ings in self._data.items()
            if any(q in ing.lower() for ing in ings)
        }

    def run(self):
        total = len(self._ids)
        for i, rid in enumerate(self._ids):
            if self._stop:
                break
            try:
                data = self._client.get_recipe(rid)
                self._data[rid] = data.get("recipeIngredient", [])
            except Exception:
                self._data[rid] = []
            self.progress.emit(i + 1, total)
        self.ready.emit()
