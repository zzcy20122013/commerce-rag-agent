# 基于 RAG 的多模态电商智能导购 Agent

这是一个面向电商导购场景的多模态 RAG Agent 项目。用户可以用自然语言描述购物需求，也可以上传图片找类似款；系统通过意图路由、SQLite 结构化过滤、Chroma 文本召回、图片向量检索和大模型生成，返回更像真人导购的建议和商品卡片。

## 当前结构

- `backend/`：FastAPI Agent 服务，包含意图路由、RAG 检索、商品库、SSE 聊天接口和评测脚本。
- `web-debug/`：React Web Debug 控制台，用来验证后端能力、SSE、trace、商品卡片和图片上传。
- `android/`：Android Kotlin + Jetpack Compose 展示端代码。
- `docs/`：项目方案、计划、架构、评测报告和开发修改指南。
- `scripts/`：常用启动、索引重建和检查脚本。

更完整的目录说明见 [项目目录说明](docs/project/项目目录说明.md)。

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

## 常用维护

重建文本和图片索引：

```powershell
.\scripts\rebuild_indexes.cmd
```

整理后检查项目：

```powershell
.\scripts\check_project.cmd
```

具体想改某个能力时，看 [开发修改指南](docs/developer/开发修改指南.md)。
