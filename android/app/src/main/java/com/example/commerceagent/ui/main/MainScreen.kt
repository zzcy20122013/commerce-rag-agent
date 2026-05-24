package com.example.commerceagent.ui.main

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ListAlt
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.ChatBubbleOutline
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.commerceagent.data.model.Session
import com.example.commerceagent.ui.chat.ChatScreen
import com.example.commerceagent.ui.sessions.SessionListViewModel
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    initialSessionId: String? = null,
    onOpenProduct: (String) -> Unit,
    onOpenOrders: () -> Unit,
    onOpenCheckout: () -> Unit,
    onLogout: () -> Unit
) {
    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    val sessionViewModel: SessionListViewModel = viewModel()
    val sessionState by sessionViewModel.state.collectAsState()

    var currentSessionId by remember { mutableStateOf(initialSessionId) }
    var newChatSignal by remember { mutableIntStateOf(0) }

    fun startNewChat() {
        currentSessionId = null
        newChatSignal += 1
    }

    var sessionToRename by remember { mutableStateOf<Pair<String, String>?>(null) }

    if (sessionToRename != null) {
        var newTitle by remember(sessionToRename?.first) { mutableStateOf(sessionToRename?.second ?: "") }
        val trimmedTitle = newTitle.trim()
        AlertDialog(
            onDismissRequest = { sessionToRename = null },
            title = { Text("重命名会话") },
            text = {
                OutlinedTextField(
                    value = newTitle,
                    onValueChange = { newTitle = it },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            },
            confirmButton = {
                TextButton(
                    enabled = trimmedTitle.isNotEmpty(),
                    onClick = {
                        sessionToRename?.let { sessionViewModel.renameSession(it.first, trimmedTitle) }
                        sessionToRename = null
                    }
                ) { Text("保存") }
            },
            dismissButton = {
                TextButton(onClick = { sessionToRename = null }) { Text("取消") }
            }
        )
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet(modifier = Modifier.width(310.dp)) {
                Spacer(Modifier.height(16.dp))

                Surface(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp)
                        .clickable {
                            startNewChat()
                            scope.launch { drawerState.close() }
                        },
                    shape = RoundedCornerShape(16.dp),
                    color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f),
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.1f))
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Add, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                        Spacer(Modifier.width(12.dp))
                        Text("开启新对话", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                    }
                }

                Spacer(Modifier.height(20.dp))

                sessionState.error?.let { errorMessage ->
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp),
                        shape = RoundedCornerShape(12.dp),
                        color = MaterialTheme.colorScheme.errorContainer
                    ) {
                        Text(
                            text = errorMessage,
                            color = MaterialTheme.colorScheme.onErrorContainer,
                            style = MaterialTheme.typography.bodySmall,
                            modifier = Modifier.padding(12.dp)
                        )
                    }
                    Spacer(Modifier.height(12.dp))
                }

                val groupedSessions = remember(sessionState.sessions) {
                    groupSessions(sessionState.sessions)
                }

                LazyColumn(modifier = Modifier.weight(1f)) {
                    groupedSessions.forEach { (header, sessions) ->
                        item {
                            Text(
                                text = header,
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.primary.copy(alpha = 0.7f),
                                modifier = Modifier.padding(horizontal = 24.dp, vertical = 8.dp)
                            )
                        }
                        items(sessions) { session ->
                            SessionItem(
                                session = session,
                                isSelected = currentSessionId == session.id,
                                onSelect = {
                                    currentSessionId = session.id
                                    scope.launch { drawerState.close() }
                                },
                                onRename = { sessionToRename = session.id to session.title },
                                onDelete = {
                                    sessionViewModel.deleteSession(session.id) {
                                        if (currentSessionId == session.id) startNewChat()
                                    }
                                }
                            )
                        }
                    }
                }

                HorizontalDivider(modifier = Modifier.padding(horizontal = 16.dp))

                NavigationDrawerItem(
                    icon = { Icon(Icons.AutoMirrored.Filled.ListAlt, contentDescription = null) },
                    label = { Text("我的订单") },
                    selected = false,
                    onClick = {
                        scope.launch { drawerState.close() }
                        onOpenOrders()
                    },
                    modifier = Modifier.padding(NavigationDrawerItemDefaults.ItemPadding)
                )

                NavigationDrawerItem(
                    icon = { Icon(Icons.AutoMirrored.Filled.Logout, contentDescription = null) },
                    label = { Text("退出登录") },
                    selected = false,
                    onClick = onLogout,
                    modifier = Modifier.padding(NavigationDrawerItemDefaults.ItemPadding)
                )
                Spacer(Modifier.height(12.dp))
            }
        }
    ) {
        ChatScreen(
            sessionId = currentSessionId,
            onOpenProduct = onOpenProduct,
            onOpenOrders = onOpenOrders,
            onOpenCheckout = onOpenCheckout,
            onMenuClick = {
                sessionViewModel.refresh()
                scope.launch { drawerState.open() }
            },
            onSessionChanged = { sessionId ->
                currentSessionId = sessionId
                sessionViewModel.refresh()
            },
            newChatSignal = newChatSignal
        )
    }
}

@Composable
private fun SessionItem(
    session: Session,
    isSelected: Boolean,
    onSelect: () -> Unit,
    onRename: () -> Unit,
    onDelete: () -> Unit
) {
    var showMenu by remember { mutableStateOf(false) }

    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 2.dp)
            .clickable { onSelect() },
        shape = RoundedCornerShape(14.dp),
        color = if (isSelected) MaterialTheme.colorScheme.surfaceVariant else Color.Transparent
    ) {
        Row(
            modifier = Modifier.padding(start = 16.dp, end = 4.dp, top = 10.dp, bottom = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                Icons.Outlined.ChatBubbleOutline,
                contentDescription = null,
                modifier = Modifier.size(18.dp),
                tint = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(Modifier.width(12.dp))
            Text(
                text = session.title,
                maxLines = 1,
                modifier = Modifier.weight(1f),
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal
            )

            Box {
                IconButton(onClick = { showMenu = true }) {
                    Icon(Icons.Default.MoreVert, contentDescription = null, modifier = Modifier.size(20.dp))
                }
                DropdownMenu(expanded = showMenu, onDismissRequest = { showMenu = false }) {
                    DropdownMenuItem(
                        text = { Text("重命名") },
                        leadingIcon = { Icon(Icons.Default.Edit, null, Modifier.size(18.dp)) },
                        onClick = { showMenu = false; onRename() }
                    )
                    DropdownMenuItem(
                        text = { Text("删除", color = MaterialTheme.colorScheme.error) },
                        leadingIcon = { Icon(Icons.Default.Delete, null, Modifier.size(18.dp), tint = MaterialTheme.colorScheme.error) },
                        onClick = { showMenu = false; onDelete() }
                    )
                }
            }
        }
    }
}

private fun groupSessions(sessions: List<Session>): Map<String, List<Session>> {
    val groups = linkedMapOf<String, MutableList<Session>>()
    val now = Calendar.getInstance()
    val today = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(now.time)

    now.add(Calendar.DAY_OF_YEAR, -1)
    val yesterday = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(now.time)

    sessions.forEach { session ->
        val datePart = session.updatedAt.take(10)
        val header = when (datePart) {
            today -> "今天"
            yesterday -> "昨天"
            else -> "更早之前"
        }
        groups.getOrPut(header) { mutableListOf() }.add(session)
    }
    return groups
}
