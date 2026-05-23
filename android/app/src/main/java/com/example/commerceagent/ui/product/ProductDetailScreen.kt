package com.example.commerceagent.ui.product

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AddShoppingCart
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.example.commerceagent.data.api.ApiConfig
import com.example.commerceagent.data.model.ProductDetail
import com.example.commerceagent.data.repository.CartRepository
import com.example.commerceagent.data.repository.ProductRepository
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProductDetailScreen(
    productId: String,
    onBack: () -> Unit,
    repository: ProductRepository = ProductRepository(),
    cartRepository: CartRepository = CartRepository()
) {
    var product by remember { mutableStateOf<ProductDetail?>(null) }
    var quantityInCart by remember { mutableStateOf(0) }
    var isAdding by remember { mutableStateOf(false) }
    var notice by remember { mutableStateOf<String?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()
    LaunchedEffect(productId) {
        runCatching { repository.getProduct(productId) }
            .onSuccess { product = it }
            .onFailure { error = it.message }
        runCatching { cartRepository.getCart() }
            .onSuccess { cart ->
                quantityInCart = cart.items.firstOrNull { it.product.id == productId }?.quantity ?: 0
            }
    }

    Scaffold(
        topBar = { TopAppBar(title = { Text("商品详情") }) },
        bottomBar = {
            ProductDetailBottomBar(
                quantityInCart = quantityInCart,
                isAdding = isAdding,
                onBack = onBack,
                onAddToCart = {
                    isAdding = true
                    notice = null
                    scope.launch {
                        runCatching { cartRepository.addItem(productId, quantity = 1) }
                            .onSuccess { cart ->
                                quantityInCart = cart.items.firstOrNull { it.product.id == productId }?.quantity ?: 0
                                notice = "已加入购物车，当前这款 $quantityInCart 件。"
                                error = null
                            }
                            .onFailure { error = it.message }
                        isAdding = false
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp)
        ) {
            if (error != null) Text(error.orEmpty(), color = MaterialTheme.colorScheme.error)
            if (notice != null) {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)
                ) {
                    Text(
                        notice.orEmpty(),
                        modifier = Modifier.padding(12.dp),
                        color = MaterialTheme.colorScheme.primary
                    )
                }
                Spacer(Modifier.height(12.dp))
            }
            product?.let {
                ProductImageHeader(product = it)
                Spacer(Modifier.height(12.dp))
                Text(it.title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                Text("￥${it.price}", color = MaterialTheme.colorScheme.tertiary, style = MaterialTheme.typography.titleLarge)
                Text("${it.brand} · ${it.category} · 评分 ${it.rating} · 库存 ${it.stock}")
                Spacer(Modifier.height(12.dp))
                Text(it.description)
            } ?: Text("加载中...")
            Spacer(Modifier.height(20.dp))
        }
    }
}

@Composable
private fun ProductDetailBottomBar(
    quantityInCart: Int,
    isAdding: Boolean,
    onBack: () -> Unit,
    onAddToCart: () -> Unit
) {
    Surface(
        tonalElevation = 3.dp,
        shadowElevation = 3.dp
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Button(onClick = onBack, modifier = Modifier.weight(0.9f)) {
                Text("返回聊天")
            }
            Spacer(Modifier.width(12.dp))
            FilledTonalButton(
                onClick = onAddToCart,
                enabled = !isAdding,
                modifier = Modifier.weight(1.3f)
            ) {
                Icon(Icons.Default.AddShoppingCart, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(6.dp))
                Text(
                    when {
                        isAdding -> "加入中..."
                        quantityInCart > 0 -> "再加一件 · $quantityInCart"
                        else -> "加入购物车"
                    }
                )
            }
        }
    }
}

@Composable
private fun ProductImageHeader(product: ProductDetail) {
    if (product.imageUrl.isBlank()) {
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .height(180.dp),
            color = MaterialTheme.colorScheme.primary.copy(alpha = 0.08f)
        ) {
            Box(contentAlignment = Alignment.Center) {
                Text(product.category, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
            }
        }
    } else {
        AsyncImage(
            model = ApiConfig.resolveUrl(product.imageUrl),
            contentDescription = product.title,
            modifier = Modifier.height(180.dp)
        )
    }
}
