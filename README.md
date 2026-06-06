# Nextcloud Cookbook

A pair of clients for the [Nextcloud Cookbook](https://apps.nextcloud.com/apps/cookbook) app — a **desktop app** (Python/PySide6) and an **Android app** (Kotlin/Jetpack Compose). Both sync recipes and meal plans directly with your Nextcloud instance.

## Features

- Browse, search and filter recipes by category or keyword
- Create, edit, and delete recipes
- Import recipes from any URL supported by the Nextcloud Cookbook app
- Full recipe view: ingredients, instructions, tools, nutrition info
- Servings scaling and imperial → metric unit conversion
- Weekly meal planner (Breakfast / Lunch / Dinner) synced across devices via WebDAV
- Shopping list generated from the week's meal plan
- Offline mode with local cache (desktop) / Room database (Android)
- Import and export recipe collections as ZIP (desktop)

---

## Desktop App (Python / PySide6)

### Requirements

- Python 3.11+
- A running Nextcloud instance with the [Cookbook app](https://apps.nextcloud.com/apps/cookbook) installed

### Install & run

```bash
cd nextcloud-cookbook          # repo root
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### First run

On first launch go to **File → Settings** and enter:

| Field | Example |
|---|---|
| Server URL | `https://cloud.example.com` or `http://192.168.1.10` |
| Username | your Nextcloud username |
| Password | your Nextcloud password (or app password) |
| Trust all certificates | enable for self-signed certs |

### Menu overview

| Menu | Actions |
|---|---|
| **File** | New Recipe, Import from URL, Import ZIP, Export ZIP, Settings |
| **Library** | Refresh, Reindex, Meal Planner |
| **Help** | About |

### Keyboard shortcuts

| Action | Shortcut |
|---|---|
| New Recipe | `Ctrl+N` |
| Import from URL | `Ctrl+I` |
| Refresh | `F5` |
| Meal Planner | `Ctrl+M` |
| Settings | `Ctrl+,` |
| Back (recipe view) | `Escape` |
| Edit recipe | `E` |

---

## Android App (Kotlin / Jetpack Compose)

Located in the `android/` directory.

### Requirements

- Android 8.0 (API 26) or later
- A running Nextcloud instance with the Cookbook app installed

### Build

Open `android/` in Android Studio (Iguana or later) and run the project, or build from the command line:

```bash
cd android
./gradlew assembleDebug
```

The APK will be at `android/app/build/outputs/apk/debug/app-debug.apk`.

### First run

On first launch tap **⋮ → Settings** (or the Settings icon in the Recipes tab top bar) and enter your server URL, username, and password. Tap **Test Connection** to verify, then **Save**.

### Navigation

The app uses a four-tab bottom navigation bar:

| Tab | Description |
|---|---|
| **Recipes** | All recipes in a card grid. Tap 🔍 to search. |
| **Categories** | Browse by category. Tap a category to see its recipes. |
| **Planner** | Weekly meal planner. Assign recipes to Breakfast / Lunch / Dinner slots. |
| **Shopping** | Shopping list auto-generated from this week's meal plan. |

### Recipe actions

- **View** — tap any recipe card
- **Edit** — tap the ✏️ icon on the recipe detail screen
- **Delete** — tap **⋮ → Delete recipe** on the recipe detail screen
- **Import from URL** — tap **+** then the 🔗 icon in the editor
- **Servings** — adjust with +/− on the detail screen; quantities scale automatically
- **Metric units** — tap the ruler icon to convert imperial measurements

---

## Meal Plan Sync

The meal plan is stored as `Cookbook/meal_plan.json` in your Nextcloud Files (via WebDAV). Both the desktop and Android apps read and write this file, so changes made on one device are reflected on the other.

---

## License

This project is licensed under the **GNU General Public License v3.0**. See [LICENSE](LICENSE) for details.
