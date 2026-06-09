package com.example.commerceagent.ui.chat

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class ChatSendStateTest {
    @Test
    fun sendStartClearsComposerImageButKeepsUserMessageImage() {
        val pending = buildPendingSendState(
            current = ChatUiState(
                input = "请按这张图片找相似商品",
                sessionId = "session_1",
                uploadId = "upload_1",
                previewUrl = "/static/uploads/upload_1.jpg"
            ),
            text = "请按这张图片找相似商品",
            assistantTempId = "assistant_temp"
        )

        assertNull(pending.state.uploadId)
        assertNull(pending.state.previewUrl)
        assertEquals("", pending.state.input)
        assertEquals("upload_1", pending.uploadId)
        assertEquals("session_1", pending.sessionId)
        assertEquals("/static/uploads/upload_1.jpg", pending.state.messages.first().imageUrl)
    }
}
