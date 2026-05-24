package com.example.commerceagent.data.mock

import com.example.commerceagent.data.model.CartProduct
import com.example.commerceagent.data.model.Order
import com.example.commerceagent.data.model.OrderItem

object MockOrderStore {
    private val orders = mutableListOf(
        Order(
            id = "ord_mock_1001",
            status = "待支付",
            logisticsStatus = "订单已提交，库存已锁定，等待支付。",
            returnStatus = "未申请售后",
            createdAt = "2026-05-24T10:00:00+00:00",
            total = 899,
            items = listOf(
                OrderItem(
                    id = "order_item_mock_1",
                    quantity = 1,
                    subtotal = 899,
                    product = CartProduct(
                        id = "p_shoe_001",
                        title = "Nike Air Zoom Pegasus 41 男子缓震跑步鞋",
                        price = 899,
                        stock = 1760,
                        imageUrl = "/static/products/shoe.jpg"
                    )
                )
            )
        )
    )

    fun listOrders(): List<Order> = orders.toList()

    fun addOrders(newOrders: List<Order>) {
        if (newOrders.isEmpty()) return
        orders.removeAll { existing -> newOrders.any { it.id == existing.id } }
        orders.addAll(0, newOrders)
    }

    fun pay(orderId: String): Order = update(orderId, "已支付", "支付成功，等待仓库出库。")

    fun cancel(orderId: String): Order = update(orderId, "已取消", "订单已取消，锁定库存已释放。")

    fun ship(orderId: String): Order = update(orderId, "已发货", "包裹已出库，正在运输中。")

    fun complete(orderId: String): Order = update(orderId, "已完成", "订单已确认收货。")

    fun refund(orderId: String, reason: String): Order {
        val updated = update(orderId, "已退款", "售后完成，库存已回补。")
        return replace(updated.copy(returnStatus = "退款已完成。原因：${reason.ifBlank { "用户申请售后" }}。"))
    }

    fun delete(orderId: String): Boolean {
        return orders.removeAll { it.id == orderId }
    }

    private fun update(orderId: String, status: String, logisticsStatus: String): Order {
        val order = orders.firstOrNull { it.id == orderId } ?: orders.first()
        return replace(order.copy(status = status, logisticsStatus = logisticsStatus))
    }

    private fun replace(order: Order): Order {
        val index = orders.indexOfFirst { it.id == order.id }
        if (index >= 0) orders[index] = order
        return order
    }
}
