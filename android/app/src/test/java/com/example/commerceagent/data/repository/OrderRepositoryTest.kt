package com.example.commerceagent.data.repository

import com.example.commerceagent.data.api.OrderApi
import com.example.commerceagent.data.mock.MockOrderStore
import com.example.commerceagent.data.model.CartProduct
import com.example.commerceagent.data.model.Order
import com.example.commerceagent.data.model.OrderItem
import kotlinx.coroutines.runBlocking
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import kotlin.test.Test
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

class OrderRepositoryTest {
    @Test
    fun deleteDoesNotFallbackToMockWhenBackendRejectsRequest() = runBlocking {
        val orderId = "ord_backend_reject"
        MockOrderStore.addOrders(listOf(sampleOrder(orderId)))
        val rejectingApi = OrderApi(
            OkHttpClient.Builder()
                .addInterceptor { chain ->
                    Response.Builder()
                        .request(chain.request())
                        .protocol(Protocol.HTTP_1_1)
                        .code(404)
                        .message("Not Found")
                        .body("""{"detail":"Order not found"}""".toResponseBody("application/json".toMediaType()))
                        .build()
                }
                .build()
        )

        val error = assertFailsWith<IllegalStateException> {
            OrderRepository(rejectingApi).delete(orderId)
        }

        assertTrue(error.message.orEmpty().contains("删除订单失败"))
        assertTrue(MockOrderStore.listOrders().any { it.id == orderId })
    }

    private fun sampleOrder(orderId: String): Order {
        return Order(
            id = orderId,
            status = "已退款",
            logisticsStatus = "售后完成，库存已回补。",
            returnStatus = "退款已完成。",
            createdAt = "2026-05-25T10:00:00+00:00",
            total = 100,
            items = listOf(
                OrderItem(
                    id = "item_$orderId",
                    quantity = 1,
                    subtotal = 100,
                    product = CartProduct(
                        id = "p_test",
                        title = "测试商品",
                        price = 100,
                        stock = 10,
                        imageUrl = ""
                    )
                )
            )
        )
    }
}
