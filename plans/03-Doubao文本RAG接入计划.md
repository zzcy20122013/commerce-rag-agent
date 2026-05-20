# Doubao 文本 RAG 接入计划

**目标：** 将文本 Embedding 技术选型从本地 bge-m3 调整为 `Doubao-embedding-vision`，用于商品文本、FAQ、营销文档、上传文档的语义索引与检索。

## 1. 定位

Doubao-embedding-vision 作为项目正式文本向量模型。原 bge-m3 本地模型只作为历史实现和可选 fallback，不再作为主路线。

## 2. 技术配置

后端通过环境变量控制：

```env
EMBEDDING_PROVIDER=doubao
TEXT_EMBEDDING_PROVIDER=doubao
DOUBAO_EMBEDDING_API_KEY=你的火山方舟或向量服务 Key
DOUBAO_EMBEDDING_BASE_URL=https://api-vikingdb.vikingdb.cn-beijing.volces.com/api/vikingdb/embedding
DOUBAO_EMBEDDING_MODEL=doubao-embedding-vision-250615
DOUBAO_EMBEDDING_DIMENSION=2048
DOUBAO_EMBEDDING_ENABLE_REAL=true
```

## 3. 改造范围

1. 新增 `backend/app/embeddings/doubao_embedding_vision.py`。
2. `backend/app/embeddings/bge_m3.py` 改为 provider 门面，默认走 Doubao。
3. `TextIndex`、`DocumentIndex` 无需理解具体模型，只调用统一 embedding 接口。
4. 切换真实 Doubao 后必须重建 Chroma 文本索引。

## 4. 验收标准

1. 商品文本、FAQ、上传文档能写入 Chroma。
2. “学生平板 2000 以内”“退货政策是什么”等问题能正常召回相关内容。
3. Web Debug 的 trace 能看到对应商品或 FAQ 命中。
4. 向量维度统一为 Doubao 配置维度，避免旧索引维度冲突。

## 5. 注意事项

如果暂时没有 Doubao Key，系统会使用确定性 fallback embedding 跑通流程；这只能验证工程链路，不代表真实语义检索效果。
