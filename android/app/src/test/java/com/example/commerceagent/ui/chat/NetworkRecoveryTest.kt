package com.example.commerceagent.ui.chat

import com.example.commerceagent.data.model.MessageRole
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class NetworkRecoveryTest {
    @Test
    fun failedAssistantMessageKeepsRetryPrompt() {
        val message = buildFailedAssistantMessage(
            messageId = "assistant_tmp",
            prompt = "推荐 300 以内通勤鞋",
            errorMessage = "Failed to connect"
        )

        assertEquals("assistant_tmp", message.id)
        assertEquals(MessageRole.Assistant, message.role)
        assertEquals("推荐 300 以内通勤鞋", message.retryPrompt)
        assertTrue(message.networkError)
        assertTrue(message.content.contains("Failed to connect"))
    }

    @Test
    fun stoppedAssistantMessageKeepsPartialTextAndStopsStreaming() {
        val message = buildStoppedAssistantMessage(
            messageId = "assistant_tmp",
            partialContent = "这几款可以先看"
        )

        assertEquals("assistant_tmp", message.id)
        assertEquals(MessageRole.Assistant, message.role)
        assertEquals("这几款可以先看\n\n已停止生成。", message.content)
        assertFalse(message.isStreaming)
        assertFalse(message.feedbackEnabled)
        assertFalse(message.networkError)
    }

    @Test
    fun stoppedAssistantMessageUsesFallbackWhenNoTextGenerated() {
        val message = buildStoppedAssistantMessage(
            messageId = "assistant_tmp",
            partialContent = ""
        )

        assertEquals("已停止生成。", message.content)
        assertFalse(message.isStreaming)
    }
}
