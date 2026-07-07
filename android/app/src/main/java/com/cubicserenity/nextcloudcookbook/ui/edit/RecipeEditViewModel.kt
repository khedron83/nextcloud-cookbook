package com.cubicserenity.nextcloudcookbook.ui.edit

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cubicserenity.nextcloudcookbook.data.repository.RecipeRepository
import com.cubicserenity.nextcloudcookbook.domain.model.Nutrition
import com.cubicserenity.nextcloudcookbook.domain.model.Recipe
import com.cubicserenity.nextcloudcookbook.util.minutesToDuration
import com.cubicserenity.nextcloudcookbook.util.parseDurationMinutes
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class EditUiState(
    val id: Int? = null,
    val name: String = "",
    val description: String = "",
    val url: String = "",
    val image: String = "",
    val recipeYield: String = "",
    val prepTimeMin: Int = 0,
    val cookTimeMin: Int = 0,
    val totalTimeMin: Int = 0,
    val category: String = "",
    val keywords: String = "",
    val ingredients: List<String> = emptyList(),
    val instructions: List<String> = emptyList(),
    val tools: List<String> = emptyList(),
    val nutrition: Nutrition = Nutrition(),
    val rating: Int = 0,
    val isLoading: Boolean = false,
    val isSaving: Boolean = false,
    val error: String? = null,
    val importUrl: String = "",
    val isImporting: Boolean = false,
)

@HiltViewModel
class RecipeEditViewModel @Inject constructor(
    private val repository: RecipeRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(EditUiState())
    val state: StateFlow<EditUiState> = _state.asStateFlow()

    fun load(recipeId: Int?) {
        if (recipeId == null) return
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true) }
            try {
                val recipe = repository.getRecipe(recipeId)
                _state.update { _ ->
                    EditUiState(
                        id = recipe.id,
                        name = recipe.name,
                        description = recipe.description,
                        url = recipe.url,
                        image = recipe.image,
                        recipeYield = recipe.recipeYield,
                        prepTimeMin = parseDurationMinutes(recipe.prepTime),
                        cookTimeMin = parseDurationMinutes(recipe.cookTime),
                        totalTimeMin = parseDurationMinutes(recipe.totalTime),
                        category = recipe.recipeCategory,
                        keywords = recipe.keywords,
                        ingredients = recipe.recipeIngredient,
                        instructions = recipe.recipeInstructions,
                        tools = recipe.tools,
                        nutrition = recipe.nutrition ?: Nutrition(),
                        rating = recipe.rating,
                        isLoading = false,
                    )
                }
            } catch (e: Exception) {
                _state.update { it.copy(isLoading = false, error = e.message) }
            }
        }
    }

    fun update(block: EditUiState.() -> EditUiState) = _state.update(block)

    fun addIngredient() = _state.update { it.copy(ingredients = it.ingredients + "") }
    fun updateIngredient(index: Int, value: String) = _state.update {
        it.copy(ingredients = it.ingredients.toMutableList().also { l -> l[index] = value })
    }
    fun removeIngredient(index: Int) = _state.update {
        it.copy(ingredients = it.ingredients.toMutableList().also { l -> l.removeAt(index) })
    }

    fun addInstruction() = _state.update { it.copy(instructions = it.instructions + "") }
    fun updateInstruction(index: Int, value: String) = _state.update {
        it.copy(instructions = it.instructions.toMutableList().also { l -> l[index] = value })
    }
    fun removeInstruction(index: Int) = _state.update {
        it.copy(instructions = it.instructions.toMutableList().also { l -> l.removeAt(index) })
    }

    fun addTool() = _state.update { it.copy(tools = it.tools + "") }
    fun updateTool(index: Int, value: String) = _state.update {
        it.copy(tools = it.tools.toMutableList().also { l -> l[index] = value })
    }
    fun removeTool(index: Int) = _state.update {
        it.copy(tools = it.tools.toMutableList().also { l -> l.removeAt(index) })
    }

    fun importFromUrl(url: String, onSuccess: () -> Unit) {
        viewModelScope.launch {
            _state.update { it.copy(isImporting = true) }
            try {
                val recipe = repository.importFromUrl(url)
                _state.update { _ ->
                    EditUiState(
                        id = null,
                        name = recipe.name,
                        description = recipe.description,
                        url = recipe.url,
                        recipeYield = recipe.recipeYield,
                        prepTimeMin = parseDurationMinutes(recipe.prepTime),
                        cookTimeMin = parseDurationMinutes(recipe.cookTime),
                        totalTimeMin = parseDurationMinutes(recipe.totalTime),
                        category = recipe.recipeCategory,
                        keywords = recipe.keywords,
                        ingredients = recipe.recipeIngredient,
                        instructions = recipe.recipeInstructions,
                        tools = recipe.tools,
                        nutrition = recipe.nutrition ?: Nutrition(),
                        isImporting = false,
                    )
                }
                onSuccess()
            } catch (e: Exception) {
                _state.update { it.copy(isImporting = false, error = e.message) }
            }
        }
    }

    fun save(onSaved: (Int) -> Unit) {
        val s = _state.value
        if (s.name.isBlank()) { _state.update { it.copy(error = "Name is required") }; return }
        viewModelScope.launch {
            _state.update { it.copy(isSaving = true, error = null) }
            try {
                val recipe = Recipe(
                    id = s.id,
                    name = s.name.trim(),
                    description = s.description.trim(),
                    url = s.url.trim(),
                    image = s.image,
                    recipeYield = s.recipeYield.trim(),
                    prepTime = minutesToDuration(s.prepTimeMin),
                    cookTime = minutesToDuration(s.cookTimeMin),
                    totalTime = minutesToDuration(s.totalTimeMin),
                    recipeCategory = s.category.trim(),
                    keywords = s.keywords.trim(),
                    recipeIngredient = s.ingredients.filter { it.isNotBlank() },
                    recipeInstructions = s.instructions.filter { it.isNotBlank() },
                    tools = s.tools.filter { it.isNotBlank() },
                    nutrition = s.nutrition,
                    rating = s.rating,
                )
                val saved = if (s.id == null) repository.createRecipe(recipe) else repository.updateRecipe(recipe)
                _state.update { it.copy(isSaving = false) }
                onSaved(saved.id ?: 0)
            } catch (e: Exception) {
                _state.update { it.copy(isSaving = false, error = e.message) }
            }
        }
    }
}
