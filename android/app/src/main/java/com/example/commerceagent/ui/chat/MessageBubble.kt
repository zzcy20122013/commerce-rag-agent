package com.example.commerceagent.ui.chat

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.commerceagent.data.model.ChatMessage
import com.example.commerceagent.data.model.MessageRole
import com.example.commerceagent.ui.components.FeedbackBar
import com.example.commerceagent.ui.components.LoadingDots
import com.example.commerceagent.ui.components.StreamingText

@Composable
fun MessageBubble(
    message: ChatMessage,
    onOpenProduct: (String) -> Unit,
    onFeedback: (String, Int) -> Unit
) {
    val isUser = message.role == MessageRole.User
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 7.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
            verticalAlignment = Alignment.Top
        ) {
            if (!isUser) {
                AgentAvatar()
                Spacer(Modifier.width(8.dp))
            }
            Surface(
                modifier = Modifier.widthIn(max = if (isUser) 310.dp else 340.dp),
                shape = RoundedCornerShape(
                    topStart = 20.dp,
                    topEnd = 20.dp,
                    bottomStart = if (isUser) 20.dp else 6.dp,
                    bottomEnd = if (isUser) 6.dp else 20.dp
                ),
                color = if (isUser) Color(0xFF5B35EA) else Color.White,
                contentColor = if (isUser) Color.White else MaterialTheme.colorScheme.onSurface,
                border = if (isUser) null else BorderStroke(1.dp, Color(0xFFEAE6F8)),
                shadowElevation = if (isUser) 0.dp else 1.dp
            ) {
                Column(Modifier.padding(horizontal = 14.dp, vertical = 12.dp)) {
                    if (message.isStreaming) {
                        StreamingText(
                            text = message.content,
                            color = if (isUser) Color.White else MaterialTheme.colorScheme.onSurface
                        )
                        LoadingDots()
                    } else {
                        Text(message.content)
                    }
                }
            }
        }
        if (message.productCards.isNotEmpty()) {
            Row(modifier = Modifier.fillMaxWidth()) {
                if (!isUser) {
                    Spacer(Modifier.width(40.dp))
                }
                Column(modifier = Modifier.weight(1f)) {
                    ProductCardRow(cards = message.productCards, onOpenProduct = onOpenProduct)
                }
            }
        }
        if (!isUser && !message.isStreaming && message.content.isNotBlank()) {
            Row(modifier = Modifier.padding(start = 40.dp)) {
                FeedbackBar(
                    rating = message.feedbackRating,
                    onLike = { onFeedback(message.id, 1) },
                    onDislike = { onFeedback(message.id, -1) }
                )
            }
        }
    }
}

@Composable
private fun AgentAvatar() {
    Surface(
        modifier = Modifier.size(32.dp),
        shape = RoundedCornerShape(12.dp),
        color = Color(0xFF5B35EA).copy(alpha = 0.1f),
        contentColor = Color(0xFF5B35EA)
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text("AI", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
        }
    }
}
