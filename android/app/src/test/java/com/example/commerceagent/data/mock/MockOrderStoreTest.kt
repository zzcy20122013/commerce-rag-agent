package com.example.commerceagent.data.mock

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class MockOrderStoreTest {
    @Test
    fun deleteOrderRemovesRecordFromMockHistory() {
        val order = MockOrderStore.listOrders().first()

        assertTrue(MockOrderStore.delete(order.id))

        assertFalse(MockOrderStore.listOrders().any { it.id == order.id })
    }
}
