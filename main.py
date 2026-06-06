import sys
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from app.gui.main_window import MainWindow

_ICON = Path(__file__).parent / "app" / "resources" / "icon.svg"
_FLATPAK_APP_ID = "io.github.khedron83.NextcloudCookbook"


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Nextcloud Cookbook")
    app.setOrganizationName("kane")
    app.setApplicationDisplayName("Nextcloud Cookbook")
    app.setDesktopFileName(_FLATPAK_APP_ID)
    if _ICON.exists():
        app.setWindowIcon(QIcon(str(_ICON)))
    else:
        app.setWindowIcon(QIcon.fromTheme(_FLATPAK_APP_ID))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
