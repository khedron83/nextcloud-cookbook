package com.cubicserenity.nextcloudcookbook.data.api

import com.cubicserenity.nextcloudcookbook.data.preferences.PreferencesRepository
import com.cubicserenity.nextcloudcookbook.data.preferences.ServerConfig
import com.cubicserenity.nextcloudcookbook.di.NetworkModule
import com.google.gson.Gson
import kotlinx.coroutines.flow.first
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class NetworkClient @Inject constructor(
    private val prefs: PreferencesRepository,
    private val gson: Gson,
) {
    private var cachedApi: CookbookApi? = null
    private var cachedConfig: ServerConfig? = null

    suspend fun api(): CookbookApi {
        val config = prefs.serverConfig.first()
        if (config == cachedConfig && cachedApi != null) return cachedApi!!
        cachedConfig = config
        cachedApi = buildApi(config)
        return cachedApi!!
    }

    private fun buildApi(config: ServerConfig): CookbookApi {
        val baseUrl = config.serverUrl.trimEnd('/') + "/index.php/apps/cookbook/"
        val safeBase = if (baseUrl.startsWith("http")) baseUrl else "https://unconfigured.invalid/"
        return Retrofit.Builder()
            .baseUrl(safeBase)
            .client(NetworkModule.buildClient(config))
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()
            .create(CookbookApi::class.java)
    }
}
