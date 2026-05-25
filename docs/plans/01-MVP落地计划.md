# MVP 落地计划 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建第一版可演示闭环：用户输入购物需求，后端通过 RAG 和 Agent 检索商品并用 SSE 返回导购回答与商品卡片。

**Architecture:** 第一阶段只做文本导购，不接图片检索和 Android。FastAPI 提供服务边界，LangGraph 编排 IntentRouter 与 ShoppingGuide，当前采用自研 Chroma retriever 负责文本检索，SQLite 存商品、会话、消息、反馈和日志；LlamaIndex 保留为后续可接入方向。

**Tech Stack:** Python FastAPI, LangGraph, Custom Chroma Retriever, Chroma, SQLite, SQLAlchemy, bge-m3, Chinese-CLIP, Doubao-Seed-2.0-lite, SSE, React + Vite debug UI.

---

## 1. 范围

本阶段只实现“文本导购主链路”。

包含：

- FastAPI 后端工程骨架
- SQLite 商品、会话、消息、反馈、检索日志表
- 商品 seed 数据
- Doubao-Seed-2.0-lite client
- bge-m3 文本 embedding
- Chroma 文本向量库
- 自研 Chroma retriever 商品与 FAQ 检索，后续可接入 LlamaIndex
- `.md`、`.txt`、`.csv` 非结构化文档导入
- LangGraph Agent 主流程
- 会话记忆与多轮约束继承
- `/api/chat/stream` SSE
- 商品卡片 JSON 协议
- React debug 页面

不包含：

- Chinese-CLIP 图片检索
- Android 原生端
- Docker Compose
- PostgreSQL 迁移
- 真实支付、真实物流和完整交易闭环

## 2. 文件结构

创建工程目录：

```text
agent/
  backend/
    app/
      main.py
      api/
        chat.py
        docs.py
        products.py
        sessions.py
        feedback.py
        debug.py
      agents/
        graph.py
        state.py
        intent_router.py
        shopping_guide.py
        faq.py
        chitchat.py
      retrieval/
        text_index.py
        document_index.py
        retrievers.py
        reranker.py
      embeddings/
        bge_m3.py
      llm/
        openai_compatible_client.py
        prompts.py
        schemas.py
      models/
        db.py
        tables.py
        schemas.py
      services/
        product_service.py
        session_service.py
        document_service.py
        feedback_service.py
        log_service.py
      scripts/
        seed_products.py
        ingest_text.py
        ingest_docs.py
      tests/
        test_health.py
        test_product_filter.py
        test_intent_router.py
        test_document_ingestion.py
        test_chat_stream.py
    pyproject.toml
    .env.example
  web-debug/
```

## 3. 数据模型

SQLite 表：

| 表 | 关键字段 |
| --- | --- |
| `products` | `id`, `title`, `category`, `brand`, `price`, `description`, `specs_json`, `rating`, `sales`, `stock`, `image_url` |
| `sessions` | `id`, `user_id`, `title`, `created_at`, `updated_at` |
| `messages` | `id`, `session_id`, `role`, `content`, `metadata_json`, `created_at` |
| `documents` | `id`, `source_file`, `doc_type`, `category`, `version`, `metadata_json`, `created_at` |
| `feedback` | `id`, `message_id`, `rating`, `reason`, `created_at` |
| `retrieval_logs` | `id`, `session_id`, `query`, `intent`, `filters_json`, `candidates_json`, `created_at` |
| `recommendation_logs` | `id`, `session_id`, `message_id`, `products_json`, `created_at` |

## 4. 商品卡片协议

SSE 返回 `product_cards` 事件：

```json
{
  "type": "product_cards",
  "cards": [
    {
      "product_id": "p001",
      "title": "荣耀平板 X",
      "subtitle": "适合学生记笔记和网课",
      "price": 1899,
      "original_price": 2199,
      "image_url": "/static/products/p001.jpg",
      "rating": 4.7,
      "sales": 3821,
      "stock_status": "in_stock",
      "reasons": ["预算内", "适合记笔记", "屏幕适合网课"],
      "score": 0.91
    }
  ]
}
```

## 5. 任务拆分

### Task 1: 后端工程骨架

**Files:**

- Create: `backend/app/main.py`
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Test: `backend/app/tests/test_health.py`

- [ ] 创建 FastAPI app，暴露 `/health`。
- [ ] 添加 CORS 配置，允许本地 React debug 访问。
- [ ] 添加 `.env.example`，包含 `DOUBAO_API_KEY`、`DATABASE_URL`、`CHROMA_PATH`。
- [ ] 编写 `test_health.py`，断言 `/health` 返回 `{"status":"ok"}`。
- [ ] 运行 `pytest app/tests/test_health.py -v`，预期通过。

### Task 2: SQLite 数据层

**Files:**

- Create: `backend/app/models/db.py`
- Create: `backend/app/models/tables.py`
- Create: `backend/app/models/schemas.py`
- Create: `backend/app/scripts/seed_products.py`
- Test: `backend/app/tests/test_product_filter.py`

- [ ] 定义 SQLAlchemy engine、session factory、Base。
- [ ] 定义 `Product`、`Session`、`Message`、`Feedback`、`RetrievalLog`、`RecommendationLog`。
- [ ] 编写 seed 脚本，插入至少 20 个中文商品样例，覆盖平板、耳机、鞋、背包。
- [ ] 实现按类目、价格、库存过滤商品。
- [ ] 测试“平板 + 预算 2000”能返回价格小于等于 2000 的平板商品。

### Task 3: Doubao-Seed-2.0-lite Client

**Files:**

- Create: `backend/app/llm/openai_compatible_client.py`
- Create: `backend/app/llm/prompts.py`
- Create: `backend/app/llm/schemas.py`
- Test: `backend/app/tests/test_intent_router.py`

