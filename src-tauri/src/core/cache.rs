use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use crate::core::models::{MealEntry, Recipe, RecipeSummary};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "op")]
pub enum PendingOp {
    Create { recipe: Recipe },
    Update { id: i64, recipe: Recipe },
    Delete { id: i64 },
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Cache {
    pub recipes: Vec<RecipeSummary>,
    pub categories: Vec<String>,
    pub details: HashMap<String, Recipe>,
    pub meal_plan: Vec<MealEntry>,
    pub pending: Vec<PendingOp>,
}

impl Cache {
    pub fn load(path: &Path) -> Self {
        std::fs::read_to_string(path)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_default()
    }

    pub fn save(&self, path: &Path) -> Result<(), String> {
        if let Some(p) = path.parent() {
            std::fs::create_dir_all(p).map_err(|e| e.to_string())?;
        }
        std::fs::write(path, serde_json::to_string(self).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())
    }

    pub fn push_op(&mut self, op: PendingOp) {
        match &op {
            PendingOp::Delete { id } => {
                let id = *id;
                self.pending.retain(|o| match o {
                    PendingOp::Create { recipe } => recipe.id != Some(id),
                    PendingOp::Update { id: oid, .. } => *oid != id,
                    PendingOp::Delete { id: oid } => *oid != id,
                });
                self.pending.push(op);
            }
            PendingOp::Update { id, .. } => {
                let id = *id;
                if let Some(pos) = self.pending.iter().position(|o| {
                    matches!(o, PendingOp::Update { id: oid, .. } if *oid == id)
                }) {
                    self.pending[pos] = op;
                } else {
                    self.pending.push(op);
                }
            }
            PendingOp::Create { .. } => self.pending.push(op),
        }
    }
}

pub fn cache_file(data_dir: &Path) -> PathBuf {
    data_dir.join("cache.json")
}
