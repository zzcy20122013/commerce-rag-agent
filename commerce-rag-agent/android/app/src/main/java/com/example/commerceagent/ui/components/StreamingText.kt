package com.example.commerceagent.ui.components

import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

@Composable
fun StreamingText(text: String, color: Color) {
    Text(text = text.ifBlank { "正在思考..." }, color = color)
}
