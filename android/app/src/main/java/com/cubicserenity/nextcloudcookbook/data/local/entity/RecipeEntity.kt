package com.cubicserenity.nextcloudcookbook.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "recipe_summaries")
data class RecipeSummaryEntity(
    @PrimaryKey val id: Int,
    val name: String,
    val keywords: String,
    val dateModified: String,
    val category: String,
)

@Entity(tableName = "recipe_details")
data class RecipeDetailEntity(
    @PrimaryKey val id: Int,
    val json: String,
)

@Entity(tableName = "meal_plan")
data class MealPlanEntity(
    @PrimaryKey val key: String,   // "date/meal"
    val recipeId: Int,
    val recipeName: String,
    val date: String,
    val meal: String,
)
