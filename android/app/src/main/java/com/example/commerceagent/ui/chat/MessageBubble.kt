package com.example.commerceagent.ui.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
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
    val background = if (isUser) MaterialTheme.colorScheme.primary else Color.White
    val textColor = if (isUser) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 6.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth(if (isUser) 0.88f else 1f)
                .background(background, RoundedCornerShape(8.dp))
                .padding(12.dp)
        ) {
            if (message.isStreaming) {
                StreamingText(text = message.content, color = textColor)
                LoadingDots()
            } else {
                Text(message.content, color = textColor)
            }
        }
        if (message.productCards.isNotEmpty()) {
            ProductCardRow(cards = message.productCards, onOpenProduct = onOpenProduct)
        }
        if (!isUser && !message.isStreaming && message.content.isNotBlank()) {
            FeedbackBar(
                rating = message.feedbackRating,
                onLike = { onFeedback(message.id, 1) },
                onDislike = { onFeedback(message.id, -1) }
            )
        }
    }
}
