package com.example.commerceagent.ui.main

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.commerceagent.ui.chat.ChatScreen
import com.example.commerceagent.ui.sessions.SessionListViewModel
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    initialSessionId: String? = null,
    onOpenProduct: (String) -> Unit,
    onLogout: () -> Unit
) {
    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    val sessionViewModel: SessionListViewModel = viewModel()
    val sessionState by sessionViewModel.state.collectAsState()
    
    var currentSessionId by remember { mutableStateOf(initialSessionId) }
    var newChatSignal by remember { mutableIntStateOf(0) }

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet(
                modifier = Modifier.width(300.dp),
            ) {
                Spacer(Modifier.height(12.dp))
                NavigationDrawerItem(
                    icon = { Icon(Icons.Default.Add, contentDescription = null) },
                    label = { Text("开启新对话") },
                    selected = currentSessionId == null,
                    onClick = {
                        currentSessionId = null
                        newChatSignal += 1
                        scope.launch { drawerState.close() }
                    },
                    modifier = Modifier.padding(NavigationDrawerItemDefaults.ItemPadding)
                )
                HorizontalDivider(Modifier.padding(vertical = 8.dp, horizontal = 12.dp))
                Text(
                    "最近记录",
                    style = MaterialTheme.typography.labelMedium,
                    modifier = Modifier.padding(horizontal = 28.dp, vertical = 8.dp),
                    color = MaterialTheme.colorScheme.primary
                )
                sessionState.sessions.forEach { session ->
                    val selected = currentSessionId == session.id
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 12.dp, vertical = 3.dp)
                            .clickable {
                                currentSessionId = session.id
                                scope.launch { drawerState.close() }
                            },
                        shape = RoundedCornerShape(24.dp),
                        color = if (selected) {
                            MaterialTheme.colorScheme.primary.copy(alpha = 0.12f)
                        } else {
                            Color.Transparent
                        }
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(start = 16.dp, end = 8.dp, top = 10.dp, bottom = 10.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = session.title,
                                maxLines = 1,
                                modifier = Modifier.weight(1f),
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            TextButton(
                                onClick = {
                                    sessionViewModel.deleteSession(session.id) {
                                        if (currentSessionId == session.id) {
                                            currentSessionId = null
                                            newChatSignal += 1
                                        }
                                    }
                                },
                                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp)
                            ) {
                                Text(
                                    text = "删除",
                                    color = MaterialTheme.colorScheme.error,
                                    style = MaterialTheme.typography.labelSmall
                                )
                            }
                        }
                    }
                }
                Spacer(Modifier.weight(1f))
                NavigationDrawerItem(
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
            onMenuClick = { scope.launch { drawerState.open() } },
            newChatSignal = newChatSignal
        )
    }
}
