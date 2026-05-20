package com.example.commerceagent.data.api

import com.example.commerceagent.data.model.Session
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
}
