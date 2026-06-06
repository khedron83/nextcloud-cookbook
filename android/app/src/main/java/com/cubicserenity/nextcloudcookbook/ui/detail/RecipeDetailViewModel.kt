package com.cubicserenity.nextcloudcookbook.ui.detail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cubicserenity.nextcloudcookbook.data.repository.RecipeRepository
import com.cubicserenity.nextcloudcookbook.domain.model.Recipe
import com.cubicserenity.nextcloudcookbook.util.convertIngredient
import com.cubicserenity.nextcloudcookbook.util.convertInstruction
import com.cubicserenity.nextcloudcookbook.util.scaleIngredient
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject
import kotlin.math.abs

data class RecipeDetailUiState(
    val recipe: Recipe? = null,
    val isLoading: Boolean = false,
    val error: String? = null,
    val servings: Int = 1,
    val originalServings: Int = 1,
    val metricMode: Boolean = false,
    val keepScreenOn: Boolean = true,
)

@HiltViewModel
class RecipeDetailViewModel @Inject constructor(
    private val repository: RecipeRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(RecipeDetailUiState())
    val state: StateFlow<RecipeDetailUiState> = _state.asStateFlow()

    fun load(id: Int) {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            try {
                val recipe = repository.getRecipe(id)
                val origServings = parseServings(recipe.recipeYield)
                _state.update {
                    it.copy(
                        recipe = recipe,
                        isLoading = false,
                        servings = origServings,
                        originalServings = origServings,
                    )
                }
            } catch (e: Exception) {
                _state.update { it.copy(isLoading = false, error = e.message) }
            }
        }
    }

    fun setServings(value: Int) {
        _state.update { it.copy(servings = value.coerceIn(1, 999)) }
    }

    fun toggleMetric() {
        _state.update { it.copy(metricMode = !it.metricMode) }
    }

    fun toggleKeepScreenOn() {
        _state.update { it.copy(keepScreenOn = !it.keepScreenOn) }
    }

    fun deleteRecipe(onDeleted: () -> Unit) {
        val id = _state.value.recipe?.id ?: return
        viewModelScope.launch {
            try {
                repository.deleteRecipe(id)
                onDeleted()
            } catch (e: Exception) {
                _state.update { it.copy(error = e.message) }
            }
        }
    }

    fun getDisplayIngredients(): List<String> {
        val s = _state.value
        val recipe = s.recipe ?: return emptyList()
        val factor = if (s.originalServings > 0) s.servings.toDouble() / s.originalServings else 1.0
        return recipe.recipeIngredient.map { ing ->
            var text = if (abs(factor - 1.0) > 0.001) scaleIngredient(ing, factor) else ing
            if (s.metricMode) text = convertIngredient(text)
            text
        }
    }

    fun getDisplayInstructions(): List<String> {
        val s = _state.value
        val recipe = s.recipe ?: return emptyList()
        return if (s.metricMode) recipe.recipeInstructions.map { convertInstruction(it) }
        else recipe.recipeInstructions
    }

    private fun parseServings(yield: String): Int {
        if (yield.isBlank()) return 1
        return Regex("\\d+").find(yield)?.value?.toIntOrNull() ?: 1
    }
}
