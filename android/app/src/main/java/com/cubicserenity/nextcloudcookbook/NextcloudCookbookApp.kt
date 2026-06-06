package com.cubicserenity.nextcloudcookbook

import android.app.Application
import coil3.ImageLoader
import coil3.PlatformContext
import coil3.SingletonImageLoader
import coil3.network.okhttp.OkHttpNetworkFetcherFactory
import com.cubicserenity.nextcloudcookbook.data.preferences.PreferencesRepository
import com.cubicserenity.nextcloudcookbook.di.NetworkModule
import dagger.hilt.EntryPoint
import dagger.hilt.InstallIn
import dagger.hilt.android.EntryPointAccessors
import dagger.hilt.android.HiltAndroidApp
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking

@EntryPoint
@InstallIn(SingletonComponent::class)
interface AppEntryPoint {
    fun prefsRepository(): PreferencesRepository
}

@HiltAndroidApp
class NextcloudCookbookApp : Application(), SingletonImageLoader.Factory {

    override fun newImageLoader(context: PlatformContext): ImageLoader {
        val prefs = EntryPointAccessors
            .fromApplication(this, AppEntryPoint::class.java)
            .prefsRepository()

        return ImageLoader.Builder(context)
            .components {
                add(OkHttpNetworkFetcherFactory(callFactory = {
                    val config = runBlocking { prefs.serverConfig.first() }
                    NetworkModule.buildClient(config)
                }))
            }
            .build()
    }
}
