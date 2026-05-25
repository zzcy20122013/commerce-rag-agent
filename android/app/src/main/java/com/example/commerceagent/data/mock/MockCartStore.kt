package com.example.commerceagent.data.mock

import com.example.commerceagent.data.model.Cart
import com.example.commerceagent.data.model.CartItem
import com.example.commerceagent.data.model.CartProduct
import com.example.commerceagent.data.model.CheckoutResult
import com.example.commerceagent.data.model.Order
import com.example.commerceagent.data.model.OrderItem
import com.example.commerceagent.data.model.ShippingAddress

object MockCartStore {
    private val quantities = linkedMapOf<String, Int>()

    fun clear() {
        quantities.clear()
    }

    fun getCart(): Cart = buildCart()

    fun addItem(productId: String, quantity: Int = 1): Cart {
        quantities[productId] = (quantities[productId] ?: 0) + quantity.coerceAtLeast(1)
        return buildCart()
    }

    fun updateItem(position: Int, quantity: Int): Cart {
        val productId = quantities.keys.elementAtOrNull(position - 1) ?: return buildCart()
        quantities[productId] = quantity.coerceAtLeast(1)
        return buildCart()
    }

    fun removeItem(position: Int): Cart {
        val productId = quantities.keys.elementAtOrNull(position - 1)
        if (productId != null) quantities.remove(productId)
        return buildCart()
    }

    fun checkout(shippingAddress: ShippingAddress): CheckoutResult {
        val checkedOutItems = buildCart().items
        val total = checkedOutItems.sumOf { it.subtotal }
        val order = Order(
            id = "mock_ord_${System.currentTimeMillis().toString().takeLast(6)}",
            status = "待支付",
            logisticsStatus = "订单已提交，库存已锁定，等待支付。",
            returnStatus = "未申请售后",
            shippingAddress = shippingAddress,
            createdAt = "2026-05-24T10:00:00+00:00",
            total = total,
            items = checkedOutItems.mapIndexed { index, item ->
                OrderItem(
                    id = "mock_order_item_${index + 1}",
                    quantity = item.quantity,
                    product = item.product,
                    subtotal = item.subtotal
                )
            }
        )
        MockOrderStore.addOrders(listOf(order))
        quantities.clear()
        return CheckoutResult(
            orderIds = listOf(order.id),
            orders = listOf(order),
            items = checkedOutItems,
            total = total,
            cart = buildCart()
        )
    }

    private fun buildCart(): Cart {
        val items = quantities.entries.mapIndexed { index, entry ->
            val detail = MockCommerceData.productDetail(entry.key)
            val product = CartProduct(
                id = entry.key,
                title = detail?.title ?: entry.key,
                price = detail?.price ?: 0,
                stock = detail?.stock ?: 0,
                imageUrl = detail?.imageUrl.orEmpty()
            )
            CartItem(
                id = "mock_cart_${index + 1}",
                quantity = entry.value,
                product = product,
                subtotal = product.price * entry.value
            )
        }
        return Cart(items = items, total = items.sumOf { it.subtotal })
    }
}
