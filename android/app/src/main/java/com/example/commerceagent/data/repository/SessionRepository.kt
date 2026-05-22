package com.example.commerceagent.data.repository

import com.example.commerceagent.data.api.SessionApi
import com.example.commerceagent.data.model.Session
import com.example.commerceagent.data.model.SessionMessage

class SessionRepository(
    private val api: SessionApi = SessionApi()
) {
    suspend fun listSessions(): List<Session> = api.listSessions()

    suspend fun createSession(): Session = api.createSession()

    suspend fun listMessages(sessionId: String): List<SessionMessage> = api.listMessages(sessionId)

    suspend fun deleteSession(sessionId: String) = api.deleteSession(sessionId)
}
