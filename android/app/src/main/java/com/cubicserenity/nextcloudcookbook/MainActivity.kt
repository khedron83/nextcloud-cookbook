package com.cubicserenity.nextcloudcookbook

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import com.cubicserenity.nextcloudcookbook.ui.NavGraph
import com.cubicserenity.nextcloudcookbook.ui.theme.NextcloudCookbookTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            NextcloudCookbookTheme {
                NavGraph()
            }
        }
    }
}
