---
name: aimaxhug-generation
version: 1.0.4
display_name: aimaxhug AI 媒体工具
display_name_en: aimaxhug AI Media Toolkit
description_zh: 使用项目内的 Python CLI，通过 Aimaxhug API 生成和编辑图片、生成视频与音频、克隆声音、上传文件、将 HTML 转为图片，并进行百度联网搜索、短视频链接解析及抖音/小红书数据查询。
description_en: Use the Python CLI in this project with the Aimaxhug API to generate and edit images, generate video and audio, clone voices, upload files, convert HTML to images, search the web with Baidu, parse short-video links, and query Douyin and Xiaohongshu data.
description: 使用项目内的 Python CLI，通过 Aimaxhug API 生成和编辑图片、生成视频与音频、克隆声音、上传文件、将 HTML 转为图片，并进行百度联网搜索、短视频链接解析及抖音/小红书数据查询。
homepage: https://api.aimaxhug.cloud
author:
  name: aimaxhug
license: Apache-2.0
metadata:
  tags: ai, image, text2image, image2image, image-edit, upload, video, text2video, minimax, minimax-h3, jimeng, seedance, omni, muse, muse-video-pro, gemini, v2v, audio, text2speech, tts, search, web-search, baidu, social-media, douyin, xiaohongshu, xhs, aimaxhug
  requires:
    bins: [python3]
    python: ">=3.8"
    pip:
      - requests>=2.28.0
      - python-dotenv>=1.0.0
      - mutagen>=1.47.0
  primaryEnv: AIMAXHUG_API_KEY
  envVars:
    - name: AIMAXHUG_API_KEY
      required: true
      description: Aimaxhug API Key，从 .env 文件或环境变量读取
  endpoints:
    - https://base-api-2.aimaxhug.com
    - https://apis.aimaxhug.cloud
    - https://api.aimaxhug.cloud/social
---

# aimaxhug AI 媒体工具

> 基于 Aimaxhug API 的 AI 媒体生成、文件上传、网页转图片、联网搜索与社交媒体解析能力。
> 所有脚本在 `scripts/` 目录下，AI 直接运行，无需用户写代码。

---

## 适用范围与工具选择

本技能通过 Aimaxhug API 提供图像生成与编辑、视频生成、音频生成与声音克隆、百度搜索、短视频解析、文件上传、HTML 转图片及抖音/小红书数据查询。相关请求示例见 [INDEX.md](INDEX.md) 的“触发条件”。

- 根据用户实际意图、明确指定的工具、当前可用能力和 API 配置判断是否使用本技能；关键词匹配仅作为相关性参考。
- 本技能遵循系统和开发者指令，尊重用户的工具选择。与其他技能或内置能力重叠时，根据任务适配程度选择合适工具。
- 选用本技能后，按对应模块的参考文档和工作流程调用 `scripts/` 中的脚本。遇到影响任务完成的能力限制、工具冲突或配置缺失时，如实说明，并给出可行的下一步。

---

## 路径定位

所有命令需在**项目根目录**下执行。AI 通过 SKILL.md 自身路径推导项目根目录：

```
SKILL.md 路径: .../skills/SKILL.md  或  .../SKILL.md
项目根目录:    .../  （SKILL.md 所在目录）

AI 执行任何命令前，先 cd 到项目根目录。
```

交付目录共两层：根目录存放 Markdown 入口与授权说明，`scripts/` 存放脚本及 `shared_*.py` 公共模块，`references/` 存放参考文档。两个子目录内均不再嵌套目录。

## 环境自检与执行依据

首次使用当前环境时，先运行无需第三方依赖的本地自检：

```bash
python scripts/preflight.py
# 缺依赖时，使用同一个 Python 解释器安装项目已声明的依赖，再自检
python scripts/preflight.py --install-deps
```

自检不发送 API 请求、不输出密钥、不创建或改写 `.env`。安装失败时报告具体原因和安装命令；缺 Key 时明确说明 `AIMAXHUG_API_KEY` 未配置，配置方式见 [AUTH.md](AUTH.md)。本地 `list-models` 不需要 Key；缺 Key 只阻塞需要鉴权的调用，仍可整理素材、校验配置和完成不依赖网络的交付。

