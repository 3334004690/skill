# Video Generation Module (即梦 Seedance + MiniMax H3)

视频生成通过异步接口提交任务并轮询到视频完成。支持两个系列：**即梦 Seedance** 与 **MiniMax H3**，由同一个脚本 `scripts/minimax_video.py` 提供。

## 能力依据与模型标识

下列模型表、字段映射和校验表描述的是 [当前 CLI](../scripts/minimax_video.py) 已实现的范围，不是即梦或 MiniMax 全部产品能力。先用 `list-models` 查看本地注册表，遇到首尾帧、时长或素材组合争议时，再核对用户指定的**完整模型 key**与官方来源，不能只按“2.5”等简称判断。

本次参数依据（用户于 2026-11-02 提供，未重新联网核实）：

- `seedance2-0-pro-2`：图片≤9 / 视频≤3 / 音频≤3，均仅接受公网 HTTPS URL。
- `seedance2-5-pro-2`：图片≤30（支持人像）/ 视频≤10 / 音频≤10；素材输入保留原脚本的本地文件上传或公网 URL 方式。
- `seedance-mini-2`：时长 4–15 秒、默认 5 秒、步长 1；画幅默认 16:9；分辨率 480p / 720p、默认 480p；图片≤9 / 视频≤3 / 音频≤3，均须公网 HTTPS URL；视频或音频参考须至少配一张图片，按秒计费。

历史公开来源（2026-10-26 查阅；其中旧素材数量由上面的用户补充说明更新）：

