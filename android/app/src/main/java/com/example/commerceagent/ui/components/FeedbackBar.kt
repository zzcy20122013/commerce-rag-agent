package com.example.commerceagent.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AssistChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun FeedbackBar(
    rating: Int?,
    reason: String?,
    onLike: () -> Unit,
    onDislike: (String) -> Unit
) {
    var showReasons by remember { mutableStateOf(false) }
    val dislikeReasons = listOf("不相关", "太贵", "解释不清", "商品太少", "图片不准")

    Column(Modifier.padding(top = 4.dp)) {
        Row {
            TextButton(
                enabled = rating == null,
                onClick = {
                    showReasons = false
                    onLike()
                }
            ) {
                Text(if (rating == 1) "已点赞" else "赞")
            }
            TextButton(
                enabled = rating == null,
                onClick = { showReasons = true }
            ) {
                Text(if (rating == -1) "已点踩" else "踩")
            }
        }

        if (showReasons && rating == null) {
            Text(
                text = "哪里不满意？",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(start = 8.dp, bottom = 2.dp)
            )
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                dislikeReasons.chunked(3).forEach { rowReasons ->
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        rowReasons.forEach { item ->
                            AssistChip(
                                onClick = {
                                    showReasons = false
                                    onDislike(item)
                                },
                                label = { Text(item) }
                            )
                        }
                    }
                }
            }
        }

        if (rating == -1 && !reason.isNullOrBlank()) {
            Text(
                text = "已记录：$reason",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(start = 8.dp, top = 2.dp)
            )
        }
    }
}
