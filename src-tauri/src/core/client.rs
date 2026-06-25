use reqwest::{Client, ClientBuilder, Method, StatusCode};
use serde_json::Value;
use crate::core::models::{MealEntry, Recipe, RecipeSummary};

pub struct CookbookClient {
    client: Client,
    base: String,
    username: String,
    password: String,
}

impl CookbookClient {
    pub fn new(base_url: &str, username: &str, password: &str, verify_ssl: bool) -> Result<Self, String> {
        let client = ClientBuilder::new()
            .danger_accept_invalid_certs(!verify_ssl)
            .build()
            .map_err(|e| e.to_string())?;
        Ok(Self {
            client,
            base: base_url.trim_end_matches('/').to_string(),
            username: username.to_string(),
            password: password.to_string(),
        })
    }

    fn api(&self, path: &str) -> String {
        format!("{}/index.php/apps/cookbook/api/v1{}", self.base, path)
    }

    fn dav(&self, path: &str) -> String {
        format!("{}/remote.php/dav/files/{}/{}", self.base, self.username, path)
    }

    fn req(&self, method: Method, url: &str) -> reqwest::RequestBuilder {
        self.client.request(method, url)
            .basic_auth(&self.username, Some(&self.password))
            .header("OCS-APIREQUEST", "true")
    }

    pub async fn version(&self) -> Result<String, String> {
        let v: Value = self.req(Method::GET, &self.api("/version"))
            .send().await.map_err(|e| e.to_string())?
            .json().await.map_err(|e| e.to_string())?;
        Ok(v["cookbook_version"].as_str().unwrap_or("ok").to_string())
    }

    pub async fn get_recipes(&self) -> Result<Vec<RecipeSummary>, String> {
        let arr: Vec<Value> = self.req(Method::GET, &self.api("/recipes"))
            .send().await.map_err(|e| e.to_string())?
            .json().await.map_err(|e| e.to_string())?;
        Ok(arr.iter().map(RecipeSummary::from_value).collect())
    }

    pub async fn get_recipe(&self, id: i64) -> Result<Recipe, String> {
        let v: Value = self.req(Method::GET, &self.api(&format!("/recipes/{}", id)))
            .send().await.map_err(|e| e.to_string())?
            .json().await.map_err(|e| e.to_string())?;
        Recipe::from_value(&v)
    }

    pub async fn get_recipe_image(&self, id: i64, thumb: bool) -> Result<Vec<u8>, String> {
        let url = if thumb {
            self.api(&format!("/recipes/{}/image?size=thumb", id))
        } else {
            self.api(&format!("/recipes/{}/image", id))
        };
        let resp = self.req(Method::GET, &url)
            .send().await.map_err(|e| e.to_string())?;
        if !resp.status().is_success() {
            return Err(format!("Image not found ({})", resp.status()));
        }
        resp.bytes().await.map(|b| b.to_vec()).map_err(|e| e.to_string())
    }

    pub async fn create_recipe(&self, recipe: &Recipe) -> Result<Recipe, String> {
        let v: Value = self.req(Method::POST, &self.api("/recipes"))
            .json(&recipe.to_api_value())
            .send().await.map_err(|e| e.to_string())?
            .json().await.map_err(|e| e.to_string())?;
        Recipe::from_value(&v)
    }

    pub async fn update_recipe(&self, id: i64, recipe: &Recipe) -> Result<Recipe, String> {
        let v: Value = self.req(Method::PUT, &self.api(&format!("/recipes/{}", id)))
            .json(&recipe.to_api_value())
            .send().await.map_err(|e| e.to_string())?
            .json().await.map_err(|e| e.to_string())?;
        Recipe::from_value(&v)
    }

    pub async fn delete_recipe(&self, id: i64) -> Result<(), String> {
        self.req(Method::DELETE, &self.api(&format!("/recipes/{}", id)))
            .send().await.map_err(|e| e.to_string())?;
        Ok(())
    }

    pub async fn import_recipe(&self, url: &str) -> Result<Recipe, String> {
        let resp = self.req(Method::POST, &self.api("/import"))
            .json(&serde_json::json!({"url": url}))
            .send().await.map_err(|e| e.to_string())?;
        if resp.status().is_success() {
            let v: Value = resp.json().await.map_err(|e| e.to_string())?;
            Recipe::from_value(&v)
        } else {
            scrape_json_ld(url).await
        }
    }

    pub async fn get_categories(&self) -> Result<Vec<String>, String> {
        let arr: Vec<Value> = self.req(Method::GET, &self.api("/categories"))
            .send().await.map_err(|e| e.to_string())?
            .json().await.map_err(|e| e.to_string())?;
        Ok(arr.iter()
            .filter_map(|v| v["name"].as_str().filter(|s| !s.is_empty()).map(|s| s.to_string()))
            .collect())
    }

    pub async fn reindex(&self) -> Result<(), String> {
        self.req(Method::POST, &self.api("/reindex"))
            .send().await.map_err(|e| e.to_string())?;
        Ok(())
    }

    pub async fn get_meal_plan(&self) -> Result<Vec<MealEntry>, String> {
        let resp = self.client.get(&self.dav("Cookbook/meal_plan.json"))
            .basic_auth(&self.username, Some(&self.password))
            .send().await.map_err(|e| e.to_string())?;
        if resp.status() == StatusCode::NOT_FOUND {
            return Ok(vec![]);
        }
        resp.json().await.map_err(|e| e.to_string())
    }

    pub async fn save_meal_plan(&self, entries: &[MealEntry]) -> Result<(), String> {
        let body = serde_json::to_string(entries).map_err(|e| e.to_string())?;
        self.client.put(&self.dav("Cookbook/meal_plan.json"))
            .basic_auth(&self.username, Some(&self.password))
            .header("Content-Type", "application/json")
            .body(body)
            .send().await.map_err(|e| e.to_string())?;
        Ok(())
    }
}

async fn scrape_json_ld(url: &str) -> Result<Recipe, String> {
    let client = ClientBuilder::new()
        .danger_accept_invalid_certs(true)
        .build()
        .map_err(|e| e.to_string())?;
    let html = client.get(url)
        .header("User-Agent", "Mozilla/5.0 (compatible; cookbook-importer/1.0)")
        .send().await.map_err(|e| e.to_string())?
        .text().await.map_err(|e| e.to_string())?;

    let re = regex::Regex::new(
        r#"(?s)<script[^>]+type=["']application/ld\+json["'][^>]*>(.*?)</script>"#
    ).unwrap();

    for cap in re.captures_iter(&html) {
        let text = cap[1].trim();
        if let Ok(val) = serde_json::from_str::<Value>(text) {
            if let Some(node) = find_recipe_node(&val) {
                return Recipe::from_value(node);
            }
        }
    }
    Err("No recipe data found at that URL".to_string())
}

fn find_recipe_node(val: &Value) -> Option<&Value> {
    let is_recipe = |v: &Value| {
        matches!(v["@type"].as_str(), Some("Recipe"))
        || v["@type"].as_array()
            .map(|a| a.iter().any(|t| t.as_str() == Some("Recipe")))
            .unwrap_or(false)
    };
    if is_recipe(val) { return Some(val); }
    if let Some(graph) = val["@graph"].as_array() {
        return graph.iter().find(|v| is_recipe(v));
    }
    None
}
