package com.example.commerceagent.data.api

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.runBlocking
import com.example.commerceagent.data.model.SseEvent
import com.example.commerceagent.data.repository.ChatRepository

class ChatSseClientTest {
    @Test
    fun parsesSseErrorJsonIntoReadableMessage() {
        val message = parseSseErrorMessage(
            """{"code":"SSE_STREAM_ERROR","message":"流式回复中断，请稍后重试","detail":{"type":"ResponseNotRead"}}"""
        )

        assertEquals("流式回复中断，请稍后重试", message)
    }

    @Test
    fun repositoryFallsBackToMockWhenSseErrorArrivesAfterPartialText() = runBlocking {
        val repository = ChatRepository(
            client = object : ChatSseClient() {
                override fun streamChat(message: String, sessionId: String?, uploadId: String?) = kotlinx.coroutines.flow.flow {
                    emit(SseEvent.Message(delta = "半", messageId = "m1", sessionId = "s1", feedbackEnabled = false))
                    emit(SseEvent.Error("流式回复中断，请稍后重试"))
                }
            }
        )

        val events = repository.streamChat("推荐 3500 以内学生记笔记平板", null, null).toList()

        assertEquals(false, events.any { it is SseEvent.Error })
        assertEquals(true, events.any { it is SseEvent.ProductCards })
        assertEquals(true, events.last() is SseEvent.Done)
    }
}
