# 真实 bge-m3 文本 RAG 接入计划

**目标：** 接入本地 `bge-m3` 文本 Embedding，用于商品文本、FAQ、营销文档、上传文档的语义索引与检索。

## 1. 定位

bge-m3 作为项目正式文本向量模型，负责商品文本、FAQ、营销文档和上传文档的语义检索。

## 2. 技术配置

后端通过环境变量控制：

```env
EMBEDDING_PROVIDER=local
TEXT_EMBEDDING_PROVIDER=bge_m3
BGE_M3_MODEL_NAME=BAAI/bge-m3
BGE_M3_DEVICE=cpu
BGE_M3_BATCH_SIZE=16
BGE_M3_USE_FP16=false
BGE_M3_ENABLE_REAL=true
```

## 3. 改造范围

1. 使用 `backend/app/embeddings/bge_m3.py`。
2. `backend/app/embeddings/bge_m3.py` 默认走本地 bge-m3，保留 fallback。
3. `TextIndex`、`DocumentIndex` 无需理解具体模型，只调用统一 embedding 接口。
4. 切换或重装 bge-m3 后必须重建 Chroma 文本索引。

## 4. 验收标准

1. 商品文本、FAQ、上传文档能写入 Chroma。
2. “学生平板 2000 以内”“退货政策是什么”等问题能正常召回相关内容。
3. Web Debug 的 trace 能看到对应商品或 FAQ 命中。
4. 向量维度统一为 bge-m3 输出维度，避免旧索引维度冲突。

## 5. 注意事项

如果本地模型不可用，系统会使用确定性 fallback embedding 跑通流程；这只能验证工程链路，不代表真实语义检索效果。

