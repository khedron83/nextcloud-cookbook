from PySide6.QtCore import QThread, Signal


class IngredientIndex(QThread):
    """Loads all recipes in the background and builds an ingredient search index."""
    progress = Signal(int, int)   # loaded, total
    ready    = Signal()

    def __init__(self, client, recipe_ids: list[int], cached_data: dict | None = None):
        super().__init__()
        self._client     = client
        self._ids        = list(recipe_ids)
        self._stop       = False
        self._from_cache = cached_data is not None
        self._data: dict[int, list[str]] = (
            {int(k): v for k, v in cached_data.items()} if cached_data else {}
        )

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

    def to_dict(self) -> dict:
        return {str(k): v for k, v in self._data.items()}

    def run(self):
        if self._from_cache:
            self.ready.emit()
            return
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
