---
name: image-generation
description: >
  图像生成技能。用户请求生图、图生图时调用。AI 只需执行 scripts/ai_image.py 并传入参数，
  无需手动编写代码。支持 Nano Banana / Nano Banana Pro / gpt-image-2。
---

# 图像生成技能

## 前置检查

```
检查 .env 是否存在且包含 AIMAXHUG_API_KEY
  ├── 不存在 → 询问用户输入，保存到 .env
  │            echo AIMAXHUG_API_KEY=sk-xxx > .env
  └── 存在   → 继续
```

> ⚠️ 不要在输出中回显完整 Token，只展示前 8 位：`sk-abc123...****`

---

## 执行步骤

### 第一步：列出模型（让用户选择）

```bash
python scripts/ai_image.py --list-models
```

输出内容包含每个模型的完整参数约束，用户选择后进入下一步。

### 第二步：执行生图

根据用户选择的模型和参数，直接执行脚本：

**文生图（无参考图）：**
```bash
python scripts/ai_image.py --model nano-banana --prompt "用户提示词" --proportion 16:9 --resolution 2k
```

**图生图（有参考图，自动上传）：**
```bash
python scripts/ai_image.py --model nano-banana-pro --prompt "编辑指令" --input-images photo1.jpg --proportion 16:9 --resolution 4k
```

**gpt-image-2（无需 --resolution）：**
```bash
python scripts/ai_image.py --model gpt-image-2 --prompt "提示词" --proportion 9:16
```

---

## 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--model` | 是 | `nano-banana` / `nano-banana-pro` / `gpt-image-2` |
| `--prompt` | 是 | 提示词 |
| `--proportion` | 否 | 比例，如 `16:9`、`1:1`、`9:16` |
| `--resolution` | 否 | 仅 nano-banana/pro 有效：`1k`、`2k`、`4k` |
| `--input-images` | 否 | 本地图片路径，传了=图生图，不传=文生图。支持多张 |

---

## 模型选择

```
用户请求生图
  ├── 指定模型         ──→ 对应模型
  ├── 高画质/商业级    ──→ nano-banana-pro
  ├── 日常快速出图     ──→ nano-banana
  ├── 照片级写实/风格  ──→ gpt-image-2
  └── 未明确偏好       ──→ nano-banana（默认）
```

### 注意事项

- **gpt-image-2** 不支持 `--resolution` 参数，分辨率按比例自动映射：
  - `9:16` / `16:9` → 4k
  - `1:1` → 2k
  - 其他 → 1k
- 图生图时，上传的图片 `{tmp_url, name, type, size}` 四个字段都会传给后端，无需手动构造

---

## 输出格式

脚本会自动展示：

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

URL 为可点击超链接，支持预览的环境直接显示图片。
