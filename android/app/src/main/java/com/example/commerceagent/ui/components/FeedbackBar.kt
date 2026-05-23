package com.example.commerceagent.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ThumbDown
import androidx.compose.material.icons.filled.ThumbUp
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
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

    Column(Modifier.padding(top = 8.dp)) {
        if (rating != null) {
            FeedbackRecordedPill(reason = reason)
            return@Column
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            AssistChip(
                onClick = {
                    showReasons = false
                    onLike()
                },
                leadingIcon = {
                    Icon(Icons.Default.ThumbUp, contentDescription = null, modifier = Modifier.size(16.dp))
                },
                label = { Text("有帮助") }
            )
            AssistChip(
                onClick = { showReasons = true },
                leadingIcon = {
                    Icon(Icons.Default.ThumbDown, contentDescription = null, modifier = Modifier.size(16.dp))
                },
                label = { Text("不合适") }
            )
        }

        if (showReasons) {
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
    }
}

@Composable
private fun FeedbackRecordedPill(reason: String?) {
    Surface(
        color = MaterialTheme.colorScheme.primary.copy(alpha = 0.08f),
        contentColor = MaterialTheme.colorScheme.primary,
        shape = RoundedCornerShape(999.dp)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(Icons.Default.CheckCircle, contentDescription = null, modifier = Modifier.size(15.dp))
            Spacer(Modifier.size(6.dp))
            Text(
                text = if (reason.isNullOrBlank()) "感谢反馈" else "已记录：$reason",
                style = MaterialTheme.typography.labelSmall,
            )
        }
    }
}
