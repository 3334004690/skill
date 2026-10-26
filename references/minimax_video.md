# Video Generation Module (即梦 Seedance + MiniMax H3)

视频生成通过异步接口提交任务并轮询到视频完成。支持两个系列：**即梦 Seedance** 与 **MiniMax H3**，由同一个脚本 `scripts/minimax_video.py` 提供。

## 能力依据与模型标识

下列模型表、字段映射和校验表描述的是 [当前 CLI](../scripts/minimax_video.py) 已实现的范围，不是即梦或 MiniMax 全部产品能力。先用 `list-models` 查看本地注册表，遇到首尾帧、时长或素材组合争议时，再核对用户指定的**完整模型 key**与官方来源，不能只按“2.5”等简称判断。

公开来源（2026-10-26 查阅）：

- [官方 Seedance 文档](https://docs.aimaxhug.cloud/js/data/seedance.js)：`seedance2-0-pro-2` 与 `Seedance-2.0-pro`、`Seedance-2.5` 等是不同条目。部分条目提供 `first_image_url` / `last_image_url` / `reference_image_urls`；因此不能笼统说“即梦没有首尾帧”，也不能把其他条目的参数直接混入现有 CLI。
- [当前公开模型配置](https://apis.aimaxhug.cloud/v1/videos/models)：其中 `seedance2-0-pro-2` 的时长为 4–15 秒，`seedance2-5-pro-2` 为 15 / 30 秒。这里的结论只对应这两个 key，不能推出“8 秒只能使用即梦 2.0”。
- [官方 MiniMax 文档](https://docs.aimaxhug.cloud/js/data/minimax.js)：`referenceImages` 与 `first_image` / `last_image` 互斥有明确文档依据，保留现有校验；不能仅因评测判错就删除。
- [公开 OpenAPI](https://apis.aimaxhug.cloud/openapi.json)：`/v1/videos` 描述为参数原样透传，时长范围与默认值由上游决定。该描述未提供首尾帧与参考图互斥的字段 schema，不能用它单独证明此类组合一定可用或不可用。

具体比对：Seedance 文档对象 `seedance-pro-2` 明确写 `seedance2-0-pro-2` 不支持 `first_image` / `last_image`；另一个对象 `seedance-2-5` 对应 **`Seedance-2.5`**，写明 4–15 秒、最多 30 张参考图及首尾帧 URL 参数。公开模型配置中两个旧 key 的 `channel_details.channel_3.internal_model` 仅列 `16:9 / 9:16 / 1:1`、默认 `720p`，旧 2.5 还列参考视频/音频数量各 3；这与本地注册表六种比例、默认 `480p`、旧 2.5 仅图片的范围有差异。当前 CLI 表不能作为实时模型配置引用；正式接入这些差异前，需核对模型/渠道和字段映射，保留现有业务校验。

当前 CLI 未实现的官方模型或字段，应说明“当前脚本尚未接入”，并列出已核实的支持范围；不能擅自改模型、牺牲参考图或把首尾帧塞入普通参考图组后声称效果等价。需要接入新能力时应作为代码变更核对真实映射，再验证；运行生成任务时不得新建临时调用器绕过本地校验。无证据时保留冲突说明，不给出产品层面的绝对结论。

## Supported Models（当前 CLI）

### 即梦 Seedance

| Model key | Model | Duration | Resolution | Reference assets |
|-----------|-------|----------|------------|------------------|
| `seedance2-0-pro-2` | 即梦 Seedance 2.0 Pro | 4–15 秒 | 480p / 720p | 图片(≤9) / 视频(≤3) / 音频(≤3) |
| `seedance2-5-pro-2` | 即梦 Seedance 2.5 Pro | 15 / 30 秒 | 480p / 720p | 图片(≤9) |

即梦画幅：`16:9` / `9:16` / `1:1` / `21:9` / `4:3` / `3:4`（**没有** `adaptive`）。

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

```bash
python {baseDir}/scripts/minimax_video.py run \
  --model seedance2-0-pro-2 \
  --prompt "保持人物动作节奏，改为电影级暖色调" \
  --images photo1.jpg photo2.jpg \
  --videos clip.mp4 \
  --audios bgm.mp3 \
  --duration 8 \
  --ratio 9:16 \
  --resolution 720p
```

### 即梦 Seedance 2.5 — Long Duration

```bash
python {baseDir}/scripts/minimax_video.py run \
  --model seedance2-5-pro-2 \
  --prompt "人物在雨中缓慢行走，镜头跟随" \
  --images portrait.jpg \
  --duration 30 \
  --ratio 16:9 \
  --resolution 720p
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
| `--model` | `seedance2-0-pro-2` / `seedance2-5-pro-2` | `minimax-h3-*` | One of the model keys above |
| `--prompt` | `prompt` | `prompt` | Required; API silently truncates text beyond 7000 characters |
| `--duration` | `duration` | `duration` | 2.0 / MiniMax: 4–15 秒；2.5: 15 或 30 秒 |
| `--ratio` | `aspect_ratio` | `ratio` | 即梦无 `adaptive`；MiniMax 含 `adaptive` |
| `--resolution` | `resolution` | — | 即梦：`480p` / `720p`（默认 480p） |
| `--images` | `images` | — | 即梦参考图，最多 9 个（URL 或本地文件） |
| `--videos` | `videos` | — | 仅 2.0，最多 3 个（URL 或本地文件） |
| `--audios` | `audios` | — | 仅 2.0，最多 3 个（URL 或本地文件） |
| `--reference-images` | — | `referenceImages` | MiniMax，最多 5 个（URL / data URI / 本地文件） |
| `--reference-audios` | — | `referenceAudios` | MiniMax，最多 3 个且须配参考图 |
| `--reference-videos` | — | `referenceVideos` | MiniMax Pro only；exactly one 2-5 second source video |
| `--first-image` | — | `first_image` | MiniMax，不能与 `referenceImages` 同用 |
| `--last-image` | — | `last_image` | MiniMax，不能与 `referenceImages` 同用 |
| `--poll-timeout` | client-side polling limit | client-side polling limit | Defaults to 1800 seconds (30 minutes); polls every 10 seconds |

### 参考素材处理差异

- **即梦**：本地文件先通过 `/api/v2/upload/file` 上传，拿到 URL 后放进 `images` / `videos` / `audios` 数组；公网直链可直接传入。不生成 data URI。
- **MiniMax**：本地文件在内存中编码为 `data:<mime>;base64,...`；也可直接传公网 URL 或 data URI。脚本会预检参考音视频时长，无法校验文档中的限制时直接停止。

两类模型不能混用对方的参数名：给即梦传 `--reference-images`、或给 MiniMax 传 `--images` / `--resolution`，脚本都会直接报错。

## Validation Rules（当前 CLI 本地校验）

以下限制由现有脚本执行，未覆盖平台其他模型/调用方式。尤其 `--first-image` / `--last-image` 仅在本 CLI 的 MiniMax 分支提供，不能由此推断 Seedance 产品整体没有首尾帧能力。关于即梦 2.5 的素材支持，公开配置与本地注册表可能不同；生成任务仍按当前 CLI 校验执行并披露差异，不擅自放宽。

- 即梦 2.5 只支持图片参考；视频 / 音频参考仅 2.0 支持。
- 即梦 2.5 时长只能是 15 或 30 秒；即梦 2.0 与 MiniMax 为 4–15 秒。
- MiniMax 文生视频不能使用 `ratio=adaptive`。
- MiniMax `first_image` / `last_image` 与 `referenceImages` 互斥。
- MiniMax 参考音频必须与参考图同时提供；最多 3 个，总时长不超过 15 秒。
- MiniMax 参考视频仅 Pro 模型，且必须为 1 段 2–5 秒的源视频。
- 2K 与参考视频请求在高峰期可能更慢；保持轮询直到完成或超时。
- 内容策略由 API 强制；被拒的提示词通常在创建任务前以 HTTP 400 返回。若 400 响应仍带 `task_id`，脚本会保留该 ID 继续轮询。
- 视频时长以 JSON 的 `duration` 字段为准；`prompt` 中的时长措辞需与之一致。MiniMax 使用 `ratio` 字段，即梦使用 `aspect_ratio` 字段。
