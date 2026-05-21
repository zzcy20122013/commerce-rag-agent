# 真实 Chinese-CLIP 多模态图搜计划

**目标：** 接入本地 `Chinese-CLIP` 图片 Embedding，实现用户上传图片查找相似商品。

## 1. 定位

Chinese-CLIP 作为项目正式图片向量模型，用于商品图片和用户上传图片的视觉相似检索。

## 2. 技术配置

后端通过环境变量控制：

```env
EMBEDDING_PROVIDER=local
IMAGE_EMBEDDING_PROVIDER=chinese_clip
CHINESE_CLIP_MODEL_NAME=OFA-Sys/chinese-clip-vit-base-patch16
CHINESE_CLIP_DEVICE=cpu
CHINESE_CLIP_ENABLE_REAL=true
CHINESE_CLIP_LOCAL_FILES_ONLY=true
```

## 3. 图片输入约束

Chinese-CLIP 运行在本地，可以直接读取商品图片和用户上传图片：

1. 当前阶段：商品图片、用户上传图均走本地文件路径。
2. 后续阶段：如需要部署到云端，再补对象存储或静态资源服务。

## 4. 改造范围

1. 使用 `backend/app/embeddings/chinese_clip.py`。
2. `ChineseClipEmbedding` 默认走本地 Chinese-CLIP，保留 fallback。
3. `ImageIndex`、`MultimodalSearchAgent` 继续使用统一 `embed_image()` 接口。
4. 切换或重装 Chinese-CLIP 后必须重建 `product_images` Chroma collection。

## 5. 验收标准

1. 商品图片能写入 `product_images` collection。
2. 用户上传图片后能触发图搜链路。
3. “找类似这双鞋，但价格 300 以内，适合通勤”能返回价格符合的鞋款商品卡片。
4. Web Debug 能显示上传图片、图搜回答、商品卡片和 trace。

## 6. 注意事项

Chinese-CLIP 本地推理对机器性能有要求。CPU 可以跑通链路，但首次加载和索引重建会比较慢。

