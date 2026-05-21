# 商品图片资产放置说明

这个目录用于存放 04A 阶段的商品图片资产，为后续真实 Chinese-CLIP 图搜做准备。

## 目录结构

```text
images/
  tablets/      平板图片
  headphones/   耳机图片
  shoes/        鞋子图片
  backpacks/    背包图片
```

## 支持格式

推荐使用：

```text
.jpg
.jpeg
.png
.webp
```

## 命名建议

```text
tablet_001.jpg
tablet_002.jpg
headphone_001.jpg
shoes_001.jpg
backpack_001.jpg
```

## CSV 绑定方式

商品 CSV 的 `image_file` 字段使用相对路径，例如：

```csv
image_file
images/tablets/tablet_001.jpg
images/headphones/headphone_001.jpg
images/shoes/shoes_001.jpg
images/backpacks/backpack_001.jpg
```

## 数量建议

第一版每类放 5-10 张即可：

- 平板：5-10 张
- 耳机：5-10 张
- 鞋：5-10 张
- 背包：5-10 张

后续可以扩到每类 20-50 张。

## 注意

不要直接大规模爬取电商平台图片。项目路演阶段建议使用自有图片、授权图片、公开可用图片，或者后续生成仿真商品图。
