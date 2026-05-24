package com.example.commerceagent.ui.orders

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material.icons.filled.LocalShipping
import androidx.compose.material.icons.filled.Payment
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.example.commerceagent.data.api.ApiConfig
import com.example.commerceagent.data.model.Order
import com.example.commerceagent.data.model.OrderItem

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OrdersScreen(
    onBack: () -> Unit,
    viewModel: OrdersViewModel = viewModel()
) {
    val state by viewModel.state.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(Unit) {
        viewModel.loadOrders()
    }
    LaunchedEffect(state.notice) {
        val notice = state.notice
        if (!notice.isNullOrBlank()) {
            snackbarHostState.showSnackbar(notice)
            viewModel.consumeNotice()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("我的订单", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "返回")
                    }
                },
                actions = {
                    if (state.isLoading) {
                        CircularProgressIndicator(modifier = Modifier.size(22.dp), strokeWidth = 2.dp)
                    }
                }
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            contentPadding = PaddingValues(bottom = 24.dp)
        ) {
            state.error?.let { error ->
                item {
                    AssistChip(
                        onClick = viewModel::loadOrders,
                        label = { Text(error) },
                        leadingIcon = { Icon(Icons.Default.Refresh, contentDescription = null) }
                    )
                }
            }
            if (state.orders.isEmpty() && !state.isLoading) {
                item {
                    EmptyOrdersCard()
                }
            }
            items(state.orders, key = { it.id }) { order ->
                OrderCard(
                    order = order,
                    onPay = { viewModel.pay(order.id) },
                    onCancel = { viewModel.cancel(order.id) },
                    onShip = { viewModel.ship(order.id) },
                    onComplete = { viewModel.complete(order.id) },
                    onRefund = { viewModel.refund(order.id) },
                    onDelete = { viewModel.delete(order.id) }
                )
            }
        }
    }
}

@Composable
private fun EmptyOrdersCard() {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 48.dp),
        shape = RoundedCornerShape(16.dp),
        color = Color(0xFFF6F3FF)
    ) {
        Column(modifier = Modifier.padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text("还没有订单", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(8.dp))
            Text("从购物车提交订单后，会在这里看到支付、物流和售后状态。", color = Color.Gray)
        }
    }
}

@Composable
private fun OrderCard(
    order: Order,
    onPay: () -> Unit,
    onCancel: () -> Unit,
    onShip: () -> Unit,
    onComplete: () -> Unit,
    onRefund: () -> Unit,
    onDelete: () -> Unit
) {
    var showDeleteConfirm by remember { mutableStateOf(false) }
    if (showDeleteConfirm) {
        AlertDialog(
            onDismissRequest = { showDeleteConfirm = false },
            title = { Text("删除订单记录") },
            text = { Text("这会从订单历史中删除该记录，后端数据库也会同步删除。") },
            confirmButton = {
                TextButton(
                    onClick = {
                        showDeleteConfirm = false
                        onDelete()
                    }
                ) { Text("删除", color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = {
                TextButton(onClick = { showDeleteConfirm = false }) { Text("取消") }
            }
        )
    }

    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 1.dp,
        border = BorderStroke(1.dp, Color(0xFFEDEAF8))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(order.id, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text(order.createdAt.take(19).replace("T", " "), color = Color.Gray, style = MaterialTheme.typography.bodySmall)
                }
                StatusChip(order.status)
            }
            Spacer(Modifier.height(12.dp))
            order.items.forEach { item ->
                OrderItemRow(item)
                Spacer(Modifier.height(10.dp))
            }
            HorizontalDivider()
            Spacer(Modifier.height(10.dp))
            Text(order.logisticsStatus, style = MaterialTheme.typography.bodySmall)
            Text(order.returnStatus, color = Color.Gray, style = MaterialTheme.typography.bodySmall)
            Spacer(Modifier.height(12.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("合计 ￥${order.total}", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Spacer(Modifier.weight(1f))
            }
            Spacer(Modifier.height(12.dp))
            OrderActions(order.status, onPay, onCancel, onShip, onComplete, onRefund)
            if (canDeleteOrderRecord(order.status)) {
                Spacer(Modifier.height(8.dp))
                FilledTonalButton(
                    onClick = { showDeleteConfirm = true },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.filledTonalButtonColors(contentColor = MaterialTheme.colorScheme.error)
                ) {
                    Icon(Icons.Default.DeleteOutline, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("删除记录")
                }
            }
        }
    }
}

private fun canDeleteOrderRecord(status: String): Boolean {
    return status in setOf("已取消", "已退款", "已完成")
}

@Composable
private fun StatusChip(status: String) {
    val color = when (status) {
        "待支付" -> Color(0xFFFFF3D8)
        "已支付", "已发货" -> Color(0xFFE8F3FF)
        "已完成" -> Color(0xFFE8F8EF)
        "已取消", "已退款" -> Color(0xFFF2F2F2)
        else -> Color(0xFFF6F3FF)
    }
    Surface(shape = RoundedCornerShape(999.dp), color = color) {
        Text(status, modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp), style = MaterialTheme.typography.labelMedium)
    }
}

@Composable
private fun OrderItemRow(item: OrderItem) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        AsyncImage(
            model = ApiConfig.resolveUrl(item.product.imageUrl),
            contentDescription = item.product.title,
            contentScale = ContentScale.Crop,
            modifier = Modifier
                .size(56.dp)
                .clip(RoundedCornerShape(12.dp))
        )
        Spacer(Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(item.product.title, maxLines = 2, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            Text("￥${item.product.price} × ${item.quantity}", color = Color.Gray, style = MaterialTheme.typography.bodySmall)
        }
        Text("￥${item.subtotal}", fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun OrderActions(
    status: String,
    onPay: () -> Unit,
    onCancel: () -> Unit,
    onShip: () -> Unit,
    onComplete: () -> Unit,
    onRefund: () -> Unit
) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
        when (status) {
            "待支付" -> {
                ActionButton(text = "取消", icon = Icons.Default.Close, onClick = onCancel, tonal = true)
                ActionButton(text = "立即支付", icon = Icons.Default.Payment, onClick = onPay)
            }
            "已支付" -> {
                ActionButton(text = "申请退款", icon = Icons.Default.Refresh, onClick = onRefund, tonal = true)
                ActionButton(text = "模拟发货", icon = Icons.Default.LocalShipping, onClick = onShip)
            }
            "已发货" -> {
                ActionButton(text = "申请退款", icon = Icons.Default.Refresh, onClick = onRefund, tonal = true)
                ActionButton(text = "确认收货", icon = Icons.Default.CheckCircle, onClick = onComplete)
            }
            "已完成" -> {
                ActionButton(text = "申请售后", icon = Icons.Default.Refresh, onClick = onRefund)
            }
        }
    }
}

@Composable
private fun RowScope.ActionButton(
    text: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    onClick: () -> Unit,
    tonal: Boolean = false
) {
    if (tonal) {
        FilledTonalButton(onClick = onClick, modifier = Modifier.weight(1f), shape = RoundedCornerShape(12.dp)) {
            Icon(icon, contentDescription = null, modifier = Modifier.size(16.dp))
            Spacer(Modifier.width(6.dp))
            Text(text)
        }
    } else {
        Button(onClick = onClick, modifier = Modifier.weight(1f), shape = RoundedCornerShape(12.dp)) {
            Icon(icon, contentDescription = null, modifier = Modifier.size(16.dp))
            Spacer(Modifier.width(6.dp))
            Text(text)
        }
    }
}
