package com.example.commerceagent.data.api

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

class FeedbackApi(
    private val client: OkHttpClient = OkHttpClient()
) {
    suspend fun submit(messageId: String, rating: Int) = withContext(Dispatchers.IO) {
        val body = JSONObject()
            .put("message_id", messageId)
            .put("rating", rating)
            .toString()
            .toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/feedback")
            .post(body)
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("反馈失败：${response.code}")
        }
    }
}
