# Doubao 多模态图搜计划

**目标：** 将图片 Embedding 技术选型从本地 Chinese-CLIP 调整为 `Doubao-embedding-vision`，实现文本和图片统一向量空间下的商品图搜。

## 1. 定位

Doubao-embedding-vision 作为项目正式图片向量模型。Chinese-CLIP 本地模型保留为历史实现和离线 fallback，不再作为主路线。

## 2. 技术配置

后端通过环境变量控制：

```env
EMBEDDING_PROVIDER=doubao
IMAGE_EMBEDDING_PROVIDER=doubao
DOUBAO_EMBEDDING_API_KEY=你的火山方舟或向量服务 Key
DOUBAO_EMBEDDING_BASE_URL=https://api-vikingdb.vikingdb.cn-beijing.volces.com/api/vikingdb/embedding
DOUBAO_EMBEDDING_MODEL=doubao-embedding-vision-250615
DOUBAO_EMBEDDING_DIMENSION=2048
DOUBAO_EMBEDDING_ENABLE_REAL=true
DOUBAO_EMBEDDING_IMAGE_MODE=url
```

## 3. 图片输入约束

官方多模态向量接口更适合接收公网图片 URL 或 TOS 地址。当前项目商品图片和用户上传图多为本地文件，所以分两步落地：

1. 当前阶段：保留本地 fallback，先完成接口切换、索引维度统一和图搜链路验证。
2. 后续阶段：接入 TOS/对象存储或公网静态图片地址，让商品图片和用户上传图片真正走 Doubao 图像向量。

## 4. 改造范围

1. 新增统一 Doubao 多模态 embedding adapter。
2. `ChineseClipEmbedding` 改为 provider 门面，默认走 Doubao。
3. `ImageIndex`、`MultimodalSearchAgent` 继续使用统一 `embed_image()` 接口。
4. 切换真实 Doubao 后必须重建 `product_images` Chroma collection。

## 5. 验收标准

1. 商品图片能写入 `product_images` collection。
2. 用户上传图片后能触发图搜链路。
3. “找类似这双鞋，但价格 300 以内，适合通勤”能返回价格符合的鞋款商品卡片。
4. Web Debug 能显示上传图片、图搜回答、商品卡片和 trace。

## 6. 注意事项

如果没有公网/TOS 图片地址，真实 Doubao 图像向量可能无法直接处理本地文件。这个不是代码问题，而是云端多模态接口的输入形态限制；后续做真实平台简化版数据层时应补对象存储或可访问图片 URL。
