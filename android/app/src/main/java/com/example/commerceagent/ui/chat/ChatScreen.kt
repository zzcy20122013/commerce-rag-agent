package com.example.commerceagent.ui.chat

import android.Manifest
import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.PackageManager
import android.speech.RecognizerIntent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ListAlt
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.core.content.ContextCompat
import coil.compose.AsyncImage
import com.example.commerceagent.data.api.ApiConfig
import com.example.commerceagent.data.model.CartItem
import kotlinx.coroutines.launch
import java.util.Locale

private val quickPrompts = listOf(
    "推荐 3500 以内学生记笔记平板",
    "找 100 元以内方便早餐",
    "找 100 元以内速溶咖啡",
    "推荐 300 元以内控油防晒",
    "推荐 200 元以内速干运动上衣"
)

@Composable
fun ChatScreen(
    sessionId: String?,
    onOpenProduct: (String) -> Unit,
    onOpenOrders: () -> Unit,
    onOpenCheckout: () -> Unit,
    onMenuClick: () -> Unit,
    onSessionChanged: (String) -> Unit,
    newChatSignal: Int,
    viewModel: ChatViewModel = viewModel()
) {
    val state by viewModel.state.collectAsState()
    val listState = rememberLazyListState()
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val snackbarHostState = remember { SnackbarHostState() }
    val coroutineScope = rememberCoroutineScope()
    var showCartSheet by remember { mutableStateOf(false) }
    val cartQuantities = remember(state.cartItems) {
        state.cartItems.associate { it.product.id to it.quantity }
    }
    val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) viewModel.uploadImage(context.contentResolver, uri)
    }
    val voiceLauncher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val transcript = result.data
                ?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
                ?.firstOrNull()
                .orEmpty()
            if (transcript.isNotBlank()) {
                viewModel.applyVoiceTranscript(transcript)
            }
        }
    }
    fun launchVoiceInput() {
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.SIMPLIFIED_CHINESE.toLanguageTag())
            putExtra(RecognizerIntent.EXTRA_PROMPT, "请说出您的购物需求")
        }
        try {
            voiceLauncher.launch(intent)
        } catch (_: ActivityNotFoundException) {
            coroutineScope.launch {
                snackbarHostState.showSnackbar("当前设备没有可用的语音识别服务")
            }
        }
    }
    val voicePermissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) {
            launchVoiceInput()
        } else {
            coroutineScope.launch {
                snackbarHostState.showSnackbar("需要麦克风权限才能使用语音输入")
            }
        }
    }

    val background = Brush.verticalGradient(
        colors = listOf(Color(0xFFF8F9FF), Color(0xFFFFFFFF))
    )

    LaunchedEffect(sessionId) {
        viewModel.setSession(sessionId)
    }
    LaunchedEffect(Unit) {
        viewModel.loadCart()
    }
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                viewModel.loadCart()
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }
    LaunchedEffect(state.cartNotice) {
        val notice = state.cartNotice
        if (!notice.isNullOrBlank()) {
            snackbarHostState.showSnackbar(notice)
            viewModel.consumeCartNotice()
        }
    }
    LaunchedEffect(newChatSignal) {
        if (newChatSignal > 0) {
            viewModel.startNewChat()
        }
    }
    LaunchedEffect(state.sessionId) {
        val resolvedSessionId = state.sessionId
        if (resolvedSessionId != null && resolvedSessionId != sessionId) {
            onSessionChanged(resolvedSessionId)
        }
    }

    Scaffold(
        containerColor = Color.Transparent,
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            ChatTopBar(
                onMenuClick = onMenuClick,
                cartCount = state.cartItems.sumOf { it.quantity },
                onViewCart = {
                    viewModel.loadCart()
                    showCartSheet = true
                },
                onOpenOrders = onOpenOrders
            )
        },
        bottomBar = {
            ChatInputBar(
                input = state.input,
                previewUrl = state.previewUrl,
                isSending = state.isSending,
                onInput = viewModel::updateInput,
                onPickImage = { imagePicker.launch("image/*") },
                onVoiceInput = {
                    val permission = Manifest.permission.RECORD_AUDIO
                    if (ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED) {
                        launchVoiceInput()
                    } else {
                        voicePermissionLauncher.launch(permission)
                    }
                },
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
                            cartQuantities = cartQuantities,
                            onOpenProduct = onOpenProduct,
                            onAddToCart = viewModel::addProductToCart,
                            onFeedback = viewModel::sendFeedback,
                            onRetry = viewModel::retryMessage
                        )
                    }
                    item { Spacer(Modifier.height(100.dp)) }
                }
            }
        }
    }

    if (showCartSheet) {
        CartBottomSheet(
            items = state.cartItems,
            total = state.cartTotal,
            isLoading = state.isCartLoading,
            onDismiss = { showCartSheet = false },
            onDecrease = { position, quantity -> viewModel.updateCartQuantity(position, quantity - 1) },
            onIncrease = { position, quantity -> viewModel.updateCartQuantity(position, quantity + 1) },
            onRemove = viewModel::removeCartItem,
            onCheckout = {
                showCartSheet = false
                onOpenCheckout()
            }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ChatTopBar(
    onMenuClick: () -> Unit,
    cartCount: Int,
    onViewCart: () -> Unit,
    onOpenOrders: () -> Unit
) {
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
            IconButton(onClick = onOpenOrders) {
                Icon(Icons.AutoMirrored.Filled.ListAlt, contentDescription = "查看订单")
            }
            IconButton(onClick = onViewCart) {
                BadgedBox(
                    badge = {
                        if (cartCount > 0) {
                            Badge { Text(cartCount.coerceAtMost(99).toString()) }
                        }
                    }
                ) {
                    Icon(Icons.Default.ShoppingCart, contentDescription = "查看购物车")
                }
            }
        },
        colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
            containerColor = Color.Transparent
        )
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CartBottomSheet(
    items: List<CartItem>,
    total: Int,
    isLoading: Boolean,
    onDismiss: () -> Unit,
    onDecrease: (Int, Int) -> Unit,
    onIncrease: (Int, Int) -> Unit,
    onRemove: (Int) -> Unit,
    onCheckout: () -> Unit
) {
    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .fillMaxHeight(0.78f)
                .padding(horizontal = 20.dp)
                .navigationBarsPadding()
                .padding(bottom = 16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text("购物车", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Text(
                        if (items.isEmpty()) "还没有加购商品" else "共 ${items.sumOf { it.quantity }} 件商品",
                        style = MaterialTheme.typography.bodyMedium,
                        color = Color.Gray
                    )
                }
                if (isLoading) {
                    CircularProgressIndicator(modifier = Modifier.size(22.dp), strokeWidth = 2.dp)
                }
            }
            Spacer(Modifier.height(16.dp))

            if (items.isEmpty()) {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    color = Color(0xFFF6F3FF)
                ) {
                    Text(
                        "看到合适的商品后，点商品卡片里的“加入购物车”就会出现在这里。",
                        modifier = Modifier.padding(16.dp),
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
            } else {
                LazyColumn(
                    modifier = Modifier.weight(1f, fill = false),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    itemsIndexed(items) { index, item ->
                        CartItemRow(
                            item = item,
                            position = index + 1,
                            onDecrease = onDecrease,
                            onIncrease = onIncrease,
                            onRemove = onRemove
                        )
                    }
                }
                Spacer(Modifier.height(18.dp))
                HorizontalDivider()
                Spacer(Modifier.height(14.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("合计", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text(
                        "￥$total",
                        style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.tertiary,
                        fontWeight = FontWeight.Bold
                    )
                }
                Spacer(Modifier.height(16.dp))
                Button(
                    onClick = onCheckout,
                    enabled = !isLoading,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(14.dp)
                ) {
                    Icon(Icons.Default.CheckCircle, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(8.dp))
                    Text("去结算")
                }
            }
        }
    }
}

@Composable
private fun CartItemRow(
    item: CartItem,
    position: Int,
    onDecrease: (Int, Int) -> Unit,
    onIncrease: (Int, Int) -> Unit,
    onRemove: (Int) -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 1.dp
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            CartProductImage(item)
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    item.product.title,
                    maxLines = 2,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    "￥${item.product.price} · 小计 ￥${item.subtotal}",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color.Gray
                )
                Spacer(Modifier.height(8.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    IconButton(
                        onClick = { onDecrease(position, item.quantity) },
                        modifier = Modifier.size(32.dp)
                    ) {
                        Icon(Icons.Default.Remove, contentDescription = "减少数量", modifier = Modifier.size(18.dp))
                    }
                    Text(
                        item.quantity.toString(),
                        modifier = Modifier.widthIn(min = 32.dp),
                        textAlign = TextAlign.Center,
                        style = MaterialTheme.typography.titleSmall
                    )
                    IconButton(
                        onClick = { onIncrease(position, item.quantity) },
                        modifier = Modifier.size(32.dp)
                    ) {
                        Icon(Icons.Default.Add, contentDescription = "增加数量", modifier = Modifier.size(18.dp))
                    }
                }
            }
            IconButton(onClick = { onRemove(position) }) {
                Icon(Icons.Default.DeleteOutline, contentDescription = "删除商品")
            }
        }
    }
}

