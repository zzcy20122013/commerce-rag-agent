package com.example.commerceagent.data.model

data class ProductDetail(
    val id: String,
    val title: String,
    val category: String,
    val brand: String,
    val price: Int,
    val description: String,
    val rating: Double,
    val sales: Int,
    val stock: Int,
    val imageUrl: String
)
