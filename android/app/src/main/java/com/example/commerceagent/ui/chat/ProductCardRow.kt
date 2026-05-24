package com.example.commerceagent.ui.chat

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AddShoppingCart
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.example.commerceagent.data.api.ApiConfig
import com.example.commerceagent.data.model.ProductCard
import com.example.commerceagent.data.model.ProductEvidence

data class ProductReasonUi(
    val highlights: List<String>,
    val risk: String?
)

data class ProductEvidenceUiItem(
    val source: String,
    val text: String
)

data class ProductEvidenceUi(
    val title: String,
    val sources: List<String>,
    val highlight: String?
)

fun buildProductReasonUi(reasons: List<String>): ProductReasonUi {
    val cleaned = reasons
        .map { it.trim() }
        .filter { it.isNotEmpty() }
        .distinct()
    val risk = cleaned.firstOrNull { it.startsWith("差评提醒") || it.contains("风险") }
    val highlights = cleaned
        .filter { it != risk }
        .take(4)
    return ProductReasonUi(highlights = highlights, risk = risk)
}

fun buildProductEvidenceUi(
    sourceSummary: String,
    evidence: List<ProductEvidenceUiItem>,
    reasons: List<String> = emptyList()
): ProductEvidenceUi {
    val sources = evidence
        .map { it.source.trim() }
        .filter { it.isNotEmpty() }
        .distinct()
        .take(3)
    val title = sourceSummary.trim().ifBlank {
        reasons
            .map { it.trim() }
            .filter { it.isNotEmpty() && !it.startsWith("差评提醒") && !it.contains("风险") }
            .distinct()
            .take(2)
            .joinToString("、", prefix = "推荐依据：")
            .takeIf { it != "推荐依据：" }
            .orEmpty()
    }
    val highlight = evidence
        .map { it.text.trim() }
        .firstOrNull { it.isNotEmpty() }
    return ProductEvidenceUi(title = title, sources = sources, highlight = highlight)
}

@Composable
fun ProductCardRow(
    cards: List<ProductCard>,
    cartQuantities: Map<String, Int>,
    onOpenProduct: (String) -> Unit,
    onAddToCart: (String) -> Unit
) {
    Column(
        modifier = Modifier.padding(vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        cards.take(3).forEachIndexed { index, card ->
            ProductRecommendationCard(
                card = card,
                badge = when (index) {
                    0 -> "主推"
                    1 -> "备选"
                    else -> "再看看"
                },
                quantityInCart = cartQuantities[card.productId] ?: 0,
                onOpenProduct = onOpenProduct,
                onAddToCart = onAddToCart
            )
        }
    }
}

@Composable
private fun ProductRecommendationCard(
    card: ProductCard,
    badge: String,
    quantityInCart: Int,
    onOpenProduct: (String) -> Unit,
    onAddToCart: (String) -> Unit
) {
    val reasonUi = buildProductReasonUi(card.reasons)
    val evidenceUi = buildProductEvidenceUi(
        sourceSummary = card.sourceSummary,
        evidence = card.evidence.map { it.toUiItem() },
        reasons = card.reasons
    )
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onOpenProduct(card.productId) },
        shape = RoundedCornerShape(10.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.Top
        ) {
            ProductCardImage(card = card)
            Spacer(Modifier.width(2.dp))
            Column(modifier = Modifier.weight(1f)) {
                Surface(
                    color = MaterialTheme.colorScheme.primary.copy(alpha = 0.12f),
                    contentColor = MaterialTheme.colorScheme.primary,
                    shape = RoundedCornerShape(999.dp)
                ) {
                    Text(
                        text = badge,
                        style = MaterialTheme.typography.labelSmall,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                    )
                }
                Spacer(Modifier.height(6.dp))
                Text(
                    text = card.title,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    text = card.subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.68f),
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(Modifier.height(8.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = "￥${card.price}",
                        color = MaterialTheme.colorScheme.tertiary,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(Modifier.width(10.dp))
                    Text(
                        text = "评分 ${"%.1f".format(card.rating)} · 销量 ${card.sales}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.62f)
                    )
                }
                if (reasonUi.highlights.isNotEmpty()) {
                    Spacer(Modifier.height(6.dp))
                    Text(
                        text = reasonUi.highlights.joinToString(" · "),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.secondary,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                }
                if (!reasonUi.risk.isNullOrBlank()) {
                    Spacer(Modifier.height(6.dp))
                    Surface(
                        color = MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.5f),
                        contentColor = MaterialTheme.colorScheme.onErrorContainer,
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 5.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = Icons.Default.WarningAmber,
                                contentDescription = null,
                                modifier = Modifier.size(14.dp)
                            )
                            Spacer(Modifier.width(4.dp))
                            Text(
                                text = reasonUi.risk,
                                style = MaterialTheme.typography.labelSmall,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
                    }
                }
                if (evidenceUi.title.isNotBlank()) {
                    Spacer(Modifier.height(6.dp))
                    ProductEvidenceBlock(evidenceUi = evidenceUi)
                }
                Spacer(Modifier.height(8.dp))
                FilledTonalButton(
                    onClick = { onAddToCart(card.productId) },
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(Icons.Default.AddShoppingCart, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(6.dp))
                    Text(if (quantityInCart > 0) "再加一件 · $quantityInCart" else "加入购物车")
                }
            }
        }
    }
}

@Composable
private fun ProductEvidenceBlock(evidenceUi: ProductEvidenceUi) {
    Surface(
        color = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.42f),
        contentColor = MaterialTheme.colorScheme.onSecondaryContainer,
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(modifier = Modifier.padding(horizontal = 8.dp, vertical = 6.dp)) {
            Text(
                text = evidenceUi.title,
                style = MaterialTheme.typography.labelSmall,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
            if (evidenceUi.sources.isNotEmpty()) {
                Spacer(Modifier.height(3.dp))
                Text(
                    text = evidenceUi.sources.joinToString(" · "),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.72f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
            if (!evidenceUi.highlight.isNullOrBlank()) {
                Spacer(Modifier.height(3.dp))
                Text(
                    text = evidenceUi.highlight,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.78f),
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
    }
}

@Composable
private fun ProductCardImage(card: ProductCard) {
    val imageModifier = Modifier
        .size(88.dp)
        .padding(end = 10.dp)
        .clip(RoundedCornerShape(12.dp))
    if (card.imageUrl.isBlank()) {
        Surface(
            modifier = imageModifier,
            color = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)
        ) {
            Box(contentAlignment = Alignment.Center) {
                Text(
                    text = card.title.take(2),
                    color = MaterialTheme.colorScheme.primary,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    } else {
        AsyncImage(
            model = ApiConfig.resolveUrl(card.imageUrl),
            contentDescription = card.title,
            contentScale = ContentScale.Crop,
            modifier = imageModifier
        )
    }
}

private fun ProductEvidence.toUiItem(): ProductEvidenceUiItem {
    return ProductEvidenceUiItem(source = source, text = text)
}
