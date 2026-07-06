from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
    QLabel, QPushButton, QVBoxLayout, QMessageBox, QCheckBox, QSpinBox, QHBoxLayout,
    QFileDialog,
)
from PySide6.QtCore import QSettings
from app.api.client import CookbookClient


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nextcloud Settings")
        self.setMinimumWidth(420)
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._url = QLineEdit()
        self._url.setPlaceholderText("https://cloud.example.com")
        form.addRow("Server URL:", self._url)

        self._user = QLineEdit()
        self._user.setPlaceholderText("your-username")
        form.addRow("Username:", self._user)

        self._pwd = QLineEdit()
        self._pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self._pwd.setPlaceholderText("app password (recommended)")
        form.addRow("Password:", self._pwd)

        self._verify_ssl = QCheckBox("Verify SSL certificate")
        self._verify_ssl.setChecked(True)
        form.addRow("", self._verify_ssl)

        obsidian_row = QHBoxLayout()
        self._obsidian_folder = QLineEdit()
        self._obsidian_folder.setPlaceholderText("Optional — leave blank to be prompted each time")
        obsidian_row.addWidget(self._obsidian_folder)
        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(72)
        browse_btn.clicked.connect(self._browse_obsidian)
        obsidian_row.addWidget(browse_btn)
        form.addRow("Obsidian vault:", obsidian_row)

        sync_row = QHBoxLayout()
        self._sync_interval = QSpinBox()
        self._sync_interval.setRange(0, 60)
        self._sync_interval.setValue(5)
        self._sync_interval.setSuffix(" min")
        self._sync_interval.setFixedWidth(90)
        sync_row.addWidget(self._sync_interval)
        sync_row.addWidget(QLabel("(0 = on close only)"))
        sync_row.addStretch()
        form.addRow("Auto-sync every:", sync_row)

        layout.addLayout(form)

        note = QLabel(
            '<small>Use an <b>app password</b> (Settings → Security) '
            'rather than your account password. Uncheck SSL verification '
            'only for self-signed certificates on trusted local servers.</small>'
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self._test)
        layout.addWidget(test_btn)

        self._status = QLabel()
        layout.addWidget(self._status)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load(self):
        s = QSettings()
        self._url.setText(s.value("server/url", ""))
        self._user.setText(s.value("server/username", ""))
        self._pwd.setText(s.value("server/password", ""))
        self._verify_ssl.setChecked(s.value("server/verify_ssl", True, type=bool))
        self._sync_interval.setValue(s.value("sync/interval_minutes", 5, type=int))
        self._obsidian_folder.setText(s.value("export/obsidian_folder", ""))

    def _save_and_accept(self):
        if not self._url.text().strip():
            QMessageBox.warning(self, "Missing", "Server URL is required.")
            return
        s = QSettings()
        s.setValue("server/url", self._url.text().strip())
        s.setValue("server/username", self._user.text().strip())
        s.setValue("server/password", self._pwd.text())
        s.setValue("server/verify_ssl", self._verify_ssl.isChecked())
        s.setValue("sync/interval_minutes", self._sync_interval.value())
        s.setValue("export/obsidian_folder", self._obsidian_folder.text().strip())
        self.accept()

    def _browse_obsidian(self):
        path = QFileDialog.getExistingDirectory(self, "Select Obsidian Vault Folder")
        if path:
            self._obsidian_folder.setText(path)

    def _test(self):
        url = self._url.text().strip()
        user = self._user.text().strip()
        pwd = self._pwd.text()
        if not url or not user:
            self._status.setText("Fill in URL and username first.")
            return
        try:
            CookbookClient(url, user, pwd, verify_ssl=self._verify_ssl.isChecked()).get_api_version()
            self._status.setText("Connected successfully.")
            self._status.setStyleSheet("color: green;")
        except Exception as e:
            self._status.setText(str(e))
            self._status.setStyleSheet("color: red;")

    @staticmethod
    def get_client() -> CookbookClient | None:
        s = QSettings()
        url = s.value("server/url", "")
        user = s.value("server/username", "")
        pwd = s.value("server/password", "")
        verify_ssl = s.value("server/verify_ssl", True, type=bool)
        if url and user:
            return CookbookClient(url, user, pwd, verify_ssl=verify_ssl)
        return None
