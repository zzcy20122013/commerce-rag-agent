package com.example.commerceagent.data.model

data class Cart(
    val items: List<CartItem> = emptyList(),
    val total: Int = 0
)

data class CheckoutResult(
    val orderIds: List<String> = emptyList(),
    val items: List<CartItem> = emptyList(),
    val total: Int = 0,
    val cart: Cart = Cart()
)

data class CartItem(
    val id: String,
    val quantity: Int,
    val product: CartProduct,
    val subtotal: Int
)

data class CartProduct(
    val id: String,
    val title: String,
    val price: Int,
    val stock: Int,
    val imageUrl: String
)
