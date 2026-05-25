package com.example.commerceagent.ui.chat

import com.example.commerceagent.data.model.MessageRole
import kotlin.test.Test
import kotlin.test.assertEquals

class UserMessageImageTest {
    @Test
    fun userMessageKeepsAttachedImagePreviewUrl() {
        val message = buildUserMessage(
            text = "我想买这个",
            imageUrl = "/static/uploads/upload_abc.png"
        )

        assertEquals(MessageRole.User, message.role)
        assertEquals("我想买这个", message.content)
        assertEquals("/static/uploads/upload_abc.png", message.imageUrl)
    }
}
