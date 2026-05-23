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
}
