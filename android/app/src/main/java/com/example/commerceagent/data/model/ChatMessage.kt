package com.example.commerceagent.data.model

data class ChatMessage(
    val id: String,
    val role: MessageRole,
    val content: String,
    val productCards: List<ProductCard> = emptyList(),
    val isStreaming: Boolean = false,
    val feedbackEnabled: Boolean = false,
    val feedbackRating: Int? = null,
    val feedbackReason: String? = null
)

enum class MessageRole {
    User,
    Assistant
}
