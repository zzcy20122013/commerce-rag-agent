package com.example.commerceagent.data.api

import android.content.ContentResolver
import android.net.Uri
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

data class UploadResult(
    val uploadId: String,
    val previewUrl: String
)

class UploadApi(
    private val client: OkHttpClient = OkHttpClient()
) {
    suspend fun uploadImage(resolver: ContentResolver, uri: Uri): UploadResult = withContext(Dispatchers.IO) {
        val bytes = resolver.openInputStream(uri)?.use { it.readBytes() } ?: error("无法读取图片")
        val requestBody = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart(
                "file",
                "upload.png",
                bytes.toRequestBody("image/png".toMediaType())
            )
            .build()
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/upload/image")
            .post(requestBody)
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("上传失败：${response.code}")
            val json = JSONObject(response.body?.string().orEmpty())
            UploadResult(
                uploadId = json.optString("upload_id"),
                previewUrl = json.optString("preview_url")
            )
        }
    }
}
