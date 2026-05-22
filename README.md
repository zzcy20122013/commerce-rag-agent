# 基于 RAG 的多模态电商智能导购 Agent

这是一个面向电商导购场景的多模态 RAG Agent 项目。用户可以用自然语言描述购物需求，也可以上传图片找类似款；系统通过意图路由、SQLite 结构化过滤、Chroma 文本召回、图片向量检索和大模型生成，返回更像真人导购的建议和商品卡片。

## 当前结构

- `backend/`：FastAPI Agent 服务，包含意图路由、RAG 检索、商品库、SSE 聊天接口和评测脚本。
- `web-debug/`：React Web Debug 控制台，用来验证后端能力、SSE、trace、商品卡片和图片上传。
- `android/`：Android Kotlin + Jetpack Compose 展示端代码，已包含登录页、聊天页、侧边栏会话、商品卡片、图片上传入口和反馈入口。
- `docs/`：项目方案、计划、架构、评测报告和开发修改指南。
- `scripts/`：常用启动、索引重建和检查脚本。

更完整的目录说明见 [项目目录说明](docs/project/项目目录说明.md)。

## 当前进度

- 后端主链路：已跑通 `IntentRouter -> 各业务 Agent -> ResponseComposer -> SSE`。
- 大模型回复：导购、决策、FAQ、闲聊和最终用户可见回答均为 Doubao 优先，失败时使用 fallback。
- 会话能力：支持会话列表、新建会话、历史消息加载和真实删除会话。
- Android 展示端：可在 Android Studio 模拟器运行，模拟器访问后端使用 `http://10.0.2.2:8000`。
- 反馈闭环：Android 端按 `feedback_enabled` 显示赞踩，后端记录反馈数据。
- 评测与测试：已有 ResponseComposer、闲聊、反馈显示规则、会话历史/删除等后端测试。

## 本地模型目录

`models/` 不属于 GitHub 仓库内容，只是本机运行真实 embedding 时可能出现的模型权重缓存。删除后不影响源码，但需要重新下载模型才能跑真实本地 embedding。

## 本地配置

1. 复制环境变量模板：

```powershell
Copy-Item .env.example backend\.env
```

2. 在 `backend/.env` 中填入你的豆包 Ark API Key：

```env
DOUBAO_API_KEY=你的 key
ARK_API_KEY=你的 key
DOUBAO_MODEL=doubao-seed-2-0-lite-260428
```

如果火山方舟控制台要求使用 endpoint id，就把 `DOUBAO_MODEL` 改成控制台里的 `ep-...`。

## 启动

后端：

```powershell
.\scripts\start_backend.cmd
```

Web Debug：

```powershell
.\scripts\start_web_debug.cmd
```

默认后端地址是 `http://127.0.0.1:8000`，Web Debug 默认运行在 Vite 输出的本地地址。

Android：

1. 打开 Android Studio。
2. 选择 `C:\Users\zzcy2\Desktop\agent\android`。
3. 启动 Pixel/Android 模拟器。
4. 确认后端正在 `127.0.0.1:8000` 运行。
5. 点击 Run。Android 代码里的后端地址是 `http://10.0.2.2:8000`，这是模拟器访问宿主机本地服务的地址。

## 关键接口

- `POST /api/chat/stream`：聊天 SSE，返回文本、商品卡片、trace、done。
- `POST /api/upload/image`：上传图片，返回 `upload_id` 和预览地址。
- `GET /api/sessions`：会话列表。
- `POST /api/sessions`：创建会话。
- `GET /api/sessions/{id}/messages`：加载历史消息和商品卡片。
- `DELETE /api/sessions/{id}`：真实删除会话、消息、推荐日志、检索日志和反馈。
- `POST /api/feedback`：提交点赞/点踩。
- `GET /api/products/{id}`：商品详情。

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

Android 构建：

```powershell
cd android
.\gradlew.bat :app:assembleDebug
```

具体想改某个能力时，看 [开发修改指南](docs/developer/开发修改指南.md)。
