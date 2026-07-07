package com.cubicserenity.nextcloudcookbook.data.preferences

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

data class ServerConfig(
    val serverUrl: String = "",
    val username: String = "",
    val password: String = "",
    val ignoreSsl: Boolean = false,
)

@Singleton
class PreferencesRepository @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val urlKey = stringPreferencesKey("server_url")
    private val userKey = stringPreferencesKey("username")
    private val passKey = stringPreferencesKey("password")
    private val sslKey = booleanPreferencesKey("ignore_ssl")

    val serverConfig: Flow<ServerConfig> = context.dataStore.data.map { prefs ->
        ServerConfig(
            serverUrl = prefs[urlKey] ?: "",
            username = prefs[userKey] ?: "",
            password = prefs[passKey] ?: "",
            ignoreSsl = prefs[sslKey] ?: false,
        )
    }

    suspend fun saveServerConfig(config: ServerConfig) {
        context.dataStore.edit { prefs ->
            prefs[urlKey] = config.serverUrl
            prefs[userKey] = config.username
            prefs[passKey] = config.password
            prefs[sslKey] = config.ignoreSsl
        }
    }
}
