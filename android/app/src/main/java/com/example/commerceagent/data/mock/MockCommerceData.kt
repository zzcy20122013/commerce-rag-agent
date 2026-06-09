package com.example.commerceagent.data.mock

import com.example.commerceagent.data.model.ProductCard
import com.example.commerceagent.data.model.ProductDetail

data class MockChatScenario(
    val answer: String,
    val cards: List<ProductCard>
)

object MockCommerceData {
    private val products = listOf(
        MockProduct(
            id = "mock_tablet_note",
            title = "青云 Pad Note 11 学习平板",
            category = "数码电子",
            brand = "青云",
            price = 2199,
            subtitle = "适合网课、手写笔记和轻办公",
            description = "11 英寸护眼屏，支持手写笔，续航适合一天网课和图书馆自习。",
            rating = 4.7,
            sales = 3280,
            stock = 86,
            reasons = listOf("预算友好", "适合记笔记", "续航够用")
        ),
        MockProduct(
            id = "mock_tablet_air",
            title = "星河 Tab Air 12 轻薄平板",
            category = "数码电子",
            brand = "星河",
            price = 3299,
            subtitle = "更轻薄，适合学生党随身携带",
            description = "轻薄机身和高亮屏幕，适合网课、批注 PDF、宿舍娱乐和外出携带。",
            rating = 4.8,
            sales = 2160,
            stock = 42,
            reasons = listOf("轻薄便携", "屏幕更好", "适合学生")
        ),
        MockProduct(
            id = "mock_shoe_commute",
            title = "轻云通勤缓震跑鞋",
            category = "服饰运动",
            brand = "轻云",
            price = 269,
            subtitle = "300 元以内，通勤和日常走路都舒服",
            description = "软弹中底和耐磨外底，适合每天通勤、校园步行和轻量运动。",
            rating = 4.6,
            sales = 5480,
            stock = 120,
            reasons = listOf("符合预算", "适合通勤", "脚感轻")
        ),
        MockProduct(
            id = "mock_shoe_walk",
            title = "森步城市休闲通勤鞋",
            category = "服饰运动",
            brand = "森步",
            price = 199,
            subtitle = "更便宜的备选，适合日常通勤",
            description = "鞋面透气，脚感偏软，适合办公室、校园和短距离通勤。",
            rating = 4.5,
            sales = 3920,
            stock = 74,
            reasons = listOf("价格更低", "休闲百搭", "透气")
        ),
        MockProduct(
            id = "mock_powder_oil",
            title = "净透控油柔焦散粉",
            category = "美妆护肤",
            brand = "净透",
            price = 89,
            subtitle = "适合油皮补妆和日常定妆",
            description = "细腻粉质，控油力适中，适合通勤补妆和夏天定妆。",
            rating = 4.6,
            sales = 4520,
            stock = 96,
            reasons = listOf("100 元以内", "控油定妆", "粉质细")
        ),
        MockProduct(
            id = "mock_headphone_noise",
            title = "声阔 Lite 降噪蓝牙耳机",
            category = "数码电子",
            brand = "声阔",
            price = 399,
            subtitle = "通勤降噪、网课通话都够用",
            description = "主动降噪、长续航和清晰通话，适合地铁通勤、网课和图书馆自习。",
            rating = 4.7,
            sales = 6890,
            stock = 58,
            reasons = listOf("降噪稳定", "适合通勤", "通话清楚")
        )
    )

    fun scenarioFor(query: String, hasImage: Boolean): MockChatScenario {
        val normalized = query.lowercase()
        val selected = when {
            hasImage -> listOf(product("mock_shoe_commute"), product("mock_shoe_walk"))
            listOf("平板", "记笔记", "网课", "学生").any { it in normalized } ->
                listOf(product("mock_tablet_air"), product("mock_tablet_note"))
            listOf("鞋", "通勤", "跑步").any { it in normalized } ->
                listOf(product("mock_shoe_commute"), product("mock_shoe_walk"))
            listOf("粉饼", "散粉", "控油", "油皮").any { it in normalized } ->
                listOf(product("mock_powder_oil"))
            listOf("耳机", "降噪", "蓝牙").any { it in normalized } ->
                listOf(product("mock_headphone_noise"))
            else -> listOf(product("mock_tablet_note"), product("mock_shoe_commute"), product("mock_powder_oil"))
        }
        return MockChatScenario(
            answer = buildAnswer(query, selected, hasImage),
            cards = selected.mapIndexed { index, item -> item.toCard(index + 1) }
        )
    }

    fun productDetail(productId: String): ProductDetail? {
        return products.firstOrNull { it.id == productId }?.toDetail()
    }

    fun sessionTitleFor(message: String): String {
        val topic = firstTopic(message)
        val modifier = firstModifier(message)
        val title = when {
            topic.isNotBlank() && modifier.isNotBlank() && modifier !in topic -> "$modifier$topic 选购"
            topic.isNotBlank() -> "$topic 选购"
            else -> message
                .replace("我想买", "")
                .replace("帮我推荐", "")
                .replace("帮我找", "")
                .replace("推荐", "")
                .trim()
        }
        return title.replace(" ", "").take(12).ifBlank { "导购会话" }
    }

    private fun buildAnswer(query: String, selected: List<MockProduct>, hasImage: Boolean): String {
        val lead = if (hasImage) {
            "我先按图片外观和文字条件帮你筛了一轮。"
        } else {
            "我先按你的需求帮你筛一轮。"
        }
        val primary = selected.first()
        val backup = selected.drop(1).firstOrNull()
        return buildString {
            append(lead)
            append("更建议你优先看「${primary.title}」，它的优势是${primary.reasons.joinToString("、")}。")
            if (backup != null) {
                append("如果你更在意价格或想要备选，可以再看看「${backup.title}」。")
            }
            append("这条回答来自 APK 内置 Mock 数据；后端启动后会自动走真实 RAG 和商品库。")
            if (query.contains("300") && selected.any { it.price <= 300 }) {
                append("这几款都控制在 300 元以内。")
            }
        }
    }

    private fun product(id: String): MockProduct = products.first { it.id == id }

    private fun firstTopic(text: String): String {
        return listOf("蓝牙耳机", "降噪耳机", "洗面奶", "平板", "电脑", "耳机", "通勤鞋", "跑鞋", "鞋", "粉饼", "散粉", "精华", "饮料")
            .firstOrNull { it in text }
            .orEmpty()
    }

    private fun firstModifier(text: String): String {
        return listOf("敏感肌", "油皮", "学生", "通勤", "跑步", "无糖", "低糖", "轻便")
            .firstOrNull { it in text }
            .orEmpty()
    }
}

private data class MockProduct(
    val id: String,
    val title: String,
    val category: String,
    val brand: String,
    val price: Int,
    val subtitle: String,
    val description: String,
    val rating: Double,
    val sales: Int,
    val stock: Int,
    val reasons: List<String>
) {
    fun toCard(index: Int): ProductCard = ProductCard(
        productId = id,
        title = title,
        subtitle = subtitle,
        price = price,
        originalPrice = price + 80 + index * 20,
        imageUrl = "",
        rating = rating,
        sales = sales,
        stockStatus = "in_stock",
        reasons = reasons,
        score = 0.92 - index * 0.04
    )

    fun toDetail(): ProductDetail = ProductDetail(
        id = id,
        title = title,
        category = category,
        brand = brand,
        price = price,
        description = description,
        rating = rating,
        sales = sales,
        stock = stock,
        imageUrl = ""
    )
}
