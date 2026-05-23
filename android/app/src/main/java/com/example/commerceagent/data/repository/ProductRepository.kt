package com.example.commerceagent.data.repository

import com.example.commerceagent.data.api.ProductApi
import com.example.commerceagent.data.mock.MockCommerceData
import com.example.commerceagent.data.model.ProductDetail

class ProductRepository(
    private val api: ProductApi = ProductApi()
) {
    suspend fun getProduct(productId: String): ProductDetail {
        return runCatching { api.getProduct(productId) }
            .getOrElse { error ->
                MockCommerceData.productDetail(productId) ?: throw error
            }
    }
}