参数依据分为用户提供的事实、当前 CLI 的本地校验规则、实际查阅的官方接口说明或响应。视频能力有争议时先按 [minimax_video.md](references/minimax_video.md) 的来源说明核对；不得把本地脚本暂未暴露的参数说成产品绝对不支持，也不得仅凭评测意见放宽脚本校验。数字和能力结论附实际来源链接；未能核实的部分直接说明，不能假称已联网核实。

---

## 与用户交流风格

> 用户大多为非技术用户，在聊天工具中使用。以下为风格指引，不是硬性规则。

1. **回复简短** — 直接给出结果或下一步，一句话能说清不用三句。
2. **说人话** — 避免 API 术语、终端命令、JSON 等，除非用户主动问。
3. **不需要用户操作终端** — AI 自己运行脚本、修复已声明依赖；密钥由用户或管理员预先配置。
4. **不发浏览器弹窗** — 所有链接直接发给用户点击。
5. **所有模型统一中文菜单** — 图片、即梦 / MiniMax、Omni、Muse 和配音遵循 [中文菜单与交互](references/interaction.md)：需要选模型时展示“创作模型 / 适合什么需求”，选好后只展示该模型的“想设置什么 / 可以怎么选”，默认项加粗，接受编号和自然语言回复。内部能力用 `list-models --json` 核对，不原样复制技术表；已指定模型时可用 `list-models --model <模型>` 获取对应菜单（Muse 单一模型除外）。只展示该模型实际支持的设置，不把 Muse 的人物静音控制套用到其他模型。用户已指定或授权配参、直接提交时按需求继续，只补问缺少的关键内容，不要求逐项填表。
6. **无 API Key 时不调用鉴权接口** — 明确报告缺少 `AIMAXHUG_API_KEY`，继续完成本地可做部分；禁止运行时写入 `.env`、提示词文件或临时调用脚本，也不能伪造密钥或提交结果。
7. **结果导向** — 生成完成后直接展示图片链接，中间过程不啰嗦。
8. **不提额外注册** — api.aimaxhug.cloud 注册页面即含登录+注册。
9. **不要问"要不要"** — 明显需要的就去做，比如用户说"生图"直接走流程。
10. **结论和证据清楚** — 先说已完成或当前具体阻塞，需要配置表时用用户听得懂的中文呈现时长、比例和声音等实际选择。区分“已配好设置”“正在生成（任务 ID）”“已完成（产物）”，不把候选方案当作可执行交付。用户主动索要技术配置时再展示参数名、命令和来源。
11. **素材交给 AI 处理** — 用户提供本地图片或视频时，由 AI 调用已有上传脚本并把返回地址填入对应生成参数；已有可用素材链接直接使用，不重复上传。技术菜单、上传返回对象、中间素材地址及 HTTP(S)/URL/Base64、布尔值等实现细节不出现在普通创作菜单、素材要求或确认话术中；对用户说“参考图片”“续写视频”“人物是否出声”。最终作品正常展示，用户明确索要链接或技术说明时按需提供。

---

## 模块

