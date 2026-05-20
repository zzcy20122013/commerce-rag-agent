# 四仓代码复用分析与 Phase 0 调研结论

> 项目：基于 RAG 的多模态电商智能导购 Agent  
> 目标：从四个参考仓库中提炼可复用资产，明确哪些可借鉴、哪些不宜直接搬运，并为后续五个阶段计划提供依据。

## 1. 结论摘要

四个仓库不适合直接合并成一个工程。更稳妥的方式是：

1. 用 `Conversational-E-Commerce-RAG-Agent` 参考前后端分离、聊天组件、商品/订单/购物车页面和基础 ORM 设计。
2. 用 `ecommerce-rag-agent` 参考 LangGraph Agent 流程和“搜索工具 + 推荐生成”的主链路。
3. 用 `multimodal-rag-ecommerce` 参考图文 embedding、图片向量入库、图片检索和多模态召回流程。
4. 用 `MultiAgent-Commerce-Copilot` 参考意图路由、FAQ RAG、SQLite 商品查询和 Streamlit 原型链路。

我们的项目应重新组织为一个干净工程：

```text
Android / React Debug
  -> FastAPI
    -> LangGraph Agents
      -> LlamaIndex Retrieval
        -> SQLite + Chroma
          -> bge-m3 + Chinese-CLIP
```

## 2. 参考仓库分析

### 2.1 Conversational-E-Commerce-RAG-Agent

本地路径：

```text
C:\Users\zzcy2\Desktop\agent\repos\Conversational-E-Commerce-RAG-Agent
```

关键文件：

| 文件 | 观察 |
| --- | --- |
| `client/src/ChatWidget.jsx` | 有完整聊天浮窗、登录注册、商品卡片、购物车、订单追踪 UI 逻辑 |
| `client/src/api/apiService.js` | 有 Auth、Products、Cart、Orders 的 API 调用封装 |
| `server/app/main.py` | FastAPI 应用入口 |
| `server/app/routers/routes.py` | 实际只挂了 `auth_route`，业务路由没有完整接入 |
| `server/app/models/product_model.py` | 商品、订单、购物车、分类 ORM 模型 |
| `server/app/models/payment_model.py` | 支付、物流 ORM 模型 |
| `server/requirements.txt` | 依赖里含 FastAPI、SQLAlchemy、LangChain，但版本偏新且存在拼写异常依赖 |

可复用资产：

1. React 调试后台的聊天 UI 结构。
2. 商品卡片、购物车卡片、订单追踪卡片的组件思路。
3. Auth Context 和 token 存储方式。
4. 商品、订单、购物车、支付、物流的基础数据模型。
5. FastAPI + SQLAlchemy + Alembic 的工程分层方式。

不建议直接搬的部分：

1. 后端业务路由不完整，README 描述和实际代码不完全一致。
2. 前端接口路径存在 `/api/auth/login`、`/api/chat/message`、`/api/v1` 等不一致风险。
3. 聊天接口不是 SSE，和我们的 Android 流式体验目标不一致。
4. 依赖版本过新，`fastapi==0.135.3`、`starlette==1.0.0` 等组合需要谨慎验证。
5. UI 里有较多 emoji 和印度卢比符号，不适合作为正式端样式直接复用。

迁移方式：

1. 只抽取 React 调试后台概念，不直接作为正式端。
2. 商品卡片协议改成我们的 `product_cards` JSON。
3. SQLAlchemy 模型字段重写为适合中文电商数据的 SQLite schema。
4. 后端路由重建，不沿用现有路由。

### 2.2 ecommerce-rag-agent

本地路径：

```text
C:\Users\zzcy2\Desktop\agent\repos\ecommerce-rag-agent
```

关键文件：

| 文件 | 观察 |
| --- | --- |
| `ecommerce_agent/agent.py` | LangGraph `StateGraph`、tool node、chat node、MemorySaver |
| `ecommerce_agent/ecommerce.py` | MongoDB Vector Search、OpenAI embedding、推荐 prompt |
| `ecommerce_agent/demo.py` | FastAPI + CopilotKit 暴露 LangGraph Agent |
| `ecommerce_agent/product_data.py` | 示例商品数据 |
| `pyproject.toml` | LangGraph、LangChain、OpenAI、CopilotKit、PyMongo 依赖 |

