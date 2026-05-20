# 05-Agent能力扩展计划

## 目标

将导购 Agent 从“商品推荐”扩展到“商品咨询、商品对比、订单查询、澄清追问和多轮约束继承”。

## 当前完成状态

状态：核心能力已完成第一版。

已完成：

1. IntentRouter 扩展
   - 支持 `shopping_guide`
   - 支持 `product_knowledge`
   - 支持 `compare`
   - 支持 `order_query`
   - 支持 `faq`
   - 支持 `clarification`
   - trace 中输出 intent 和 confidence

2. ProductKnowledgeAgent
   - 文件：`backend/app/agents/product_knowledge.py`
   - 支持通过商品 ID / 商品名 / 商品相关描述定位商品
   - 返回商品价格、评分、库存、描述、结构化参数和标签
   - 返回统一商品卡片

3. CompareAgent
   - 文件：`backend/app/agents/compare.py`
   - 支持 `p201 和 p203 哪个好` 这类对比
   - 支持从上一轮推荐记忆里读取 `last_product_ids`
   - 输出价格、评分、销量、参数、场景和结论

4. OrderAgent
   - 文件：`backend/app/agents/order.py`
   - 新增 SQLite 模拟订单表 `orders`
   - 服务文件：`backend/app/services/order_service.py`
   - 内置模拟订单：
     - `ord_1001`
     - `ord_1002`
   - 支持订单状态、物流状态、退货状态查询

5. 多轮记忆增强
   - ShoppingGuideAgent 会继承：
     - `budget_max`
     - `category`
     - `audience`
     - `use_cases`
     - `preferences`
     - `last_product_ids`
   - 支持“有没有更轻一点的”“换个便宜点的”这类追问继续沿用上一轮预算和品类

6. LangGraph 主流程扩展
   - 文件：`backend/app/agents/graph.py`
   - 已接入：
     - `product_knowledge`
     - `compare`
     - `order`
     - `clarification`

## 验证用例

已本地验证：

1. `帮我推荐 2000 以内适合学生记笔记和网课的平板`
   - 路由：`shopping_guide`
   - 返回：`p203 / p201 / p204`

2. `有没有更轻一点的`
   - 输入上一轮 memory 后路由：`shopping_guide`
   - 继承：预算 2000、品类平板、用途记笔记/网课
   - 新增偏好：轻便

3. `p201 支持手写笔吗，重量参数怎么样？`
   - 路由：`product_knowledge`
   - 返回：商品参数和商品卡片

4. `p201 和 p203 哪个好？`
   - 路由：`compare`
   - 返回：对比结论和两张商品卡片

5. `我的订单 ord_1001 到哪了？`
   - 路由：`order_query`
   - 返回：订单状态、物流状态、退货状态

## 后续可增强

1. ProductKnowledgeAgent 接入知识文档检索结果，而不只依赖商品表。
2. CompareAgent 增加更结构化的对比 JSON，方便前端渲染对比表。
3. OrderAgent 后续可替换为真实订单/物流 API。
4. 多轮记忆后续可持久化到会话数据库，而不是只由前端传回 memory。
5. 引入小规模评测集，验证意图路由准确率、多轮约束继承准确率和对比回答稳定性。
