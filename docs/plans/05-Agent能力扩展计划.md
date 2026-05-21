# 05-Agent能力扩展计划

## 目标

将导购 Agent 从“商品推荐”扩展到“商品咨询、商品对比、订单查询、澄清追问和多轮约束继承”。

## 当前完成状态

状态：核心能力已完成第三版，已适配 100 条真实商品数据集，并完成导购 Prompt 统一管理。当前不再优先新增 Agent 数量，而是优先补强已有 Agent 的导购表达、约束继承、推荐取舍和评测稳定性。

当前补强重点：

1. 让回答更像真人导购：先确认需求重点，再给明确倾向，避免写成检索报告。
2. 强化主推、备选和劝退：不要平均介绍所有商品，要说明适合谁、不适合谁。
3. 统一预算不匹配话术：`no_exact_match=true` 时必须说明没有严格符合条件的商品，再给“可加预算考虑”或“退一步可选”。
4. 提升多轮继承：第二轮追问要继承上一轮预算、品类、用途和偏好。
5. 通过 Plan 08 小规模评测固定效果，避免改 Prompt 后其他场景回退。

已完成：

1. IntentRouter 扩展
   - 支持 `shopping_guide`
   - 支持 `decision_guide`
   - 支持 `product_knowledge`
   - 支持 `compare`
   - 支持 `order_query`
   - 支持 `purchase_help`
   - 支持 `faq`
   - 支持 `clarification`
   - 支持 `chitchat`
   - trace 中输出 intent 和 confidence
   - 已接入 `taxonomy.json`，品类、子品类、用途、偏好不再散落在硬编码字典中

2. ShoppingGuideAgent
   - 文件：`backend/app/agents/shopping_guide.py`
   - 支持 SQLite 结构化过滤 + Chroma 文本语义召回 + 本地 rerank
   - 支持预算、品类、子品类、用途、偏好、库存等约束
   - 支持严格条件筛选：如“200 元以下的蓝牙耳机有哪些？”无结果时不硬推超预算或不相关商品
   - 支持无严格匹配时展示同子品类“可加预算考虑”备选，并明确说明预算差距
   - 支持统一商品卡片 JSON 输出

3. DecisionGuideAgent
   - 文件：`backend/app/agents/decision_guide.py`
   - 支持开放式选购决策场景
   - 示例：`我马上大学了，想买一台电脑，不知道买什么样的`
   - 先给选购框架，再结合商品卡片给当前可买选择
   - 适合“用户还没明确预算/参数/品类细分”的导购入口

4. ProductKnowledgeAgent
   - 文件：`backend/app/agents/product_knowledge.py`
   - 支持通过商品 ID / 商品名 / 商品相关描述定位商品
   - 返回商品价格、评分、库存、描述、结构化参数和标签
   - 返回统一商品卡片
   - 已接入 `documents` 表中的商品知识片段，包括营销说明、官方 FAQ 和用户评价
   - 支持“这款怎么用？”这类追问从上一轮 `last_product_ids` 继承商品

5. CompareAgent
   - 文件：`backend/app/agents/compare.py`
   - 支持 `p_beauty_002 和 p_beauty_004 哪个好` 这类真实商品 ID 对比
   - 支持从上一轮推荐记忆里读取 `last_product_ids`
   - 输出价格、评分、销量、参数、场景和结论
   - 已接入商品知识文档作为对比证据，能围绕“敏感肌、修护维稳、通勤、跑步”等需求做偏好判断
   - Web Debug 已支持对比结果表格展示

6. OrderAgent
   - 文件：`backend/app/agents/order.py`
   - 新增 SQLite 模拟订单表 `orders`
   - 服务文件：`backend/app/services/order_service.py`
   - 内置模拟订单：
     - `ord_1001`
     - `ord_1002`
   - 支持订单状态、物流状态、退货状态查询

7. PurchaseHelpAgent
   - 文件：`backend/app/agents/purchase.py`
   - 支持“怎么买”“如何下单”“加入购物车”等购买流程类问题
   - 能结合上一轮推荐的 `last_product_ids` 给出购买建议

8. FAQAgent
   - 文件：`backend/app/agents/faq.py`
   - 支持售后、退货政策、保修、发票等 FAQ / 售后知识库问答
   - 通过 Chroma 检索 FAQ 文档，再由 LLM 基于检索上下文回答

9. ChitchatAgent
   - 文件：`backend/app/agents/chitchat.py`
   - 作为兜底节点，处理无法归类或普通闲聊问题

