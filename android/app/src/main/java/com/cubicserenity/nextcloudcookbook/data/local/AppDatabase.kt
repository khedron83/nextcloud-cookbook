package com.cubicserenity.nextcloudcookbook.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.cubicserenity.nextcloudcookbook.data.local.dao.MealPlanDao
import com.cubicserenity.nextcloudcookbook.data.local.dao.RecipeDetailDao
import com.cubicserenity.nextcloudcookbook.data.local.dao.RecipeSummaryDao
import com.cubicserenity.nextcloudcookbook.data.local.entity.MealPlanEntity
import com.cubicserenity.nextcloudcookbook.data.local.entity.RecipeDetailEntity
import com.cubicserenity.nextcloudcookbook.data.local.entity.RecipeSummaryEntity

@Database(
    entities = [RecipeSummaryEntity::class, RecipeDetailEntity::class, MealPlanEntity::class],
    version = 1,
    exportSchema = false,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun recipeSummaryDao(): RecipeSummaryDao
    abstract fun recipeDetailDao(): RecipeDetailDao
    abstract fun mealPlanDao(): MealPlanDao
}
