package com.cubicserenity.nextcloudcookbook.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cubicserenity.nextcloudcookbook.data.preferences.PreferencesRepository
import com.cubicserenity.nextcloudcookbook.data.preferences.ServerConfig
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SettingsUiState(
    val serverUrl: String = "",
    val username: String = "",
    val password: String = "",
    val ignoreSsl: Boolean = false,
    val isSaved: Boolean = false,
    val isTesting: Boolean = false,
    val testResult: String? = null,
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val prefs: PreferencesRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(SettingsUiState())
    val state: StateFlow<SettingsUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            prefs.serverConfig.collect { config ->
                _state.update {
                    it.copy(
                        serverUrl = config.serverUrl,
                        username = config.username,
                        password = config.password,
                        ignoreSsl = config.ignoreSsl,
                    )
                }
            }
        }
    }

    fun update(block: SettingsUiState.() -> SettingsUiState) = _state.update(block)

    fun save() {
        viewModelScope.launch {
            prefs.saveServerConfig(
                ServerConfig(
                    serverUrl = _state.value.serverUrl.trim().trimEnd('/'),
                    username = _state.value.username.trim(),
                    password = _state.value.password,
                    ignoreSsl = _state.value.ignoreSsl,
                )
            )
            _state.update { it.copy(isSaved = true, testResult = null) }
        }
    }

    fun testConnection() {
        val s = _state.value
        if (s.serverUrl.isBlank() || s.username.isBlank()) {
            _state.update { it.copy(testResult = "Enter server URL and username first.") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(isTesting = true, testResult = null) }
            try {
                val config = ServerConfig(s.serverUrl.trim().trimEnd('/'), s.username.trim(), s.password, s.ignoreSsl)
                val client = com.cubicserenity.nextcloudcookbook.di.NetworkModule.buildClient(config)
                val retrofit = retrofit2.Retrofit.Builder()
                    .baseUrl("${config.serverUrl}/index.php/apps/cookbook/")
                    .client(client)
                    .addConverterFactory(retrofit2.converter.gson.GsonConverterFactory.create())
                    .build()
                val api = retrofit.create(com.cubicserenity.nextcloudcookbook.data.api.CookbookApi::class.java)
                api.getApiVersion()
                _state.update { it.copy(isTesting = false, testResult = "Connection successful!") }
            } catch (e: Exception) {
                _state.update { it.copy(isTesting = false, testResult = "Failed: ${e.message}") }
            }
        }
    }
}
