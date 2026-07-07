package com.cubicserenity.nextcloudcookbook.ui.shopping

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cubicserenity.nextcloudcookbook.data.repository.RecipeRepository
import com.cubicserenity.nextcloudcookbook.domain.model.MealPlanEntry
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.temporal.TemporalAdjusters
import javax.inject.Inject

private val ISO = DateTimeFormatter.ISO_LOCAL_DATE

data class ShoppingUiState(
    val weekLabel: String = "",
    val mealPlan: List<MealPlanEntry> = emptyList(),
    val ingredients: List<Pair<String, Boolean>> = emptyList(),
    val isLoading: Boolean = false,
    val missingCount: Int = 0,
)

@HiltViewModel
class ShoppingViewModel @Inject constructor(
    private val repository: RecipeRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(ShoppingUiState())
    val state: StateFlow<ShoppingUiState> = _state.asStateFlow()

    private val monday = LocalDate.now().with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY))

    init {
        val end = monday.plusDays(6)
        val label = "${monday.format(DateTimeFormatter.ofPattern("d MMM"))} – ${end.format(DateTimeFormatter.ofPattern("d MMM yyyy"))}"
        _state.update { it.copy(weekLabel = label) }

        viewModelScope.launch {
            repository.mealPlanForWeek(monday.format(ISO), end.format(ISO)).collect { entries ->
                _state.update { it.copy(mealPlan = entries) }
                buildShoppingList(entries)
            }
        }
        viewModelScope.launch {
            repository.syncMealPlanFromServer()
        }
    }

    private fun buildShoppingList(entries: List<MealPlanEntry>) {
        if (entries.isEmpty()) {
            _state.update { it.copy(ingredients = emptyList(), missingCount = 0) }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true) }
            var missing = 0
            val seen = mutableSetOf<String>()
            val all = mutableListOf<String>()
            val ids = entries.map { it.recipeId }.toSet()
            for (id in ids) {
                val ings = try { repository.getIngredients(id) } catch (_: Exception) { missing++; continue }
                for (ing in ings) {
                    val key = ing.trim().lowercase()
                    if (key !in seen) { seen.add(key); all.add(ing.trim()) }
                }
            }
            all.sort()
            val currentChecked = _state.value.ingredients.filter { it.second }.map { it.first }.toSet()
            _state.update {
                it.copy(
                    isLoading = false,
                    missingCount = missing,
                    ingredients = all.map { ing -> ing to (ing in currentChecked) },
                )
            }
        }
    }

    fun toggleItem(ingredient: String) {
        _state.update { state ->
            state.copy(ingredients = state.ingredients.map { (ing, checked) ->
                if (ing == ingredient) ing to !checked else ing to checked
            })
        }
    }

    fun refresh() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true) }
            repository.syncMealPlanFromServer()
        }
    }
}
