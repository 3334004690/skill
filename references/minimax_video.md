# Video Generation Module (即梦 Seedance + MiniMax H3)

视频生成通过异步接口提交任务并轮询到视频完成。支持两个系列：**即梦 Seedance** 与 **MiniMax H3**，由同一个脚本 `scripts/minimax_video.py` 提供。

## Supported Models

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

The predefined script performs all validation and polling. It never creates `.env`, prompt files, helper scripts, or alternate video-generation scripts at runtime. Any validation or API error stops the request before generation.

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

## Request Mapping

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

## Validation Rules

- 即梦 2.5 只支持图片参考；视频 / 音频参考仅 2.0 支持。
- 即梦 2.5 时长只能是 15 或 30 秒；即梦 2.0 与 MiniMax 为 4–15 秒。
- MiniMax 文生视频不能使用 `ratio=adaptive`。
- MiniMax `first_image` / `last_image` 与 `referenceImages` 互斥。
- MiniMax 参考音频必须与参考图同时提供；最多 3 个，总时长不超过 15 秒。
- MiniMax 参考视频仅 Pro 模型，且必须为 1 段 2–5 秒的源视频。
- 2K 与参考视频请求在高峰期可能更慢；保持轮询直到完成或超时。
- 内容策略由 API 强制；被拒的提示词通常在创建任务前以 HTTP 400 返回。若 400 响应仍带 `task_id`，脚本会保留该 ID 继续轮询。
- 视频时长以 JSON 的 `duration` 字段为准；`prompt` 中的时长措辞需与之一致。MiniMax 使用 `ratio` 字段，即梦使用 `aspect_ratio` 字段。
