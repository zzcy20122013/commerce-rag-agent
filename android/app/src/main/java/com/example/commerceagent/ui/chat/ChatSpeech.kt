package com.example.commerceagent.ui.chat

import com.example.commerceagent.data.model.ChatMessage
import com.example.commerceagent.data.model.MessageRole

fun speakableTextForMessage(message: ChatMessage): String? {
    if (message.role != MessageRole.Assistant) return null
    if (message.isStreaming) return null
    return message.content.trim().takeIf { it.isNotBlank() }
}

fun hasAssistantInlineActions(message: ChatMessage): Boolean {
    return speakableTextForMessage(message) != null
}

fun isMessageSpeechPlaying(message: ChatMessage, speakingMessageId: String?): Boolean {
    return speakingMessageId == message.id && hasAssistantInlineActions(message)
}
