package com.example.commerceagent.ui.orders

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.commerceagent.data.model.Order
import com.example.commerceagent.data.repository.OrderRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class OrdersUiState(
    val orders: List<Order> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
    val notice: String? = null
)

class OrdersViewModel(
    private val repository: OrderRepository = OrderRepository()
) : ViewModel() {
    private val _state = MutableStateFlow(OrdersUiState())
    val state: StateFlow<OrdersUiState> = _state.asStateFlow()

    fun loadOrders() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true)
            runCatching { repository.listOrders() }
                .onSuccess { orders ->
                    _state.value = _state.value.copy(orders = orders, isLoading = false, error = null)
                }
                .onFailure { error ->
                    _state.value = _state.value.copy(isLoading = false, error = error.message)
                }
        }
    }

    fun pay(orderId: String) = runAction("支付成功") { repository.pay(orderId) }

    fun cancel(orderId: String) = runAction("订单已取消") { repository.cancel(orderId) }

    fun ship(orderId: String) = runAction("已模拟发货") { repository.ship(orderId) }

    fun complete(orderId: String) = runAction("已确认收货") { repository.complete(orderId) }

    fun refund(orderId: String) = runAction("退款已完成") { repository.refund(orderId, "项目路演模拟售后") }

    fun delete(orderId: String) {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true)
            runCatching { repository.delete(orderId) }
                .onSuccess {
                    _state.value = _state.value.copy(
                        orders = _state.value.orders.filterNot { it.id == orderId },
                        isLoading = false,
                        error = null,
                        notice = "订单记录已删除"
                    )
                }
                .onFailure { error ->
                    _state.value = _state.value.copy(isLoading = false, error = error.message)
                }
        }
    }

    fun consumeNotice() {
        _state.value = _state.value.copy(notice = null)
    }

    private fun runAction(notice: String, action: suspend () -> Order) {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true)
            runCatching { action() }
                .onSuccess { updated ->
                    _state.value = _state.value.copy(
                        orders = _state.value.orders.map { if (it.id == updated.id) updated else it },
                        isLoading = false,
                        error = null,
                        notice = notice
                    )
                }
                .onFailure { error ->
                    _state.value = _state.value.copy(isLoading = false, error = error.message)
                }
        }
    }
}
