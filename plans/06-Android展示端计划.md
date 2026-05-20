# Android 展示端计划 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建正式 Android 展示端，实现类似“豆包”的流式聊天体验，支持商品卡片、图片上传、会话历史和点赞/点踩反馈。

**Architecture:** Android 使用 Kotlin + Jetpack Compose。网络层使用 OkHttp 连接 FastAPI SSE；状态层使用 ViewModel + Kotlin Flow；图片展示用 Coil；页面由会话列表、聊天页、商品详情页组成。

**Tech Stack:** Kotlin, Jetpack Compose, ViewModel, Kotlin Flow, OkHttp, Coil, Navigation Compose, Material 3.

---

## 1. 范围

包含：

- Android 工程
- 会话列表页
- 聊天页
- SSE 流式渲染
- 商品卡片组件
- 图片上传
- 点赞/点踩反馈
- 商品详情页

不包含：

- iOS 客户端
- 推送通知
- 支付下单
- 离线缓存复杂同步

## 2. Android 目录结构

```text
commerce-rag-agent/android/
  app/src/main/java/com/example/commerceagent/
    MainActivity.kt
    app/
      CommerceAgentApp.kt
      AppNavGraph.kt
    data/
      api/
        ApiConfig.kt
        ChatSseClient.kt
        UploadApi.kt
        FeedbackApi.kt
      model/
        ChatMessage.kt
        ProductCard.kt
        SseEvent.kt
        Session.kt
      repository/
        ChatRepository.kt
        SessionRepository.kt
        FeedbackRepository.kt
    ui/
      chat/
        ChatScreen.kt
        ChatViewModel.kt
        MessageBubble.kt
        ProductCardRow.kt
        ImagePickerBar.kt
      sessions/
        SessionListScreen.kt
        SessionListViewModel.kt
      product/
        ProductDetailScreen.kt
      components/
        StreamingText.kt
        FeedbackBar.kt
        LoadingDots.kt
    theme/
      Color.kt
      Theme.kt
```

## 3. 事件协议

Android 需要解析后端 SSE：

```text
event: message
data: {"delta":"我为你筛选了 3 款适合学生党的平板。"}

event: product_cards
data: {"cards":[...]}

event: trace
data: {"intent":"shopping_guide","filters":{"budget_max":2000}}

event: done
data: {"status":"ok"}
```

解析为：

```kotlin
sealed interface SseEvent {
    data class Message(val delta: String) : SseEvent
    data class ProductCards(val cards: List<ProductCard>) : SseEvent
    data class Trace(val payload: String) : SseEvent
    data class Error(val message: String) : SseEvent
    data object Done : SseEvent
}
```

## 4. 任务拆分

### Task 1: Android 工程初始化

**Files:**

- Create: `commerce-rag-agent/android/app/src/main/java/com/example/commerceagent/MainActivity.kt`
- Create: `commerce-rag-agent/android/app/src/main/java/com/example/commerceagent/app/AppNavGraph.kt`
- Create: `commerce-rag-agent/android/app/src/main/java/com/example/commerceagent/theme/Theme.kt`

- [ ] 创建 Kotlin + Jetpack Compose Android 项目。
- [ ] 配置 Material 3。
- [ ] 配置 Navigation Compose。
- [ ] 添加网络权限 `android.permission.INTERNET`。
- [ ] App 启动进入会话列表页。

### Task 2: 数据模型

**Files:**

- Create: `data/model/ChatMessage.kt`
- Create: `data/model/ProductCard.kt`
- Create: `data/model/SseEvent.kt`
- Create: `data/model/Session.kt`

- [ ] 定义 `ChatMessage`，字段包含 `id`、`role`、`content`、`productCards`、`isStreaming`。
- [ ] 定义 `ProductCard`，字段与后端 JSON 协议一致。
- [ ] 定义 `SseEvent` sealed interface。
- [ ] 定义 `Session`，字段包含 `id`、`title`、`updatedAt`。

### Task 3: SSE 网络层

**Files:**

- Create: `data/api/ApiConfig.kt`
- Create: `data/api/ChatSseClient.kt`
- Create: `data/repository/ChatRepository.kt`

- [ ] 使用 OkHttp 创建 POST `/api/chat/stream` 请求。
- [ ] 支持请求体传 `session_id`、`message`、`upload_id`。
- [ ] 逐行解析 SSE。
- [ ] 将 `message` event 转为 `SseEvent.Message`。
- [ ] 将 `product_cards` event 转为 `SseEvent.ProductCards`。
- [ ] 网络异常转为 `SseEvent.Error`。

### Task 4: 聊天 ViewModel

**Files:**

- Create: `ui/chat/ChatViewModel.kt`

- [ ] 暴露 `StateFlow<ChatUiState>`。
- [ ] 用户发送消息时，先插入 user message。
- [ ] 创建 assistant streaming message。
- [ ] 收到 `Message` delta 时追加文本。
- [ ] 收到 `ProductCards` 时绑定到 assistant message。
- [ ] 收到 `Done` 时将 `isStreaming=false`。
- [ ] 失败时显示重试按钮状态。

### Task 5: 聊天页面

**Files:**

- Create: `ui/chat/ChatScreen.kt`
- Create: `ui/chat/MessageBubble.kt`
- Create: `ui/chat/ProductCardRow.kt`
- Create: `ui/components/StreamingText.kt`
- Create: `ui/components/LoadingDots.kt`

- [ ] 页面底部固定输入框。
- [ ] 消息列表自动滚动到底部。
- [ ] assistant 消息流式展示。
- [ ] 商品卡片横向滚动。
- [ ] 流式状态显示 loading dots。
- [ ] 用户发送期间禁用重复发送。

### Task 6: 图片上传

**Files:**

- Create: `data/api/UploadApi.kt`
- Create: `ui/chat/ImagePickerBar.kt`
- Modify: `ui/chat/ChatScreen.kt`

- [ ] 使用系统图片选择器选择图片。
- [ ] Multipart 上传到 `/api/upload/image`。
- [ ] 上传成功后拿到 `upload_id`。
- [ ] 聊天发送时带上 `upload_id`。
- [ ] 上传图片在输入区域显示预览。

### Task 7: 反馈功能

**Files:**

- Create: `data/api/FeedbackApi.kt`
- Create: `data/repository/FeedbackRepository.kt`
- Create: `ui/components/FeedbackBar.kt`
- Modify: `ui/chat/MessageBubble.kt`

- [ ] assistant 消息下方显示点赞/点踩。
- [ ] 点赞发送 `rating=1`。
- [ ] 点踩发送 `rating=-1`。
- [ ] 反馈提交后锁定按钮。
- [ ] 失败时允许再次点击。

### Task 8: 商品详情页

**Files:**

- Create: `ui/product/ProductDetailScreen.kt`
- Modify: `app/AppNavGraph.kt`

- [ ] 点击商品卡片进入详情页。
- [ ] 展示图片、标题、价格、评分、库存、推荐理由。
- [ ] 提供“返回聊天”按钮。

## 5. 验收标准

1. Android 能连接本地 FastAPI。
2. 输入购物需求后，回答逐字/分块显示。
3. 商品卡片正常渲染。
4. 上传图片后能触发图搜接口。
5. 点赞/点踩能写入后端。
6. 会话切换不丢失当前消息状态。

## 6. 与后端依赖

Android 开发前，后端需要稳定提供：

- `POST /api/chat/stream`
- `POST /api/upload/image`
- `POST /api/feedback`
- `GET /api/products/{id}`
- `GET /api/sessions`
- `POST /api/sessions`
