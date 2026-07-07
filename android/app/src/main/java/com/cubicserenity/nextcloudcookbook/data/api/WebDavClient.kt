package com.cubicserenity.nextcloudcookbook.data.api

import com.cubicserenity.nextcloudcookbook.data.preferences.PreferencesRepository
import com.cubicserenity.nextcloudcookbook.di.NetworkModule
import com.cubicserenity.nextcloudcookbook.domain.model.MealPlanEntry
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import javax.inject.Inject
import javax.inject.Singleton

private const val MEAL_PLAN_PATH = "Cookbook/meal_plan.json"

data class MealPlanData(
    val version: Int = 1,
    val entries: List<MealPlanEntryJson> = emptyList(),
)

data class MealPlanEntryJson(
    val date: String,
    val meal: String,
    @SerializedName("recipeId") val recipeId: Int,
    val recipeName: String,
)

@Singleton
class WebDavClient @Inject constructor(
    private val prefs: PreferencesRepository,
    private val gson: Gson,
) {
    private fun fileUrl(serverUrl: String, username: String) =
        "${serverUrl.trimEnd('/')}/remote.php/dav/files/$username/$MEAL_PLAN_PATH"

    private fun dirUrl(serverUrl: String, username: String) =
        "${serverUrl.trimEnd('/')}/remote.php/dav/files/$username/Cookbook/"

    suspend fun loadMealPlan(): List<MealPlanEntry> = withContext(Dispatchers.IO) {
        val config = prefs.serverConfig.first()
        if (config.serverUrl.isBlank() || config.username.isBlank()) return@withContext emptyList()
        try {
            val client = NetworkModule.buildClient(config)
            val response = client.newCall(
                Request.Builder().url(fileUrl(config.serverUrl, config.username)).get().build()
            ).execute()
            if (!response.isSuccessful) return@withContext emptyList()
            val body = response.body?.string() ?: return@withContext emptyList()
            val data = gson.fromJson(body, MealPlanData::class.java)
            data.entries.map { MealPlanEntry(it.date, it.meal, it.recipeId, it.recipeName) }
        } catch (e: Exception) {
            emptyList()
        }
    }

    suspend fun saveMealPlan(entries: List<MealPlanEntry>) = withContext(Dispatchers.IO) {
        val config = prefs.serverConfig.first()
        if (config.serverUrl.isBlank() || config.username.isBlank()) return@withContext
        try {
            val client = NetworkModule.buildClient(config)
            // Ensure Cookbook/ directory exists (ignore errors — may already exist)
            runCatching {
                client.newCall(
                    Request.Builder()
                        .url(dirUrl(config.serverUrl, config.username))
                        .method("MKCOL", ByteArray(0).toRequestBody(null))
                        .build()
                ).execute().close()
            }
            val json = gson.toJson(
                MealPlanData(entries = entries.map { MealPlanEntryJson(it.date, it.meal, it.recipeId, it.recipeName) })
            )
            client.newCall(
                Request.Builder()
                    .url(fileUrl(config.serverUrl, config.username))
                    .put(json.toRequestBody("application/json".toMediaType()))
                    .build()
            ).execute().close()
        } catch (_: Exception) {}
    }
}
