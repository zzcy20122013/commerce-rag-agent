package com.example.commerceagent.ui.sessions

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel

@Composable
fun SessionListScreen(
    onOpenChat: (String) -> Unit,
    onNewChat: () -> Unit,
    viewModel: SessionListViewModel = viewModel()
) {
    val state by viewModel.state.collectAsState()
    var showHistory by remember { mutableStateOf(false) }
    val background = Brush.verticalGradient(
        colors = listOf(Color(0xFFF7F4FF), Color(0xFFFFFFFF), Color(0xFFF4F7FF))
    )

    Scaffold(containerColor = Color.Transparent) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(background)
                .padding(padding)
        ) {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 20.dp, vertical = 24.dp),
                verticalArrangement = Arrangement.spacedBy(18.dp)
            ) {
                item {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = "智能导购助手",
                                style = MaterialTheme.typography.headlineSmall,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "说需求、发图片，我帮你挑到更合适的商品",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.62f)
                            )
                        }
                        TextButton(onClick = { showHistory = !showHistory }) {
                            Text(if (showHistory) "收起" else "历史")
                        }
                    }
                }

                item {
                    HeroCard(onNewChat = onNewChat)
                }

                item {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text(
                            text = "你可以这样问",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                        QuickIntentCard("3500以内，学生记笔记和网课用平板", onNewChat)
                        QuickIntentCard("300以内，适合通勤的鞋", onNewChat)
                        QuickIntentCard("100以内，控油定妆粉饼或散粉", onNewChat)
                    }
                }

                if (state.error != null) {
                    item {
                        Text(state.error.orEmpty(), color = MaterialTheme.colorScheme.error)
                    }
                }

                if (showHistory) {
                    item {
                        Text(
                            text = "最近会话",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    items(state.sessions.take(6)) { session ->
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { onOpenChat(session.id) },
                            shape = RoundedCornerShape(18.dp),
                            colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.86f)),
                            elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
                            border = BorderStroke(1.dp, Color(0xFFE8E2FF))
                        ) {
                            Column(Modifier.padding(16.dp)) {
                                Text(
                                    session.title,
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.SemiBold
                                )
                                Text(
                                    session.updatedAt,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.52f),
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun HeroCard(onNewChat: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.9f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
        border = BorderStroke(1.dp, Color(0xFFE3DCFF))
    ) {
        Column(Modifier.padding(22.dp)) {
            Surface(
                modifier = Modifier.size(52.dp),
                shape = RoundedCornerShape(18.dp),
                color = Color(0xFF6D45F6).copy(alpha = 0.12f),
                contentColor = Color(0xFF5B35EA)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text("AI", fontWeight = FontWeight.Bold)
                }
            }
            Spacer(Modifier.height(18.dp))
            Text(
                text = "像和真人导购聊天一样",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = "告诉我预算、用途、偏好，或者上传图片找类似款。我会结合商品库和知识库给你更有取舍的建议。",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.66f),
                modifier = Modifier.padding(top = 8.dp)
            )
            Spacer(Modifier.height(20.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(
                    onClick = onNewChat,
                    shape = RoundedCornerShape(999.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF5B35EA))
                ) {
                    Text("开始导购")
                }
                OutlinedButton(
                    onClick = onNewChat,
                    shape = RoundedCornerShape(999.dp),
                    border = BorderStroke(1.dp, Color(0xFFD8CCFF))
                ) {
                    Text("图片找款")
                }
            }
        }
    }
}

@Composable
private fun QuickIntentCard(text: String, onClick: () -> Unit) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        color = Color.White.copy(alpha = 0.78f),
        border = BorderStroke(1.dp, Color(0xFFE9E3FF))
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold
        )
    }
}