可复用资产：

1. LangGraph 的基本组织方式：`AgentState`、`chat_node`、`tool_node`、`workflow.compile()`。
2. 将“商品检索”封装为工具，再由 Agent 决定调用的思路。
3. 查询阶段状态字段：`search_stage`、`progress_percentage`、`active_filters`、`matched_products_count`。
4. 推荐生成 prompt 中“只基于候选商品回答”的约束。
5. 基于查询历史和处理时间做可观测记录的思路。

不建议直接搬的部分：

1. 使用 MongoDB Atlas Vector Search，我们定版使用 Chroma + SQLite。
2. 使用 OpenAI embedding 和 GPT-4，我们定版使用 bge-m3 + DeepSeek。
3. 价格和类目解析是简单字符串规则，对中文需求不够可靠。
4. Agent 状态里使用类属性保存运行时状态，不适合并发请求。
5. 强依赖 CopilotKit，不符合我们 Android + FastAPI SSE 的主链路。

迁移方式：

1. 参考 LangGraph 拓扑，不直接搬 agent 文件。
2. 新建 `IntentRouterAgent`、`ShoppingGuideAgent`、`MultimodalSearchAgent` 等节点。
3. 用 DeepSeek 结构化输出替代字符串规则解析。
4. 用 LlamaIndex retriever 和 SQLite filter 替代 MongoDB pipeline。
5. 用 FastAPI SSE 替代 CopilotKit endpoint。

### 2.3 multimodal-rag-ecommerce

本地路径：

```text
C:\Users\zzcy2\Desktop\agent\repos\multimodal-rag-ecommerce
```

关键文件：

| 文件 | 观察 |
| --- | --- |
| `preprocess.py` | 下载数据集、处理商品文本和图片、用 CLIP 生成文本/图片 embedding |
| `load_vectordb.py` | 将文本和图片向量写入 Pinecone，并做 Recall@K 评估 |
| `chatbot_backend.py` | Streamlit 后端里完成 CLIP embedding、Pinecone query、LLM 生成 |
| `app.py` | Streamlit 前端 |
| `marketing_sample_for_amazon...csv` | 商品示例数据，可用于本地原型 |

可复用资产：

1. 多模态数据预处理流程。
2. 商品文本 enhanced text 组装方式：名称、类目、价格、描述、规格。
3. 每个商品支持多张图片 embedding 的设计。
4. 向量 ID 设计：`product_id_text`、`product_id_img_i`。
5. 召回后构造商品候选列表，再交给 LLM 生成回答的流程。
6. Recall@K 评估思路。

不建议直接搬的部分：

1. 使用英文 CLIP，我们定版使用 Chinese-CLIP。
2. 使用 Pinecone，我们定版使用 Chroma 本地持久化。
3. `chatbot_backend.py` 混合了配置、模型加载、检索、LLM 调用和 Streamlit secret，不适合生产结构。
4. 文件顶部直接调用 `generate_with_perplexity2()`，导入即触发外部 API 调用，不可取。
5. 图片与文本向量简单平均，后续更推荐分路召回后融合 rerank。

迁移方式：

1. 重写为 `embeddings/chinese_clip.py` 和 `retrieval/image_index.py`。
2. 商品图片向量写入 Chroma collection：`product_images`。
3. 保留多图片、多 metadata、Recall@K 的思想。
4. 图片召回和文本约束过滤分开做，最后在 `reranker.py` 融合排序。

### 2.4 MultiAgent-Commerce-Copilot

本地路径：

```text
C:\Users\zzcy2\Desktop\agent\repos\MultiAgent-Commerce-Copilot
```

关键文件：

