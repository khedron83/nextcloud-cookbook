package com.cubicserenity.nextcloudcookbook.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import android.os.Build

private val NextcloudBlue = Color(0xFF0082C9)
private val NextcloudDarkBlue = Color(0xFF00639B)

private val LightColors = lightColorScheme(
    primary = NextcloudBlue,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFCCE5F4),
    secondary = NextcloudDarkBlue,
    onSecondary = Color.White,
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF5BC4F5),
    onPrimary = Color(0xFF003549),
    primaryContainer = Color(0xFF004C6A),
    secondary = Color(0xFF90CAF9),
)

@Composable
fun NextcloudCookbookTheme(
    darkTheme: Boolean = androidx.compose.foundation.isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val colorScheme = when {
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColors
        else -> LightColors
    }
    MaterialTheme(colorScheme = colorScheme, content = content)
}
