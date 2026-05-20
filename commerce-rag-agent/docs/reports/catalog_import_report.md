# Catalog Import Report

生成时间：2026-05-20

## 导入输入

- CSV 文件：`backend/app/data/catalog/sample_products.csv`
- 图片策略：样例商品未绑定真实图片文件，系统自动生成合法 PNG 占位图。
- 导入命令：`python -m app.scripts.import_catalog app/data/catalog/sample_products.csv`

## 导入结果

```text
job_id: imp_27b9b16d36ae
imported_count: 4
failed_count: 0
errors: []
```

## 索引重建结果

重建命令：`python -m app.scripts.rebuild_indexes`

```text
job_id: idx_b5275703ba5e
status: completed
product_text_count: 24
knowledge_docs_count: 0
product_images_count: 24
```

说明：

- `product_text_count=24` 表示当前 SQLite 商品表中已有 24 条商品进入文本索引流程。
- `product_images_count=24` 表示当前商品图片表中已有 24 条图片记录进入图片索引流程。
- `knowledge_docs_count=0` 是因为本次只导入商品 CSV，没有额外导入 FAQ、营销文档或商品详情文档。

## 验证结果

```text
pytest app/tests -q
4 passed
```

## 真实 bge-m3 文本索引重建

执行时间：2026-05-20

环境变量：

```text
HF_HOME=C:\Users\zzcy2\Desktop\agent\models\huggingface
BGE_M3_ENABLE_REAL=true
BGE_M3_MODEL_NAME=BAAI/bge-m3
BGE_M3_DEVICE=cpu
BGE_M3_USE_FP16=false
```

结果：

```text
product_text_count: 24
knowledge_docs_count: 0
query: 学生平板 记笔记 网课
top_results: p101 荣耀平板 X9 学习版, p001 荣耀平板 X9 学习版, p002 小米平板 6 青春套装
```

说明：

- `product_text` collection 已使用真实 bge-m3 的 1024 维向量重建。
- `knowledge_docs_count=0` 是因为当前没有额外导入 FAQ、营销文档或商品详情文档。
- 后续导入知识文档后，需要再次执行索引重建。

## 04A 商品库扩充与图片资产准备

执行时间：2026-05-20

新增资产：

```text
tablets: 4 张
headphones: 4 张
shoes: 4 张
backpacks: 4 张
total: 16 张
```

新增文件：

- `backend/app/data/catalog/expanded_products_image_batch.csv`
- `backend/app/data/catalog/asset_manifest_generated.csv`
- `backend/app/data/catalog/images/tablets/tablet_001.png` 到 `tablet_004.png`
- `backend/app/data/catalog/images/headphones/headphone_001.png` 到 `headphone_004.png`
- `backend/app/data/catalog/images/shoes/shoes_001.png` 到 `shoes_004.png`
- `backend/app/data/catalog/images/backpacks/backpack_001.png` 到 `backpack_004.png`

导入结果：

```text
job_id: imp_a2e55d04eff7
imported_count: 16
failed_count: 0
```

当前样品库：

```text
products: 40
images: 40
tags: 192
category_distribution:
  平板: 10
  耳机: 10
  鞋: 10
  背包: 10
```

索引结果：

```text
product_text_count: 40
product_images_count: 40
```

说明：

- 商品文本索引已使用真实 bge-m3 重建。
- 商品图片索引仍使用当前 Chinese-CLIP 占位 embedding，等待 Plan 04 替换为真实 Chinese-CLIP。
