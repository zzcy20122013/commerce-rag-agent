package com.example.commerceagent.data.api

import com.example.commerceagent.data.model.SseEvent
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class ChatSseClient(
    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .readTimeout(180, TimeUnit.SECONDS)
        .callTimeout(240, TimeUnit.SECONDS)
        .build()
) {
    fun streamChat(
        message: String,
        sessionId: String?,
        uploadId: String?
    ): Flow<SseEvent> = flow {
        val body = JSONObject()
            .put("message", message)
            .apply {
                if (!sessionId.isNullOrBlank()) put("session_id", sessionId)
                if (!uploadId.isNullOrBlank()) put("upload_id", uploadId)
            }
            .toString()
            .toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/chat/stream")
            .post(body)
            .build()

        try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    emit(SseEvent.Error("请求失败：${response.code}"))
                    return@use
                }
                val source = response.body?.source() ?: return@use
                var eventName = ""
                while (!source.exhausted()) {
                    val line = source.readUtf8Line().orEmpty()
                    when {
                        line.startsWith("event:") -> eventName = line.removePrefix("event:").trim()
                        line.startsWith("data:") -> parseEvent(eventName, line.removePrefix("data:").trim())?.let { emit(it) }
                    }
                }
            }
        } catch (error: Exception) {
            emit(SseEvent.Error(error.message ?: "网络异常"))
        }
    }.flowOn(Dispatchers.IO)

    private fun parseEvent(eventName: String, data: String): SseEvent? {
        return when (eventName) {
            "message" -> {
                val json = JSONObject(data)
                SseEvent.Message(
                    delta = json.optString("content"),
                    messageId = json.optString("message_id").takeIf { it.isNotBlank() },
                    sessionId = json.optString("session_id").takeIf { it.isNotBlank() },
                    feedbackEnabled = json.optBoolean("feedback_enabled", false)
                )
            }
            "product_cards" -> {
                val array = JSONArray(data)
                SseEvent.ProductCards(List(array.length()) { index -> array.getJSONObject(index).toProductCard() })
            }
            "trace" -> SseEvent.Trace(data)
            "error" -> SseEvent.Error(data)
            "done" -> SseEvent.Done
            else -> null
        }
    }
}
