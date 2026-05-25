package com.example.commerceagent.ui.checkout

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.commerceagent.data.model.CartItem
import com.example.commerceagent.data.model.DefaultShippingAddress
import com.example.commerceagent.data.model.ShippingAddress
import com.example.commerceagent.data.repository.CartRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class CheckoutUiState(
    val items: List<CartItem> = emptyList(),
    val total: Int = 0,
    val shippingAddress: ShippingAddress = DefaultShippingAddress,
    val isLoading: Boolean = false,
    val isSubmitting: Boolean = false,
    val error: String? = null,
    val notice: String? = null,
    val submittedOrderId: String? = null
) {
    val isAddressComplete: Boolean
        get() = shippingAddress.isComplete
}

class CheckoutViewModel(
    private val repository: CartRepository = CartRepository()
) : ViewModel() {
    private val _state = MutableStateFlow(CheckoutUiState())
    val state: StateFlow<CheckoutUiState> = _state.asStateFlow()

    fun loadCart() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null)
            runCatching { repository.getCart() }
                .onSuccess { cart ->
                    _state.value = _state.value.copy(
                        items = cart.items,
                        total = cart.total,
                        isLoading = false
                    )
                }
                .onFailure { error ->
                    _state.value = _state.value.copy(isLoading = false, error = error.message)
                }
        }
    }

    fun submitOrder() {
        val current = _state.value
        if (current.items.isEmpty() || current.isSubmitting) return
        if (!current.isAddressComplete) {
            _state.value = current.copy(notice = "请先补全收货人、手机号和收货地址。")
            return
        }

        viewModelScope.launch {
            _state.value = current.copy(isSubmitting = true, error = null, notice = null)
            runCatching { repository.checkout(current.shippingAddress) }
                .onSuccess { result ->
                    val orderId = result.orderIds.firstOrNull() ?: result.orders.firstOrNull()?.id
                    _state.value = _state.value.copy(
                        items = result.cart.items,
                        total = result.cart.total,
                        isSubmitting = false,
                        notice = "订单已提交，可在我的订单里继续支付和查看售后。",
                        submittedOrderId = orderId ?: "submitted"
                    )
                }
                .onFailure { error ->
                    _state.value = _state.value.copy(isSubmitting = false, error = error.message)
                }
        }
    }

    fun updateRecipientName(value: String) {
        _state.value = _state.value.copy(
            shippingAddress = _state.value.shippingAddress.copy(recipientName = value)
        )
    }

    fun updatePhone(value: String) {
        _state.value = _state.value.copy(
            shippingAddress = _state.value.shippingAddress.copy(phone = value)
        )
    }

    fun updateAddress(value: String) {
        _state.value = _state.value.copy(
            shippingAddress = _state.value.shippingAddress.copy(address = value)
        )
    }

    fun consumeNotice() {
        _state.value = _state.value.copy(notice = null)
    }

    fun consumeSubmittedOrder() {
        _state.value = _state.value.copy(submittedOrderId = null)
    }
}
