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

data class ImageIntentResult(
    val prompt: String,
    val vlmEnabled: Boolean
)

class UploadApi(
    private val client: OkHttpClient = OkHttpClient()
) {
    suspend fun uploadImage(resolver: ContentResolver, uri: Uri): UploadResult = withContext(Dispatchers.IO) {
        val bytes = resolver.openInputStream(uri)?.use { it.readBytes() } ?: error("无法读取图片")
        uploadToBackend(bytes, resolver.getType(uri))
    }

    suspend fun recognizeImageIntent(uploadId: String): ImageIntentResult = withContext(Dispatchers.IO) {
        runCatching {
            recognizeImageIntentFromBackend(uploadId)
        }.getOrElse {
            ImageIntentResult(
                prompt = "请按这张图片找相似商品",
                vlmEnabled = false
            )
        }
    }

    private fun uploadToBackend(bytes: ByteArray, declaredContentType: String?): UploadResult {
        val metadata = detectUploadImageMetadata(bytes, declaredContentType)
        val requestBody = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart(
                "file",
                metadata.fileName,
                bytes.toRequestBody(metadata.contentType.toMediaType())
            )
            .build()
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/upload/image")
            .post(requestBody)
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("上传失败：${response.code}")
            val json = JSONObject(response.body?.string().orEmpty())
            return UploadResult(
                uploadId = json.optString("upload_id"),
                previewUrl = json.optString("preview_url")
            )
        }
    }

    private fun recognizeImageIntentFromBackend(uploadId: String): ImageIntentResult {
        val request = Request.Builder()
            .url("${ApiConfig.BASE_URL}/api/upload/image/$uploadId/intent")
            .post(ByteArray(0).toRequestBody(null))
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("图片识别失败：${response.code}")
            val json = JSONObject(response.body?.string().orEmpty())
            return ImageIntentResult(
                prompt = json.optString("prompt").ifBlank { "请按这张图片找相似商品" },
                vlmEnabled = json.optBoolean("vlm_enabled", false)
            )
        }
    }
}

data class UploadImageMetadata(
    val fileName: String,
    val contentType: String
)

fun detectUploadImageMetadata(bytes: ByteArray, declaredContentType: String?): UploadImageMetadata {
    val contentType = when {
        bytes.isJpeg() -> "image/jpeg"
        bytes.isPng() -> "image/png"
        bytes.isWebp() -> "image/webp"
        declaredContentType in setOf("image/jpeg", "image/png", "image/webp") -> declaredContentType!!
        else -> "image/jpeg"
    }
    val extension = when (contentType) {
        "image/jpeg" -> "jpg"
        "image/png" -> "png"
        "image/webp" -> "webp"
        else -> "jpg"
    }
    return UploadImageMetadata(fileName = "upload.$extension", contentType = contentType)
}

private fun ByteArray.isJpeg(): Boolean =
    size >= 3 &&
        this[0] == 0xFF.toByte() &&
        this[1] == 0xD8.toByte() &&
        this[2] == 0xFF.toByte()

private fun ByteArray.isPng(): Boolean =
    size >= 8 &&
        this[0] == 0x89.toByte() &&
        this[1] == 0x50.toByte() &&
        this[2] == 0x4E.toByte() &&
        this[3] == 0x47.toByte() &&
        this[4] == 0x0D.toByte() &&
        this[5] == 0x0A.toByte() &&
        this[6] == 0x1A.toByte() &&
        this[7] == 0x0A.toByte()

private fun ByteArray.isWebp(): Boolean =
    size >= 12 &&
        this[0] == 0x52.toByte() &&
        this[1] == 0x49.toByte() &&
        this[2] == 0x46.toByte() &&
        this[3] == 0x46.toByte() &&
        this[8] == 0x57.toByte() &&
        this[9] == 0x45.toByte() &&
        this[10] == 0x42.toByte() &&
        this[11] == 0x50.toByte()
