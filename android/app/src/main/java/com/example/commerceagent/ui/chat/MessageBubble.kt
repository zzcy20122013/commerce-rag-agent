package com.example.commerceagent.ui.chat

import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.unit.dp
import com.example.commerceagent.data.model.ChatMessage
import com.example.commerceagent.data.model.MessageRole
import com.example.commerceagent.ui.components.FeedbackBar
import com.example.commerceagent.ui.components.LoadingDots
import com.example.commerceagent.ui.components.StreamingText

@Composable
fun MessageBubble(
    message: ChatMessage,
    cartQuantities: Map<String, Int>,
    onOpenProduct: (String) -> Unit,
    onAddToCart: (String) -> Unit,
    onFeedback: (String, Int, String) -> Unit
) {
    val isUser = message.role == MessageRole.User
    val clipboardManager = LocalClipboardManager.current
    var showMenu by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalAlignment = if (isUser) Alignment.End else Alignment.Start
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(if (isUser) 0.85f else 1f),
            horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
            verticalAlignment = Alignment.Top
        ) {
            if (!isUser) {
                Surface(
                    modifier = Modifier.size(32.dp),
                    shape = CircleShape,
                    color = Color(0xFF5B35EA).copy(alpha = 0.1f)
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(Icons.Default.Star, contentDescription = null, modifier = Modifier.size(18.dp), tint = Color(0xFF5B35EA))
                    }
                }
                Spacer(Modifier.width(12.dp))
            }
            
            Column(modifier = Modifier.weight(1f, fill = false)) {
                Box {
                    Surface(
                        shape = RoundedCornerShape(
                            topStart = 20.dp,
                            topEnd = 20.dp,
                            bottomStart = if (isUser) 20.dp else 4.dp,
                            bottomEnd = if (isUser) 4.dp else 20.dp
                        ),
                        color = if (isUser) Color(0xFF5B35EA) else Color.Transparent,
                        contentColor = if (isUser) Color.White else MaterialTheme.colorScheme.onSurface,
                        modifier = Modifier.pointerInput(Unit) {
                            detectTapGestures(
                                onLongPress = { showMenu = true }
                            )
                        }
                    ) {
                        Column(Modifier.padding(horizontal = if (isUser) 16.dp else 0.dp, vertical = 10.dp)) {
                            if (message.isStreaming) {
                                StreamingText(
                                    text = message.content,
                                    color = if (isUser) Color.White else MaterialTheme.colorScheme.onSurface
                                )
                                LoadingDots()
                            } else {
                                Text(
                                    text = message.content,
                                    style = MaterialTheme.typography.bodyLarge
                                )
                            }
                        }
                    }

                    DropdownMenu(
                        expanded = showMenu,
                        onDismissRequest = { showMenu = false }
                    ) {
                        DropdownMenuItem(
                            text = { Text("复制文本") },
                            onClick = {
                                clipboardManager.setText(AnnotatedString(message.content))
                                showMenu = false
                            }
                        )
                    }
                }
                
                if (message.productCards.isNotEmpty()) {
                    Spacer(Modifier.height(12.dp))
                    ProductCardRow(
                        cards = message.productCards,
                        cartQuantities = cartQuantities,
                        onOpenProduct = onOpenProduct,
                        onAddToCart = onAddToCart
                    )
                }

                if (!isUser && !message.isStreaming && message.feedbackEnabled) {
                    FeedbackBar(
                        rating = message.feedbackRating,
                        reason = message.feedbackReason,
                        onLike = { onFeedback(message.id, 1, "") },
                        onDislike = { reason -> onFeedback(message.id, -1, reason) }
                    )
                }
            }
        }
    }
}
