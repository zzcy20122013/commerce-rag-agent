package com.example.commerceagent.data.model

sealed interface SseEvent {
    data class Message(
        val delta: String,
        val messageId: String?,
        val sessionId: String?,
        val feedbackEnabled: Boolean
    ) : SseEvent
    data class ProductCards(val cards: List<ProductCard>) : SseEvent
    data class Trace(val payload: String) : SseEvent
    data class Error(val message: String) : SseEvent
    data object Done : SseEvent
}
