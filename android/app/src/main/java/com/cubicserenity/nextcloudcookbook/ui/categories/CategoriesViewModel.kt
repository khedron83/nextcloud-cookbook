package com.cubicserenity.nextcloudcookbook.ui.categories

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cubicserenity.nextcloudcookbook.data.preferences.PreferencesRepository
import com.cubicserenity.nextcloudcookbook.data.repository.RecipeRepository
import com.cubicserenity.nextcloudcookbook.domain.model.RecipeSummary
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

private const val UNCATEGORISED = "Uncategorised"

data class CategoriesUiState(
    val categories: List<Pair<String, Int>> = emptyList(),
    val selectedCategory: String? = null,
    val categoryRecipes: List<RecipeSummary> = emptyList(),
    val isLoading: Boolean = false,
    val serverUrl: String = "",
)

@HiltViewModel
class CategoriesViewModel @Inject constructor(
    private val repository: RecipeRepository,
    private val prefs: PreferencesRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(CategoriesUiState())
    val state: StateFlow<CategoriesUiState> = _state.asStateFlow()

    private var allRecipes: List<RecipeSummary> = emptyList()

    init {
        viewModelScope.launch {
            prefs.serverConfig.collect { config ->
                _state.update { it.copy(serverUrl = config.serverUrl) }
            }
        }
        viewModelScope.launch {
            repository.cachedSummaries.collect { recipes -> allRecipes = recipes }
        }
        loadCategories()
    }

    fun loadCategories() {
        viewModelScope.launch {
            try {
                val cats = repository.getCategoriesWithCounts()
                _state.update { it.copy(categories = cats) }
            } catch (_: Exception) {}
        }
    }

    fun selectCategory(category: String?) {
        _state.update { it.copy(selectedCategory = category, categoryRecipes = emptyList()) }
        if (category == null) return
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true) }
            try {
                val recipes = if (category == UNCATEGORISED)
                    loadUncategorised()
                else
                    repository.getCategoryRecipes(category)
                _state.update { it.copy(isLoading = false, categoryRecipes = recipes) }
            } catch (e: Exception) {
                _state.update { it.copy(isLoading = false) }
            }
        }
    }

    private suspend fun loadUncategorised(): List<RecipeSummary> {
        val namedCategories = _state.value.categories
            .map { it.first }
            .filter { it != UNCATEGORISED }
        val categorisedIds = mutableSetOf<Int>()
        for (cat in namedCategories) {
            runCatching { repository.getCategoryRecipes(cat) }
                .getOrNull()
                ?.forEach { categorisedIds.add(it.id) }
        }
        return allRecipes.filter { it.id !in categorisedIds }
    }

    fun renameCategory(oldName: String, newName: String) {
        viewModelScope.launch {
            runCatching { repository.renameCategory(oldName, newName) }
        }
    }
}
