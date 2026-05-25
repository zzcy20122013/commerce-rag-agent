# 基于 RAG 的多模态电商智能导购 Agent

这是一个面向电商导购场景的多模态 RAG Agent 项目。用户可以用自然语言描述购物需求，也可以上传图片找类似款；系统通过意图路由、SQLite 结构化过滤、Chroma 文本召回、图片向量检索和大模型生成，返回更像真人导购的建议和商品卡片。

## 当前结构

- `backend/`：FastAPI Agent 后端服务。
- `web-debug/`：React Web Debug 调试控制台。
- `android/`：Kotlin + Jetpack Compose 移动端。
- `docs/`：项目方案、计划、架构、评测和开发指南。
- `scripts/`：启动、索引重建和检查脚本。
- `models/`：本机模型缓存目录，不提交。
- `outputs/`：本地运行和导出产物目录，未提交。

更完整的目录说明见 [项目目录说明](docs/project/项目目录说明.md)。

## 当前进度

- 后端主链路：已跑通 `IntentRouter -> 各业务 Agent -> ResponseComposer -> SSE`。
- 大模型回复：导购、决策、FAQ、闲聊和最终用户可见回答均为 Doubao 优先，失败时使用 fallback。
- 会话能力：支持会话列表、新建会话、首轮消息自动命名、重命名会话、历史消息加载和真实删除会话。
- 购物车与订单闭环：支持通过对话或商品卡片加入购物车，支持查看、删除、修改数量、去结算、确认订单、扣减库存、售罄过滤、订单查看、模拟支付、模拟发货、确认收货和退款售后。
- Android 展示端：可在 Android Studio 模拟器运行，模拟器访问后端使用 `http://10.0.2.2:8000`。
- Android 体验：支持商品卡片推荐依据展示、系统语音转文字入口、图片上传/拍照找货、购物车查看和商品详情加购。
- Android 离线兜底：后端不可用时可使用本地 Mock 数据验证聊天、商品卡片、商品详情、加购和提交订单入口。
- 反馈闭环：Android 端按 `feedback_enabled` 显示赞踩，后端记录反馈数据。
- 工程稳定性：支持统一错误响应、运行统计、SSE 断开统计、并发压测脚本和 Android 网络失败重试入口。
- 评测与测试：已有 ResponseComposer、闲聊、反馈显示规则、会话历史/删除等后端测试。

## 本地模型目录

`models/` 不属于 GitHub 仓库内容，只是本机运行真实 embedding 时可能出现的模型权重缓存。删除后不影响源码，但需要重新下载模型才能跑真实本地 embedding。

## 本地配置

本项目只保留根目录 `.env.example` 作为公开模板；后端实际读取的是 `backend/.env`，不要把真实 key 写回模板或提交到 GitHub。

1. 从根目录复制环境变量模板：

```powershell
Copy-Item .env.example backend\.env
```

2. 在本地的 `backend/.env` 中填入你的豆包 Ark API Key：

```env
DOUBAO_API_KEY=你的 key
ARK_API_KEY=你的 key
DOUBAO_MODEL=doubao-seed-2-0-lite-260428
```

如果火山方舟控制台要求使用 endpoint id，就把 `DOUBAO_MODEL` 改成控制台里的 `ep-...`。

## 启动

以下命令默认在仓库根目录执行。

### 1. 启动后端服务

后端提供 Agent、RAG、商品卡片、会话、反馈和图片上传接口。

```powershell
.\scripts\start_backend.cmd
```

默认地址是 `http://127.0.0.1:8000`。

### 2. 启动 Web Debug 调试台

Web Debug 用于开发调试，可以查看 trace、Raw SSE、商品卡片、图片上传和检索链路。

```powershell
.\scripts\start_web_debug.cmd
```

启动后打开 Vite 输出的本地地址即可。页面左侧 Backend 默认填写 `http://127.0.0.1:8000`。

### 3. 启动 Android 原生端

Android 是正式展示端，用于验证接近移动端产品形态的聊天、商品卡片、多轮会话和反馈体验。

1. 打开 Android Studio。
2. 选择本仓库下的 `android/` 目录。
3. 启动 Pixel/Android 模拟器或连接 Android 真机。
4. 确认后端正在 `http://127.0.0.1:8000` 运行。
5. 点击 Android Studio 的 Run。

注意：

- Android 模拟器访问电脑本机后端要使用 `http://10.0.2.2:8000`，项目已按这个地址配置。
- 如果使用真机，需要把 Android 端后端地址改成电脑局域网 IP，例如 `http://192.168.x.x:8000`，并确保手机和电脑在同一网络。

## 关键接口

- `POST /api/chat/stream`：聊天 SSE，返回文本、商品卡片、trace、done。
- `POST /api/upload/image`：上传图片，返回 `upload_id` 和预览地址。
- `GET /api/sessions`：会话列表。
- `POST /api/sessions`：创建会话。
- `GET /api/sessions/{id}/messages`：加载历史消息和商品卡片。
- `PUT /api/sessions/{id}`：重命名会话。
- `DELETE /api/sessions/{id}`：真实删除会话、消息、推荐日志、检索日志和反馈。
- `POST /api/feedback`：提交点赞/点踩。
- `GET /api/products/{id}`：商品详情。
- `GET /api/cart`：查看购物车。
- `POST /api/cart/items`：加入购物车。
- `PUT /api/cart/items/{position}`：按位置修改购物车商品数量。
- `DELETE /api/cart/items/{position}`：按位置删除购物车商品。
- `POST /api/cart/checkout`：提交购物车订单，需携带 `shipping_address`，校验并扣减库存，生成带收货地址快照的待支付订单后清空购物车。
- `GET /api/orders`：查看订单列表。
- `GET /api/orders/{id}`：查看订单详情。
- `POST /api/orders/{id}/pay`：模拟支付。
- `POST /api/orders/{id}/cancel`：取消待支付订单并释放库存。
- `POST /api/orders/{id}/ship`：模拟发货。
- `POST /api/orders/{id}/complete`：确认收货。
- `POST /api/orders/{id}/refund`：模拟退款售后并回补库存。
- `DELETE /api/orders/{id}`：删除订单历史记录，并同步删除后端订单明细；待支付订单会先释放库存。
- `GET /api/runtime/stats`：查看本次后端进程内的请求、错误和 SSE 连接统计。

## 常用维护

重建文本和图片索引：

```powershell
.\scripts\rebuild_indexes.cmd
```

整理后检查项目：

```powershell
.\scripts\check_project.cmd
```

后端测试：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest app\tests -q
```

SSE 并发压测：

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.scripts.stress_sse --concurrency 5 --requests 10
```

Android 构建：

```powershell
cd android
.\gradlew.bat :app:assembleDebug
```

具体想改某个能力时，看 [开发修改指南](docs/developer/开发修改指南.md)。
