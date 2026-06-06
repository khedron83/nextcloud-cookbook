import json
import re
import zipfile
from datetime import date

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QFileDialog,
)
from PySide6.QtCore import QThread, Signal

from app.api.client import CookbookClient


def _safe_name(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip('._') or "recipe"


# ── Workers ───────────────────────────────────────────────────────────────────

class _ExportWorker(QThread):
    progress = Signal(int, int, str)
    finished_ok = Signal(int)
    finished_err = Signal(str)

    def __init__(self, client: CookbookClient, zip_path: str):
        super().__init__()
        self._client = client
        self._zip_path = zip_path

    def run(self):
        try:
            recipes = self._client.get_recipes()
            total = len(recipes)
            with zipfile.ZipFile(self._zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for i, item in enumerate(recipes):
                    rid = item.get("recipe_id", item.get("id", 0))
                    name = item.get("name", f"recipe_{rid}")
                    folder = _safe_name(name)
                    self.progress.emit(i, total, name)

                    data = self._client.get_recipe(rid)
                    zf.writestr(f"{folder}/recipe.json",
                                json.dumps(data, indent=2, ensure_ascii=False))
                    try:
                        zf.writestr(f"{folder}/image.jpg",
                                    self._client.get_recipe_image(rid))
                    except Exception:
                        pass

            self.progress.emit(total, total, "")
            self.finished_ok.emit(total)
        except Exception as e:
            self.finished_err.emit(str(e))


class _ImportWorker(QThread):
    progress = Signal(int, int, str)
    log = Signal(str)
    finished_ok = Signal(int, int)
    finished_err = Signal(str)

    def __init__(self, client: CookbookClient, zip_path: str):
        super().__init__()
        self._client = client
        self._zip_path = zip_path

    def run(self):
        try:
            with zipfile.ZipFile(self._zip_path, 'r') as zf:
                json_files = sorted(n for n in zf.namelist()
                                    if n.endswith('/recipe.json'))
                total = len(json_files)
                succeeded = failed = 0
                for i, path in enumerate(json_files):
                    folder = path.split('/')[0]
                    self.progress.emit(i, total, folder)
                    try:
                        data = json.loads(zf.read(path))
                        data.pop('id', None)
                        self._client.create_recipe(data)
                        succeeded += 1
                        self.log.emit(f"✓  {folder}")
                    except Exception as e:
                        failed += 1
                        self.log.emit(f"✗  {folder}: {e}")

            self.progress.emit(total, total, "")
            self.finished_ok.emit(succeeded, failed)
        except Exception as e:
            self.finished_err.emit(str(e))


# ── Dialogs ───────────────────────────────────────────────────────────────────

class ExportDialog(QDialog):
    def __init__(self, client: CookbookClient, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Recipes")
        self.setMinimumWidth(500)
        self._client = client
        self._worker: _ExportWorker | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self._status = QLabel("Choose a destination ZIP file to export all recipes.")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self._bar = QProgressBar()
        self._bar.setVisible(False)
        layout.addWidget(self._bar)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(180)
        self._log.setVisible(False)
        layout.addWidget(self._log)

        btns = QHBoxLayout()
        self._start = QPushButton("Choose File & Export…")
        self._start.clicked.connect(self._begin)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        btns.addWidget(self._start)
        btns.addWidget(close)
        layout.addLayout(btns)

    def _begin(self):
        default = f"cookbook_export_{date.today()}.zip"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save ZIP", default, "ZIP files (*.zip)"
        )
        if not path:
            return

        self._start.setEnabled(False)
        self._bar.setRange(0, 0)
        self._bar.setVisible(True)
        self._log.clear()
        self._log.setVisible(True)
        self._status.setText("Starting export…")

        self._worker = _ExportWorker(self._client, path)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_done)
        self._worker.finished_err.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current: int, total: int, label: str):
        if total:
            self._bar.setRange(0, total)
            self._bar.setValue(current)
        if label:
            self._status.setText(f"Exporting ({current + 1}/{total}): {label}")
            self._log.append(f"✓  {label}")

    def _on_done(self, total: int):
        self._bar.setValue(self._bar.maximum())
        self._status.setText(
            f"Export complete — {total} recipe{'s' if total != 1 else ''} saved."
        )
        self._start.setEnabled(True)

    def _on_error(self, msg: str):
        self._status.setText(f"Export failed: {msg}")
        self._start.setEnabled(True)


class ImportDialog(QDialog):
    imported = Signal()

    def __init__(self, client: CookbookClient, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Recipes")
        self.setMinimumWidth(500)
        self._client = client
        self._worker: _ImportWorker | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self._status = QLabel(
            "Choose a ZIP file previously exported from Nextcloud Cookbook.\n"
            "Each recipe folder must contain a recipe.json file."
        )
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self._bar = QProgressBar()
        self._bar.setVisible(False)
        layout.addWidget(self._bar)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(180)
        self._log.setVisible(False)
        layout.addWidget(self._log)

        btns = QHBoxLayout()
        self._start = QPushButton("Choose ZIP & Import…")
        self._start.clicked.connect(self._begin)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        btns.addWidget(self._start)
        btns.addWidget(close)
        layout.addLayout(btns)

    def _begin(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open ZIP", "", "ZIP files (*.zip)"
        )
        if not path:
            return

        self._start.setEnabled(False)
        self._bar.setRange(0, 0)
        self._bar.setVisible(True)
        self._log.clear()
        self._log.setVisible(True)
        self._status.setText("Starting import…")

        self._worker = _ImportWorker(self._client, path)
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._log.append)
        self._worker.finished_ok.connect(self._on_done)
        self._worker.finished_err.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current: int, total: int, label: str):
        if total:
            self._bar.setRange(0, total)
            self._bar.setValue(current)
        if label:
            self._status.setText(f"Importing ({current + 1}/{total}): {label}")

    def _on_done(self, succeeded: int, failed: int):
        self._bar.setValue(self._bar.maximum())
        self._status.setText(
            f"Import complete — {succeeded} imported, {failed} failed."
        )
        self._start.setEnabled(True)
        if succeeded:
            self.imported.emit()

    def _on_error(self, msg: str):
        self._status.setText(f"Import failed: {msg}")
        self._start.setEnabled(True)