| 文件 | 观察 |
| --- | --- |
| `app/router.py` | semantic-router + MiniLM，支持 faq、sql、chitchat 三类路由 |
| `app/faq.py` | ChromaDB FAQ ingest、top-3 query、Groq 生成答案 |
| `app/sql.py` | LLM 生成 SQL，只执行 SELECT，再将结果转自然语言 |
| `app/main.py` | Streamlit UI，根据 router 分发到 faq/sql/chitchat |
| `app/resources/faq_data.csv` | FAQ 示例数据 |
| `app/db.sqlite` | 商品 SQLite 示例库 |

可复用资产：

1. 意图路由样例组织方式。
2. `faq`、`sql`、`chitchat` 三类任务边界。
3. FAQ RAG 的 Chroma ingest/query/generate 链路。
4. SQLite 商品查询作为结构化检索工具的思路。
5. LLM-to-SQL 里只允许 SELECT 的基本安全意识。

不建议直接搬的部分：

1. 路由类别太少，需要扩展到商品推荐、商品知识、对比、订单、图搜、FAQ、闲聊。
2. 使用 MiniLM，我们定版文本 embedding 是 bge-m3。
3. SQL 由 LLM 直接生成，虽然只允许 SELECT，但仍需更严格 SQL AST 校验。
4. Streamlit UI 不进入我们的正式产品链路。
5. FAQ 使用 `chromadb.Client()` 内存模式，正式项目要使用持久化 Chroma。

迁移方式：

1. 复用路由样例集的写法，但用 DeepSeek 结构化分类或 LangGraph 路由节点实现。
2. FAQ ingest/query 思路迁移到 LlamaIndex + Chroma。
3. SQL 查询不要作为第一阶段主能力，第一阶段优先用明确的 SQLite service/filter。
4. 后续如做自然语言商品筛选，可以加入 SQL 生成，但必须做 AST 校验和字段白名单。

## 3. 我们项目的目标工程结构

建议新建独立目录，不直接在四个参考仓库内改：

```text
C:\Users\zzcy2\Desktop\agent\commerce-rag-agent
```

目标结构：

```text
commerce-rag-agent/
  backend/
    app/
      main.py
      api/
        chat.py
        upload.py
        products.py
        orders.py
        sessions.py
        feedback.py
        debug.py
      agents/
        graph.py
        state.py
        intent_router.py
        shopping_guide.py
        product_knowledge.py
        compare.py
        faq.py
        order.py
        multimodal.py
        chitchat.py
      retrieval/
        text_index.py
        image_index.py
        retrievers.py
        reranker.py
      llm/
        deepseek_client.py
        prompts.py
        schemas.py
      embeddings/
        bge_m3.py
        chinese_clip.py
      services/
        product_service.py
        order_service.py
        session_service.py
        feedback_service.py
        log_service.py
      models/
        db.py
        tables.py
        schemas.py
      data/
        app.sqlite
        chroma/
        product_images/
        docs/
      scripts/
        seed_products.py
        ingest_text.py
        ingest_images.py
        run_eval.py
      tests/
        test_intent_router.py
        test_product_filter.py
        test_text_retrieval.py
        test_image_retrieval.py
        test_chat_stream.py
  web-debug/
  android/
  docs/
    architecture.md
    api.md
    evaluation.md
```

## 4. 模块迁移映射

| 我们的模块 | 参考来源 | 迁移策略 |
| --- | --- | --- |
| `api/chat.py` | Conversational 前端聊天接口 + ecommerce demo | 重写 FastAPI SSE，不用 CopilotKit |
| `agents/graph.py` | ecommerce-rag-agent `agent.py` | 参考 StateGraph，不搬全局状态写法 |
| `agents/intent_router.py` | MultiAgent `router.py` | 扩展路由类别，改成中文样例和 DeepSeek fallback |
| `agents/shopping_guide.py` | ecommerce-rag-agent `search_ecommerce` | 改成结构化约束提取 + 检索 + rerank |
| `retrieval/text_index.py` | MultiAgent `faq.py` | 改 LlamaIndex + bge-m3 + Chroma 持久化 |
| `retrieval/image_index.py` | multimodal `preprocess.py`、`chatbot_backend.py` | 改 Chinese-CLIP + Chroma |
| `retrieval/reranker.py` | 四仓均无成熟实现 | 新写，融合相似度、价格、库存、评分 |
| `models/tables.py` | Conversational ORM + MultiAgent SQLite | 重写 SQLite 表结构 |
| `web-debug/` | Conversational React client | 参考组件，不原样迁移 |
| `android/` | 四仓无 | 新建 Kotlin + Jetpack Compose |

