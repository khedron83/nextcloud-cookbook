package com.cubicserenity.nextcloudcookbook.di

import android.content.Context
import androidx.room.Room
import com.cubicserenity.nextcloudcookbook.data.local.AppDatabase
import com.cubicserenity.nextcloudcookbook.data.local.dao.MealPlanDao
import com.cubicserenity.nextcloudcookbook.data.local.dao.RecipeDetailDao
import com.cubicserenity.nextcloudcookbook.data.local.dao.RecipeSummaryDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase =
        Room.databaseBuilder(context, AppDatabase::class.java, "cookbook.db").build()

    @Provides fun provideRecipeSummaryDao(db: AppDatabase): RecipeSummaryDao = db.recipeSummaryDao()
    @Provides fun provideRecipeDetailDao(db: AppDatabase): RecipeDetailDao = db.recipeDetailDao()
    @Provides fun provideMealPlanDao(db: AppDatabase): MealPlanDao = db.mealPlanDao()
}
