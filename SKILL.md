---
name: ai-media-generation
description: "AI 媒体生成技能。生图、画图、文生图、图生图、编辑图片、换背景、上传文件。所有网络请求均指向 base-api.aimaxhug.com。"
homepage: https://aimaxhug.com
author:
  name: aimaxhug
license: Apache-2.0
metadata:
  tags: ai, image, text2image, image2image, image-edit, upload, video, text2video, kling, vidu, aimaxhug
  requires:
    bins: [python3]
    python: ">=3.8"
    pip:
      - requests>=2.28.0
      - python-dotenv>=1.0.0
  primaryEnv: AIMAXHUG_API_KEY
  envVars:
    - name: AIMAXHUG_API_KEY
      required: true
      description: Aimaxhug API Key，从 .env 文件或环境变量读取
  endpoints:
    - https://base-api.aimaxhug.com
---

# AI 媒体生成技能

> 基于 Aimaxhug API 的 AI 图像生成与文件上传能力。
> 所有脚本在 `scripts/` 目录下，AI 直接运行，无需用户写代码。

---

## 路径定位

所有命令需在**项目根目录**下执行。AI 通过 SKILL.md 自身路径推导项目根目录：

```
SKILL.md 路径: .../skills/SKILL.md  或  .../SKILL.md
项目根目录:    .../  （SKILL.md 所在目录）

AI 执行任何命令前，先 cd 到项目根目录。
```

---

## 与用户交流风格

> 用户大多为非技术用户，在聊天工具中使用。以下为风格指引，不是硬性规则。

1. **回复简短** — 直接给出结果或下一步，一句话能说清不用三句。
2. **说人话** — 避免 API 术语、终端命令、JSON 等，除非用户主动问。
3. **不需要用户操作终端** — AI 自己运行脚本，用户只需选择模型和说需求。
4. **不发浏览器弹窗** — 所有链接直接发给用户点击。
5. **生图前必须先展示模型表格** — 用 `list-models` 列出所有模型让用户选择，不能自己决定。
6. **无 API Key 时引导** — 提示用户创建 `.env` 文件，引导到 https://aimaxhug.com 注册。
7. **结果导向** — 生成完成后直接展示图片链接，中间过程不啰嗦。
8. **不提额外注册** — aimaxhug.com 注册页面即含登录+注册。
9. **不要问"要不要"** — 明显需要的就去做，比如用户说"生图"直接走流程。

---

## 模块

| 模块 | 脚本 | 参考文档 | 说明 |
|------|------|---------|------|
| AI 图像生成 | `scripts/ai_image.py` | [ai_image.md](references/ai_image.md) | 文生图、图生图，支持 4 个模型 |
| AI 视频生成 | `scripts/ai_video.py` | [ai_video.md](references/ai_video.md) | 文生视频、图生视频，支持可灵 / Vidu |
| 文件上传 | `scripts/upload.py` | [upload.md](references/upload.md) | 上传本地文件，返回临时 URL |

> **读参考文档了解具体参数和示例。**

---

## 工作流程

### 一、图像生成

**必须按以下顺序执行：**

**第一步 — 展示模型表格（必须！）**

```bash
cd <项目根目录>
python scripts/ai_image.py list-models
```

展示后等待用户选择模型、比例、分辨率。

**第二步 — 执行生图**

```bash
cd <项目根目录>

# 文生图
python scripts/ai_image.py run --model nano-banana --prompt "提示词" --proportion 16:9 --resolution 2k

# 图生图
python scripts/ai_image.py run --model nano-banana-pro --prompt "编辑指令" --input-images photo.jpg --proportion 16:9 --resolution 4k

# gpt-image-2 不需要 --resolution
python scripts/ai_image.py run --model gpt-image-2 --prompt "提示词" --proportion 9:16

# ⭐ 多图生成（并行执行！）— 用 --count 指定数量，--styles 可选指定风格
python scripts/ai_image.py run --model gpt-image-2 --prompt "赛博朋克城市" --count 5 --proportion 16:9
python scripts/ai_image.py run --model nano-banana --prompt "一只猫" --count 3 --proportion 1:1 --resolution 4k
python scripts/ai_image.py run --model nano-banana --prompt "一只猫" --count 3 --styles 写实 卡通 油画 --proportion 1:1 --resolution 4k
```

> ⭐ **多图生成规则**：
> - `--count N` = 一次生成 N 张图，**脚本自动并行执行**，不需要逐张跑
> - `--styles 风格1 风格2 ...` = 可选，指定每张图的风格
> - 不指定 `--styles` → 自动分配不同风格（写实、卡通、油画、赛博朋克等）
> - **AI 不允许一张一张跑！用户说生成多张图时，必须用 `--count` 一次完成**
> - **最多一次性生成 14 张**（`--count` 最大 14）
> - ⚠️ **禁止同时执行多条命令**，每次只能执行一条命令，等上一条完成后才能执行下一条

