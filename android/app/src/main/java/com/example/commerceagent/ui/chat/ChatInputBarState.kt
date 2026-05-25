package com.example.commerceagent.ui.chat

enum class ChatInputToolType {
    Album,
    File,
    Cart
}

data class ChatInputToolAction(
    val type: ChatInputToolType,
    val label: String,
    val enabled: Boolean = true
)

val chatInputToolActions = listOf(
    ChatInputToolAction(ChatInputToolType.Album, "相册"),
    ChatInputToolAction(ChatInputToolType.File, "文件", enabled = false),
    ChatInputToolAction(ChatInputToolType.Cart, "购物车")
)

fun isChatSendEnabled(input: String, previewUrl: String?): Boolean {
    return input.isNotBlank() || !previewUrl.isNullOrBlank()
}

fun chatPromptForSend(input: String, previewUrl: String?): String? {
    val text = input.trim()
    if (text.isNotBlank()) return text
    if (!previewUrl.isNullOrBlank()) return "请按这张图片找相似商品"
    return null
}
