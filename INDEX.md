---
name: ai-media-skills-index
description: >
  AI 媒体生成技能索引。当用户发出任何与图像生成、图片编辑、文件上传、视频生成相关的请求时触发。
  包括：文生图、图生图、上传文件、AI 绘图、图片编辑、视频创作等。
  所有功能集中在 skills/SKILL.md，直接读取该文件执行。
---

# AI 媒体生成 — 技能索引

## 触发条件

用户请求以下内容时触发此技能：

| 类别 | 触发关键词 |
|------|-----------|
| 图像生成 | 生图、画图、AI绘图、文生图、生成图片、create image、generate image、text to image |
| 图片编辑 | 修改图片、编辑图片、换背景、风格迁移、图生图、image to image、image edit |
| 文件上传 | 上传文件、上传图片、upload file、upload image |
| 视频生成 | 生成视频、AI视频、视频创作、可灵、Kling、Vidu |

## 执行方式

```
用户请求 → 读取 skills/SKILL.md 按步骤执行
```

只有 1 个技能文件：
- `skills/SKILL.md` — 包含上传、生图、视频全部功能
- `scripts/ai_image.py` — 生图脚本（AI 直接运行）
- `scripts/upload.py` — 上传脚本（AI 直接运行）

## 前置检查

优先确认 `.env` 文件中是否配置了 `AIMAXHUG_API_KEY`，未配置则引导用户输入。
