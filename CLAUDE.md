# Nextcloud Cookbook — dev notes

## Version bumps

When bumping the version, update **both** of these:

1. `pyproject.toml` — `version = "x.y.z"`
2. `app/workers.py` — `APP_VERSION = "x.y.z"`

The About dialog (`app/gui/main_window.py`) reads `APP_VERSION` automatically — no change needed there.

After committing, tag and push:
```bash
git tag vX.Y.Z && git push origin main && git push origin vX.Y.Z
```
CI will build and publish the release automatically.
