package com.example.commerceagent.data.mock

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

class MockCommerceDataTest {
    @Test
    fun commuteShoeQueryReturnsMockProductCards() {
        val scenario = MockCommerceData.scenarioFor("推荐 300 以内通勤鞋", hasImage = false)

        assertTrue(scenario.answer.contains("通勤"))
        assertTrue(scenario.cards.isNotEmpty())
        assertTrue(scenario.cards.all { it.price <= 300 })
        assertTrue(scenario.cards.any { it.title.contains("通勤") || it.subtitle.contains("通勤") })
    }

    @Test
    fun unknownQueryStillReturnsUsefulFallbackCards() {
        val scenario = MockCommerceData.scenarioFor("我想买点东西", hasImage = false)

        assertTrue(scenario.answer.contains("先"))
        assertTrue(scenario.cards.isNotEmpty())
    }

    @Test
    fun productDetailCanBeResolvedFromMockCardId() {
        val scenario = MockCommerceData.scenarioFor("推荐学生平板", hasImage = false)
        val detail = MockCommerceData.productDetail(scenario.cards.first().productId)

        assertNotNull(detail)
        assertEquals(scenario.cards.first().productId, detail.id)
    }

    @Test
    fun sessionTitleSummarizesFirstShoppingMessage() {
        assertEquals("学生平板选购", MockCommerceData.sessionTitleFor("我想买 3500 以内适合学生记笔记和网课的平板"))
        assertEquals("通勤鞋选购", MockCommerceData.sessionTitleFor("推荐 300 以内适合通勤的鞋"))
    }
}
