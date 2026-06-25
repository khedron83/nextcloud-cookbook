use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RecipeSummary {
    pub recipe_id: i64,
    pub name: String,
    pub keywords: String,
    pub date_modified: String,
    pub category: String,
}

impl RecipeSummary {
    pub fn from_value(v: &Value) -> Self {
        Self {
            recipe_id: v["recipe_id"].as_i64()
                .or_else(|| v["id"].as_i64())
                .unwrap_or(0),
            name: sv(v, "name"),
            keywords: sv(v, "keywords"),
            date_modified: sv(v, "date_modified"),
            category: sv(v, "category"),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Nutrition {
    pub calories: Option<String>,
    pub carbohydrate_content: Option<String>,
    pub fat_content: Option<String>,
    pub fiber_content: Option<String>,
    pub protein_content: Option<String>,
    pub saturated_fat_content: Option<String>,
    pub serving_size: Option<String>,
    pub sodium_content: Option<String>,
    pub sugar_content: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Recipe {
    pub id: Option<i64>,
    pub name: String,
    pub description: String,
    pub url: String,
    pub image: String,
    pub recipe_yield: String,
    pub prep_time: String,
    pub cook_time: String,
    pub total_time: String,
    pub recipe_category: String,
    pub keywords: String,
    pub recipe_ingredient: Vec<String>,
    pub recipe_instructions: Vec<String>,
    pub tools: Vec<String>,
    pub nutrition: Option<Nutrition>,
    pub date_created: String,
    pub date_modified: String,
    pub rating: Option<i32>,
}

impl Recipe {
    pub fn from_value(v: &Value) -> Result<Self, String> {
        Ok(Self {
            id: v["id"].as_i64().or_else(|| v["recipe_id"].as_i64()),
            name: sv(v, "name"),
            description: sv(v, "description"),
            url: sv(v, "url"),
            image: image_str(v),
            recipe_yield: sv2(v, "recipeYield", "recipe_yield"),
            prep_time: sv2(v, "prepTime", "prep_time"),
            cook_time: sv2(v, "cookTime", "cook_time"),
            total_time: sv2(v, "totalTime", "total_time"),
            recipe_category: sv2(v, "recipeCategory", "recipe_category"),
            keywords: sv(v, "keywords"),
            recipe_ingredient: str_arr(v, "recipeIngredient"),
            recipe_instructions: parse_instructions(v),
            tools: str_arr(v, "tool"),
            nutrition: parse_nutrition(v.get("nutrition")),
            date_created: sv2(v, "dateCreated", "date_created"),
            date_modified: sv2(v, "dateModified", "date_modified"),
            rating: v["rating"].as_i64().map(|r| r as i32),
        })
    }

    pub fn to_api_value(&self) -> Value {
        serde_json::json!({
            "@context": "http://schema.org",
            "@type": "Recipe",
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "recipeYield": self.recipe_yield,
            "prepTime": self.prep_time,
            "cookTime": self.cook_time,
            "totalTime": self.total_time,
            "recipeCategory": self.recipe_category,
            "keywords": self.keywords,
            "recipeIngredient": self.recipe_ingredient,
            "recipeInstructions": self.recipe_instructions.iter().map(|s| {
                serde_json::json!({"@type": "HowToStep", "text": s})
            }).collect::<Vec<_>>(),
            "tool": self.tools,
            "nutrition": self.nutrition.as_ref().map(|n| serde_json::json!({
                "@type": "NutritionInformation",
                "calories": n.calories,
                "carbohydrateContent": n.carbohydrate_content,
                "fatContent": n.fat_content,
                "fiberContent": n.fiber_content,
                "proteinContent": n.protein_content,
                "saturatedFatContent": n.saturated_fat_content,
                "servingSize": n.serving_size,
                "sodiumContent": n.sodium_content,
                "sugarContent": n.sugar_content,
            })),
            "rating": self.rating,
        })
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MealEntry {
    pub date: String,
    pub meal: String,
    #[serde(rename = "recipeId")]
    pub recipe_id: i64,
    #[serde(rename = "recipeName")]
    pub recipe_name: String,
}

fn sv(v: &Value, key: &str) -> String {
    v[key].as_str().unwrap_or("").to_string()
}

fn sv2(v: &Value, k1: &str, k2: &str) -> String {
    v[k1].as_str().or_else(|| v[k2].as_str()).unwrap_or("").to_string()
}

fn image_str(v: &Value) -> String {
    match &v["image"] {
        Value::String(s) => s.clone(),
        Value::Array(a) => a.first().and_then(|i| i.as_str()).unwrap_or("").to_string(),
        Value::Object(o) => o.get("url").and_then(|u| u.as_str()).unwrap_or("").to_string(),
        _ => String::new(),
    }
}

fn str_arr(v: &Value, key: &str) -> Vec<String> {
    v[key].as_array().map(|a| {
        a.iter()
            .filter_map(|i| i.as_str())
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .collect()
    }).unwrap_or_default()
}

fn parse_instructions(v: &Value) -> Vec<String> {
    let mut steps = Vec::new();
    let Some(arr) = v["recipeInstructions"].as_array() else { return steps };
    for item in arr {
        match item {
            Value::String(s) if !s.trim().is_empty() => steps.push(s.trim().to_string()),
            Value::Object(_) => {
                if item["@type"].as_str() == Some("HowToSection") {
                    if let Some(sub) = item["itemListElement"].as_array() {
                        for s in sub {
                            let t = s["text"].as_str().or_else(|| s.as_str()).unwrap_or("").trim();
                            if !t.is_empty() { steps.push(t.to_string()); }
                        }
                    }
                } else {
                    let t = item["text"].as_str().unwrap_or("").trim();
                    if !t.is_empty() { steps.push(t.to_string()); }
                }
            }
            _ => {}
        }
    }
    steps
}

fn parse_nutrition(v: Option<&Value>) -> Option<Nutrition> {
    let v = v?;
    Some(Nutrition {
        calories: os(v, "calories"),
        carbohydrate_content: os(v, "carbohydrateContent"),
        fat_content: os(v, "fatContent"),
        fiber_content: os(v, "fiberContent"),
        protein_content: os(v, "proteinContent"),
        saturated_fat_content: os(v, "saturatedFatContent"),
        serving_size: os(v, "servingSize"),
        sodium_content: os(v, "sodiumContent"),
        sugar_content: os(v, "sugarContent"),
    })
}

fn os(v: &Value, key: &str) -> Option<String> {
    v[key].as_str().filter(|s| !s.is_empty()).map(|s| s.to_string())
}
