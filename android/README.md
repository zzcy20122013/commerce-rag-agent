# Android 原生展示端

这是电商智能导购 Agent 的 Android Kotlin + Jetpack Compose 展示端。它用于验证正式移动端体验：流式聊天、商品卡片、图片上传、会话列表、会话重命名/删除、商品详情和点赞/点踩反馈。

## 本机环境

- Android Studio Panda 或更新版本
- Android SDK：建议安装 API 35 或 API 36
- 模拟器：建议 Pixel 8
- 后端服务：`http://127.0.0.1:8000`

Android 模拟器访问电脑本机后端时不能使用 `127.0.0.1`，需要使用：

```text
http://10.0.2.2:8000
```

当前配置见：

```text
app/src/main/java/com/example/commerceagent/data/api/ApiConfig.kt
```

## 启动步骤

1. 先启动后端：

```powershell
cd C:\Users\zzcy2\Desktop\agent
.\scripts\start_backend.cmd
```

2. 用 Android Studio 打开：

```text
C:\Users\zzcy2\Desktop\agent\android
```

3. 等待 Gradle Sync 完成。

4. 顶部设备选择 `Pixel 8` 模拟器。

5. 点击绿色 Run 按钮运行 App。

## 主要页面

- 侧边栏会话页：新建、进入、重命名或删除导购会话。
- 聊天页：文本输入、图片上传、SSE 流式回答、商品推荐卡片、点赞/点踩。
- 商品详情页：点击商品卡片进入详情。

## 常见问题

### App 连不上后端

先确认后端在电脑上能打开：

```text
http://127.0.0.1:8000/docs
```

然后确认 Android 端配置是：

```text
http://10.0.2.2:8000
```

### 图片加载不出来

确认后端已经启动，并且商品图片接口可以在浏览器访问。Android 端会把后端返回的相对路径拼成 `http://10.0.2.2:8000/...`。

### 重命名会话提示 405

这表示 Android 请求到了后端，但当前 8000 端口上运行的不是最新后端，或者后端没有正确重启。请在仓库根目录启动：

```powershell
cd C:\Users\zzcy2\Desktop\agent
.\scripts\start_backend.cmd
```

然后打开 `http://127.0.0.1:8000/docs`，确认存在 `PUT /api/sessions/{session_id}`。

### Gradle Sync 提示缺 SDK

在 Android Studio 里进入：

```text
Settings -> Languages & Frameworks -> Android SDK
```

安装提示缺失的 SDK Platform 或 Build Tools 后重新 Sync。
