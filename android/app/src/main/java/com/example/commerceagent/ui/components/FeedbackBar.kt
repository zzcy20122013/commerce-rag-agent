package com.example.commerceagent.ui.components

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun FeedbackBar(
    rating: Int?,
    onLike: () -> Unit,
    onDislike: () -> Unit
) {
    Row(Modifier.padding(top = 4.dp)) {
        TextButton(enabled = rating == null, onClick = onLike) {
            Text(if (rating == 1) "已点赞" else "赞")
        }
        TextButton(enabled = rating == null, onClick = onDislike) {
            Text(if (rating == -1) "已点踩" else "踩")
        }
    }
}
