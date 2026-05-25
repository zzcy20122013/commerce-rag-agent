package com.example.commerceagent.ui.chat

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatInputBarStateTest {
    @Test
    fun toolPanelUsesCommerceActions() {
        assertEquals(
            listOf("相机", "相册", "文件", "购物车"),
            chatInputToolActions.map { it.label }
        )
    }

    @Test
    fun sendIsEnabledWhenTextOrImageIsPresent() {
        assertFalse(isChatSendEnabled("", null))
        assertTrue(isChatSendEnabled("我想买这个", null))
        assertTrue(isChatSendEnabled("", "/static/uploads/photo.jpg"))
    }

    @Test
    fun blankImageMessageUsesDefaultImageSearchPrompt() {
        assertEquals(
            "请按这张图片找相似商品",
            chatPromptForSend("", "/static/uploads/photo.jpg")
        )
    }
}
