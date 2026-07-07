package com.cubicserenity.nextcloudcookbook.data.local.dao

import androidx.room.*
import com.cubicserenity.nextcloudcookbook.data.local.entity.MealPlanEntity
import com.cubicserenity.nextcloudcookbook.data.local.entity.RecipeDetailEntity
import com.cubicserenity.nextcloudcookbook.data.local.entity.RecipeSummaryEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface RecipeSummaryDao {
    @Query("SELECT * FROM recipe_summaries ORDER BY name ASC")
    fun observeAll(): Flow<List<RecipeSummaryEntity>>

    @Query("SELECT * FROM recipe_summaries ORDER BY name ASC")
    suspend fun getAll(): List<RecipeSummaryEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(recipes: List<RecipeSummaryEntity>)

    @Query("DELETE FROM recipe_summaries")
    suspend fun deleteAll()
}

@Dao
interface RecipeDetailDao {
    @Query("SELECT * FROM recipe_details WHERE id = :id")
    suspend fun get(id: Int): RecipeDetailEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(entity: RecipeDetailEntity)
}

@Dao
interface MealPlanDao {
    @Query("SELECT * FROM meal_plan WHERE date BETWEEN :from AND :to")
    fun observeRange(from: String, to: String): Flow<List<MealPlanEntity>>

    @Query("SELECT * FROM meal_plan")
    suspend fun getAll(): List<MealPlanEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(entry: MealPlanEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(entries: List<MealPlanEntity>)

    @Query("DELETE FROM meal_plan WHERE key = :key")
    suspend fun delete(key: String)
}
