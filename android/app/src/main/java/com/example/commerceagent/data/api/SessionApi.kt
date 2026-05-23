package com.example.commerceagent.data.api

import com.example.commerceagent.data.model.Session
import com.example.commerceagent.data.model.SessionMessage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject

class SessionApi(
    private val client: OkHttpClient = OkHttpClient()
) {
    suspend fun listSessions(): List<Session> = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/sessions")
            .get()
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) return@withContext emptyList()
            val array = JSONArray(response.body?.string().orEmpty())
            List(array.length()) { index -> array.getJSONObject(index).toSession() }
        }
    }

    suspend fun createSession(title: String = "新导购会话"): Session = withContext(Dispatchers.IO) {
        val body = JSONObject()
            .put("title", title)
            .toString()
            .toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/sessions")
            .post(body)
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("会话创建失败：${response.code}")
            JSONObject(response.body?.string().orEmpty()).toSession()
        }
    }

    suspend fun listMessages(sessionId: String): List<SessionMessage> = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/sessions/$sessionId/messages")
            .get()
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("历史消息加载失败：${response.code}")
            val array = JSONArray(response.body?.string().orEmpty())
            List(array.length()) { index -> array.getJSONObject(index).toSessionMessage() }
        }
    }

    suspend fun deleteSession(sessionId: String) = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/sessions/$sessionId")
            .delete()
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("会话删除失败：${response.code}")
        }
    }

    suspend fun updateSession(sessionId: String, title: String): Session = withContext(Dispatchers.IO) {
        val body = JSONObject()
            .put("title", title)
            .toString()
            .toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/sessions/$sessionId")
            .put(body)
            .build()
        client.newCall(request).execute().use { response ->
            val responseText = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                val detail = responseText.takeIf { it.isNotBlank() }?.let { "，$it" }.orEmpty()
                error("会话更新失败：${response.code}$detail")
            }
            JSONObject(responseText).toSession()
        }
    }
}
