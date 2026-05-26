package com.example.commerceagent.ui.chat

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatInputBarStateTest {
    @Test
    fun toolPanelUsesCommerceActions() {
        assertEquals(
            listOf("相册", "文件", "购物车"),
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

    @Test
    fun imageRecognitionPromptFillsOrMergesWithUserInput() {
        assertEquals(
            "请帮我找类似黑色缓震跑鞋的商品",
            mergeImageRecognitionPrompt("", "请帮我找类似黑色缓震跑鞋的商品")
        )
        assertEquals(
            "预算 500 以内 请帮我找类似黑色缓震跑鞋的商品",
            mergeImageRecognitionPrompt("预算 500 以内", "请帮我找类似黑色缓震跑鞋的商品")
        )
        assertEquals(
            "预算 500 以内",
            mergeImageRecognitionPrompt("预算 500 以内", "")
        )
    }
}
