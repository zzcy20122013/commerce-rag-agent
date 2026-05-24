package com.example.commerceagent.data.repository

import com.example.commerceagent.data.api.ChatSseClient
import com.example.commerceagent.data.mock.MockCommerceData
import com.example.commerceagent.data.mock.MockSessionStore
import com.example.commerceagent.data.model.SseEvent
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.flow

class ChatRepository(
    private val client: ChatSseClient = ChatSseClient()
) {
    fun streamChat(message: String, sessionId: String?, uploadId: String?): Flow<SseEvent> {
        return flow {
            var completed = false
            client.streamChat(message, sessionId, uploadId)
                .catch {
                    emitMockStream(message, sessionId, uploadId)
                    completed = true
                }
                .collect { event ->
                    if (event is SseEvent.Error && !completed) {
                        emitMockStream(message, sessionId, uploadId)
                        completed = true
                    } else {
                        if (event is SseEvent.Done) completed = true
                        emit(event)
                    }
                }
        }
    }

    private suspend fun kotlinx.coroutines.flow.FlowCollector<SseEvent>.emitMockStream(
        message: String,
        sessionId: String?,
        uploadId: String?
    ) {
        val scenario = MockCommerceData.scenarioFor(message, hasImage = !uploadId.isNullOrBlank())
        val mockSessionId = sessionId ?: "mock_session_local"
        MockSessionStore.upsertFromFirstMessage(mockSessionId, message)
        val mockMessageId = "mock_msg_${System.currentTimeMillis()}"
        scenario.answer.chunked(1).forEach { chunk ->
            emit(
                SseEvent.Message(
                    delta = chunk,
                    messageId = mockMessageId,
                    sessionId = mockSessionId,
                    feedbackEnabled = true
                )
            )
            delay(70)
        }
        emit(SseEvent.ProductCards(scenario.cards))
        emit(SseEvent.Done)
    }
}
