# Demo Showcase 路演界面计划 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建面向项目路演的正式展示界面，突出智能导购体验，不展示 Web Debug 的工程调试信息。

**Architecture:** Demo Showcase 可以作为独立 React/Vite 前端，也可以在 `web-debug` 中新增独立路由。它复用 API client、SSE parser、商品卡片数据结构、图片上传和反馈接口，但 UI 面向正式产品体验。

**Tech Stack:** React, Vite, TypeScript, SSE, FastAPI API client, CSS.

---

## 1. 范围

包含：

- 正式聊天界面
- 图片上传入口
- SSE 流式回答
- 商品卡片展示
- 推荐理由展示
- 点赞/点踩反馈
- 典型演示场景快捷入口

不包含：

- trace 面板
- raw SSE 面板
- retrieved ids
- 开发调试参数

## 2. 文件结构

推荐独立目录：

```text
commerce-rag-agent/showcase/
  package.json
  index.html
  src/
    main.tsx
    api/
      chatStream.ts
      upload.ts
      feedback.ts
      types.ts
    components/
      ChatView.tsx
      ProductCard.tsx
      ScenarioRail.tsx
      ImageUploader.tsx
    styles.css
```

如果选择复用 `web-debug`：

```text
commerce-rag-agent/web-debug/src/
  pages/
    ShowcasePage.tsx
  components/
    shared/
      ProductCard.tsx
      ChatBubble.tsx
```

## 3. 任务拆分

### Task 1：确定路演界面入口

- [ ] 决定独立 `showcase/` 目录还是复用 `web-debug`
- [ ] 保证 Web Debug 继续保留，不删除调试台
- [ ] 复用已有 API client 和 SSE parser

### Task 2：聊天主界面

- [ ] 实现用户消息、Agent 消息、流式状态
- [ ] 发送后清空输入框
- [ ] SSE 过程中展示生成中状态
- [ ] 错误时展示可读错误提示

### Task 3：图片上传体验

- [ ] 支持上传图片并预览
- [ ] 上传成功后带 `upload_id` 发起聊天
- [ ] 允许用户删除已选图片
- [ ] 图片上传失败时展示错误提示

### Task 4：商品卡片

- [ ] 渲染标题、价格、评分、销量、库存、推荐理由
- [ ] 图片加载失败时显示占位图
- [ ] 支持横向滚动或响应式网格
- [ ] 点击卡片可展示商品详情区域

### Task 5：典型场景入口

- [ ] 增加 4 个路演快捷场景：学生平板、通勤鞋、送礼耳机、退货政策
- [ ] 点击场景自动填入输入框或直接发送
- [ ] 场景文案必须贴近真实用户问题

### Task 6：构建验证

- [ ] 运行 `npm.cmd install`
- [ ] 运行 `npm.cmd run build`
- [ ] 启动本地 dev server
- [ ] 验证文本导购、图片导购、FAQ、反馈都能走通

## 4. 完成标准

- 页面只展示正式产品体验。
- 不出现 trace、raw SSE、retrieved ids 等调试信息。
- 能完成一次文本导购演示。
- 能完成一次图片上传找类似商品演示。
- 商品卡片与推荐理由能正常展示。

