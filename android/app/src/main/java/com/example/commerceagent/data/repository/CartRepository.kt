package com.example.commerceagent.data.repository

import com.example.commerceagent.data.api.CartApi
import com.example.commerceagent.data.mock.MockCartStore
import com.example.commerceagent.data.model.Cart
import com.example.commerceagent.data.model.CheckoutResult
import com.example.commerceagent.data.model.ShippingAddress

class CartRepository(
    private val api: CartApi = CartApi()
) {
    suspend fun getCart(): Cart = runCatching { api.getCart() }
        .getOrElse { MockCartStore.getCart() }

    suspend fun addItem(productId: String, quantity: Int = 1): Cart = runCatching { api.addItem(productId, quantity) }
        .getOrElse { MockCartStore.addItem(productId, quantity) }

    suspend fun updateItem(position: Int, quantity: Int): Cart = runCatching { api.updateItem(position, quantity) }
        .getOrElse { MockCartStore.updateItem(position, quantity) }

    suspend fun removeItem(position: Int): Cart = runCatching { api.removeItem(position) }
        .getOrElse { MockCartStore.removeItem(position) }

    suspend fun checkout(shippingAddress: ShippingAddress): CheckoutResult = runCatching { api.checkout(shippingAddress) }
        .getOrElse { MockCartStore.checkout(shippingAddress) }
}
