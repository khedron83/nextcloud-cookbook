# Nextcloud Cookbook (Android)

A Kotlin/Compose Android client for the Nextcloud Cookbook app. Mirrors the desktop app's feature set for mobile.

- **Package**: `com.cubicserenity.nextcloudcookbook`
- **Min SDK**: 26 (Android 8.0) / **Target SDK**: 36
- **Version**: 1.1.0 (versionCode 2)

## Tech Stack

| Area | Library |
|------|---------|
| UI | Jetpack Compose + Material3 |
| DI | Hilt |
| Navigation | Navigation Compose |
| Networking | Retrofit 2 + OkHttp 4 + Gson |
| WebDAV | WebDavClient (custom OkHttp) |
| Local DB | Room |
| Preferences | DataStore |
| Images | Coil 3 |
| Async | Kotlin Coroutines |

## Project Layout

```
app/src/main/java/com/cubicserenity/nextcloudcookbook/
  MainActivity.kt
  NextcloudCookbookApp.kt          Hilt Application class
  ui/
    NavGraph.kt                    Compose navigation graph
    home/                          Home screen (recipe grid)
    recipes/                       Recipe list by category
    categories/                    Category browser
    detail/                        Recipe detail view
    edit/                          Recipe create/edit
    mealplanner/                   Meal planner
    shopping/                      Shopping list
    settings/                      Server URL, credentials, SSL
    theme/Theme.kt
  data/
    api/
      CookbookApi.kt               Retrofit interface (Cookbook REST API)
      ApiModels.kt                 API data models
      NetworkClient.kt             OkHttp + Retrofit setup
      WebDavClient.kt              WebDAV meal plan sync
    local/
      AppDatabase.kt               Room database
      dao/RecipeDao.kt
      entity/RecipeEntity.kt
    repository/RecipeRepository.kt Single source of truth (network + cache)
    preferences/PreferencesDataStore.kt
  di/
    AppModule.kt
    NetworkModule.kt
  domain/model/
    Recipe.kt
    MealPlanEntry.kt
  util/
    DurationUtils.kt
    UnitConverter.kt
```

## Building

```bash
# Debug APK
./gradlew assembleDebug

# Release APK (requires signing config)
./gradlew assembleRelease
```

Build outputs land in `app/build/outputs/apk/`.

## Architecture

MVVM with a Repository layer. Each screen has a paired ViewModel injected via Hilt. The Repository mediates between the Retrofit API and Room cache. Credentials and server URL are stored in DataStore preferences.
