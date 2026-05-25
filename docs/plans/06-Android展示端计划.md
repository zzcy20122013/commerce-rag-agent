# Android 展示端计划 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建正式 Android 展示端，实现类似“豆包”的流式聊天体验，支持商品卡片、图片上传、会话历史、购物/订单闭环和点赞/点踩反馈。

**Architecture:** Android 使用 Kotlin + Jetpack Compose。网络层使用 OkHttp 连接 FastAPI SSE 和 REST API；状态层使用 ViewModel + Kotlin Flow；图片展示用 Coil；页面由登录页、聊天页、会话侧边栏、商品详情页、确认订单页和我的订单页组成。

**Tech Stack:** Kotlin, Jetpack Compose, ViewModel, Kotlin Flow, OkHttp, Coil, Navigation Compose, Material 3.

---

## 0. 当前完成状态

状态：核心展示端已完成第一版，可在 Android Studio 模拟器运行，后续重点转为 UI 体验打磨和真机验证。

已完成：

1. Android Studio 工程可打开和构建。
2. 登录页：`ui/auth/LoginScreen.kt`。
3. 主容器和侧边栏：`ui/main/MainScreen.kt`。
4. 聊天页：`ui/chat/ChatScreen.kt`。
5. SSE 客户端：`data/api/ChatSseClient.kt`。
6. 商品卡片：`ui/chat/ProductCardRow.kt`。
7. 图片上传入口和预览。
8. 赞踩反馈入口，按后端 `feedback_enabled` 控制显示。
9. 会话列表、新建会话、重命名会话、历史消息加载。
10. 真实删除会话，调用 `DELETE /api/sessions/{id}`。
11. SSE 错误收尾：失败时不再无限显示“正在思考...”，而是显示错误提示。
12. 商品卡片和商品详情支持加入购物车，顶部购物车角标同步数量。
13. 购物车支持查看、删除、修改数量，并通过“去结算”进入确认订单页。
14. 确认订单页支持提交订单，后端扣减库存并生成待支付订单。
15. 我的订单页支持支付、取消、模拟发货、确认收货、退款售后和订单记录删除。
16. 系统语音转文字入口已接入，依赖设备可用语音识别服务。
17. Android 模拟器访问本机后端：`http://10.0.2.2:8000`。

待继续打磨：

1. UI 视觉继续贴近正式智能导购 App。
2. 消息滚动、输入框、键盘遮挡、侧边栏交互细节。
3. 商品卡片在移动端的纵向/横向展示策略。
4. 图片上传后的多模态结果展示。
5. 语音输入、真流式、确认订单和订单删除的真机/模拟器稳定性验证。
6. 不同屏幕尺寸适配。

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
- 购物车入口
- 确认订单页
- 我的订单页

不包含：

- iOS 客户端
- 推送通知
- 真实支付网关和真实物流系统
- 离线缓存复杂同步

## 2. Android 目录结构

```text
android/
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
        CartApi.kt
        OrderApi.kt
      model/
        ChatMessage.kt
        ProductCard.kt
        SseEvent.kt
        Session.kt
        Cart.kt
        Order.kt
      repository/
        ChatRepository.kt
        SessionRepository.kt
        FeedbackRepository.kt
        CartRepository.kt
        OrderRepository.kt
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
      checkout/
        CheckoutScreen.kt
        CheckoutViewModel.kt
      orders/
        OrdersScreen.kt
        OrdersViewModel.kt
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
data: {"content":"我为你筛选了 3 款适合学生党的平板。","message_id":"msg_xxx","session_id":"sess_xxx","memory":{},"feedback_enabled":true}

event: product_cards
data: [...]

event: trace
data: [{"node":"intent_router","intent":"shopping_guide"},{"node":"response_composer","llm_enabled":true}]

event: done
data: {"ok":true}
```

解析为：

```kotlin
sealed interface SseEvent {
    data class Message(
        val delta: String,
        val messageId: String?,
        val sessionId: String?,
        val feedbackEnabled: Boolean
    ) : SseEvent
    data class ProductCards(val cards: List<ProductCard>) : SseEvent
    data class Trace(val payload: String) : SseEvent
    data class Error(val message: String) : SseEvent
    data object Done : SseEvent
}
```

## 4. 任务拆分

### Task 1: Android 工程初始化

**Files:**

- Create: `android/app/src/main/java/com/example/commerceagent/MainActivity.kt`
- Create: `android/app/src/main/java/com/example/commerceagent/app/AppNavGraph.kt`
- Create: `android/app/src/main/java/com/example/commerceagent/theme/Theme.kt`

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
- [x] 失败时收尾当前 assistant 消息，避免一直停留在“正在思考...”。

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
- [x] 根据后端 `feedback_enabled` 控制显示，闲聊和无效兜底回答不展示赞踩。

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
- `GET /api/sessions/{id}/messages`
- `PUT /api/sessions/{id}`
- `DELETE /api/sessions/{id}`
