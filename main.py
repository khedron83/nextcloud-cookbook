import sys
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from app.gui.main_window import MainWindow

_ICON = Path(__file__).parent / "app" / "resources" / "icon.svg"


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Nextcloud Cookbook")
    app.setOrganizationName("kane")
    app.setApplicationDisplayName("Nextcloud Cookbook")
    if _ICON.exists():
        app.setWindowIcon(QIcon(str(_ICON)))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
