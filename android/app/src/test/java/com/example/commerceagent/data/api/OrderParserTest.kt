package com.example.commerceagent.data.api

import org.json.JSONObject
import kotlin.test.Test
import kotlin.test.assertEquals

class OrderParserTest {
    @Test
    fun parsesOrderListWithItems() {
        val payload = JSONObject(
            """
            {
              "orders": [
                {
                  "id": "ord_1001",
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
                  "items": [
                    {
                      "id": "order_item_1",
                      "quantity": 2,
                      "subtotal": 398,
                      "product": {
                        "id": "p_pants_001",
                        "title": "通勤直筒长裤",
                        "price": 199,
                        "stock": 8,
                        "image_url": "/static/products/pants.jpg"
                      }
                    }
                  ]
                }
              ]
            }
            """.trimIndent()
        )

        val orders = payload.toOrderList()

        assertEquals(1, orders.size)
        assertEquals("ord_1001", orders[0].id)
        assertEquals("待支付", orders[0].status)
        assertEquals(398, orders[0].total)
        assertEquals("张三", orders[0].shippingAddress.recipientName)
        assertEquals("13800000000", orders[0].shippingAddress.phone)
        assertEquals("上海市浦东新区世纪大道 100 号 8 楼", orders[0].shippingAddress.address)
        assertEquals("通勤直筒长裤", orders[0].items[0].product.title)
        assertEquals(2, orders[0].items[0].quantity)
    }
}
