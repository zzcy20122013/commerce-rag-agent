package com.example.commerceagent.ui.chat

import android.content.ContentResolver
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.commerceagent.data.api.UploadApi
import com.example.commerceagent.data.model.CartItem
import com.example.commerceagent.data.model.ChatMessage
import com.example.commerceagent.data.model.MessageRole
import com.example.commerceagent.data.model.SseEvent
import com.example.commerceagent.data.repository.CartRepository
import com.example.commerceagent.data.repository.ChatRepository
import com.example.commerceagent.data.repository.FeedbackRepository
import com.example.commerceagent.data.repository.SessionRepository
import kotlinx.coroutines.flow.catch
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
    val cartItems: List<CartItem> = emptyList(),
    val cartTotal: Int = 0,
    val isCartLoading: Boolean = false,
    val cartNotice: String? = null,
    val error: String? = null
)

class ChatViewModel(
    private val repository: ChatRepository = ChatRepository(),
    private val uploadApi: UploadApi = UploadApi(),
    private val cartRepository: CartRepository = CartRepository(),
    private val feedbackRepository: FeedbackRepository = FeedbackRepository(),
    private val sessionRepository: SessionRepository = SessionRepository()
) : ViewModel() {
    private val _state = MutableStateFlow(ChatUiState())
    val state: StateFlow<ChatUiState> = _state.asStateFlow()

    fun setSession(sessionId: String?) {
        if (_state.value.sessionId == sessionId) return
        val current = _state.value
        _state.value = ChatUiState(
            sessionId = sessionId,
            isSending = sessionId != null,
            cartItems = current.cartItems,
            cartTotal = current.cartTotal
        )
        if (sessionId == null) return
        viewModelScope.launch {
            runCatching { sessionRepository.listMessages(sessionId) }
                .onSuccess { history ->
                    _state.value = _state.value.copy(
                        messages = history.map {
                            ChatMessage(
                                id = it.id,
                                role = if (it.role == "user") MessageRole.User else MessageRole.Assistant,
                                content = it.content,
                                productCards = it.productCards,
                                feedbackEnabled = it.productCards.isNotEmpty()
                            )
                        },
                        isSending = false,
                        error = null
                    )
                }
                .onFailure { _state.value = _state.value.copy(error = it.message, isSending = false) }
        }
    }

    fun startNewChat() {
        val current = _state.value
        _state.value = ChatUiState(
            cartItems = current.cartItems,
            cartTotal = current.cartTotal
        )
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

    fun loadCart() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isCartLoading = true)
            runCatching { cartRepository.getCart() }
                .onSuccess { cart ->
                    _state.value = _state.value.copy(
                        cartItems = cart.items,
                        cartTotal = cart.total,
                        isCartLoading = false,
                        error = null
                    )
                }
                .onFailure { _state.value = _state.value.copy(error = it.message, isCartLoading = false) }
        }
    }

    fun addProductToCart(productId: String) {
        if (productId.isBlank()) return
        viewModelScope.launch {
            _state.value = _state.value.copy(isCartLoading = true)
            runCatching { cartRepository.addItem(productId, quantity = 1) }
                .onSuccess { cart ->
                    val addedItem = cart.items.firstOrNull { it.product.id == productId }
                    val title = addedItem?.product?.title?.takeIf { it.isNotBlank() } ?: "这件商品"
                    val quantity = addedItem?.quantity ?: 1
                    _state.value = _state.value.copy(
                        cartItems = cart.items,
                        cartTotal = cart.total,
                        isCartLoading = false,
                        error = null,
                        cartNotice = "已把「$title」加入购物车。当前这款 $quantity 件，购物车合计约 ${cart.total} 元。"
                    )
                }
                .onFailure { _state.value = _state.value.copy(error = it.message, isCartLoading = false) }
        }
    }

    fun consumeCartNotice() {
        _state.value = _state.value.copy(cartNotice = null)
    }

    fun updateCartQuantity(position: Int, quantity: Int) {
        viewModelScope.launch {
            _state.value = _state.value.copy(isCartLoading = true)
            val result = if (quantity <= 0) {
                runCatching { cartRepository.removeItem(position) }
            } else {
                runCatching { cartRepository.updateItem(position, quantity) }
            }
            result
                .onSuccess { cart ->
                    _state.value = _state.value.copy(
                        cartItems = cart.items,
                        cartTotal = cart.total,
                        isCartLoading = false,
                        error = null
                    )
                }
                .onFailure { _state.value = _state.value.copy(error = it.message, isCartLoading = false) }
        }
    }

    fun removeCartItem(position: Int) {
        viewModelScope.launch {
            _state.value = _state.value.copy(isCartLoading = true)
            runCatching { cartRepository.removeItem(position) }
                .onSuccess { cart ->
                    _state.value = _state.value.copy(
                        cartItems = cart.items,
                        cartTotal = cart.total,
                        isCartLoading = false,
                        error = null
                    )
                }
                .onFailure { _state.value = _state.value.copy(error = it.message, isCartLoading = false) }
        }
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
            repository.streamChat(text, state.value.sessionId, state.value.uploadId)
                .catch { error ->
                    failAssistant(assistantTempId, error.message ?: "网络异常，请稍后再试。")
                }
                .collect { event ->
                    when (event) {
                        is SseEvent.Message -> applyAssistantText(assistantTempId, event)
                        is SseEvent.ProductCards -> updateAssistant(assistantTempId) {
                            it.copy(productCards = event.cards, feedbackEnabled = it.feedbackEnabled || event.cards.isNotEmpty())
                        }
                        is SseEvent.Trace -> Unit
                        is SseEvent.Error -> failAssistant(assistantTempId, event.message)
                        SseEvent.Done -> {
                            updateAssistant(assistantTempId) { it.copy(isStreaming = false) }
                            _state.value = _state.value.copy(isSending = false, uploadId = null, previewUrl = null)
                        }
                    }
                }
        }
    }

    fun sendFeedback(messageId: String, rating: Int, reason: String = "") {
        viewModelScope.launch {
            runCatching { feedbackRepository.submit(messageId, rating, reason) }
                .onSuccess {
                    updateAssistant(messageId) {
                        it.copy(
                            feedbackRating = rating,
                            feedbackReason = reason.takeIf { value -> value.isNotBlank() }
                        )
                    }
                }
                .onFailure { _state.value = _state.value.copy(error = it.message) }
        }
    }

    private fun applyAssistantText(tempId: String, event: SseEvent.Message) {
        val resolvedId = event.messageId ?: tempId
        _state.value = _state.value.copy(
            sessionId = event.sessionId ?: _state.value.sessionId,
            messages = _state.value.messages.map {
                if (it.id == tempId || it.id == resolvedId) {
                    it.copy(
                        id = resolvedId,
                        content = it.content + event.delta,
                        feedbackEnabled = it.feedbackEnabled || event.feedbackEnabled
                    )
                } else {
                    it
                }
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

    private fun failAssistant(messageId: String, message: String) {
        updateAssistant(messageId) {
            it.copy(
                content = "这次请求没成功：$message",
                isStreaming = false,
                feedbackEnabled = false
            )
        }
        _state.value = _state.value.copy(isSending = false, error = message)
    }
}
