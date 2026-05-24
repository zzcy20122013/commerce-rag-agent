package com.example.commerceagent.data.model

data class Order(
    val id: String,
    val status: String,
    val logisticsStatus: String,
    val returnStatus: String,
    val createdAt: String,
    val items: List<OrderItem> = emptyList(),
    val total: Int = 0
)

data class OrderItem(
    val id: String,
    val quantity: Int,
    val product: CartProduct,
    val subtotal: Int
)
