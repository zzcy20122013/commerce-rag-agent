package com.example.commerceagent.data.mock

import kotlin.test.Test
import kotlin.test.assertEquals

class MockCartStoreTest {
    @Test
    fun addItemAccumulatesQuantityForProductDetailFallback() {
        MockCartStore.clear()

        MockCartStore.addItem("mock_shoe_commute")
        val cart = MockCartStore.addItem("mock_shoe_commute")

        assertEquals(1, cart.items.size)
        assertEquals("mock_shoe_commute", cart.items[0].product.id)
        assertEquals(2, cart.items[0].quantity)
        assertEquals(269 * 2, cart.total)
    }
}
