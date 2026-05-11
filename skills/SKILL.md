---
name: ai-media-generation
description: >
  AI 媒体生成综合技能。当用户需要生图、画图、文生图、图生图、修改图片、编辑图片、换背景、
  风格迁移、上传文件、生成视频、AI绘图等功能时调用。支持 Nano Banana / Nano Banana Pro /
  gpt-image-2 图像模型，以及可灵 Kling / Vidu 视频模型。
---

# AI 媒体生成综合技能

> 所有命令需在项目根目录 `D:\dyl-skill\zk-skill` 下执行。

## 前置检查

```
检查 .env 是否存在且包含 AIMAXHUG_API_KEY
  ├── 不存在 → 询问用户输入，保存到 .env
  │            echo AIMAXHUG_API_KEY=sk-xxx > .env
  └── 存在   → 继续
```

> 无需前置验证 Token，API 会自动校验，无效时会返回 401 错误提示。
> 不要在输出中回显完整 Token，只展示前 8 位：`sk-abc123...****`

---

## 一、文件上传

### 执行

用户提供本地文件时，AI 直接运行上传脚本：

```bash
# 上传单个文件
python scripts/upload.py photo.jpg

# 上传多个文件
python scripts/upload.py photo1.jpg photo2.png

# 输出 JSON（供脚本调用）
python scripts/upload.py photo.jpg --json
```

### 输出

```
📤 上传中: photo.jpg...
   ✅ [点击预览](https://static.aimaxhug.com/xxx.jpg)
      类型: image/jpeg  大小: 123.4 KB
```

### 传递给生图接口

上传返回的 **完整 data 对象** 传给 `original_image` 参数，4 个字段缺一不可：

```json
"original_image": [
    {
        "tmp_url": "https://static.aimaxhug.com/xxx.jpg",
        "name": "xxx.jpg",
        "type": "image/jpeg",
        "size": 123456
    }
]
```

---

## 二、图像生成

### 列出模型（用户选择）

```bash
python scripts/ai_image.py --list-models
```

输出每个模型的完整参数约束：

| 模型 | 定位 | 分辨率 |
|------|------|--------|
| **Nano Banana** | 标准生图（默认） | 手动 1k/2k/4k |
| **Nano Banana Pro** | 高质量生图 | 手动 1k/2k/4k |
| **gpt-image-2** | 照片级写实/风格 | 自动按比例映射 |

### 执行生图

```bash
# 文生图 - Nano Banana
python scripts/ai_image.py --model nano-banana --prompt "提示词" --proportion 16:9 --resolution 2k

# 图生图 - Nano Banana Pro（自动上传）
python scripts/ai_image.py --model nano-banana-pro --prompt "编辑指令" --input-images photo.jpg --proportion 16:9 --resolution 4k

# 文生图 - gpt-image-2（不需要 --resolution）
python scripts/ai_image.py --model gpt-image-2 --prompt "提示词" --proportion 9:16
```

### 模型选择

```
用户请求生图
  ├── 指定模型         ──→ 对应模型
  ├── 高画质/商业级    ──→ nano-banana-pro
  ├── 日常快速出图     ──→ nano-banana
  ├── 照片级写实/风格  ──→ gpt-image-2
  └── 未明确偏好       ──→ nano-banana（默认）
```

### 注意事项

- **gpt-image-2** 不支持 `--resolution`，分辨率自动映射：
  - `9:16` / `16:9` → 4k
  - `1:1` → 2k
  - 其他 → 1k
- 图生图时，上传的 `{tmp_url, name, type, size}` 四个字段都会自动传给后端

### 输出

```
✅ 生成成功！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📍 [点击查看生成的图片](URL)
  🖼️  ![生成结果](URL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📐 比例: 16:9
  🔍 分辨率: 4k
  🤖 模型: Nano Banana (gemini-3-pro-image-preview)
```

---

## 三、视频生成

> 待补充详细 API 文档

| 模型 | 定位 |
|------|------|
| **可灵（Kling）** | 文生视频、图生视频 |
| **Vidu** | 文生视频、图生视频 |