10. MultimodalSearchAgent
   - 文件：`backend/app/agents/multimodal.py`
   - 作为独立接口型 Agent，通过 `/api/chat/stream` 中的 `upload_id` 触发
   - 支持图片相似检索 + 文本约束 rerank + 商品卡片返回
   - 不在 LangGraph 主路由中，由图片上传入口直接调用

11. 多轮记忆增强
   - ShoppingGuideAgent 会继承：
     - `budget_max`
     - `category`
     - `subcategory`
     - `audience`
     - `use_cases`
     - `preferences`
     - `strict_filter`
     - `last_product_ids`
   - 支持“有没有更轻一点的”“换个便宜点的”这类追问继续沿用上一轮预算和品类
   - 修复 `p_beauty_002` 这类真实商品 ID 中的数字被误识别为预算的问题

12. LangGraph 主流程扩展
   - 文件：`backend/app/agents/graph.py`
   - 已接入：
     - `decision_guide`
     - `shopping_guide`
     - `product_knowledge`
     - `compare`
     - `order`
     - `purchase_help`
     - `faq`
     - `clarification`
     - `chitchat`

13. 通用分类与严格筛选
   - 文件：`backend/app/data/taxonomy.json`
   - 文件：`backend/app/services/taxonomy.py`
   - 支持按统一 taxonomy 提取：
     - category
     - subcategory
     - use_cases
     - preferences
     - strict_filter
   - 避免每新增一个品类都在 `intent_router.py` / `product_service.py` 里新增硬编码过滤

14. Prompt Registry
   - 文件：`backend/app/llm/prompt_blocks.py`
   - 文件：`backend/app/llm/prompt_registry.py`
   - 将通用导购人格、事实约束、预算规则、输出结构与 Agent 专属任务拆分管理
   - `generation.py` 只负责调用 LLM，不再直接维护大段 prompt

## 验证用例

已本地验证：

1. `帮我推荐一款适合敏感肌、修护维稳的精华，预算 800 以内`
   - 路由：`shopping_guide`
   - 返回：`p_beauty_002 / p_beauty_004 / p_beauty_024`

2. `有没有更便宜的？`
   - 输入上一轮 memory 后路由：`shopping_guide`
   - 继承：预算 800、品类美妆护肤、用途敏感肌护理
   - 新增偏好：性价比

3. `兰蔻小黑瓶适合敏感肌吗？`
   - 路由：`product_knowledge`
   - 返回：商品参数、商品卡片和知识库 FAQ / 营销说明片段

4. `p_beauty_002 和 p_beauty_004 哪个更适合敏感肌修护维稳？`
   - 路由：`compare`
   - 返回：对比结论、两张商品卡片和文档证据

5. `我的订单 ord_1001 到哪了？`
   - 路由：`order_query`
   - 返回：订单状态、物流状态、退货状态

6. `这款怎么用？`
   - 输入上一轮 memory：`last_product_ids=["p_beauty_002"]`
   - 路由：`product_knowledge`
   - 继承上一轮商品并返回用法、注意事项和商品卡片

7. `推荐一款适合油皮的洗面奶`
   - 路由：`shopping_guide`
   - 约束：`美妆护肤 / 洁面 / 控油`
   - 返回：`p_beauty_011`
   - 不再返回粉底、散粉、精华等不相关商品

8. `200 元以下的蓝牙耳机有哪些？`
   - 路由：`shopping_guide`
   - 约束：`数码电子 / 耳机 / budget_max=200 / strict_filter=true`
   - 返回空商品卡
   - 回答明确说明没有严格符合条件的现货商品，不硬推超预算商品

9. `我马上大学了，想买一台电脑，不知道买什么样的`
   - 路由：`decision_guide`
   - 先输出选购框架，再结合商品卡片给当前可买选择

10. `这两个哪个好？`
   - 输入上一轮 memory 中的 `last_product_ids`
   - 路由：`compare`
   - Web Debug 可展示对比表格

## 后续可增强

1. OrderAgent 后续可替换为真实订单/物流 API。
2. 多轮记忆后续可持久化为更结构化的会话状态，而不是只从最近 assistant message 读取 memory。
3. 扩充 Plan 08 评测集，验证意图路由准确率、多轮约束继承准确率、严格筛选正确率和导购回答稳定性。
4. 将 Prompt Registry 引入版本号，例如 `shopping_guide_v1.1`，方便后续评测对比。
5. 图搜 Agent 后续可接入更完整的图片 query 改写与跨模态 rerank 策略。
6. 针对“像真人导购”建立回答样例库，沉淀推荐、对比、劝退、追问、无严格匹配等高频话术模板。
