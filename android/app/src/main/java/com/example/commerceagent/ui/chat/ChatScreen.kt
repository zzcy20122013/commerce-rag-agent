package com.example.commerceagent.ui.chat

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel

private val quickPrompts = listOf(
    "帮我推荐 3500 以内适合学生记笔记和网课的平板",
    "帮我推荐 300 以内适合通勤的鞋",
    "帮我找 100 元以内控油定妆的粉饼或散粉"
)

@Composable
fun ChatScreen(
    sessionId: String?,
    onOpenProduct: (String) -> Unit,
    onBack: () -> Unit,
    viewModel: ChatViewModel = viewModel()
) {
    val state by viewModel.state.collectAsState()
    val listState = rememberLazyListState()
    val context = LocalContext.current
    val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) viewModel.uploadImage(context.contentResolver, uri)
    }
    val background = Brush.verticalGradient(
        colors = listOf(Color(0xFFF7F4FF), Color(0xFFFFFFFF), Color(0xFFF5F7FF))
    )

    LaunchedEffect(sessionId) {
        viewModel.setSession(sessionId)
    }
    LaunchedEffect(state.messages.size) {
        if (state.messages.isNotEmpty()) {
            listState.animateScrollToItem(state.messages.lastIndex)
        }
    }

    Scaffold(
        containerColor = Color.Transparent,
        topBar = {
            ChatTopBar(onBack = onBack)
        },
        bottomBar = {
            ChatInputBar(
                input = state.input,
                previewUrl = state.previewUrl,
                isSending = state.isSending,
                onInput = viewModel::updateInput,
                onPickImage = { imagePicker.launch("image/*") },
                onSend = viewModel::send
            )
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(background)
                .padding(padding)
        ) {
            Column(modifier = Modifier.fillMaxSize()) {
                if (state.error != null) {
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp, vertical = 8.dp),
                        color = MaterialTheme.colorScheme.error.copy(alpha = 0.08f),
                        contentColor = MaterialTheme.colorScheme.error,
                        shape = RoundedCornerShape(14.dp)
                    ) {
                        Text(
                            text = state.error.orEmpty(),
                            modifier = Modifier.padding(12.dp),
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
                LazyColumn(
                    state = listState,
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 14.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    if (state.messages.isEmpty()) {
                        item {
                            WelcomePanel(onPrompt = viewModel::sendPrompt)
                        }
                    }
                    items(state.messages, key = { it.id }) { message ->
                        MessageBubble(
                            message = message,
                            onOpenProduct = onOpenProduct,
                            onFeedback = viewModel::sendFeedback
                        )
                    }
                    item { Spacer(Modifier.height(8.dp)) }
                }
            }
        }
    }
}

@Composable
private fun ChatTopBar(onBack: () -> Unit) {
    Surface(
        color = Color.White.copy(alpha = 0.86f),
        shadowElevation = 0.dp
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            TextButton(onClick = onBack) {
                Text("返回")
            }
            Column(modifier = Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                Text("智能导购助手", fontWeight = FontWeight.Bold)
                Text(
                    text = "RAG 商品推荐 · 图文多模态",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.52f)
                )
            }
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = Color(0xFF5B35EA).copy(alpha = 0.1f),
                contentColor = Color(0xFF5B35EA)
            ) {
                Text("AI", modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp), fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun WelcomePanel(onPrompt: (String) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 22.dp, bottom = 12.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Surface(
            shape = RoundedCornerShape(22.dp),
            color = Color.White.copy(alpha = 0.88f),
            border = BorderStroke(1.dp, Color(0xFFE4DCFF))
        ) {
            Column(Modifier.padding(18.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Surface(
                    shape = RoundedCornerShape(18.dp),
                    color = Color(0xFF6D45F6).copy(alpha = 0.12f),
                    contentColor = Color(0xFF5B35EA)
                ) {
                    Text("AI", modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp), fontWeight = FontWeight.Bold)
                }
                Spacer(Modifier.height(12.dp))
                Text("今天想买点什么？", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text(
                    "告诉我预算、用途和偏好，我会给你主推和备选，不堆参数。",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.62f),
                    modifier = Modifier.padding(top = 6.dp)
                )
            }
        }
        Spacer(Modifier.height(14.dp))
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            quickPrompts.forEach { prompt ->
                Surface(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onPrompt(prompt) },
                    shape = RoundedCornerShape(999.dp),
                    color = Color.White.copy(alpha = 0.78f),
                    border = BorderStroke(1.dp, Color(0xFFE8E0FF))
                ) {
                    Text(
                        prompt,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 11.dp),
                        style = MaterialTheme.typography.bodySmall,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }
        }
    }
}

@Composable
private fun ChatInputBar(
    input: String,
    previewUrl: String?,
    isSending: Boolean,
    onInput: (String) -> Unit,
    onPickImage: () -> Unit,
    onSend: () -> Unit
) {
    Surface(color = Color.White.copy(alpha = 0.96f), shadowElevation = 8.dp) {
        Column(Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
            ImagePickerBar(previewUrl = previewUrl, onPickImage = onPickImage)
            Spacer(Modifier.height(8.dp))
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    modifier = Modifier.weight(1f),
                    value = input,
                    onValueChange = onInput,
                    placeholder = { Text("输入你的问题...") },
                    enabled = !isSending,
                    shape = RoundedCornerShape(22.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = Color(0xFF5B35EA).copy(alpha = 0.32f),
                        unfocusedBorderColor = Color(0xFFE1DAF8),
                        focusedContainerColor = Color(0xFFF9F7FF),
                        unfocusedContainerColor = Color(0xFFF9F7FF)
                    )
                )
                Button(
                    modifier = Modifier.padding(start = 10.dp),
                    enabled = !isSending,
                    onClick = onSend,
                    shape = RoundedCornerShape(999.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF5B35EA))
                ) {
                    Text("发送")
                }
            }
        }
    }
}
