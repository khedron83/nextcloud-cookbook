package com.cubicserenity.nextcloudcookbook.data.repository

import com.cubicserenity.nextcloudcookbook.data.api.CookbookApi
import com.cubicserenity.nextcloudcookbook.data.api.NetworkClient
import com.cubicserenity.nextcloudcookbook.data.api.RenameCategoryBody
import com.cubicserenity.nextcloudcookbook.data.api.WebDavClient
import com.cubicserenity.nextcloudcookbook.data.local.dao.MealPlanDao
import com.cubicserenity.nextcloudcookbook.data.local.dao.RecipeDetailDao
import com.cubicserenity.nextcloudcookbook.data.local.dao.RecipeSummaryDao
import com.cubicserenity.nextcloudcookbook.data.local.entity.MealPlanEntity
import com.cubicserenity.nextcloudcookbook.data.local.entity.RecipeDetailEntity
import com.cubicserenity.nextcloudcookbook.data.local.entity.RecipeSummaryEntity
import com.cubicserenity.nextcloudcookbook.domain.model.MealPlanEntry
import com.cubicserenity.nextcloudcookbook.domain.model.Recipe
import com.cubicserenity.nextcloudcookbook.domain.model.RecipeSummary
import com.cubicserenity.nextcloudcookbook.domain.model.toDomain
import com.cubicserenity.nextcloudcookbook.domain.model.toApiMap
import com.google.gson.Gson
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class RecipeRepository @Inject constructor(
    private val network: NetworkClient,
    private val summaryDao: RecipeSummaryDao,
    private val detailDao: RecipeDetailDao,
    private val mealPlanDao: MealPlanDao,
    private val webDav: WebDavClient,
    private val gson: Gson,
) {
    val cachedSummaries: Flow<List<RecipeSummary>> =
        summaryDao.observeAll().map { list -> list.map { it.toDomain() } }

    private suspend fun api(): CookbookApi = network.api()

    suspend fun refreshRecipes(): List<RecipeSummary> {
        val dtos = api().getRecipes()
        val entities = dtos.map {
            RecipeSummaryEntity(
                id = it.resolvedId,
                name = it.name ?: "",
                keywords = it.keywords ?: "",
                dateModified = it.dateModified ?: "",
                category = it.category ?: "",
            )
        }
        summaryDao.deleteAll()
        summaryDao.upsertAll(entities)
        return dtos.map { it.toDomain() }
    }

    suspend fun getRecipe(id: Int): Recipe {
        return try {
            val dto = api().getRecipe(id)
            detailDao.upsert(RecipeDetailEntity(id, gson.toJson(dto)))
            dto.toDomain()
        } catch (e: Exception) {
            val cached = detailDao.get(id) ?: throw e
            gson.fromJson(cached.json, com.cubicserenity.nextcloudcookbook.data.api.RecipeDto::class.java).toDomain()
        }
    }

    suspend fun createRecipe(recipe: Recipe): Recipe =
        api().createRecipe(gson.toJsonTree(recipe.toApiMap()).asJsonObject).toDomain()

    suspend fun updateRecipe(recipe: Recipe): Recipe {
        val id = requireNotNull(recipe.id)
        api().updateRecipe(id, gson.toJsonTree(recipe.toApiMap()).asJsonObject)
        return api().getRecipe(id).toDomain()
    }

    suspend fun deleteRecipe(id: Int) = api().deleteRecipe(id)

    suspend fun importFromUrl(url: String): Recipe =
        api().importRecipe(url).toDomain()

    suspend fun getCategories(): List<String> =
        api().getCategories().mapNotNull { it.name }.filter { it.isNotBlank() }

    suspend fun getCategoriesWithCounts(): List<Pair<String, Int>> {
        val raw = api().getCategories()
        val named = raw
            .mapNotNull { dto -> dto.name?.takeIf { it.isNotBlank() && it != "*" }?.let { it to (dto.recipeCount ?: 0) } }
            .sortedBy { it.first }
        val uncategorisedCount = raw.find { it.name == "*" }?.recipeCount ?: 0
        return if (uncategorisedCount > 0) named + ("Uncategorised" to uncategorisedCount)
        else named
    }

    suspend fun getCategoryRecipes(category: String): List<RecipeSummary> =
        api().getCategoryRecipes(category).map { it.toDomain() }

    suspend fun renameCategory(oldName: String, newName: String) {
        api().renameCategory(oldName, RenameCategoryBody(newName))
    }

    suspend fun reindex() = api().reindex()

    fun mealPlanForWeek(from: String, to: String): Flow<List<MealPlanEntry>> =
        mealPlanDao.observeRange(from, to).map { list ->
            list.map { MealPlanEntry(it.date, it.meal, it.recipeId, it.recipeName) }
        }

    suspend fun setMealPlanEntry(entry: MealPlanEntry) {
        mealPlanDao.upsert(
            MealPlanEntity(
                key = "${entry.date}/${entry.meal}",
                recipeId = entry.recipeId,
                recipeName = entry.recipeName,
                date = entry.date,
                meal = entry.meal,
            )
        )
        pushMealPlanToServer()
    }

    suspend fun clearMealPlanEntry(date: String, meal: String) {
        mealPlanDao.delete("$date/$meal")
        pushMealPlanToServer()
    }

    suspend fun syncMealPlanFromServer() {
        val remote = webDav.loadMealPlan()
        if (remote.isEmpty()) return
        mealPlanDao.upsertAll(remote.map {
            MealPlanEntity(
                key = "${it.date}/${it.meal}",
                recipeId = it.recipeId,
                recipeName = it.recipeName,
                date = it.date,
                meal = it.meal,
            )
        })
    }

    private suspend fun pushMealPlanToServer() {
        val all = mealPlanDao.getAll().map {
            MealPlanEntry(it.date, it.meal, it.recipeId, it.recipeName)
        }
        webDav.saveMealPlan(all)
    }

    fun thumbnailUrl(id: Int): String? = network.cachedThumbnailUrl(id)

    suspend fun getIngredients(id: Int): List<String> {
        return try {
            api().getRecipe(id).recipeIngredient?.filterNotNull() ?: emptyList()
        } catch (e: Exception) {
            detailDao.get(id)?.let {
                gson.fromJson(it.json, com.cubicserenity.nextcloudcookbook.data.api.RecipeDto::class.java)
                    .recipeIngredient?.filterNotNull()
            } ?: emptyList()
        }
    }
}

private fun RecipeSummaryEntity.toDomain() = RecipeSummary(
    id = id, name = name, keywords = keywords, dateModified = dateModified, category = category,
)
