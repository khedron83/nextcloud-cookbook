from PySide6.QtCore import QThread, Signal
from typing import Callable


class Worker(QThread):
    result = Signal(object)
    error = Signal(str)

    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            self.result.emit(self._fn(*self._args, **self._kwargs))
        except Exception as e:
            self.error.emit(str(e))


class ThumbnailLoader(QThread):
    """Loads thumbnails one-by-one and emits (recipe_id, bytes) for each."""
    thumbnail_ready = Signal(int, bytes)

    def __init__(self, client, recipe_ids: list[int]):
        super().__init__()
        self._client = client
        self._ids = list(recipe_ids)
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        for rid in self._ids:
            if self._stop:
                break
            try:
                data = self._client.get_recipe_image(rid, size="thumb")
                self.thumbnail_ready.emit(rid, data)
            except Exception:
                pass
