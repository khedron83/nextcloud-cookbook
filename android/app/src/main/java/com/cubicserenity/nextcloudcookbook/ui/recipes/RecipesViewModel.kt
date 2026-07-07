package com.cubicserenity.nextcloudcookbook.ui.recipes

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

data class RecipesUiState(
    val all: List<RecipeSummary> = emptyList(),
    val query: String = "",
    val serverUrl: String = "",
    val isLoading: Boolean = false,
    val isOffline: Boolean = false,
    val error: String? = null,
    val isUnconfigured: Boolean = false,
) {
    val filtered: List<RecipeSummary> get() = if (query.isBlank()) all
        else all.filter { query.lowercase() in it.name.lowercase() || query.lowercase() in it.keywords.lowercase() }
}

@HiltViewModel
class RecipesViewModel @Inject constructor(
    private val repository: RecipeRepository,
    private val prefs: PreferencesRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(RecipesUiState())
    val state: StateFlow<RecipesUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            prefs.serverConfig.collect { config ->
                val unconfigured = config.serverUrl.isBlank() || config.username.isBlank()
                _state.update { it.copy(serverUrl = config.serverUrl, isUnconfigured = unconfigured) }
                if (!unconfigured && _state.value.all.isEmpty() && !_state.value.isLoading) {
                    refresh()
                }
            }
        }
        viewModelScope.launch { repository.cachedSummaries.collect { _state.update { s -> s.copy(all = it) } } }
    }

    fun refresh() {
        if (_state.value.isUnconfigured) return
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            try {
                repository.refreshRecipes()
                _state.update { it.copy(isLoading = false, isOffline = false) }
            } catch (e: Exception) {
                _state.update { it.copy(isLoading = false, isOffline = true, error = e.javaClass.simpleName + ": " + e.message) }
            }
        }
    }

    fun setQuery(q: String) = _state.update { it.copy(query = q) }

    fun reindex() {
        viewModelScope.launch { runCatching { repository.reindex() } }
    }
}
