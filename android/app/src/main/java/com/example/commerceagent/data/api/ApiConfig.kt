package com.example.commerceagent.data.api

object ApiConfig {
    const val BASE_URL = "http://10.0.2.2:8000"

    fun resolveUrl(pathOrUrl: String): String {
        if (pathOrUrl.isBlank()) return ""
        if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
            return pathOrUrl
        }
        return BASE_URL + pathOrUrl
    }
}
