package com.example.commerceagent.data.repository

import com.example.commerceagent.data.api.SessionApi
import com.example.commerceagent.data.mock.MockSessionStore
import com.example.commerceagent.data.model.Session
import com.example.commerceagent.data.model.SessionMessage

class SessionRepository(
    private val api: SessionApi = SessionApi()
) {
    suspend fun listSessions(): List<Session> {
        return runCatching { api.listSessions() }
            .getOrElse { MockSessionStore.list() }
            .ifEmpty { MockSessionStore.list() }
    }

    suspend fun createSession(): Session = api.createSession()

    suspend fun listMessages(sessionId: String): List<SessionMessage> = api.listMessages(sessionId)

    suspend fun deleteSession(sessionId: String) {
        runCatching { api.deleteSession(sessionId) }
        MockSessionStore.delete(sessionId)
    }

    suspend fun renameSession(sessionId: String, title: String): Session {
        return runCatching { api.updateSession(sessionId, title) }
            .getOrElse { MockSessionStore.rename(sessionId, title) }
    }
}
