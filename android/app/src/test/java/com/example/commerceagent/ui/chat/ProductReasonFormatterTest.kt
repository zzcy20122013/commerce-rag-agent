package com.example.commerceagent.ui.chat

import kotlin.test.Test
import kotlin.test.assertEquals

class ProductReasonFormatterTest {
    @Test
    fun separatesRiskReasonFromHighlightReasons() {
        val ui = buildProductReasonUi(
            listOf(
                "预算内：269<=300",
                "适合通勤",
                "命中偏好：轻便",
                "命中偏好：黑色",
                "评分较高：4.8",
                "差评提醒：敏感肌/刺痛反馈"
            )
        )

        assertEquals(
            listOf("预算内：269<=300", "适合通勤", "命中偏好：轻便", "命中偏好：黑色"),
            ui.highlights
        )
        assertEquals("差评提醒：敏感肌/刺痛反馈", ui.risk)
    }

    @Test
    fun removesDuplicateAndBlankReasons() {
        val ui = buildProductReasonUi(
            listOf("", "适合通勤", "适合通勤", "销量较高：1800")
        )

        assertEquals(listOf("适合通勤", "销量较高：1800"), ui.highlights)
        assertEquals(null, ui.risk)
    }
}