- [官方 Seedance 文档](https://docs.aimaxhug.cloud/js/data/seedance.js)：`seedance2-0-pro-2` 与 `Seedance-2.0-pro`、`Seedance-2.5` 等是不同条目。部分条目提供 `first_image_url` / `last_image_url` / `reference_image_urls`；因此不能笼统说“即梦没有首尾帧”，也不能把其他条目的参数直接混入现有 CLI。
- [当前公开模型配置](https://apis.aimaxhug.cloud/v1/videos/models)：其中 `seedance2-0-pro-2` 的时长为 4–15 秒，`seedance2-5-pro-2` 为 15 / 30 秒。这里的结论只对应这两个 key，不能推出“8 秒只能使用即梦 2.0”。
- [官方 MiniMax 文档](https://docs.aimaxhug.cloud/js/data/minimax.js)：`referenceImages` 与 `first_image` / `last_image` 互斥有明确文档依据，保留现有校验；不能仅因评测判错就删除。
- [公开 OpenAPI](https://apis.aimaxhug.cloud/openapi.json)：`/v1/videos` 描述为参数原样透传，时长范围与默认值由上游决定。该描述未提供首尾帧与参考图互斥的字段 schema，不能用它单独证明此类组合一定可用或不可用。

历史比对：Seedance 文档对象 `seedance-pro-2` 写 `seedance2-0-pro-2` 不支持 `first_image` / `last_image`；另一个对象 `seedance-2-5` 对应 **`Seedance-2.5`**，是不同的完整模型 key，不能混用参数。历史公开配置与本地注册表在比例、默认分辨率等处存在差异；本次仅依据用户说明更新素材规则并接入 Mini 2，其他既有配置保留。当前 CLI 表不能作为平台实时配置引用。

当前 CLI 未实现的官方模型或字段，应说明“当前脚本尚未接入”，并列出已核实的支持范围；不能擅自改模型、牺牲参考图或把首尾帧塞入普通参考图组后声称效果等价。需要接入新能力时应作为代码变更核对真实映射，再验证；运行生成任务时不得新建临时调用器绕过本地校验。无证据时保留冲突说明，不给出产品层面的绝对结论。

## Supported Models（当前 CLI）

### 即梦 Seedance

| Model key | Model | Duration | Resolution | Reference assets |
|-----------|-------|----------|------------|------------------|
| `seedance2-0-pro-2` | 即梦 Seedance 2.0 Pro | 4–15 秒（默认 5） | 480p / 720p | 图片(≤9) / 视频(≤3) / 音频(≤3)，仅公网 HTTPS URL |
| `seedance2-5-pro-2` | 即梦 Seedance 2.5 Pro | 15 / 30 秒（默认 15） | 480p / 720p | 图片(≤30，支持人像) / 视频(≤10) / 音频(≤10) |
| `seedance-mini-2` | 即梦 Seedance Mini 2 | 4–15 秒（默认 5，步长 1） | 480p / 720p | 图片(≤9) / 视频(≤3) / 音频(≤3)，仅公网 HTTPS URL；视频/音频须配图 |

即梦画幅：`16:9` / `9:16` / `1:1` / `21:9` / `4:3` / `3:4`（**没有** `adaptive`），默认 `16:9`。分辨率默认 `480p`。

#### Seedance Mini 2 参数

| 提交字段 | 类型 | 默认值 / 范围 | 说明 |
|----------|------|---------------|------|
| `model` | string | `seedance-mini-2` | 必填公开模型 ID；命令中使用 `--model seedance-mini-2` |
| `prompt` | string | 非空 | 必填视频提示词；命令中使用 `--prompt` |
| `duration` | integer | 默认 5；4–15，步长 1 | 视频秒数，按秒计费 |
| `aspect_ratio` | enum | 默认 16:9；取值见上方画幅列表 | 命令中使用 `--ratio` |
| `resolution` | enum | 默认 480p；480p / 720p | 输出分辨率 |
| `images` | array | 可选，最多 9 张 | 公网 HTTPS 图片 URL |
| `videos` | array | 可选，最多 3 段 | 公网 HTTPS 视频 URL；至少同时提供一张图片 |
| `audios` | array | 可选，最多 3 个 | 公网 HTTPS 音频 URL；至少同时提供一张图片 |

### MiniMax H3

| Model key | Model | Resolution tier | Reference video |
|-----------|-------|-----------------|-----------------|
| `minimax-h3-768p` | MiniMax H3 | 768p | No |
| `minimax-h3-2k` | MiniMax H3 | 2K | No |
| `minimax-h3-pro-768p` | MiniMax H3 Pro | 768p | Yes |
| `minimax-h3-pro-2k` | MiniMax H3 Pro | 2K | Yes |

MiniMax 时长 4–15 秒；画幅 `16:9` / `9:16` / `1:1` / `21:9` / `4:3` / `3:4` / `adaptive`。清晰度已包含在模型名中，不使用 `--resolution`。

## API Workflow

1. Submit `POST https://apis.aimaxhug.cloud/v1/videos` with JSON body and Bearer authentication.
2. Read and immediately report `task_id` from the response.
3. Poll until status is completed and a video URL is returned:
   - 即梦 Seedance: `GET https://apis.aimaxhug.cloud/v1/videos/{model}/{task_id}`
   - MiniMax H3: `GET https://apis.aimaxhug.cloud/v1/videos/minimax-h3/{task_id}`

The predefined script performs validation and polling. It never creates `.env`, prompt files, helper scripts, or alternate video-generation scripts at runtime. A local validation failure prevents that request from being submitted. Fix configuration issues within the user's existing authorization, and continue independent work if one request remains blocked. An error after a task ID has been returned must be handled by preserving the ID and checking task status rather than resubmitting blindly.

用户已指定模型或明确授权代选、自动配参、直接提交时，展示所选参数（含单位及来源）后执行，无需再等待模型选择或首次生成确认。只有会改变目标且无法推断的关键输入缺失时才询问。缺 Key 时明确报告，完成本地参数检查；沙箱模式不等于有 Key，也不意味着可跳过素材和校验。

If submission returns HTTP 400 but includes a `task_id`, the script preserves the task ID and continues polling. A 400 without a task ID is treated as a submission failure.

## CLI Usage

```bash
python {baseDir}/scripts/minimax_video.py list-models
python {baseDir}/scripts/minimax_video.py run [options]
```

默认每 10 秒查询一次，最多轮询等待 30 分钟（1800 秒）；可通过 `--poll-timeout` 自定义总等待时间。

### 即梦 Seedance — Text-to-Video

```bash
python {baseDir}/scripts/minimax_video.py run \
  --model seedance2-0-pro-2 \
  --prompt "清晨的海浪涌向沙滩，金色阳光映照水面，电影感镜头" \
  --duration 5 \
  --ratio 16:9 \
  --resolution 720p
```

### 即梦 Seedance — Reference-Driven

`media.example.com` 为示例占位域名，需替换为真实可访问的公网 HTTPS 素材直链。

```bash
python {baseDir}/scripts/minimax_video.py run \
  --model seedance2-0-pro-2 \
  --prompt "保持人物动作节奏，改为电影级暖色调" \
  --images https://media.example.com/photo1.jpg https://media.example.com/photo2.jpg \
  --videos https://media.example.com/clip.mp4 \
  --audios https://media.example.com/bgm.mp3 \
  --duration 8 \
  --ratio 9:16 \
  --resolution 720p
```

### 即梦 Seedance 2.5 — Long Duration / 多素材参考

```bash
python {baseDir}/scripts/minimax_video.py run \
  --model seedance2-5-pro-2 \
  --prompt "保持参考人像特征，参考动作与音乐节奏，人物在雨中缓慢行走" \
  --images portrait.jpg \
  --videos clip.mp4 \
  --audios bgm.mp3 \
  --duration 30 \
  --ratio 16:9 \
  --resolution 720p
```

### 即梦 Seedance Mini 2

文生视频可以不传任何素材；使用视频或音频参考时必须至少提供一张公网 HTTPS 图片。

```bash
python {baseDir}/scripts/minimax_video.py run --model seedance-mini-2 --prompt "清晨海浪涌向沙滩" --duration 5 --ratio 16:9 --resolution 480p

python {baseDir}/scripts/minimax_video.py run --model seedance-mini-2 --prompt "保持人物形象，参考动作和音乐节奏" --images https://media.example.com/person.jpg --videos https://media.example.com/action.mp4 --audios https://media.example.com/music.mp3 --duration 8 --ratio 9:16 --resolution 720p --json
```

### MiniMax H3 — Text-to-Video

```bash
python {baseDir}/scripts/minimax_video.py run \
  --model minimax-h3-768p \
  --prompt "清晨的海浪涌向沙滩，金色阳光映照水面，电影感镜头" \
  --duration 5 \
  --ratio 16:9
```

### MiniMax H3 — Image-to-Video

```bash
python {baseDir}/scripts/minimax_video.py run \
  --model minimax-h3-2k \
  --prompt "人物自然转身，镜头缓慢推进" \
  --reference-images image1.jpg image2.jpg \
  --reference-audios narration.mp3 \
  --duration 8 \
  --ratio 9:16
```

### MiniMax H3 — First/Last Frame

```bash
python {baseDir}/scripts/minimax_video.py run \
  --model minimax-h3-2k \
  --prompt "花朵从含苞到盛开，画面自然过渡" \
  --first-image start.jpg \
  --last-image end.jpg \
  --duration 6 \
  --ratio 16:9
```

### MiniMax H3 — Reference-Video Driven

```bash
python {baseDir}/scripts/minimax_video.py run \
  --model minimax-h3-pro-768p \
  --prompt "保持人物动作节奏，改为电影级暖色调" \
  --reference-videos source.mp4 \
  --duration 5 \
  --ratio 16:9
```

## Request Mapping（当前 CLI）

| CLI option | 即梦 Seedance | MiniMax H3 | Constraint |
|------------|--------------|------------|------------|
| `--model` | `seedance2-0-pro-2` / `seedance2-5-pro-2` / `seedance-mini-2` | `minimax-h3-*` | One of the model keys above |
| `--prompt` | `prompt` | `prompt` | Required; API silently truncates text beyond 7000 characters |
| `--duration` | `duration` | `duration` | 2.0 / Mini 2 / MiniMax: 4–15 秒；2.5: 15 或 30 秒 |
| `--ratio` | `aspect_ratio` | `ratio` | 即梦无 `adaptive`；MiniMax 含 `adaptive` |
| `--resolution` | `resolution` | — | 即梦：`480p` / `720p`（默认 480p） |
| `--images` | `images` | — | 2.0 / Mini 2：≤9，公网 HTTPS URL；2.5：≤30，路径/URL，支持人像 |
| `--videos` | `videos` | — | 2.0 / Mini 2：≤3，公网 HTTPS URL；2.5：≤10，路径/URL；Mini 2 须配图 |
| `--audios` | `audios` | — | 2.0 / Mini 2：≤3，公网 HTTPS URL；2.5：≤10，路径/URL；Mini 2 须配图 |
| `--reference-images` | — | `referenceImages` | MiniMax，最多 5 个（URL / data URI / 本地文件） |
| `--reference-audios` | — | `referenceAudios` | MiniMax，最多 3 个且须配参考图 |
| `--reference-videos` | — | `referenceVideos` | MiniMax Pro only；exactly one 2-5 second source video |
| `--first-image` | — | `first_image` | MiniMax，不能与 `referenceImages` 同用 |
| `--last-image` | — | `last_image` | MiniMax，不能与 `referenceImages` 同用 |
| `--poll-timeout` | client-side polling limit | client-side polling limit | Defaults to 1800 seconds (30 minutes); polls every 10 seconds |

### 参考素材处理差异

- **即梦 2.0 / Mini 2**：`images` / `videos` / `audios` 仅接受公网 HTTPS URL，不接受本地文件、HTTP URL 或 data URI。脚本离线拒绝明显的本地主机及内网 IP；域名是否实际解析到公网、素材可达性及内容类型仍由调用方和接口验证。
- **即梦 2.5**：本地文件先通过 `/api/v2/upload/file` 上传，拿到 URL 后放进对应素材数组；http(s) 公网直链可直接传入。不生成 data URI。
- **MiniMax**：本地文件在内存中编码为 `data:<mime>;base64,...`；也可直接传公网 URL 或 data URI。脚本会预检参考音视频时长，无法校验文档中的限制时直接停止。

两类模型不能混用对方的参数名：给即梦传 `--reference-images`、或给 MiniMax 传 `--images` / `--resolution`，脚本都会直接报错。

## Validation Rules（当前 CLI 本地校验）

以下限制由现有脚本执行，未覆盖平台其他模型/调用方式。尤其 `--first-image` / `--last-image` 仅在本 CLI 的 MiniMax 分支提供，不能由此推断 Seedance 产品整体没有首尾帧能力。2.0 / 2.5 的素材更新及 Mini 2 配置来源为本次用户提供的参数说明，未重新联网核实。

- 即梦 2.0：图片≤9 / 视频≤3 / 音频≤3，仅接受公网 HTTPS URL。
- 即梦 2.5：图片≤30（支持人像）/ 视频≤10 / 音频≤10。
- 即梦 Mini 2：图片≤9 / 视频≤3 / 音频≤3，仅接受公网 HTTPS URL；有视频或音频参考时，至少提供一张图片。此配图要求不扩展到 2.0 / 2.5。
- 即梦 2.5 时长只能是 15 或 30 秒；即梦 2.0、Mini 2 与 MiniMax 为 4–15 秒。
- MiniMax 文生视频不能使用 `ratio=adaptive`。
- MiniMax `first_image` / `last_image` 与 `referenceImages` 互斥。
- MiniMax 参考音频必须与参考图同时提供；最多 3 个，总时长不超过 15 秒。
- MiniMax 参考视频仅 Pro 模型，且必须为 1 段 2–5 秒的源视频。
- 2K 与参考视频请求在高峰期可能更慢；保持轮询直到完成或超时。
- 内容策略由 API 强制；被拒的提示词通常在创建任务前以 HTTP 400 返回。若 400 响应仍带 `task_id`，脚本会保留该 ID 继续轮询。
- 视频时长以 JSON 的 `duration` 字段为准；`prompt` 中的时长措辞需与之一致。MiniMax 使用 `ratio` 字段，即梦使用 `aspect_ratio` 字段。
