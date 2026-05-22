package com.example.commerceagent.data.model

data class SessionMessage(
    val id: String,
    val role: String,
    val content: String,
    val createdAt: String,
    val productCards: List<ProductCard>
)
