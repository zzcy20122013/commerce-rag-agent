package com.example.commerceagent.data.api

import com.example.commerceagent.data.model.Order
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

class OrderApi(
    private val client: OkHttpClient = OkHttpClient()
) {
    suspend fun listOrders(): List<Order> = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/orders")
            .get()
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("订单加载失败：${response.code}")
            JSONObject(response.body?.string().orEmpty()).toOrderList()
        }
    }

    suspend fun pay(orderId: String): Order = postAction(orderId, "pay")

    suspend fun cancel(orderId: String): Order = postAction(orderId, "cancel")

    suspend fun ship(orderId: String): Order = postAction(orderId, "ship")

    suspend fun complete(orderId: String): Order = postAction(orderId, "complete")

    suspend fun refund(orderId: String, reason: String): Order = withContext(Dispatchers.IO) {
        val body = JSONObject()
            .put("reason", reason)
            .toString()
            .toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/orders/$orderId/refund")
            .post(body)
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("退款失败：${response.code}")
            JSONObject(response.body?.string().orEmpty()).toOrder()
        }
    }

    private suspend fun postAction(orderId: String, action: String): Order = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/orders/$orderId/$action")
            .post(ByteArray(0).toRequestBody("application/json".toMediaType()))
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("订单操作失败：${response.code}")
            JSONObject(response.body?.string().orEmpty()).toOrder()
        }
    }
}
