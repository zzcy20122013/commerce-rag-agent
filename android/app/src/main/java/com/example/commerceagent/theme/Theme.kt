package com.example.commerceagent.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val AppColorScheme = lightColorScheme(
    primary = Color(0xFF5B35EA),
    secondary = Color(0xFF1A9D8F),
    tertiary = Color(0xFFE96B2C),
    background = Color(0xFFF8F6FF),
    surface = Color.White,
    onPrimary = Color.White,
    onSecondary = Color.White,
    onTertiary = Color.White,
    onBackground = Color(0xFF171A21),
    onSurface = Color(0xFF171A21)
)

@Composable
fun CommerceAgentTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = AppColorScheme,
        typography = MaterialTheme.typography,
        content = content
    )
}
