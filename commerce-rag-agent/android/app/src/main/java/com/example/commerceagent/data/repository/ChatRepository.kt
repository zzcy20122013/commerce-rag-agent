package com.example.commerceagent.data.repository

import com.example.commerceagent.data.api.ChatSseClient
import com.example.commerceagent.data.model.SseEvent
import kotlinx.coroutines.flow.Flow

class ChatRepository(
    private val client: ChatSseClient = ChatSseClient()
) {
    fun streamChat(message: String, sessionId: String?, uploadId: String?): Flow<SseEvent> {
        return client.streamChat(message, sessionId, uploadId)
    }
}
