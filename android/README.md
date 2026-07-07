# Nextcloud Cookbook — Android

An Android client for the [Nextcloud Cookbook](https://apps.nextcloud.com/apps/cookbook) app, built with Kotlin and Jetpack Compose. Syncs recipes and meal plans directly with your Nextcloud instance.

A desktop companion app (Python/PySide6) is available at [khedron83/nextcloud-cookbook](https://github.com/khedron83/nextcloud-cookbook).

## Features

- Browse, search and filter recipes by category or keyword
- Create, edit, and delete recipes
- Import recipes from a URL via the Nextcloud Cookbook API
- Full recipe view: ingredients, instructions, tools, nutrition info
- Servings scaling and imperial → metric unit conversion
- Weekly meal planner (Breakfast / Lunch / Dinner) synced across devices via WebDAV
- Shopping list generated from the week's meal plan
- Offline-capable with local Room database cache

## Requirements

- Android 8.0 (API 26) or later
- A running Nextcloud instance with the [Cookbook app](https://apps.nextcloud.com/apps/cookbook) installed

## Install

Download the latest APK from the [releases page](https://github.com/khedron83/nextcloud-cookbook-android/releases) and install it directly on your device (you will need to allow installation from unknown sources).

## Build from source

Open the repo root in Android Studio (Iguana or later) and run the project, or build from the command line:

```bash
./gradlew assembleDebug
```

The APK will be at `app/build/outputs/apk/debug/app-debug.apk`.

## First run

On first launch tap **⋮ → Settings** and enter your server URL, username, and password. Tap **Save** to connect.

## Navigation

The app uses a four-tab bottom navigation bar:

| Tab | Description |
|---|---|
| **Recipes** | All recipes in a card grid. Tap the search icon to filter. |
| **Categories** | Browse by category. Tap a category to see its recipes. |
| **Planner** | Weekly meal planner. Assign recipes to Breakfast / Lunch / Dinner slots. |
| **Shopping** | Shopping list auto-generated from this week's meal plan. |

## Recipe actions

| Action | How |
|---|---|
| View | Tap any recipe card |
| Edit | Tap the pencil icon on the recipe detail screen |
| Delete | Tap **⋮ → Delete recipe** on the recipe detail screen |
| Import from URL | Tap **+** then the link icon in the recipe editor |
| Adjust servings | Use +/− on the detail screen; quantities scale automatically |
| Convert units | Tap the ruler icon to convert imperial measurements |

## Meal Plan Sync

The meal plan is stored as `Cookbook/meal_plan.json` in your Nextcloud Files (via WebDAV). Both this app and the desktop app read and write this file, so changes made on one device are reflected on the other.

## License

This project is licensed under the **GNU General Public License v3.0**. See [LICENSE](LICENSE) for details.
