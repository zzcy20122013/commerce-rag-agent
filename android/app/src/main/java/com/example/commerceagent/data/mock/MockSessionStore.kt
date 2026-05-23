package com.example.commerceagent.data.mock

import com.example.commerceagent.data.model.Session
import java.time.Instant

object MockSessionStore {
    private val sessions = linkedMapOf<String, Session>()

    fun upsertFromFirstMessage(sessionId: String, message: String): Session {
        val existing = sessions[sessionId]
        if (existing != null && existing.title !in setOf("导购会话", "新导购会话")) {
            return existing
        }
        val session = Session(
            id = sessionId,
            title = MockCommerceData.sessionTitleFor(message),
            updatedAt = Instant.now().toString()
        )
        sessions[sessionId] = session
        return session
    }

    fun list(): List<Session> = sessions.values.sortedByDescending { it.updatedAt }

    fun rename(sessionId: String, title: String): Session {
        val session = Session(
            id = sessionId,
            title = title,
            updatedAt = Instant.now().toString()
        )
        sessions[sessionId] = session
        return session
    }

    fun delete(sessionId: String) {
        sessions.remove(sessionId)
    }
}
