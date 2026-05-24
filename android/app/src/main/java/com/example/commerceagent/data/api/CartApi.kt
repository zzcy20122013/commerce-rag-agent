package com.example.commerceagent.data.api

import com.example.commerceagent.data.model.Cart
import com.example.commerceagent.data.model.CheckoutResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

class CartApi(
    private val client: OkHttpClient = OkHttpClient()
) {
    suspend fun getCart(): Cart = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/cart")
            .get()
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("购物车加载失败：${response.code}")
            JSONObject(response.body?.string().orEmpty()).toCart()
        }
    }

    suspend fun addItem(productId: String, quantity: Int = 1): Cart = withContext(Dispatchers.IO) {
        val body = JSONObject()
            .put("product_id", productId)
            .put("quantity", quantity)
            .toString()
            .toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/cart/items")
            .post(body)
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("加购失败：${response.code}")
            JSONObject(response.body?.string().orEmpty()).toCart()
        }
    }

    suspend fun updateItem(position: Int, quantity: Int): Cart = withContext(Dispatchers.IO) {
        val body = JSONObject()
            .put("quantity", quantity)
            .toString()
            .toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/cart/items/$position")
            .put(body)
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("数量修改失败：${response.code}")
            JSONObject(response.body?.string().orEmpty()).toCart()
        }
    }

    suspend fun removeItem(position: Int): Cart = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/cart/items/$position")
            .delete()
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("删除失败：${response.code}")
            JSONObject(response.body?.string().orEmpty()).toCart()
        }
    }

    suspend fun checkout(): CheckoutResult = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/cart/checkout")
            .post(ByteArray(0).toRequestBody("application/json".toMediaType()))
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("提交订单失败：${response.code}")
            JSONObject(response.body?.string().orEmpty()).toCheckoutResult()
        }
    }
}
