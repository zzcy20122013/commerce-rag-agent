package com.example.commerceagent.data.api

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Test

class CartJsonParsersTest {
    @Test
    fun parsesCartResponseWithItemsAndTotal() {
        val json = JSONObject(
            """
            {
              "items": [
                {
                  "id": "cart_001",
                  "quantity": 100,
                  "subtotal": 6900,
                  "product": {
                    "id": "p_food_020",
                    "title": "日清合味道海鲜风味杯面",
                    "price": 69,
                    "stock": 10,
                    "image_url": "/static/product_images/cup.jpg"
                  }
                }
              ],
              "total": 6900
            }
            """.trimIndent()
        )

        val cart = json.toCart()

        assertEquals(6900, cart.total)
        assertEquals(1, cart.items.size)
        assertEquals("cart_001", cart.items[0].id)
        assertEquals("p_food_020", cart.items[0].product.id)
        assertEquals(100, cart.items[0].quantity)
        assertEquals(6900, cart.items[0].subtotal)
    }

    @Test
    fun parsesProductCardEvidenceAndSourceSummary() {
        val json = JSONObject(
            """
            {
              "product_id": "p_food_020",
              "title": "日清合味道海鲜风味杯面",
              "subtitle": "适合夜宵和宿舍囤货",
              "price": 69,
              "original_price": 89,
              "image_url": "/static/product_images/cup.jpg",
              "rating": 3.4,
              "sales": 1750,
              "stock_status": "in_stock",
              "reasons": ["预算内", "适合囤货"],
              "score": 0.91,
              "source_summary": "推荐依据：商品库结构化字段、用户评价摘要",
              "evidence": [
                {
                  "source": "商品库结构化字段",
                  "text": "价格 69 元，库存充足"
                },
                {
                  "source": "用户评价摘要",
                  "text": "适合夜宵，泡面香味明显"
                }
              ]
            }
            """.trimIndent()
        )

        val card = json.toProductCard()

        assertEquals("推荐依据：商品库结构化字段、用户评价摘要", card.sourceSummary)
        assertEquals(2, card.evidence.size)
        assertEquals("商品库结构化字段", card.evidence[0].source)
        assertEquals("价格 69 元，库存充足", card.evidence[0].text)
        assertEquals("用户评价摘要", card.evidence[1].source)
    }

    @Test
    fun parsesCheckoutResponseWithClearedCartAndOrderIds() {
        val json = JSONObject(
            """
            {
              "order_ids": ["ord_abc"],
              "orders": [
                {
                  "id": "ord_abc",
                  "status": "待支付",
                  "logistics_status": "订单已提交，库存已锁定，等待支付。",
                  "return_status": "未申请售后",
                  "shipping_address": {
                    "recipient_name": "张三",
                    "phone": "13800000000",
                    "address": "上海市浦东新区世纪大道 100 号 8 楼"
                  },
                  "created_at": "2026-05-24T10:00:00+00:00",
                  "total": 398,
                  "items": []
                }
              ],
              "items": [
                {
                  "id": "cart_001",
                  "quantity": 2,
                  "subtotal": 398,
                  "product": {
                    "id": "p_pants_001",
                    "title": "通勤直筒长裤",
                    "price": 199,
                    "stock": 0,
                    "image_url": ""
                  }
                }
              ],
              "total": 398,
              "cart": {
                "items": [],
                "total": 0
              }
            }
            """.trimIndent()
        )

        val result = json.toCheckoutResult()

        assertEquals(listOf("ord_abc"), result.orderIds)
        assertEquals(398, result.total)
        assertEquals("张三", result.orders[0].shippingAddress.recipientName)
        assertEquals("上海市浦东新区世纪大道 100 号 8 楼", result.orders[0].shippingAddress.address)
        assertEquals(1, result.items.size)
        assertEquals(0, result.items[0].product.stock)
        assertEquals(emptyList<Any>(), result.cart.items)
        assertEquals(0, result.cart.total)
    }
}
