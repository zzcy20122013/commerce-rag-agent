package com.example.commerceagent.data.model

data class Order(
    val id: String,
    val status: String,
    val logisticsStatus: String,
    val returnStatus: String,
    val shippingAddress: ShippingAddress = ShippingAddress(),
    val createdAt: String,
    val items: List<OrderItem> = emptyList(),
    val total: Int = 0
)

data class ShippingAddress(
    val recipientName: String = "",
    val phone: String = "",
    val address: String = ""
) {
    val isComplete: Boolean
        get() = recipientName.isNotBlank() && phone.isNotBlank() && address.isNotBlank()
}

val DefaultShippingAddress = ShippingAddress(
    recipientName = "张三",
    phone = "13800000000",
    address = "上海市浦东新区世纪大道 100 号 8 楼"
)

data class OrderItem(
    val id: String,
    val quantity: Int,
    val product: CartProduct,
    val subtotal: Int
)
