package com.example.commerceagent.ui.chat

import android.content.ContentResolver
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.commerceagent.data.api.UploadApi
import com.example.commerceagent.data.model.ChatMessage
import com.example.commerceagent.data.model.MessageRole
import com.example.commerceagent.data.model.SseEvent
import com.example.commerceagent.data.repository.ChatRepository
import com.example.commerceagent.data.repository.FeedbackRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.UUID

data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val input: String = "",
    val isSending: Boolean = false,
    val sessionId: String? = null,
    val uploadId: String? = null,
    val previewUrl: String? = null,
    val error: String? = null
)

class ChatViewModel(
    private val repository: ChatRepository = ChatRepository(),
    private val uploadApi: UploadApi = UploadApi(),
    private val feedbackRepository: FeedbackRepository = FeedbackRepository()
) : ViewModel() {
    private val _state = MutableStateFlow(ChatUiState())
    val state: StateFlow<ChatUiState> = _state.asStateFlow()

    fun setSession(sessionId: String?) {
        _state.value = _state.value.copy(sessionId = sessionId)
    }

    fun updateInput(value: String) {
        _state.value = _state.value.copy(input = value)
    }

    fun uploadImage(resolver: ContentResolver, uri: Uri) {
        viewModelScope.launch {
            runCatching { uploadApi.uploadImage(resolver, uri) }
                .onSuccess { _state.value = _state.value.copy(uploadId = it.uploadId, previewUrl = it.previewUrl, error = null) }
                .onFailure { _state.value = _state.value.copy(error = it.message) }
        }
    }

    fun send() {
        val text = state.value.input.trim()
        sendText(text)
    }

    fun sendPrompt(text: String) {
        sendText(text.trim())
    }

    private fun sendText(text: String) {
        if (text.isBlank() || state.value.isSending) return
        val assistantTempId = "assistant_${UUID.randomUUID().toString().take(8)}"
        _state.value = state.value.copy(
            input = "",
            isSending = true,
            messages = state.value.messages + ChatMessage(id = UUID.randomUUID().toString(), role = MessageRole.User, content = text) +
                ChatMessage(id = assistantTempId, role = MessageRole.Assistant, content = "", isStreaming = true),
            error = null
        )
        viewModelScope.launch {
            repository.streamChat(text, state.value.sessionId, state.value.uploadId).collect { event ->
                when (event) {
                    is SseEvent.Message -> applyAssistantText(assistantTempId, event)
                    is SseEvent.ProductCards -> updateAssistant(assistantTempId) { it.copy(productCards = event.cards) }
                    is SseEvent.Trace -> Unit
                    is SseEvent.Error -> _state.value = _state.value.copy(error = event.message, isSending = false)
                    SseEvent.Done -> {
                        updateAssistant(assistantTempId) { it.copy(isStreaming = false) }
                        _state.value = _state.value.copy(isSending = false, uploadId = null, previewUrl = null)
                    }
                }
            }
        }
    }

    fun sendFeedback(messageId: String, rating: Int) {
        viewModelScope.launch {
            runCatching { feedbackRepository.submit(messageId, rating) }
                .onSuccess { updateAssistant(messageId) { it.copy(feedbackRating = rating) } }
                .onFailure { _state.value = _state.value.copy(error = it.message) }
        }
    }

    private fun applyAssistantText(tempId: String, event: SseEvent.Message) {
        val resolvedId = event.messageId ?: tempId
        _state.value = _state.value.copy(
            sessionId = event.sessionId ?: _state.value.sessionId,
            messages = _state.value.messages.map {
                if (it.id == tempId) it.copy(id = resolvedId, content = it.content + event.delta) else it
            }
        )
    }

    private fun updateAssistant(messageId: String, block: (ChatMessage) -> ChatMessage) {
        _state.value = _state.value.copy(
            messages = _state.value.messages.map { message ->
                if (message.id == messageId || message.role == MessageRole.Assistant && message.isStreaming) block(message) else message
            }
        )
    }
}