## 5. Phase 0 调研结论

本阶段的核心判断是：四个参考仓库都不能作为完整主工程直接继承，但各自有清晰的参考价值。我们应该新建独立工程 `commerce-rag-agent`，按“FastAPI + LangGraph + LlamaIndex + Chroma + SQLite + DeepSeek + bge-m3 + Chinese-CLIP”的技术路线重建。

后续正式计划已经拆成五份文档：

| 阶段 | 文档 | 说明 |
| --- | --- | --- |
| Phase 1 | `plans/01-MVP落地计划.md` | 文本导购主链路，跑通 FastAPI、SQLite、DeepSeek、bge-m3、Chroma、LangGraph、SSE、商品卡片 |
| Phase 2 | `plans/02-多模态检索计划.md` | 接入 Chinese-CLIP，完成图片上传、商品图片向量库、看图找类似款 |
| Phase 3 | `plans/03-Android展示端计划.md` | Kotlin + Jetpack Compose 正式展示端，支持流式聊天、商品卡片、图片上传、反馈 |
| Phase 4 | `plans/04-质量评测与反馈闭环计划.md` | 意图、检索、推荐、图片召回、用户反馈的评测体系 |
| Phase 5 | `plans/05-工程化与部署计划.md` | Docker Compose、配置管理、日志、索引重建、测试和部署文档 |

因此，本文件只保留 Phase 0 的调研和复用判断，不再承担 MVP 执行计划职责。MVP 的详细任务、验收标准和执行顺序以 `plans/01-MVP落地计划.md` 为准。

## 6. 风险与处理

| 风险 | 处理方式 |
| --- | --- |
| 四仓代码风格差异大 | 不合并代码，只吸收设计 |
| DeepSeek 结构化输出不稳定 | Pydantic 校验，失败时重试一次 |
| Chroma 本地库数据变脏 | 提供 rebuild index 脚本 |
| Chinese-CLIP 本地推理慢 | 先离线批量生成商品图向量，查询端只处理用户上传图 |
| LLM-to-SQL 有注入风险 | 第一阶段不开放自由 SQL，先用 service/filter |
| SSE 中断 | 客户端显示重试按钮，后端消息落库 |
| 参考仓库 license 不一致 | 借鉴思路，不复制商业敏感代码 |

## 7. 依赖建议

后端第一阶段：

```text
fastapi
uvicorn[standard]
pydantic
pydantic-settings
sqlalchemy
aiosqlite
python-dotenv
httpx
langgraph
llama-index
llama-index-vector-stores-chroma
chromadb
sentence-transformers
```

第二阶段多模态：

```text
torch
transformers
Pillow
cn_clip 或 chinese-clip 相关实现
```

调试前端：

```text
react
vite
typescript
```

Android：

```text
Kotlin
Jetpack Compose
OkHttp SSE 或自定义 EventSource
Coil
Navigation Compose
```

## 8. 下一步建议

下一步进入 Phase 1，执行 `plans/01-MVP落地计划.md`。

Phase 1 的优先闭环是：

1. 新建 `commerce-rag-agent` 工程。
2. 搭建 FastAPI `/health`。
3. 建立 SQLite schema 和 seed 数据。
4. 封装 DeepSeek client。
5. 建立 bge-m3 + Chroma 文本索引。
6. 实现 LangGraph `shopping_guide` 主链路。
7. 实现 `/api/chat/stream` SSE。
8. 返回商品卡片 JSON。

做到这一步，项目就有可演示的核心闭环：用户输入购物需求，系统流式回答并返回商品卡片。
