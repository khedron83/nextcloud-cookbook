package com.cubicserenity.nextcloudcookbook.ui.mealplanner

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cubicserenity.nextcloudcookbook.data.repository.RecipeRepository
import com.cubicserenity.nextcloudcookbook.domain.model.MealPlanEntry
import com.cubicserenity.nextcloudcookbook.domain.model.RecipeSummary
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.temporal.TemporalAdjusters
import javax.inject.Inject

val MEALS = listOf("Breakfast", "Lunch", "Dinner")
private val ISO = DateTimeFormatter.ISO_LOCAL_DATE

@HiltViewModel
class MealPlannerViewModel @Inject constructor(
    private val repository: RecipeRepository,
) : ViewModel() {

    private val _weekStart = MutableStateFlow(currentWeekMonday())
    val weekStart: StateFlow<LocalDate> = _weekStart

    private val _recipes = MutableStateFlow<List<RecipeSummary>>(emptyList())
    val recipes: StateFlow<List<RecipeSummary>> = _recipes

    @OptIn(ExperimentalCoroutinesApi::class)
    val entries: StateFlow<List<MealPlanEntry>> = _weekStart.flatMapLatest { monday ->
        val from = monday.format(ISO)
        val to = monday.plusDays(6).format(ISO)
        repository.mealPlanForWeek(from, to)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    init {
        viewModelScope.launch {
            runCatching { repository.syncMealPlanFromServer() }
        }
        viewModelScope.launch {
            try { repository.refreshRecipes() } catch (_: Exception) {}
            repository.cachedSummaries.collect { _recipes.value = it }
        }
    }

    fun prevWeek() = _weekStart.update { it.minusWeeks(1) }
    fun nextWeek() = _weekStart.update { it.plusWeeks(1) }
    fun goToday() = _weekStart.update { currentWeekMonday() }

    fun assign(date: LocalDate, meal: String, recipe: RecipeSummary) {
        viewModelScope.launch {
            repository.setMealPlanEntry(MealPlanEntry(date.format(ISO), meal, recipe.id, recipe.name))
        }
    }

    fun clear(date: LocalDate, meal: String) {
        viewModelScope.launch {
            repository.clearMealPlanEntry(date.format(ISO), meal)
        }
    }

    fun thumbnailUrl(recipeId: Int): String? = repository.thumbnailUrl(recipeId)

    private fun currentWeekMonday(): LocalDate =
        LocalDate.now().with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY))
}
