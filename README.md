# Nextcloud Cookbook

A desktop client for the [Nextcloud Cookbook](https://apps.nextcloud.com/apps/cookbook) app, built with Python and PySide6. Syncs recipes and meal plans directly with your Nextcloud instance.

An Android companion app is available at [khedron83/nextcloud-cookbook-android](https://github.com/khedron83/nextcloud-cookbook-android).

## Features

- Browse, search and filter recipes by category or keyword
- Create, edit, and delete recipes
- Import recipes from any URL supported by the Nextcloud Cookbook app
- Full recipe view: ingredients, instructions, tools, nutrition info
- Servings scaling and imperial → metric unit conversion
- Weekly meal planner (Breakfast / Lunch / Dinner) synced across devices via WebDAV
- Shopping list generated from the week's meal plan
- Offline mode with local recipe cache
- Import and export recipe collections as ZIP

## Requirements

- Python 3.11+
- A running Nextcloud instance with the [Cookbook app](https://apps.nextcloud.com/apps/cookbook) installed

## Install & run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## First run

On first launch go to **File → Settings** and enter:

| Field | Example |
|---|---|
| Server URL | `https://cloud.example.com` or `http://192.168.1.10` |
| Username | your Nextcloud username |
| Password | your Nextcloud password (or app password) |
| Trust all certificates | enable for self-signed certs |

## Menu overview

| Menu | Actions |
|---|---|
| **File** | New Recipe, Import from URL, Import ZIP, Export ZIP, Settings |
| **Library** | Refresh, Reindex, Meal Planner |
| **Help** | About |

## Keyboard shortcuts

| Action | Shortcut |
|---|---|
| New Recipe | `Ctrl+N` |
| Import from URL | `Ctrl+I` |
| Refresh | `F5` |
| Meal Planner | `Ctrl+M` |
| Settings | `Ctrl+,` |
| Back (recipe view) | `Escape` |
| Edit recipe | `E` |

## Meal Plan Sync

The meal plan is stored as `Cookbook/meal_plan.json` in your Nextcloud Files (via WebDAV). Both this app and the Android app read and write this file, so changes made on one device are reflected on the other.

## Downloads

Pre-built binaries (Linux, Windows) and a Flatpak are attached to each [release](https://github.com/khedron83/nextcloud-cookbook/releases).

## License

This project is licensed under the **GNU General Public License v3.0**. See [LICENSE](LICENSE) for details.
