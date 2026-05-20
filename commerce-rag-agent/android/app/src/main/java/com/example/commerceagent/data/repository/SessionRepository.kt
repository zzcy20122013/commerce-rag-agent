package com.example.commerceagent.data.repository

import com.example.commerceagent.data.api.SessionApi
import com.example.commerceagent.data.model.Session

class SessionRepository(
    private val api: SessionApi = SessionApi()
) {
    suspend fun listSessions(): List<Session> = api.listSessions()

    suspend fun createSession(): Session = api.createSession()
}