@Composable
private fun CartProductImage(item: CartItem) {
    val modifier = Modifier
        .size(56.dp)
        .clip(RoundedCornerShape(12.dp))
    if (item.product.imageUrl.isBlank()) {
        Surface(modifier = modifier, color = Color(0xFFF0EAFF)) {
            Box(contentAlignment = Alignment.Center) {
                Text(item.product.title.take(2), color = Color(0xFF5B35EA), fontWeight = FontWeight.Bold)
            }
        }
    } else {
        AsyncImage(
            model = ApiConfig.resolveUrl(item.product.imageUrl),
            contentDescription = item.product.title,
            contentScale = ContentScale.Crop,
            modifier = modifier
        )
    }
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
        Spacer(Modifier.height(44.dp))
        QuickPromptChips(onPrompt = onPrompt)
    }
}

@Composable
private fun QuickPromptChips(onPrompt: (String) -> Unit) {
    LazyRow(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        contentPadding = PaddingValues(horizontal = 30.dp)
    ) {
        items(quickPrompts.chunked(2)) { columnPrompts ->
            Column(
                modifier = Modifier.width(228.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                columnPrompts.forEach { prompt ->
                    QuickPromptChip(prompt = prompt, onClick = { onPrompt(prompt) })
                }
            }
        }
    }
}

@Composable
private fun QuickPromptChip(prompt: String, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 48.dp),
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, Color(0xFFE8E6EF)),
        color = Color.White
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            contentAlignment = Alignment.Center
        ) {
            Text(
                prompt,
                style = MaterialTheme.typography.bodyMedium,
                textAlign = TextAlign.Center,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
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
    onVoiceInput: () -> Unit,
    onSend: () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .padding(horizontal = 16.dp, vertical = 12.dp)
    ) {
        Surface(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(24.dp),
            color = Color(0xFFF2F2F7),
            border = BorderStroke(1.dp, Color(0xFFE5E5EA))
        ) {
            Column {
                if (previewUrl != null) {
                    Box(Modifier.padding(8.dp)) {
                        AsyncImage(
                            model = previewUrl,
                            contentDescription = null,
                            modifier = Modifier.size(64.dp).clip(RoundedCornerShape(12.dp)),
                            contentScale = ContentScale.Crop
                        )
                    }
                }
                Row(
                    verticalAlignment = Alignment.Bottom, // Allows TextField to grow upwards
                    modifier = Modifier.padding(horizontal = 4.dp, vertical = 4.dp)
                ) {
                    IconButton(
                        onClick = onPickImage,
                        modifier = Modifier.padding(bottom = 4.dp)
                    ) {
                        Icon(Icons.Default.Add, contentDescription = "上传图片", tint = Color(0xFF5B35EA))
                    }

                    TextField(
                        value = input,
                        onValueChange = onInput,
                        placeholder = { Text("输入您的问题...") },
                        modifier = Modifier
                            .weight(1f)
                            .padding(vertical = 4.dp),
                        colors = TextFieldDefaults.colors(
                            focusedContainerColor = Color.Transparent,
                            unfocusedContainerColor = Color.Transparent,
                            focusedIndicatorColor = Color.Transparent,
                            unfocusedIndicatorColor = Color.Transparent,
                            cursorColor = Color(0xFF5B35EA)
                        ),
                        maxLines = 6
                    )

                    Box(modifier = Modifier.padding(bottom = 4.dp, end = 4.dp)) {
                        if (isSending) {
                            IconButton(
                                onClick = { /* TODO: Implement Stop */ },
                                colors = IconButtonDefaults.iconButtonColors(
                                    containerColor = Color(0xFF5B35EA),
                                    contentColor = Color.White
                                ),
                                modifier = Modifier.size(32.dp)
                            ) {
                                // Using a simple Box as a square stop icon if Icons.Default.Stop is missing
                                Box(
                                    modifier = Modifier
                                        .size(12.dp)
                                        .background(Color.White, RoundedCornerShape(2.dp))
                                )
                            }
                        } else {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                IconButton(
                                    onClick = onVoiceInput,
                                    modifier = Modifier.size(36.dp)
                                ) {
                                    Icon(
                                        Icons.Default.Mic,
                                        contentDescription = "语音输入",
                                        tint = Color(0xFF5B35EA),
                                        modifier = Modifier.size(20.dp)
                                    )
                                }
                                IconButton(
                                    onClick = onSend,
                                    enabled = input.isNotBlank(),
                                    colors = IconButtonDefaults.iconButtonColors(
                                        containerColor = if (input.isNotBlank()) Color(0xFF5B35EA) else Color.Transparent,
                                        contentColor = if (input.isNotBlank()) Color.White else Color.Gray
                                    ),
                                    modifier = Modifier.size(32.dp)
                                ) {
                                    Icon(
                                        Icons.AutoMirrored.Filled.Send,
                                        contentDescription = "发送",
                                        modifier = Modifier.size(18.dp)
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
