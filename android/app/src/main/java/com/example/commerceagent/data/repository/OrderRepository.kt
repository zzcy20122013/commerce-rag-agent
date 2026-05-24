package com.example.commerceagent.data.repository

import com.example.commerceagent.data.api.OrderApi
import com.example.commerceagent.data.mock.MockOrderStore
import com.example.commerceagent.data.model.Order

class OrderRepository(
    private val api: OrderApi = OrderApi()
) {
    suspend fun listOrders(): List<Order> = runCatching { api.listOrders() }
        .getOrElse { MockOrderStore.listOrders() }

    suspend fun pay(orderId: String): Order = runCatching { api.pay(orderId) }
        .getOrElse { MockOrderStore.pay(orderId) }

    suspend fun cancel(orderId: String): Order = runCatching { api.cancel(orderId) }
        .getOrElse { MockOrderStore.cancel(orderId) }

    suspend fun ship(orderId: String): Order = runCatching { api.ship(orderId) }
        .getOrElse { MockOrderStore.ship(orderId) }

    suspend fun complete(orderId: String): Order = runCatching { api.complete(orderId) }
        .getOrElse { MockOrderStore.complete(orderId) }

    suspend fun refund(orderId: String, reason: String): Order = runCatching { api.refund(orderId, reason) }
        .getOrElse { MockOrderStore.refund(orderId, reason) }
}
