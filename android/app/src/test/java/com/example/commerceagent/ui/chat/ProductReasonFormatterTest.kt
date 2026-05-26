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

        assertEquals(listOf("预算内：269 元", "适合通勤", "命中偏好：轻便", "命中偏好：黑色"), ui.highlights)
        assertEquals("评价提醒：敏感肌/刺痛反馈", ui.risk)
    }

    @Test
    fun keepsFormattedRiskOutOfHighlights() {
        val ui = buildProductReasonUi(
            listOf(
                "适合通勤",
                "差评提醒：敏感肌/刺痛反馈"
            )
        )

        assertEquals(listOf("适合通勤"), ui.highlights)
        assertEquals("评价提醒：敏感肌/刺痛反馈", ui.risk)
    }

    @Test
    fun removesDuplicateAndBlankReasons() {
        val ui = buildProductReasonUi(
            listOf("", "适合通勤", "适合通勤", "销量较高：1800")
        )

        assertEquals(listOf("适合通勤", "销量较高：1800"), ui.highlights)
        assertEquals(null, ui.risk)
    }

    @Test
    fun buildsCompactEvidenceLineFromSourceSummaryAndEvidence() {
        val ui = buildProductEvidenceUi(
            sourceSummary = "推荐依据：商品库结构化字段、用户评价摘要、商品规格/知识字段",
            evidence = listOf(
                ProductEvidenceUiItem("商品库结构化字段", "价格 269 元，库存充足"),
                ProductEvidenceUiItem("用户评价摘要", "通勤脚感反馈较多"),
                ProductEvidenceUiItem("商品规格/知识字段", "轻便缓震")
            )
        )

        assertEquals("推荐依据：价格/销量/评分、用户评价、商品规格", ui.title)
        assertEquals(listOf("价格/销量/评分", "用户评价", "商品规格"), ui.sources)
        assertEquals("通勤脚感反馈较多", ui.highlight)
    }

    @Test
    fun evidenceLineFallsBackToReasonsWhenEvidenceIsMissing() {
        val ui = buildProductEvidenceUi(
            sourceSummary = "",
            evidence = emptyList(),
            reasons = listOf("预算内", "适合通勤")
        )

        assertEquals("推荐依据：预算内、适合通勤", ui.title)
        assertEquals(emptyList(), ui.sources)
        assertEquals(null, ui.highlight)
    }

    @Test
    fun marksOverBudgetCardAsBudgetAlternative() {
        assertEquals("预算外备选", buildProductBadge(index = 0, reasons = listOf("超预算：1399>300")))
        assertEquals("预算外", buildProductBadge(index = 1, reasons = listOf("超预算：899>300")))
    }

    @Test
    fun formatsOverBudgetReasonForUsers() {
        val ui = buildProductReasonUi(listOf("超预算：1399>300", "适合通勤"))

        assertEquals(listOf("预算外：比预算高 1099 元", "适合通勤"), ui.highlights)
    }
}
