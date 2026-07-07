package com.cubicserenity.nextcloudcookbook.data.api

import com.google.gson.annotations.SerializedName

data class RecipeSummaryDto(
    @SerializedName("recipe_id") val recipeId: Int? = null,
    @SerializedName("id") val id: Int? = null,
    val name: String? = null,
    val keywords: String? = null,
    @SerializedName("dateModified") val dateModified: String? = null,
    @SerializedName("recipeCategory") val category: String? = null,
) {
    val resolvedId: Int get() = recipeId ?: id ?: 0
}

data class NutritionDto(
    val calories: String? = null,
    val carbohydrateContent: String? = null,
    val cholesterolContent: String? = null,
    val fatContent: String? = null,
    val fiberContent: String? = null,
    val proteinContent: String? = null,
    val saturatedFatContent: String? = null,
    val servingSize: String? = null,
    val sodiumContent: String? = null,
    val sugarContent: String? = null,
    val transFatContent: String? = null,
    val unsaturatedFatContent: String? = null,
)

data class AggregateRatingDto(
    val ratingValue: String? = null,
    val ratingCount: String? = null,
)

data class RecipeDto(
    val id: Int? = null,
    val name: String? = null,
    val description: String? = null,
    val url: String? = null,
    val image: String? = null,
    val recipeYield: String? = null,
    val prepTime: String? = null,
    val cookTime: String? = null,
    val totalTime: String? = null,
    val recipeCategory: String? = null,
    val keywords: String? = null,
    val recipeIngredient: List<String?>? = null,
    val recipeInstructions: List<Any>? = null,
    val tool: Any? = null,
    val nutrition: NutritionDto? = null,
    val dateCreated: String? = null,
    val dateModified: String? = null,
    val aggregateRating: AggregateRatingDto? = null,
)

data class CategoryDto(
    val name: String? = null,
    @SerializedName("recipe_count") val recipeCount: Int? = null,
)

data class ApiVersionDto(
    val epoch: Int? = null,
    val major: Int? = null,
    val minor: Int? = null,
)

data class ImportRequestBody(val url: String)
data class RenameCategoryBody(val name: String)
