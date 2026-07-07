package com.cubicserenity.nextcloudcookbook.domain.model

import com.cubicserenity.nextcloudcookbook.data.api.NutritionDto
import com.cubicserenity.nextcloudcookbook.data.api.RecipeDto
import com.cubicserenity.nextcloudcookbook.data.api.RecipeSummaryDto

data class RecipeSummary(
    val id: Int,
    val name: String,
    val keywords: String,
    val dateModified: String,
    val category: String,
)

data class Nutrition(
    val calories: String = "",
    val carbohydrateContent: String = "",
    val cholesterolContent: String = "",
    val fatContent: String = "",
    val fiberContent: String = "",
    val proteinContent: String = "",
    val saturatedFatContent: String = "",
    val servingSize: String = "",
    val sodiumContent: String = "",
    val sugarContent: String = "",
    val transFatContent: String = "",
    val unsaturatedFatContent: String = "",
)

data class Recipe(
    val id: Int? = null,
    val name: String = "",
    val description: String = "",
    val url: String = "",
    val image: String = "",
    val recipeYield: String = "",
    val prepTime: String = "",
    val cookTime: String = "",
    val totalTime: String = "",
    val recipeCategory: String = "",
    val keywords: String = "",
    val recipeIngredient: List<String> = emptyList(),
    val recipeInstructions: List<String> = emptyList(),
    val tools: List<String> = emptyList(),
    val nutrition: Nutrition? = null,
    val dateCreated: String = "",
    val dateModified: String = "",
    val rating: Int = 0,
)

fun RecipeSummaryDto.toDomain() = RecipeSummary(
    id = resolvedId,
    name = name ?: "",
    keywords = keywords ?: "",
    dateModified = dateModified ?: "",
    category = category ?: "",
)

fun RecipeDto.toDomain(): Recipe {
    val instructions = recipeInstructions?.mapNotNull { item ->
        when (item) {
            is String -> item.takeIf { it.isNotBlank() }
            is Map<*, *> -> item["text"]?.toString()?.takeIf { it.isNotBlank() }
            else -> null
        }
    } ?: emptyList()
    val toolList: List<String> = when (val t = tool) {
        is List<*> -> t.filterIsInstance<String>()
        is String -> t.split(",").map { it.trim() }.filter { it.isNotBlank() }
        else -> emptyList()
    }
    val rating = aggregateRating?.ratingValue
        ?.toFloatOrNull()
        ?.toInt()
        ?.coerceIn(0, 5) ?: 0

    return Recipe(
        id = id,
        name = name ?: "",
        description = description ?: "",
        url = url ?: "",
        image = image ?: "",
        recipeYield = recipeYield ?: "",
        prepTime = prepTime ?: "",
        cookTime = cookTime ?: "",
        totalTime = totalTime ?: "",
        recipeCategory = recipeCategory ?: "",
        keywords = keywords ?: "",
        recipeIngredient = recipeIngredient?.filterNotNull() ?: emptyList(),
        recipeInstructions = instructions,
        tools = toolList,
        nutrition = nutrition?.toDomain(),
        dateCreated = dateCreated ?: "",
        dateModified = dateModified ?: "",
        rating = rating,
    )
}

fun NutritionDto.toDomain() = Nutrition(
    calories = calories ?: "",
    carbohydrateContent = carbohydrateContent ?: "",
    cholesterolContent = cholesterolContent ?: "",
    fatContent = fatContent ?: "",
    fiberContent = fiberContent ?: "",
    proteinContent = proteinContent ?: "",
    saturatedFatContent = saturatedFatContent ?: "",
    servingSize = servingSize ?: "",
    sodiumContent = sodiumContent ?: "",
    sugarContent = sugarContent ?: "",
    transFatContent = transFatContent ?: "",
    unsaturatedFatContent = unsaturatedFatContent ?: "",
)

fun Recipe.toApiMap(): Map<String, Any?> = buildMap {
    put("@context", "http://schema.org")
    put("@type", "Recipe")
    if (id != null) put("id", id)
    put("name", name)
    put("description", description)
    put("url", url)
    put("image", image)
    put("recipeYield", recipeYield)
    put("prepTime", prepTime)
    put("cookTime", cookTime)
    put("totalTime", totalTime)
    put("recipeCategory", recipeCategory)
    put("keywords", keywords)
    put("recipeIngredient", recipeIngredient)
    put("recipeInstructions", recipeInstructions.map { mapOf("@type" to "HowToStep", "text" to it) })
    put("tool", tools)
    if (rating > 0) put("aggregateRating", mapOf(
        "@type" to "AggregateRating",
        "ratingValue" to rating.toString(),
        "ratingCount" to "1",
    ))
    if (nutrition != null) {
        put("nutrition", mapOf(
            "@type" to "NutritionInformation",
            "calories" to nutrition.calories,
            "carbohydrateContent" to nutrition.carbohydrateContent,
            "cholesterolContent" to nutrition.cholesterolContent,
            "fatContent" to nutrition.fatContent,
            "fiberContent" to nutrition.fiberContent,
            "proteinContent" to nutrition.proteinContent,
            "saturatedFatContent" to nutrition.saturatedFatContent,
            "servingSize" to nutrition.servingSize,
            "sodiumContent" to nutrition.sodiumContent,
            "sugarContent" to nutrition.sugarContent,
            "transFatContent" to nutrition.transFatContent,
            "unsaturatedFatContent" to nutrition.unsaturatedFatContent,
        ))
    }
}
