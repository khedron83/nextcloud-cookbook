package com.cubicserenity.nextcloudcookbook.data.api

import com.google.gson.JsonObject
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.*

interface CookbookApi {

    @GET("api/version")
    suspend fun getApiVersion(): ApiVersionDto

    @GET("api/v1/recipes")
    suspend fun getRecipes(): List<RecipeSummaryDto>

    @GET("api/v1/recipes/{id}")
    suspend fun getRecipe(@Path("id") id: Int): RecipeDto

    @POST("api/v1/recipes")
    suspend fun createRecipe(@Body body: JsonObject): RecipeDto

    @PUT("api/v1/recipes/{id}")
    suspend fun updateRecipe(@Path("id") id: Int, @Body body: JsonObject): Response<ResponseBody>

    @DELETE("api/v1/recipes/{id}")
    suspend fun deleteRecipe(@Path("id") id: Int): Response<ResponseBody>

    @FormUrlEncoded
    @POST("api/v1/import")
    suspend fun importRecipe(@Field("url") url: String): RecipeDto

    @GET("api/v1/search/{query}")
    suspend fun searchRecipes(@Path("query") query: String): List<RecipeSummaryDto>

    @GET("api/v1/categories")
    suspend fun getCategories(): List<CategoryDto>

    @GET("api/v1/category/{name}")
    suspend fun getCategoryRecipes(@Path("name") name: String): List<RecipeSummaryDto>

    @GET("api/v1/keywords")
    suspend fun getKeywords(): List<String>

    @GET("api/v1/recipes/{id}/image")
    suspend fun getRecipeImage(
        @Path("id") id: Int,
        @Query("size") size: String = "thumb",
    ): Response<ResponseBody>

    @PUT("api/v1/category/{name}")
    suspend fun renameCategory(@Path("name") name: String, @Body body: RenameCategoryBody): Response<ResponseBody>

    @POST("api/v1/reindex")
    suspend fun reindex(): Response<ResponseBody>
}
