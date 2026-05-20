package com.example.commerceagent.data.repository

import com.example.commerceagent.data.api.FeedbackApi

class FeedbackRepository(
    private val api: FeedbackApi = FeedbackApi()
) {
    suspend fun submit(messageId: String, rating: Int) {
        api.submit(messageId, rating)
    }
}