详细见 [ai_image.md](references/ai_image.md)。

### 二、视频生成

**必须按以下顺序执行：**

**第一步 — 展示模型表格（必须！）**

```bash
cd <项目根目录>
python scripts/ai_video.py list-models
```

展示后等待用户选择模型、比例、时长、分辨率。

**第二步 — 执行生成**

```bash
cd <项目根目录>

# 文生视频
python scripts/ai_video.py run --model kling --prompt "提示词" --proportion 16:9 --duration 5 --resolution 720p

# 15秒时长
python scripts/ai_video.py run --model vidu --prompt "提示词" --proportion 9:16 --duration 15 --resolution 720p

# 图生视频
python scripts/ai_video.py run --model vidu --prompt "提示词" --input-images photo.jpg --proportion 9:16

# ⭐ 视频生视频（消耗巨大，必须警告用户确认）
python scripts/ai_video.py run --model kling --prompt "提示词" --input-images video.mp4 --proportion 16:9

# ⭐ 多视频并行生成 — 用 --count 指定数量
python scripts/ai_video.py run --model kling --prompt "赛博朋克城市" --count 3 --proportion 16:9 --resolution 720p
```

> **三种模式说明**：
> - **文生视频** — 仅传 `--prompt`，不传 `--input-images`
> - **图生视频** — 传 `--prompt` + `--input-images`（图片文件）
> - **视频生视频** — 传 `--prompt` + `--input-images`（视频文件，⚠️ **消耗巨大，必须提前告知用户并确认**）
>
> ⭐ **多视频生成规则**：
> - `--count N` = 一次生成 N 个视频，**脚本自动并行执行**
> - **AI 不允许一个一个跑！用户说生成多个视频时，必须用 `--count` 一次完成**
> - **最多一次性生成 5 个**（`--count` 最大 5）
> - ⚠️ **禁止同时执行多条命令**，每次只能执行一条命令，等上一条完成后才能执行下一条

详细见 [ai_video.md](references/ai_video.md)。

### 模型选择指南

| 需求 | 推荐模型 |
|------|---------|
| 默认首选 | **Nano Banana** — 速度快、性价比高，支持10种比例 |
| 更高画质 | **Nano Banana Pro** — 支持10种比例 |
| 细节丰富/色彩鲜艳 | **Seedream 5.0** — 手动选 1k/2k/4k，支持10种比例 |
| 照片级写实/艺术风格 | **gpt-image-2** — 仅支持 `1:1` `9:16` `16:9`，分辨率自动固定 `4k` |

> ⚠️ 每个模型支持的**比例不同**，展示模型表格时会列出各模型专属的比例列表。
> ⚠️ **gpt-image-2** 不支持 `--resolution`，任何比例下分辨率固定为 `4k`。

---

## 执行前检查清单

1. **确认参数完整** — 模型、提示词、比例、分辨率（如适用）是否齐全
2. **比例选择** — 如果用户没说，问一下要什么比例（16:9、1:1、9:16 等）
3. **首次生成确认** — 第一次执行前告知用户方案并确认

---

## 结果展示格式

**成功模板：**

```text
✅ 生成成功！

📍 URL
🖼️  ![](URL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📐 比例: 16:9
  🔍 分辨率: 4k
  🤖 模型: Nano Banana

不满意的话告诉我，帮你调整重试。
```

**格式要求：**
1. 图片链接放在最前面（URL 单独一行 + markdown 图片语法各一行，让平台自动展示）
2. 关键元数据：比例、分辨率、模型
3. 提供调整选项

---

## 能力边界

| 能力 | 状态 | 命令 |
|------|------|------|
| 文生图 | Available | `scripts/ai_image.py run` (不带 `--input-images`) |
| 图生图 | Available | `scripts/ai_image.py run` (带 `--input-images`) |
| 多图并行生成 | Available | `scripts/ai_image.py run --count N` (自动不同风格) |
| 自定义风格生成 | Available | `scripts/ai_image.py run --count N --styles 写实 卡通 ...` |
| 列出模型 | Available | `scripts/ai_image.py list-models` |
| 文件上传 | Available | `scripts/upload.py run` |
| 文生视频 | Available | `scripts/ai_video.py run` (不带 `--input-images`) |
| 图生视频 | Available | `scripts/ai_video.py run` (带 `--input-images` 图片) |
| 视频生视频 | Available（消耗巨大） | `scripts/ai_video.py run` (带 `--input-images` 视频) |
| 多视频并行生成 | Available | `scripts/ai_video.py run --count N` |
| 列出视频模型 | Available | `scripts/ai_video.py list-models` |
