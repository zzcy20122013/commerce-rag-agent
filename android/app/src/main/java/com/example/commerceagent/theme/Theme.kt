package com.example.commerceagent.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val AppColorScheme = lightColorScheme(
    primary = Color(0xFF2457D6),
    secondary = Color(0xFF0F8B8D),
    tertiary = Color(0xFFE56B2F),
    background = Color(0xFFF7F8FA),
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
