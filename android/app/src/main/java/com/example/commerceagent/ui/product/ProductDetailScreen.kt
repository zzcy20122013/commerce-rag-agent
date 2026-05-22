package com.example.commerceagent.ui.product

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.example.commerceagent.data.api.ApiConfig
import com.example.commerceagent.data.api.ProductApi
import com.example.commerceagent.data.model.ProductDetail

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProductDetailScreen(productId: String, onBack: () -> Unit) {
    var product by remember { mutableStateOf<ProductDetail?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(productId) {
        runCatching { ProductApi().getProduct(productId) }
            .onSuccess { product = it }
            .onFailure { error = it.message }
    }

    Scaffold(
        topBar = { TopAppBar(title = { Text("商品详情") }) }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
        ) {
            if (error != null) Text(error.orEmpty(), color = MaterialTheme.colorScheme.error)
            product?.let {
                AsyncImage(
                    model = ApiConfig.resolveUrl(it.imageUrl),
                    contentDescription = it.title,
                    modifier = Modifier.height(180.dp)
                )
                Spacer(Modifier.height(12.dp))
                Text(it.title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                Text("￥${it.price}", color = MaterialTheme.colorScheme.tertiary, style = MaterialTheme.typography.titleLarge)
                Text("${it.brand} · ${it.category} · 评分 ${it.rating} · 库存 ${it.stock}")
                Spacer(Modifier.height(12.dp))
                Text(it.description)
            } ?: Text("加载中...")
            Spacer(Modifier.height(20.dp))
            Button(onClick = onBack) {
                Text("返回聊天")
            }
        }
    }
}
