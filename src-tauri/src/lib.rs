mod core;

use std::collections::HashSet;
use std::sync::Mutex;
use tauri::Manager;
use core::cache::{self, Cache, PendingOp};
use core::client::CookbookClient;
use core::models::{MealEntry, Recipe, RecipeSummary};
use core::settings::{self, Settings};

struct AppState {
    cache: Mutex<Cache>,
}

fn data_dir(app: &tauri::AppHandle) -> std::path::PathBuf {
    app.path().app_data_dir().unwrap_or_default()
}

fn settings_path(app: &tauri::AppHandle) -> std::path::PathBuf {
    let dir = app.path().app_config_dir().unwrap_or_default();
    settings::settings_file(&dir)
}

fn make_client(s: &Settings) -> Result<CookbookClient, String> {
    let url = s.url.as_deref().ok_or("Server URL not configured")?;
    let username = s.username.as_deref().ok_or("Username not configured")?;
    let password = s.password.as_deref().unwrap_or("");
    CookbookClient::new(url, username, password, s.verify_ssl)
}

#[tauri::command]
async fn get_settings(app: tauri::AppHandle) -> Result<Settings, String> {
    Ok(settings::load(&settings_path(&app)))
}

#[tauri::command]
async fn save_settings(app: tauri::AppHandle, s: Settings) -> Result<(), String> {
    settings::save(&settings_path(&app), &s)
}

#[tauri::command]
async fn test_connection(url: String, username: String, password: String, verify_ssl: bool) -> Result<String, String> {
    CookbookClient::new(&url, &username, &password, verify_ssl)?
        .version().await
}

#[tauri::command]
async fn get_recipes(
    app: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
) -> Result<Vec<RecipeSummary>, String> {
    let settings = settings::load(&settings_path(&app));
    let client = make_client(&settings)?;
    let recipes = client.get_recipes().await?;
    let mut cats: Vec<String> = recipes.iter()
        .map(|r| r.category.clone())
        .filter(|c| !c.is_empty())
        .collect::<HashSet<_>>()
        .into_iter()
        .collect();
    cats.sort();
    let mut cache = state.cache.lock().unwrap();
    cache.recipes = recipes.clone();
    cache.categories = cats;
    let _ = cache.save(&cache::cache_file(&data_dir(&app)));
    Ok(recipes)
}

#[tauri::command]
async fn get_cached_recipes(state: tauri::State<'_, AppState>) -> Result<Vec<RecipeSummary>, String> {
    Ok(state.cache.lock().unwrap().recipes.clone())
}

#[tauri::command]
async fn get_recipe(
    app: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
    id: i64,
) -> Result<Recipe, String> {
    {
        let cache = state.cache.lock().unwrap();
        if let Some(r) = cache.details.get(&id.to_string()) {
            return Ok(r.clone());
        }
    }
    let settings = settings::load(&settings_path(&app));
    let recipe = make_client(&settings)?.get_recipe(id).await?;
    let mut cache = state.cache.lock().unwrap();
    cache.details.insert(id.to_string(), recipe.clone());
    let _ = cache.save(&cache::cache_file(&data_dir(&app)));
    Ok(recipe)
}

#[tauri::command]
async fn get_recipe_image(app: tauri::AppHandle, id: i64, thumb: bool) -> Result<Vec<u8>, String> {
    let settings = settings::load(&settings_path(&app));
    make_client(&settings)?.get_recipe_image(id, thumb).await
}

#[tauri::command]
async fn create_recipe(
    app: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
    recipe: Recipe,
) -> Result<Recipe, String> {
    let settings = settings::load(&settings_path(&app));
    match make_client(&settings) {
        Ok(client) => {
            let created = client.create_recipe(&recipe).await?;
            let recipes = client.get_recipes().await.unwrap_or_default();
            let mut cache = state.cache.lock().unwrap();
            cache.recipes = recipes;
            if let Some(id) = created.id {
                cache.details.insert(id.to_string(), created.clone());
            }
            let _ = cache.save(&cache::cache_file(&data_dir(&app)));
            Ok(created)
        }
        Err(_) => {
            let mut cache = state.cache.lock().unwrap();
            cache.push_op(PendingOp::Create { recipe: recipe.clone() });
            let _ = cache.save(&cache::cache_file(&data_dir(&app)));
            Ok(recipe)
        }
    }
}