| 模块 | 脚本 | 参考文档 | 说明 |
|------|------|---------|------|
| AI 图像生成 | `scripts/ai_image.py` | [ai_image.md](references/ai_image.md) | 文生图、图生图，支持 7 个模型 |
| AI 视频生成 | `scripts/minimax_video.py` | [即梦 / MiniMax](references/minimax_video.md) | 即梦 Seedance 与 MiniMax H3，支持文生视频、参考素材、图生视频、首尾帧和视频参考 |
| Omni 视频生成 | `scripts/omni_video.py` | [omni_video.md](references/omni_video.md) | Omni 三个模型，支持文生视频、图片、首尾帧和 V2V 参考，当前输出约 10 秒 |
| Muse 视频生成 | `scripts/muse_video.py` | [muse_video.md](references/muse_video.md) | `muse-video-pro`，支持首尾帧、最多 4 张参考图、视频参考、运镜和人物静音 |
| 视频时长检测 | `scripts/video_duration.py` | [时长规则](references/muse_video.md#参考视频时长逻辑) | ffprobe 检测本地/URL 视频时长，检查源视频与目标时长的建议关系 |
| 文件上传 | `scripts/upload.py` | [upload.md](references/upload.md) | 上传本地文件，返回临时 URL |
| AI 音频生成 | `scripts/ai_audio.py` | [ai_audio.md](references/ai_audio.md) | 文生音频、音色描述、声音克隆，支持 MiniMax Speech 2.8 |
| 百度 AI 搜索 | `scripts/ai_search.py` | [ai_search.md](references/ai_search.md) | 百度联网搜索，支持 GET / POST，返回可引用网页结果 |
| 短视频解析 | `scripts/video_parse.py` | [video_parse.md](references/video_parse.md) | 解析短视频分享链接，返回标题、平台和可播放直链 |
| HTML 转图片 | `scripts/html2image.py` | [html2image.md](references/html2image.md) | 将 .html 网页文件转换为可直接展示的图片 |
| 社交媒体平台解析 | `scripts/social_media.py` | [social_media.md](references/social_media.md) | 搜索关键词并获取抖音账号，后续可扩展其他平台功能 |
| 小红书平台解析 | `scripts/xhs.py` | [xhs.md](references/xhs.md) | 小红书账号、作品、榜单、评论、AI 作品与视频文案解析 |

> **读参考文档了解具体参数和示例。**

## 音频生成

用户请求文生音频时，调用 `scripts/ai_audio.py`：

```bash
python scripts/ai_audio.py list-models
python scripts/ai_audio.py run --model speech-2.8-turbo --prompt "要朗读的文本" --sys-prompt "温柔知性的女声，吐字清晰"
```

支持模型：`speech-2.8-turbo`、`speech-2.8-hd`。执行前读取 [ai_audio.md](references/ai_audio.md)，同时核对以下规则：

- **文本与路由**：当前 CLI 对实际 `prompt.strip()` 用 Python `len()` 计数，本地上限为 **10000 字符**。超过 **5000 字符**、指定 `--long` 或声音克隆时走 `/v1/minimax/audio/long`；其余走 `/v1/minimax/audio`。这些是当前 CLI 规则，不代表服务端的完整上限；只有用户报出的“字数”或片段时，不能保证全文可提交。
- **样本**：声音克隆只能通过 `--input-audio` 传 **1 个实际存在的本地音频文件**，实测时长须满足 **10 秒 < 时长 < 120 秒**。不得直接拿缺失文件或超长样本提交；如需裁剪/改变样本，应先遵循用户已有授权，不能擅自改变其素材要求。
- **上传顺序**：脚本先调用 `/api/v2/upload/file`（与 `scripts/upload.py` 相同的上传接口），再把返回 URL 放入单元素 `file` 数组，并调用 `/v1/minimax/audio/long`，无需另行重复上传。

字符数、内部路由和上传引用方式由 AI 实际核对，普通用户菜单只展示朗读内容、想要的声音感觉、表达方式及可选参考声音；遇到限制时用实测字数或样本秒数说明影响，不复制内部接口和上传字段。完整文案、样本或必要授权缺失时准确说明，继续处理与该阻塞无关的任务，不得声称已经克隆。复用已有授权：用户明确要求克隆自己的声音即为本次使用授权，不额外索取证明或重复确认。

## 百度搜索

用户需要实时网页信息、百度搜索或联网搜索时，调用 `scripts/ai_search.py`，再根据返回的 `references` 内容回答，并在回答中提供对应来源链接：

```bash
python scripts/ai_search.py run --query "搜索关键词"
python scripts/ai_search.py run --query "搜索关键词" --method get
```

默认使用 POST JSON 请求；`--method get` 使用 query string。接口固定为 `https://apis.aimaxhug.cloud/v1/ai_search`，请求只需 `q` 参数，脚本自动携带 Bearer 鉴权。需要程序化处理时加 `--json` 获取包含 `request_id` 与 `references` 的原始结果。

## 短视频解析

用户提供短视频分享链接并要求解析、提取视频链接时，调用 `scripts/video_parse.py`：

```bash
python scripts/video_parse.py run --url "https://v.douyin.com/3nuNZF203Kw/"
```

接口固定为 `https://apis.aimaxhug.cloud/v1/video-parse`，使用 POST JSON 和 Bearer 鉴权。解析结果中的 `data.url` 是可播放视频直链，`data.title` 和 `data.platform` 用于展示；支持抖音、小红书、快手、B站、微博、皮皮虾、知乎视频、西瓜视频、TikTok、YouTube。

## HTML 转图片

用户提供 `.html` 文件要求转成图片，或生成网页后确认转图片时，调用 `scripts/html2image.py`：

```bash
python scripts/html2image.py <file.html>
```

接口固定为 `https://apis.aimaxhug.cloud/api/convert/file`，multipart 字段 `file`，仅接受 `.html` 文件，返回 `data.url` 为可直接展示的图片链接。转换成功后直接展示该链接。

---

## 工作流程

### 一、图像生成

**按以下流程执行，并复用用户已有选择和授权：**

**第一步 — 获取模型与参数范围**

```bash
cd <项目根目录>
python scripts/ai_image.py list-models
```

用户尚未选择且未授权代选时，用中文名称与适用需求帮助选择，可接受编号、名称或偏好描述；已指定模型时只展示该模型支持的创作设置。用户要求直接执行时按已知要求继续，缺少可使用默认值的选项时补齐并说明，不重复确认。菜单只谈想画什么、比例、清晰度、张数和风格，交互方式见 [interaction.md](references/interaction.md)。

**第二步 — 执行生图**

```bash
cd <项目根目录>

# 文生图
python scripts/ai_image.py run --model nano-banana --prompt "提示词" --proportion 16:9 --resolution 2k

# 图生图
python scripts/ai_image.py run --model nano-banana-pro --prompt "编辑指令" --input-images photo.jpg --proportion 16:9 --resolution 4k

# gpt-image-2 / 2.5 支持 auto 或自定义 WIDTHxHEIGHT
python scripts/ai_image.py run --model gpt-image-2 --prompt "提示词" --resolution 1024x1536
python scripts/ai_image.py run --model gpt-image-2.5-sunburst --prompt "提示词" --resolution 1024x1536
python scripts/ai_image.py run --model gpt-image-2.5-flare --prompt "提示词" --resolution 1024x1536

# ⭐ 多图生成（并行执行！）— 用 --count 指定数量，--styles 可选指定风格
python scripts/ai_image.py run --model gpt-image-2 --prompt "赛博朋克城市" --count 5 --resolution 2048x1152
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

### 二、视频生成（即梦 Seedance / MiniMax H3 / Omni / Muse）

视频生成支持四个系列：**即梦 Seedance**（`seedance2-0-pro-2`、`seedance2-5-pro-2`、`seedance-mini-2`）、**MiniMax H3**（`minimax-h3-*`）、**Omni**（`omni-fast-v2v-no-water`、`omni-fast`、`omni-fast-no-water`）、**Muse Video Pro**（`muse-video-pro`）。即梦 / MiniMax 调用 `scripts/minimax_video.py`，Omni 调用 `scripts/omni_video.py`（[参数文档](references/omni_video.md)），Muse 调用 `scripts/muse_video.py`（[参数与时长规则](references/muse_video.md)）。先运行对应脚本的 `list-models` 获取参数范围；用户已指定模型或授权配参、直接提交时，按需求配齐参数并执行。运行时使用这些已定义的脚本，不创建临时调用器、提示词文件或密钥配置。

遇到参数或素材问题，先检查路径、参数名、默认值及当前接口依据，修正授权范围内不改变目标的配置问题。仍有缺失素材、鉴权或本地校验冲突时，仅暂停受影响的提交并明确原因，继续其他独立可执行任务。不能为了凑出可执行方案，擅自换模型、改变时长、删参考图或把首尾帧控制降为普通参考图；也不能把 CLI 的限制直接归结为产品能力缺失。

```bash
cd <项目根目录>
python scripts/minimax_video.py list-models
python scripts/omni_video.py list-models
python scripts/muse_video.py list-models
```

**即梦 Seedance**（`--images` / `--videos` / `--audios` / `--resolution`）：2.0 与 Mini 2 的素材仅接受公网 HTTPS 直链；2.5 可传本地文件（脚本自动上传）或公网直链。下例中的 `media.example.com` 为占位域名，调用时替换为实际素材 HTTPS 直链。

```bash
# 文生视频（2.0：4-15 秒）
python scripts/minimax_video.py run --model seedance2-0-pro-2 --prompt "提示词" --duration 5 --ratio 16:9 --resolution 720p

# 2.0：图片最多 9 张、视频最多 3 段、音频最多 3 个，均须公网 HTTPS URL
python scripts/minimax_video.py run --model seedance2-0-pro-2 --prompt "提示词" --images https://media.example.com/photo.jpg --videos https://media.example.com/clip.mp4 --audios https://media.example.com/bgm.mp3 --duration 8 --ratio 9:16 --resolution 720p

# 2.5：15 / 30 秒；图片最多 30 张（支持人像）、视频最多 10 段、音频最多 10 个
python scripts/minimax_video.py run --model seedance2-5-pro-2 --prompt "提示词" --images photo.jpg --videos clip.mp4 --audios bgm.mp3 --duration 30 --ratio 16:9 --resolution 720p

# Mini 2：4-15 秒，素材上限 9/3/3；视频或音频参考必须至少搭配一张图片
python scripts/minimax_video.py run --model seedance-mini-2 --prompt "保持人像特征，参考动作节奏" --images https://media.example.com/photo.jpg --videos https://media.example.com/clip.mp4 --duration 5 --ratio 16:9 --resolution 480p
```

**MiniMax H3**（`--reference-images` / `--reference-audios` / `--reference-videos` / `--first-image` / `--last-image`；参考素材可传公网直链、data URI 或本地文件）：

```bash
# 文生视频
python scripts/minimax_video.py run --model minimax-h3-768p --prompt "提示词" --duration 5 --ratio 16:9

# 图生视频：最多 5 张参考图，可选最多 3 个参考音频
python scripts/minimax_video.py run --model minimax-h3-2k --prompt "提示词" --reference-images photo.jpg --duration 5 --ratio 9:16

# 首尾帧：不可与 --reference-images 同时使用
python scripts/minimax_video.py run --model minimax-h3-2k --prompt "提示词" --first-image start.jpg --last-image end.jpg --duration 5 --ratio 16:9

# 参考视频驱动：仅 Pro 模型，且只能 1 段 2-5 秒参考视频
python scripts/minimax_video.py run --model minimax-h3-pro-768p --prompt "提示词" --reference-videos source.mp4 --duration 5 --ratio 16:9
```

> **当前 CLI 参数速查**（本地规则，非服务端全部能力；争议项及在线来源见参考文档）：
>
> | 参数 | 即梦 Seedance | MiniMax H3 |
> |------|--------------|------------|
> | `--duration` | 2.0 / Mini 2：4-15 秒（默认 5 秒）；2.5：15 / 30 秒（默认 15 秒） | 4-15 秒 |
> | `--ratio` | 16:9 / 9:16 / 1:1 / 21:9 / 4:3 / 3:4（无 adaptive） | 16:9 / 9:16 / 1:1 / 21:9 / 4:3 / 3:4 / adaptive |
> | `--resolution` | 480p / 720p（默认 480p） | 不支持（清晰度在模型名里，如 768p / 2K） |
> | 参考素材 | 2.0 / Mini 2：图片≤9、视频≤3、音频≤3；2.5：图片≤30（含人像）、视频≤10、音频≤10 | `--reference-images`(≤5) `--reference-audios`(≤3) `--reference-videos`(1) `--first-image` `--last-image` |
> | 提交字段 | `aspect_ratio` / `resolution` / `images` / `videos` / `audios` | `ratio` / `referenceImages` / `referenceAudios` / `referenceVideos` / `first_image` / `last_image` |
> | 轮询路径 | `/v1/videos/{model}/{task_id}` | `/v1/videos/minimax-h3/{task_id}` |
>
> 即梦三个模型都支持 `--images` / `--videos` / `--audios`；2.0 与 Mini 2 仅接受公网 HTTPS 素材 URL，Mini 2 使用视频或音频时必须至少提供一张图片。2.5 的 30/10/10 上限、2.0 的 HTTPS 约束及 Mini 2 的配置依据用户于 2026-11-02 提供的参数说明，未重新联网核实。MiniMax 的 `first_image`/`last_image` 不能与 `referenceImages` 同用，参考音频必须配参考图（合计不超过 15 秒），参考视频仅 Pro 且只能 1 段 2-5 秒。两种模型都不能混用对方的参数名，脚本会直接报错。
>
> 四个系列都提交到 `POST https://apis.aimaxhug.cloud/v1/videos`。Omni、Muse 与即梦按 `/v1/videos/{model}/{task_id}` 查询，MiniMax 保留 `/v1/videos/minimax-h3/{task_id}`。提交成功后必须立即向用户报告任务 ID，并持续轮询返回状态/进度，直到完成或失败。**每 10 秒查询一次，总期限 30 分钟（1800 秒）**；2K 和参考视频请求在高峰期可能排队。
>
> 如果提交响应是 HTTP 400 但响应体包含 `task_id`，不得丢弃任务或停止；必须保留该 ID，继续调用轮询接口查询最终状态。只有 400 且没有 `task_id` 时，才在提交阶段停止。
>
> 即梦 / MiniMax 的 `prompt` 按原有 7000 字符接口规则处理；**Omni 不设本地硬性长度上限，不截断提示词**。`duration` 未指定时按各模型默认值提交（即梦 2.0、Mini 2 与 MiniMax 为 5 秒，即梦 2.5 为 15 秒；Omni 为 10 秒）。
>
> 即梦 / MiniMax 的视频请求时长以 JSON 的 `duration` 字段为准，提示词中的时长描述应与参数一致。Muse 以整数 `seconds` 提交。Omni 的 `seconds` / `duration` 仅表示请求值，**当前 Gemini 固定输出约 10 秒**，不能承诺传入时长就是实际视频时长。MiniMax 使用 `ratio`，即梦、Omni 和 Muse 使用 `aspect_ratio`。

**Omni**：`--ratio` / `--aspect-ratio` 仅支持 `16:9`、`9:16`；`--seconds` 和 `--duration` 二选一；支持单图 `--image-url`（公网 URL 或图片 Base64）、首尾帧 `--first-image-url` / `--last-image-url`、源视频 `--video` / `--video-url` / `--videos`（合计最多 2 个）、多参考图 `--images`（最多 5 张）。远程素材须每个≤8MB、源视频≤1920×1080，具体检查范围见 [Omni 文档](references/omni_video.md)。

```bash
python scripts/omni_video.py run --model omni-fast --prompt "清晨海浪涌向沙滩" --ratio 16:9 --duration 10 --json
python scripts/omni_video.py run --model omni-fast-no-water --prompt "保持参考场景，镜头平稳环绕" --image-url https://media.example.com/scene.jpg --seconds "10" --json
python scripts/omni_video.py run --model omni-fast-v2v-no-water --prompt "参考源视频动作生成连贯画面" --video-url https://media.example.com/action.mp4 --json
```

**Muse Video Pro**：面向用户展示 [中文创作菜单](references/muse_video.md#面向用户的创作菜单)，重点是画面内容、多少秒、横屏或竖屏、镜头怎么动、人物是否出声及参考素材。默认 5 秒、横屏、人物正常说话；时长可选 5 / 8 / 10 / 20 / 30 / 40 / 50 / 60 秒，推荐 5–40 秒，参考图片最多 4 张。用户发来的本地素材由 AI 调用 `scripts/upload.py run <路径...> --json`，从结果提取 `tmp_url` 后填入对应参数；已有链接直接使用。这些上传和链接处理属于内部执行，不要求用户转换素材格式，也不把技术参数表当成用户菜单。字段映射与示例见 [内部调用参数](references/muse_video.md#内部调用参数)。

使用 Muse 参考视频一般是视频续写，`seconds` 表示续写后的**目标总时长**，必须 ≥20 秒；脚本用 ffprobe 实测源视频，报告可续写余量（目标总秒数−源视频实测秒数），**源视频时长 ≥目标总时长则禁止提交**。源视频更短时，建议 ≤目标总时长−2 秒（20→18、30→28，依次类推）；余量不足 2 秒只提示，检测失败则不提交。本地素材先用独立脚本检测再上传，已上传的 URL 在生成前自动复查。独立检测用 `python scripts/video_duration.py <文件或URL> --seconds 20 --json`，无需 Key。首次配置和完整示例见 [muse_video.md](references/muse_video.md)。

```bash
python scripts/muse_video.py run --prompt "人物面向镜头说欢迎回来，保留自然口型和街道环境音" --seconds 10 --camera-motion zoom_in --mute-voice true --json
python scripts/muse_video.py run --prompt "参考源视频动作生成连贯画面" --video-url https://media.example.com/action.mp4 --seconds 20 --json
```

即梦 / MiniMax 详细见 [minimax_video.md](references/minimax_video.md)。

### 内部模型匹配指南（不作为用户菜单）

下表用于 AI 将用户需求匹配到已有模型。面向用户按 [中文交互规范](references/interaction.md) 展示产品名称和当前相关选项，不复制完整调用标识、像素约束或全部模型参数。

| 需求 | 推荐模型 |
|------|---------|
| 默认首选 | **Nano Banana** — 速度快、性价比高，支持10种比例 |
| 更高画质 | **Nano Banana Pro** — 支持10种比例 |
| 细节丰富/色彩鲜艳 | **Seedream 5.0** — `doubao-seedream-5-0-260128`，手动选 1k/2k/4k，支持10种比例 |
| 更高品质/复杂场景 | **Seedream 5.0 Pro** — `doubao-seedream-5-0-pro-260628`，手动选 1k/2k/4k，支持10种比例 |
| 照片级写实/艺术风格 | **gpt-image-2** — 支持 `auto` 或自定义 `WIDTHxHEIGHT` 动态像素尺寸（最大 3840px，须为16的倍数） |
| gpt-image-2 升级版 | **gpt-image-2.5-sunburst** — `auto` 或自定义 `WIDTHxHEIGHT` 动态像素尺寸 |
| gpt-image-2 升级版 | **gpt-image-2.5-flare** — `auto` 或自定义 `WIDTHxHEIGHT` 动态像素尺寸 |

> 每个模型支持的比例应单独核对，用户选择模型后只展示该模型的画幅选项。
> **gpt-image-2 / 2.5-sunburst / 2.5-flare** 支持 `auto` 或自定义 `WIDTHxHEIGHT` 分辨率；宽高均不超过 3840px、须为 16px 的倍数、长宽比不超过 3:1，总像素范围为 655,360–8,294,400。

**内部视频模型匹配指南：**

| 需求 | 推荐模型 |
|------|---------|
| 默认首选 | **即梦 Seedance 2.0 Pro**（`seedance2-0-pro-2`）— 4-15 秒，支持图片 / 视频 / 音频参考 |
| 更长时长或更多素材 | **即梦 Seedance 2.5 Pro**（`seedance2-5-pro-2`）— 15 / 30 秒，图片≤30（含人像）/ 视频≤10 / 音频≤10 |
| 指定 Mini 模型 | **即梦 Seedance Mini 2**（`seedance-mini-2`）— 4-15 秒、480p / 720p；视频或音频参考须配图 |
| 指定 Omni 模型或 Omni V2V | **Omni**（`omni-fast` / `omni-fast-no-water` / `omni-fast-v2v-no-water`）— 约 10 秒、横/竖屏，参数见专用文档 |
| 指定 Muse、人物静音口型或更长时长 | **Muse Video Pro**（`muse-video-pro`）— 推荐 5–40 秒、最多 4 张参考图；视频参考须生成 ≥20 秒 |
| 当前 CLI 的首尾帧 / 参考视频驱动 | **MiniMax H3 Pro**（`minimax-h3-pro-768p` / `minimax-h3-pro-2k`）；不据此断言其他产品无首尾帧能力 |

---

## 执行前检查清单

1. **核对参数与素材** — 按本次模块参考文档检查模型、实际提示词、时长、比例、分辨率及素材；区分实际检查值与用户口述值。
2. **复用授权并补齐参数** — 用户给定参数优先；已授权自动配参时采用适用默认值并列明。只有无法推断且会改变目标的缺失项才询问，不以首次生成为由重复确认。
3. **按授权执行并处理局部阻塞** — 用户要求直接提交即构成该范围内的执行授权；沙箱/免确认不意味着可以省略真实 Key、必要素材或绕过校验。条件齐全就提交并报告任务 ID、持续轮询；有阻塞就写明具体缺失项，完成可独立执行部分及已核实的参数配置，不只抛回一组待选方案。
4. **交付可复核结果** — 用户要求文件时在 `output/` 或指定目录保存实际参数表、对应 CLI 命令和执行状态（不得含密钥）。未齐备的配置明确列出待补项，不能标为“可直接执行”；文件中的命令需与实际参数一致。

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
4. **本地保存** — 检测到环境变量 `SKILL_OUTPUT_DIR` 时，脚本会自动把产物下载到该目录并输出
   `IMAGE_SAVED / AUDIO_SAVED / VIDEO_SAVED: <绝对路径>` 标记行；直接引用该本地路径汇报即可，
   **不要自行下载文件到工作区根目录**

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
| HTML 转图片 | Available | `scripts/html2image.py <file.html>` |
| 文生视频（即梦 Seedance） | Available | `scripts/minimax_video.py run --model seedance2-0-pro-2 --prompt <提示词>` |
| 参考素材生视频（即梦 Seedance） | Available | `scripts/minimax_video.py run --model seedance2-0-pro-2 --images <图片> --videos <视频> --audios <音频>` |
| 长时长视频（即梦 Seedance 2.5） | Available | `scripts/minimax_video.py run --model seedance2-5-pro-2 --duration 30` |
| 文生视频 / 多素材参考（即梦 Seedance Mini 2） | Available | `scripts/minimax_video.py run --model seedance-mini-2 --prompt <提示词>`（视频/音频参考须配图） |
| 文生视频（MiniMax H3） | Available | `scripts/minimax_video.py run --model minimax-h3-768p --prompt <提示词>` |
| 图生视频（MiniMax H3） | Available | `scripts/minimax_video.py run --model minimax-h3-2k --reference-images <图片>` |
| 首尾帧视频（MiniMax H3） | Available | `scripts/minimax_video.py run --model minimax-h3-2k --first-image <首帧> --last-image <尾帧>` |
| 参考视频驱动（MiniMax H3 Pro） | Available | `scripts/minimax_video.py run --model minimax-h3-pro-768p --reference-videos <视频>` |
| 文生视频 / 图片及首尾帧参考（Omni） | Available | `scripts/omni_video.py run --model omni-fast --prompt <提示词>`（也支持 `omni-fast-no-water`） |
| 视频参考（Omni V2V） | Available | `scripts/omni_video.py run --model omni-fast-v2v-no-water --prompt <提示词> --video-url <视频URL>` |
| 文生视频 / 首尾帧 / 多参考图（Muse） | Available | `scripts/muse_video.py run --prompt <提示词>`（默认 `muse-video-pro`，可选 `--mute-voice true`） |
| 视频参考（Muse） | Available | `scripts/muse_video.py run --prompt <提示词> --video-url <视频URL> --seconds 20`（自动检测时长） |
| 视频时长检测 | Available | `scripts/video_duration.py <文件或URL> --seconds 20 --json`（需 ffprobe，无需 Key） |
| 列出视频模型 | Available | `scripts/minimax_video.py list-models` |
| 文生音频 | Available | `scripts/ai_audio.py run`（短文本 `/v1/minimax/audio`） |
| 长文本音频 | Available | `scripts/ai_audio.py run --long`（`/v1/minimax/audio/long`） |
| 声音克隆 | Available | `scripts/ai_audio.py run --input-audio voice.mp3`（只能一个文件，时长 >10 秒且 <2 分钟，先调用上传接口并使用 `/audio/long`） |
| 列出音频模型 | Available | `scripts/ai_audio.py list-models` |
| 短视频解析 | Available | `scripts/video_parse.py run --url <分享链接>` |
| 抖音账号搜索 | Available | `scripts/social_media.py search-douyin-users --keyword <关键词>` |
| 抖音账号、作品、榜单与用户数据 | Available | `scripts/social_media.py <子命令>` |

| 小红书账号、作品、榜单与评论数据 | Available | `scripts/xhs.py <子命令>` |

## 社交媒体平台解析

当用户请求自媒体平台解析、社交媒体数据、抖音账号搜索或搜索抖音用户时，使用 `scripts/social_media.py`。当前已实现按关键词搜索抖音账号：

```bash
python scripts/social_media.py search-douyin-users --keyword "摄影"
```

接口为 `POST https://api.aimaxhug.cloud/social/story/api/dyData/searchUser`，脚本会自动携带 `Authorization: Bearer <AIMAXHUG_API_KEY>` 和 `Content-Type: application/json`。参数说明和原始 JSON 输出方式见 [references/social_media.md](references/social_media.md)。

当前抖音子命令还包括：`search-douyin-accounts`、`query-douyin-work-list`、`list-douyin-works-by-account`、`search-douyin-articles`、`search-douyin-works`、`query-douyin-work`、`get-douyin-work-detail`、`recommend-douyin-accounts`、`douyin-likes-rank`、`query-douyin-user`、`search-douyin-ai-works`、`douyin-daily-rank`、`douyin-weekly-rank`、`extract-douyin-audio-text`。

小红书功能统一使用 `scripts/xhs.py`，命令和参数见 [references/xhs.md](references/xhs.md)。
