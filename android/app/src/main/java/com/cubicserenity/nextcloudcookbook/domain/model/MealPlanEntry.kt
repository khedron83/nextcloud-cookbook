package com.cubicserenity.nextcloudcookbook.domain.model

data class MealPlanEntry(
    val date: String,   // ISO 8601 date: "2026-06-06"
    val meal: String,   // "Breakfast" | "Lunch" | "Dinner"
    val recipeId: Int,
    val recipeName: String,
)
