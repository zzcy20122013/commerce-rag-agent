package com.example.commerceagent.ui.chat

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage

private val quickPrompts = listOf(
    "推荐 3500 以内学生记笔记平板",
    "推荐 300 以内通勤鞋",
    "找 100 元以内控油粉饼"
)

@Composable
fun ChatScreen(
    sessionId: String?,
    onOpenProduct: (String) -> Unit,
    onMenuClick: () -> Unit,
    newChatSignal: Int,
    viewModel: ChatViewModel = viewModel()
) {
    val state by viewModel.state.collectAsState()
    val listState = rememberLazyListState()
    val context = LocalContext.current
    val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) viewModel.uploadImage(context.contentResolver, uri)
    }
    
    val background = Brush.verticalGradient(
        colors = listOf(Color(0xFFF8F9FF), Color(0xFFFFFFFF))
    )

    LaunchedEffect(sessionId) {
        viewModel.setSession(sessionId)
    }
    LaunchedEffect(newChatSignal) {
        if (newChatSignal > 0) {
            viewModel.startNewChat()
        }
    }

    Scaffold(
        containerColor = Color.Transparent,
        topBar = {
            ChatTopBar(onMenuClick = onMenuClick, onNewChat = { viewModel.startNewChat() })
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
                LazyColumn(
                    state = listState,
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    if (state.messages.isEmpty()) {
                        item {
                            WelcomePanel(onPrompt = viewModel::sendPrompt)
                        }
                    } else {
                        item { Spacer(Modifier.height(8.dp)) }
                    }
                    items(state.messages, key = { it.id }) { message ->
                        MessageBubble(
                            message = message,
                            onOpenProduct = onOpenProduct,
                            onFeedback = viewModel::sendFeedback
                        )
                    }
                    item { Spacer(Modifier.height(100.dp)) }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ChatTopBar(onMenuClick: () -> Unit, onNewChat: () -> Unit) {
    CenterAlignedTopAppBar(
        title = {
            Text(
                "Commerce AI",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
        },
        navigationIcon = {
            IconButton(onClick = onMenuClick) {
                Icon(Icons.Default.Menu, contentDescription = "菜单")
            }
        },
        actions = {
            IconButton(onClick = onNewChat) {
                Icon(Icons.Default.Add, contentDescription = "新对话")
            }
        },
        colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
            containerColor = Color.Transparent
        )
    )
}

@Composable
private fun WelcomePanel(onPrompt: (String) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 60.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Surface(
            modifier = Modifier.size(64.dp),
            shape = CircleShape,
            color = Color(0xFF5B35EA).copy(alpha = 0.1f)
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    Icons.Default.Star,
                    contentDescription = null,
                    tint = Color(0xFF5B35EA),
                    modifier = Modifier.size(32.dp)
                )
            }
        }
        Spacer(Modifier.height(24.dp))
        Text(
            "您好，我是您的 AI 导购",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center
        )
        Text(
            "您可以问我关于商品、预算或对比的任何问题",
            style = MaterialTheme.typography.bodyMedium,
            color = Color.Gray,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 8.dp)
        )
        Spacer(Modifier.height(48.dp))
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            quickPrompts.forEach { prompt ->
                Surface(
                    onClick = { onPrompt(prompt) },
                    shape = RoundedCornerShape(16.dp),
                    border = BorderStroke(1.dp, Color(0xFFEEEEEE)),
                    color = Color.White
                ) {
                    Text(
                        prompt,
                        modifier = Modifier.padding(horizontal = 20.dp, vertical = 12.dp),
                        style = MaterialTheme.typography.bodyMedium
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
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .padding(16.dp)
    ) {
        Surface(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(28.dp),
            color = Color(0xFFF7F7F7),
            border = BorderStroke(1.dp, Color(0xFFEEEEEE))
        ) {
            Column {
                if (previewUrl != null) {
                    Box(Modifier.padding(8.dp)) {
                        AsyncImage(
                            model = previewUrl,
                            contentDescription = null,
                            modifier = Modifier.size(60.dp).clip(RoundedCornerShape(12.dp)),
                            contentScale = ContentScale.Crop
                        )
                    }
                }
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.padding(horizontal = 4.dp, vertical = 4.dp)
                ) {
                    IconButton(onClick = onPickImage) {
                        Icon(Icons.Default.Add, contentDescription = "上传图片", tint = Color.Gray)
                    }
                    TextField(
                        value = input,
                        onValueChange = onInput,
                        placeholder = { Text("输入您的问题...") },
                        modifier = Modifier.weight(1f),
                        colors = TextFieldDefaults.colors(
                            focusedContainerColor = Color.Transparent,
                            unfocusedContainerColor = Color.Transparent,
                            focusedIndicatorColor = Color.Transparent,
                            unfocusedIndicatorColor = Color.Transparent
                        ),
                        maxLines = 5
                    )
                    IconButton(
                        onClick = onSend,
                        enabled = input.isNotBlank() && !isSending,
                        colors = IconButtonDefaults.iconButtonColors(
                            contentColor = Color(0xFF5B35EA),
                            disabledContentColor = Color.Gray
                        )
                    ) {
                        Icon(Icons.Default.Send, contentDescription = "发送")
                    }
                }
            }
        }
    }
}
