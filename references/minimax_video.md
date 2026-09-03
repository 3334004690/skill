# MiniMax H3 Video Module

视频生成使用 MiniMax H3 系列，通过异步接口提交任务并轮询到视频完成。

## Supported Models

| Model key | Model | Resolution tier | Reference video |
|-----------|-------|-----------------|-----------------|
| `minimax-h3-768p` | MiniMax H3 | 768p | No |
| `minimax-h3-2k` | MiniMax H3 | 2K | No |
| `minimax-h3-pro-768p` | MiniMax H3 Pro | 768p | Yes |
| `minimax-h3-pro-2k` | MiniMax H3 Pro | 2K | Yes |

## API Workflow

1. Submit `POST https://apis.aimaxhug.cloud/v1/videos` with JSON body and Bearer authentication.
2. Read and immediately report `task_id` from the response.
3. Poll `GET https://apis.aimaxhug.cloud/v1/videos/minimax-h3/{task_id}` until status is completed and `video_url` is returned.

The predefined script performs all validation and polling. It never creates `.env`, prompt files, helper scripts, or alternate video-generation scripts at runtime. Any validation or API error stops the request before generation.

If submission returns HTTP 400 but includes a `task_id`, the script preserves the task ID and continues polling. A 400 without a task ID is treated as a submission failure.

## CLI Usage

```bash
python {baseDir}/scripts/minimax_video.py list-models
python {baseDir}/scripts/minimax_video.py run [options]
```

默认最多轮询等待 20 分钟（1200 秒）；可通过 `--poll-timeout` 自定义等待时间。

### Text-to-Video

```bash
python {baseDir}/scripts/minimax_video.py run \
  --model minimax-h3-768p \
  --prompt "清晨的海浪涌向沙滩，金色阳光映照水面，电影感镜头" \
  --duration 5 \
  --ratio 16:9
```

### Image-to-Video

```bash
python {baseDir}/scripts/minimax_video.py run \
  --model minimax-h3-2k \
  --prompt "人物自然转身，镜头缓慢推进" \
  --reference-images image1.jpg image2.jpg \
  --reference-audios narration.mp3 \
  --duration 8 \
  --ratio 9:16
```

### First/Last Frame

```bash
python {baseDir}/scripts/minimax_video.py run \
  --model minimax-h3-2k \
  --prompt "花朵从含苞到盛开，画面自然过渡" \
  --first-image start.jpg \
  --last-image end.jpg \
  --duration 6 \
  --ratio 16:9
```

### Reference-Video Driven

```bash
python {baseDir}/scripts/minimax_video.py run \
  --model minimax-h3-pro-768p \
  --prompt "保持人物动作节奏，改为电影级暖色调" \
  --reference-videos source.mp4 \
  --duration 5 \
  --ratio 16:9
```

## Request Mapping

| CLI option | API field | Constraint |
|------------|-----------|------------|
| `--model` | `model` | One of the four model keys above |
| `--prompt` | `prompt` | Required; API silently truncates text beyond 7000 characters |
| `--duration` | `duration` | Integer from 4 to 15 seconds; script sends 5 seconds when omitted |
| `--ratio` | `ratio` | `16:9`, `9:16`, `1:1`, `21:9`, `4:3`, `3:4`, or `adaptive` |
| `--reference-images` | `referenceImages` | Up to 5 URLs, data URIs, or local files |
| `--reference-audios` | `referenceAudios` | Up to 3; requires `referenceImages` |
| `--reference-videos` | `referenceVideos` | Pro models only; exactly one 2-5 second source video |
| `--first-image` | `first_image` | Cannot be combined with `referenceImages` |
| `--last-image` | `last_image` | Cannot be combined with `referenceImages` |
| `--poll-timeout` | client-side polling limit | Defaults to 1200 seconds (20 minutes) |

Local files are automatically encoded as `data:<mime>;base64,...`. Public URLs must be directly accessible. The script probes reference-media duration before submission and stops if it cannot verify the documented limits.

## Validation Rules

- Text-only video cannot use `ratio=adaptive`.
- `first_image` / `last_image` and `referenceImages` are mutually exclusive.
- Reference audio must be supplied together with reference images; provide at most three audio files and keep their total duration within 15 seconds.
- Reference video is available only to Pro models and must be one 2-5 second source video.
- 2K and reference-video requests can take longer during peak periods; keep polling until completion or timeout.
- Content policy is enforced by the API. A normal rejected prompt fails with HTTP 400 before a task is created or billed. If a 400 response nevertheless contains a `task_id`, the predefined script preserves that ID and continues polling it.
- Video length is controlled by the JSON `duration` field. Keep any duration wording inside `prompt` consistent with that value; `ratio` is the current aspect-ratio field even if legacy backend logs label it as `aspect_ratio`.