- [ ] 封装非流式 chat completion。
- [ ] 封装流式 chat completion，返回 async iterator。
- [ ] 定义 `ShoppingConstraints` schema，字段包含 `category`、`budget_max`、`use_cases`、`audience`、`preferences`。
- [ ] 定义意图分类 schema，意图包含 `shopping_guide`、`faq`、`product_knowledge`、`chitchat`。
- [ ] 测试“我想买学生党平板，预算 2000，记笔记和网课”能提取预算和用途。

### Task 4: 文本向量与 RAG

**Files:**

- Create: `backend/app/embeddings/bge_m3.py`
- Create: `backend/app/retrieval/text_index.py`
- Create: `backend/app/retrieval/retrievers.py`
- Create: `backend/app/scripts/ingest_text.py`

- [ ] 封装 bge-m3 embedding model。
- [ ] 建立 Chroma 持久化目录 `backend/app/data/chroma`。
- [ ] 建立 `product_text` collection。
- [ ] 建立 `faq` collection。
- [ ] 将商品标题、详情、参数、卖点组合为检索文本。
- [ ] 将 FAQ 样例写入 Chroma。
- [ ] 验证“退货政策是什么”能召回 FAQ。
- [ ] 验证“适合学生记笔记的平板”能召回平板商品。

### Task 5: 非结构化文档上传/导入

**Files:**

- Create: `backend/app/api/docs.py`
- Create: `backend/app/services/document_service.py`
- Create: `backend/app/retrieval/document_index.py`
- Create: `backend/app/scripts/ingest_docs.py`
- Test: `backend/app/tests/test_document_ingestion.py`

- [ ] 支持 `.md`、`.txt`、`.csv` 三类文件导入。
- [ ] 解析文档文本并按固定长度 chunk 切分。
- [ ] 为每个 chunk 写入 metadata：`doc_type`、`source_file`、`category`、`version`。
- [ ] 使用 bge-m3 生成 embedding。
- [ ] 写入 Chroma `knowledge_docs` collection。
- [ ] 将文档元数据写入 SQLite `documents` 表。
- [ ] 提供 `/api/docs/ingest` 接口。
- [ ] 测试上传营销文档后，查询“春季活动优惠是什么”能召回对应 chunk。

### Task 6: LangGraph Agent 主流程

**Files:**

- Create: `backend/app/agents/state.py`
- Create: `backend/app/agents/graph.py`
- Create: `backend/app/agents/intent_router.py`
- Create: `backend/app/agents/shopping_guide.py`
- Create: `backend/app/agents/faq.py`
- Create: `backend/app/agents/chitchat.py`

- [ ] 定义 `AgentState`，包含 `messages`、`intent`、`constraints`、`memory`、`retrieved_items`、`product_cards`、`trace`。
- [ ] 定义会话记忆字段，保存 `budget_max`、`category`、`audience`、`use_cases`、`preferences`。
- [ ] 实现 `IntentRouterAgent`，先用规则 + Doubao-Seed-2.0-lite fallback。
- [ ] 实现 `ShoppingGuideAgent`，完成约束提取、SQLite 过滤、Chroma 召回、rerank、推荐理由生成。
- [ ] 实现多轮约束继承：用户追问“有没有更轻一点的”时继承上一轮预算、品类和用途，并新增“轻便”偏好。
- [ ] 实现 `FAQAgent`，从 `faq` collection 检索并回答。
- [ ] 实现 `ChitchatAgent`，限制为导购身份的轻量闲聊。
- [ ] 编译 LangGraph，入口为 intent router。

### Task 7: SSE 聊天接口

**Files:**

- Create: `backend/app/api/chat.py`
- Modify: `backend/app/main.py`
- Test: `backend/app/tests/test_chat_stream.py`

- [ ] 实现 `/api/chat/stream`。
- [ ] SSE 事件类型支持 `message`、`trace`、`product_cards`、`error`、`done`。
- [ ] 用户消息先写入 `messages` 表。
- [ ] Agent 回复写入 `messages` 表。
- [ ] 检索和推荐记录写入日志表。
- [ ] 测试接口返回 `text/event-stream`。

### Task 8: React Debug 页面

**Files:**

- Create: `web-debug/package.json`
- Create: `web-debug/src/App.tsx`
- Create: `web-debug/src/api/chatStream.ts`
- Create: `web-debug/src/components/ProductCards.tsx`

- [ ] 创建 Vite React TypeScript 工程。
- [ ] 实现聊天输入框。
- [ ] 实现 SSE 消息接收。
- [ ] 实现商品卡片渲染。
- [ ] 实现 trace 面板，显示 intent、filters、retrieved product ids。
- [ ] 增加文档导入调试入口，支持上传 `.md`、`.txt`、`.csv`。

## 6. 验收标准

MVP 完成时，必须满足：

1. 后端 `/health` 正常。
2. seed 商品写入 SQLite。
3. 文本索引写入 Chroma。
4. 非结构化文档能写入 `knowledge_docs` collection。
5. 输入“帮我推荐 2000 以内适合学生记笔记的平板”能得到流式回答。
6. 第二轮追问“有没有更轻一点的”时仍继承预算、品类和用途。
7. SSE 返回至少 3 个商品卡片。
8. React debug 页面能显示文字回答、商品卡片、trace 和文档导入结果。
9. 所有第一阶段测试通过。

## 7. 执行顺序

推荐顺序：

1. Task 1
2. Task 2
3. Task 3
4. Task 4
5. Task 5
6. Task 6
7. Task 7
8. Task 8

每个 Task 独立提交一次，便于回滚和检查。


