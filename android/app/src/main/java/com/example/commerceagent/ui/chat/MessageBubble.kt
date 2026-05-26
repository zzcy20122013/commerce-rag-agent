package com.example.commerceagent.ui.chat

import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.VolumeUp
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.commerceagent.data.api.ApiConfig
import com.example.commerceagent.data.model.ChatMessage
import com.example.commerceagent.data.model.MessageRole
import com.example.commerceagent.ui.components.FeedbackBar
import com.example.commerceagent.ui.components.LoadingDots

@Composable
fun MessageBubble(
    message: ChatMessage,
    cartQuantities: Map<String, Int>,
    onOpenProduct: (String) -> Unit,
    onAddToCart: (String) -> Unit,
    onFeedback: (String, Int, String) -> Unit,
    onRetry: (String) -> Unit,
    onSpeak: (ChatMessage) -> Unit,
    onStopSpeech: () -> Unit,
    speakingMessageId: String?
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
                            if (!message.imageUrl.isNullOrBlank()) {
                                AsyncImage(
                                    model = ApiConfig.resolveUrl(message.imageUrl),
                                    contentDescription = "用户上传图片",
                                    contentScale = ContentScale.Crop,
                                    modifier = Modifier
                                        .widthIn(max = 180.dp)
                                        .height(120.dp)
                                )
                                Spacer(Modifier.height(8.dp))
                            }
                            if (message.isStreaming) {
                                MessageText(
                                    text = message.content.ifBlank { "正在思考..." },
                                    isUser = isUser,
                                    color = if (isUser) Color.White else MaterialTheme.colorScheme.onSurface
                                )
                                LoadingDots()
                            } else {
                                MessageText(
                                    text = message.content,
                                    isUser = isUser,
                                    color = if (isUser) Color.White else MaterialTheme.colorScheme.onSurface
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
                
                if (hasAssistantInlineActions(message)) {
                    val isSpeaking = isMessageSpeechPlaying(message, speakingMessageId)
                    Spacer(Modifier.height(4.dp))
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        AssistActionIconButton(
                            onClick = {
                                if (isSpeaking) {
                                    onStopSpeech()
                                } else {
                                    onSpeak(message)
                                }
                            },
                            contentDescription = if (isSpeaking) "停止播报" else "语音播报"
                        ) {
                            Icon(
                                if (isSpeaking) Icons.Default.Stop else Icons.AutoMirrored.Filled.VolumeUp,
                                contentDescription = null,
                                modifier = Modifier.size(if (isSpeaking) 15.dp else 16.dp)
                            )
                        }
                        AssistActionIconButton(
                            onClick = {
                                clipboardManager.setText(AnnotatedString(message.content))
                            },
                            contentDescription = "复制文本"
                        ) {
                            Icon(
                                Icons.Default.ContentCopy,
                                contentDescription = null,
                                modifier = Modifier.size(15.dp)
                            )
                        }
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
                if (!isUser && message.networkError && !message.retryPrompt.isNullOrBlank()) {
                    Spacer(Modifier.height(8.dp))
                    FilledTonalButton(
                        onClick = { onRetry(message.retryPrompt) },
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("重试")
                    }
                }
            }
        }
    }
}

@Composable
private fun AssistActionIconButton(
    onClick: () -> Unit,
    contentDescription: String,
    content: @Composable () -> Unit
) {
    IconButton(
        onClick = onClick,
        modifier = Modifier.size(32.dp),
        colors = IconButtonDefaults.iconButtonColors(
            containerColor = Color(0xFFF1EEFA),
            contentColor = Color(0xFF5B35EA)
        )
    ) {
        Box(
            modifier = Modifier
                .size(20.dp)
                .semantics { this.contentDescription = contentDescription },
            contentAlignment = Alignment.Center
        ) {
            content()
        }
    }
}

@Composable
private fun MessageText(
    text: String,
    isUser: Boolean,
    color: Color
) {
    if (isUser) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyLarge.copy(lineHeight = 26.sp),
            color = color
        )
        return
    }

    val paragraphs = remember(text) { readableParagraphs(text) }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        paragraphs.forEachIndexed { index, paragraph ->
            Text(
                text = paragraph,
                style = MaterialTheme.typography.bodyLarge.copy(lineHeight = 29.sp),
                color = color.copy(alpha = 0.92f),
                fontWeight = if (index == 0 && paragraphs.size > 1) FontWeight.Medium else FontWeight.Normal
            )
        }
    }
}

private fun readableParagraphs(text: String): List<String> {
    val cleaned = text.trim()
    if (cleaned.isBlank()) return listOf("正在思考...")
    val existingParagraphs = cleaned
        .split(Regex("\\n\\s*\\n"))
        .map { it.trim() }
        .filter { it.isNotEmpty() }
    if (existingParagraphs.size > 1) return existingParagraphs

    val sentences = Regex("(?<=[。！？!?])")
        .split(cleaned)
        .map { it.trim() }
        .filter { it.isNotEmpty() }
    if (sentences.size <= 2 || cleaned.length < 88) return listOf(cleaned)
    return sentences.chunked(2).map { it.joinToString("") }
}
