package com.example.commerceagent.data.model

data class ProductCard(
    val productId: String,
    val title: String,
    val subtitle: String,
    val price: Int,
    val originalPrice: Int,
    val imageUrl: String,
    val rating: Double,
    val sales: Int,
    val stockStatus: String,
    val reasons: List<String>,
    val score: Double
)