#[tauri::command]
async fn update_recipe(
    app: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
    id: i64,
    recipe: Recipe,
) -> Result<Recipe, String> {
    let settings = settings::load(&settings_path(&app));
    match make_client(&settings) {
        Ok(client) => {
            let updated = client.update_recipe(id, &recipe).await?;
            let mut cache = state.cache.lock().unwrap();
            cache.details.insert(id.to_string(), updated.clone());
            if let Some(s) = cache.recipes.iter_mut().find(|r| r.recipe_id == id) {
                s.name = updated.name.clone();
                s.keywords = updated.keywords.clone();
                s.category = updated.recipe_category.clone();
            }
            let _ = cache.save(&cache::cache_file(&data_dir(&app)));
            Ok(updated)
        }
        Err(_) => {
            let mut cache = state.cache.lock().unwrap();
            cache.push_op(PendingOp::Update { id, recipe: recipe.clone() });
            cache.details.insert(id.to_string(), recipe.clone());
            let _ = cache.save(&cache::cache_file(&data_dir(&app)));
            Ok(recipe)
        }
    }
}

#[tauri::command]
async fn delete_recipe(
    app: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
    id: i64,
) -> Result<(), String> {
    let settings = settings::load(&settings_path(&app));
    match make_client(&settings) {
        Ok(client) => { client.delete_recipe(id).await?; }
        Err(_) => {
            state.cache.lock().unwrap().push_op(PendingOp::Delete { id });
        }
    }
    let mut cache = state.cache.lock().unwrap();
    cache.recipes.retain(|r| r.recipe_id != id);
    cache.details.remove(&id.to_string());
    let _ = cache.save(&cache::cache_file(&data_dir(&app)));
    Ok(())
}

#[tauri::command]
async fn import_recipe_url(app: tauri::AppHandle, url: String) -> Result<Recipe, String> {
    let settings = settings::load(&settings_path(&app));
    make_client(&settings)?.import_recipe(&url).await
}

#[tauri::command]
async fn get_categories(state: tauri::State<'_, AppState>) -> Result<Vec<String>, String> {
    Ok(state.cache.lock().unwrap().categories.clone())
}

#[tauri::command]
async fn reindex(app: tauri::AppHandle) -> Result<(), String> {
    let settings = settings::load(&settings_path(&app));
    make_client(&settings)?.reindex().await
}

#[tauri::command]
async fn get_meal_plan(
    app: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
) -> Result<Vec<MealEntry>, String> {
    let settings = settings::load(&settings_path(&app));
    match make_client(&settings) {
        Ok(client) => {
            let plan = client.get_meal_plan().await?;
            let mut cache = state.cache.lock().unwrap();
            cache.meal_plan = plan.clone();
            let _ = cache.save(&cache::cache_file(&data_dir(&app)));
            Ok(plan)
        }
        Err(_) => Ok(state.cache.lock().unwrap().meal_plan.clone()),
    }
}

#[tauri::command]
async fn save_meal_plan(
    app: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
    entries: Vec<MealEntry>,
) -> Result<(), String> {
    {
        let mut cache = state.cache.lock().unwrap();
        cache.meal_plan = entries.clone();
        let _ = cache.save(&cache::cache_file(&data_dir(&app)));
    }
    let settings = settings::load(&settings_path(&app));
    if let Ok(client) = make_client(&settings) {
        let _ = client.save_meal_plan(&entries).await;
    }
    Ok(())
}

#[tauri::command]
async fn sync_pending(
    app: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
) -> Result<u32, String> {
    let settings = settings::load(&settings_path(&app));
    let client = make_client(&settings)?;

    let pending = state.cache.lock().unwrap().pending.clone();
    let mut failed: Vec<PendingOp> = Vec::new();
    let mut synced = 0u32;

    for op in pending {
        let ok = match &op {
            PendingOp::Create { recipe } => client.create_recipe(recipe).await.is_ok(),
            PendingOp::Update { id, recipe } => client.update_recipe(*id, recipe).await.is_ok(),
            PendingOp::Delete { id } => client.delete_recipe(*id).await.is_ok(),
        };
        if ok { synced += 1; } else { failed.push(op); }
    }

    let mut cache = state.cache.lock().unwrap();
    cache.pending = failed;
    let _ = cache.save(&cache::cache_file(&data_dir(&app)));
    Ok(synced)
}

#[tauri::command]
async fn get_pending_count(state: tauri::State<'_, AppState>) -> Result<usize, String> {
    Ok(state.cache.lock().unwrap().pending.len())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let data = app.path().app_data_dir().unwrap_or_default();
            let cache = Cache::load(&cache::cache_file(&data));
            app.manage(AppState { cache: Mutex::new(cache) });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_settings,
            save_settings,
            test_connection,
            get_recipes,
            get_cached_recipes,
            get_recipe,
            get_recipe_image,
            create_recipe,
            update_recipe,
            delete_recipe,
            import_recipe_url,
            get_categories,
            reindex,
            get_meal_plan,
            save_meal_plan,
            sync_pending,
            get_pending_count,
        ])
        .run(tauri::generate_context!())
        .expect("error running nextcloud-cookbook")
}
