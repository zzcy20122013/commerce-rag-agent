package com.example.commerceagent.data.api

import com.example.commerceagent.data.model.ProductDetail
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject

class ProductApi(
    private val client: OkHttpClient = OkHttpClient()
) {
    suspend fun getProduct(productId: String): ProductDetail = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/products/$productId")
            .get()
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("商品加载失败：${response.code}")
            JSONObject(response.body?.string().orEmpty()).toProductDetail()
        }
    }
}
