from PySide6.QtGui import QIcon


def theme_icon(*names: str) -> QIcon | None:
    """Return the first available icon from the system icon theme (e.g. Breeze on
    KDE), or None if none of the given names resolve — platforms without an icon
    theme (non-Linux, or Linux without one installed) fall through so callers can
    keep their emoji-glyph fallback instead of showing a blank icon."""
    for name in names:
        icon = QIcon.fromTheme(name)
        if not icon.isNull():
            return icon
    return None
