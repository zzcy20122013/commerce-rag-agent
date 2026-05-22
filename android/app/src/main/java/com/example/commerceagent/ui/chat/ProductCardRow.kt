package com.example.commerceagent.ui.chat

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.example.commerceagent.data.api.ApiConfig
import com.example.commerceagent.data.model.ProductCard

@Composable
fun ProductCardRow(cards: List<ProductCard>, onOpenProduct: (String) -> Unit) {
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
                onOpenProduct = onOpenProduct
            )
        }
    }
}

@Composable
private fun ProductRecommendationCard(
    card: ProductCard,
    badge: String,
    onOpenProduct: (String) -> Unit
) {
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
            AsyncImage(
                model = ApiConfig.resolveUrl(card.imageUrl),
                contentDescription = card.title,
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .size(88.dp)
                    .padding(end = 10.dp)
            )
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
                if (card.reasons.isNotEmpty()) {
                    Spacer(Modifier.height(6.dp))
                    Text(
                        text = card.reasons.take(3).joinToString(" · "),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.secondary,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
        }
    }
}
