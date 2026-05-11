---
name: ai-media-skills-index
description: >
  AI 媒体生成技能索引。当用户需要生图、画图、文生图、图生图、上传文件、AI 绘图时触发。
  所有功能在 SKILL.md，脚本在 scripts/。
---

# AI 媒体生成 — 技能索引

## 触发条件

| 类别 | 触发关键词 |
|------|-----------|
| 图像生成 | 生图、画图、AI绘图、文生图、生成图片、create image、generate image、text to image |
| 图片编辑 | 修改图片、编辑图片、换背景、风格迁移、图生图、image to image、image edit |
| 文件上传 | 上传文件、上传图片、upload file、upload image |

## 文件结构

```
SKILL.md                 ← 主技能入口（AI 读取）
scripts/
  ai_image.py            ← 生图脚本
  upload.py              ← 上传脚本
  shared/                ← 共享模块（config, client）
references/
  ai_image.md            ← 生图参考文档
  upload.md              ← 上传参考文档
```

读取 `SKILL.md` 按步骤执行。
