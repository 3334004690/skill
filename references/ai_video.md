# AI Video Module

Generate videos from text prompts or with reference images using Kling / Vidu.

## Supported Task Types

| Type | Description |
|------|-------------|
| **Text-to-Video** | Generate a video from a text prompt (no `--input-images`) |
| **Image-to-Video** | Generate a video with reference images (pass `--input-images`) |

## Subcommands

| Subcommand | When to use |
|------------|-------------|
| `run` | **Default.** Generate video and show result |
| `list-models` | Show available video models, durations, resolutions, and proportions |

## Usage

```bash
python {baseDir}/scripts/ai_video.py <subcommand> [options]
```

## Examples

### List Models

```bash
python {baseDir}/scripts/ai_video.py list-models
```

### Text-to-Video

```bash
# Kling — 720p default
python {baseDir}/scripts/ai_video.py run \
  --model kling \
  --prompt "一只橘猫在阳光下打滚" \
  --proportion 16:9 \
  --duration 5 \
  --resolution 720p

# Vidu — 1080p
python {baseDir}/scripts/ai_video.py run \
  --model vidu \
  --prompt "城市夜景航拍" \
  --proportion 9:16 \
  --duration 10 \
  --resolution 1080p

# Kling — 15s duration
python {baseDir}/scripts/ai_video.py run \
  --model kling \
  --prompt "壮丽的山河航拍" \
  --proportion 16:9 \
  --duration 15 \
  --resolution 720p
```

### Image-to-Video (with reference)

```bash
# Vidu with reference image
python {baseDir}/scripts/ai_video.py run \
  --model vidu \
  --prompt "人物在沙滩上行走" \
  --input-images photo.jpg \
  --proportion 16:9

# Kling with multiple images (first/last frame)
python {baseDir}/scripts/ai_video.py run \
  --model kling \
  --prompt "花朵从绽放到凋谢" \
  --input-images start.jpg end.jpg \
  --proportion 9:16
```

### Multi-Video Generation (Parallel)

```bash
# Generate 3 videos with different cinematic styles
python {baseDir}/scripts/ai_video.py run \
  --model kling \
  --prompt "赛博朋克城市" \
  --count 3 \
  --proportion 16:9 \
  --resolution 720p
```

> ⚠️ Max `--count` is **5**. Single command at a time — wait for completion before next.

## Options

| Option | Description |
|--------|-------------|
| `--model` | Model key: `kling`, `vidu` (required) |
| `--prompt` | Text prompt describing the video (required) |
| `--proportion` | Aspect ratio: `16:9`, `9:16`, `1:1` |
| `--duration` | Duration in seconds: `5`, `10`, `15` (default: `5`)。传入参考素材时仅支持 5-10 秒 |
| `--resolution` | `720p` / `1080p` / `4k`（4k 仅可灵支持，Vidu 不支持） |
| `--input-images` | Local image path(s) for image-to-video (space-separated) |
| `--count` | Number of videos to generate (default: 1, max: 5). **When > 1, tasks run in parallel** |
| `--json` | Output result as JSON |

## Supported Models

| Model | Key | Resolutions | Durations | Proportions | Notes |
|-------|-----|-------------|-----------|-------------|-------|
| **可灵 (Kling)** | `kling` | 720p / 1080p / 4k | 5s / 10s / 15s | 16:9 / 9:16 / 1:1 | 传参考素材时 15s 不可用 |
| **Vidu** | `vidu` | 720p / 1080p | 5s / 10s / 15s | 16:9 / 9:16 / 1:1 | 传参考素材时 15s 不可用；不支持 4k |

## Compatibility Notes

| 场景 | 说明 |
|------|------|
| 文生视频 + 15 秒 | 所有模型均支持 |
| 图生视频 + 15 秒 | **不支持**，脚本会提示但继续请求；如失败请换 5/10 秒 |
| Vidu + 4k | **不支持**，脚本会提示但继续请求；如失败请换 720p/1080p |
| Kling + 4k | 仅文生视频支持，图生视频不保证 |

## Notes

- Video generation typically takes 1–3 minutes
- Reference images are optional — omit for pure text-to-video
- When providing multiple reference images, the first becomes the start frame and the last becomes the end frame (Vidu首尾帧)
