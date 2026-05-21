package com.example.commerceagent.ui.components

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha

@Composable
fun LoadingDots() {
    Text(
        text = "...",
        modifier = Modifier.alpha(0.65f),
        style = MaterialTheme.typography.bodyMedium
    )
}
