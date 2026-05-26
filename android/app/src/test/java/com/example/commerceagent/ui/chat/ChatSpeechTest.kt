package com.example.commerceagent.ui.chat

import com.example.commerceagent.data.model.ChatMessage
import com.example.commerceagent.data.model.MessageRole
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class ChatSpeechTest {
    @Test
    fun assistantFinishedMessageCanBeSpoken() {
        val message = ChatMessage(
            id = "assistant_1",
            role = MessageRole.Assistant,
            content = "我推荐这几款商品。"
        )

        assertEquals("我推荐这几款商品。", speakableTextForMessage(message))
    }

    @Test
    fun userStreamingAndBlankMessagesAreNotSpoken() {
        assertNull(
            speakableTextForMessage(
                ChatMessage(id = "user_1", role = MessageRole.User, content = "我想买这个")
            )
        )
        assertNull(
            speakableTextForMessage(
                ChatMessage(id = "assistant_2", role = MessageRole.Assistant, content = "正在", isStreaming = true)
            )
        )
        assertNull(
            speakableTextForMessage(
                ChatMessage(id = "assistant_3", role = MessageRole.Assistant, content = "   ")
            )
        )
    }

    @Test
    fun assistantFinishedTextMessageShowsInlineActions() {
        val message = ChatMessage(
            id = "assistant_4",
            role = MessageRole.Assistant,
            content = "可以先看这几款。"
        )

        assertTrue(hasAssistantInlineActions(message))
        assertFalse(
            hasAssistantInlineActions(
                message.copy(content = "   ")
            )
        )
        assertFalse(
            hasAssistantInlineActions(
                message.copy(role = MessageRole.User, content = "我想买这个")
            )
        )
    }

    @Test
    fun onlyCurrentAssistantMessageShowsSpeechPlayingState() {
        val message = ChatMessage(
            id = "assistant_5",
            role = MessageRole.Assistant,
            content = "这条正在播报。"
        )

        assertTrue(isMessageSpeechPlaying(message, "assistant_5"))
        assertFalse(isMessageSpeechPlaying(message, "assistant_other"))
        assertFalse(isMessageSpeechPlaying(message, null))
        assertFalse(isMessageSpeechPlaying(message.copy(role = MessageRole.User), "assistant_5"))
    }
}
