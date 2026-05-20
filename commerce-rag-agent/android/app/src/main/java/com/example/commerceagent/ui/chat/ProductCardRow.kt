package com.example.commerceagent.ui.chat

import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.example.commerceagent.data.api.ApiConfig
import com.example.commerceagent.data.model.ProductCard

@Composable
fun ProductCardRow(cards: List<ProductCard>, onOpenProduct: (String) -> Unit) {
    Row(
        modifier = Modifier
            .horizontalScroll(rememberScrollState())
            .padding(vertical = 8.dp)
    ) {
        cards.forEach { card ->
            Card(
                modifier = Modifier
                    .width(220.dp)
                    .padding(end = 10.dp)
                    .clickable { onOpenProduct(card.productId) }
            ) {
                Column(Modifier.padding(12.dp)) {
                    AsyncImage(
                        model = ApiConfig.BASE_URL + card.imageUrl,
                        contentDescription = card.title,
                        modifier = Modifier.height(96.dp)
                    )
                    Spacer(Modifier.height(8.dp))
                    Text(card.title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                    Text("￥${card.price}", color = MaterialTheme.colorScheme.tertiary)
                    Text(card.reasons.joinToString(" · "), style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}
