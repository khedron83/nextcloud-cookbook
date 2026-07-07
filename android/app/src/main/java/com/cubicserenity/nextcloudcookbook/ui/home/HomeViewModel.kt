package com.cubicserenity.nextcloudcookbook.ui.home

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

data class HomeUiState(
    val allRecipes: List<RecipeSummary> = emptyList(),
    val categories: List<String> = emptyList(),
    val selectedCategory: String? = null,
    val searchQuery: String = "",
    val keywordFilter: String? = null,
    val isLoading: Boolean = false,
    val isOffline: Boolean = false,
    val error: String? = null,
    val serverUrl: String = "",
)

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val repository: RecipeRepository,
    private val prefs: PreferencesRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            prefs.serverConfig.collect { config ->
                _state.update { it.copy(serverUrl = config.serverUrl) }
            }
        }
        viewModelScope.launch {
            repository.cachedSummaries.collect { recipes ->
                _state.update { it.copy(allRecipes = recipes) }
            }
        }
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            try {
                repository.refreshRecipes()
                val categories = repository.getCategories()
                _state.update { it.copy(isLoading = false, isOffline = false, categories = categories) }
            } catch (e: Exception) {
                _state.update { it.copy(isLoading = false, isOffline = true, error = e.javaClass.simpleName + ": " + e.message) }
            }
        }
    }

    fun selectCategory(category: String?) {
        _state.update { it.copy(selectedCategory = category, keywordFilter = null) }
    }

    fun setSearch(query: String) {
        _state.update { it.copy(searchQuery = query) }
    }

    fun setKeywordFilter(keyword: String?) {
        _state.update { it.copy(keywordFilter = keyword, selectedCategory = null) }
    }

    fun reindex() {
        viewModelScope.launch {
            try { repository.reindex() } catch (_: Exception) {}
        }
    }

    fun renameCategory(oldName: String, newName: String) {
        viewModelScope.launch {
            try {
                repository.renameCategory(oldName, newName)
                refresh()
            } catch (e: Exception) {
                _state.update { it.copy(error = e.message) }
            }
        }
    }

    fun getFilteredRecipes(state: HomeUiState): List<RecipeSummary> {
        var list = state.allRecipes
        state.selectedCategory?.let { cat ->
            list = list.filter { it.category.equals(cat, ignoreCase = true) }
        }
        state.keywordFilter?.let { kw ->
            list = list.filter { kw.lowercase() in it.keywords.lowercase() }
        }
        val q = state.searchQuery.trim()
        if (q.isNotBlank()) {
            list = list.filter { q.lowercase() in it.name.lowercase() }
        }
        return list
    }
}
