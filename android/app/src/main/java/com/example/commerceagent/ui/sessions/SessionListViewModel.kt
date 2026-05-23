package com.example.commerceagent.ui.sessions

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.commerceagent.data.model.Session
import com.example.commerceagent.data.repository.SessionRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class SessionListUiState(
    val sessions: List<Session> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

class SessionListViewModel(
    private val repository: SessionRepository = SessionRepository()
) : ViewModel() {
    private val _state = MutableStateFlow(SessionListUiState())
    val state: StateFlow<SessionListUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null)
            runCatching { repository.listSessions() }
                .onSuccess { _state.value = SessionListUiState(sessions = it) }
                .onFailure { _state.value = SessionListUiState(error = it.message) }
        }
    }

    fun createSession(onCreated: (String) -> Unit) {
        viewModelScope.launch {
            runCatching { repository.createSession() }
                .onSuccess { onCreated(it.id) }
                .onFailure { _state.value = _state.value.copy(error = it.message) }
        }
    }

    fun deleteSession(sessionId: String, onDeleted: () -> Unit = {}) {
        viewModelScope.launch {
            runCatching { repository.deleteSession(sessionId) }
                .onSuccess {
                    onDeleted()
                    refresh()
                }
                .onFailure { _state.value = _state.value.copy(error = it.message) }
        }
    }

    fun renameSession(sessionId: String, newTitle: String) {
        val title = newTitle.trim()
        if (title.isBlank()) {
            _state.value = _state.value.copy(error = "会话名称不能为空")
            return
        }

        viewModelScope.launch {
            runCatching { repository.renameSession(sessionId, title) }
                .onSuccess { updatedSession ->
                    _state.value = _state.value.copy(
                        sessions = _state.value.sessions.map { session ->
                            if (session.id == updatedSession.id) updatedSession else session
                        },
                        error = null
                    )
                    refresh()
                }
                .onFailure { _state.value = _state.value.copy(error = it.message) }
        }
    }
}
