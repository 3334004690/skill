# AI Image Module

Generate images from text prompts or edit existing images with reference images.

## Supported Task Types

| Type | Description |
|------|-------------|
| **Text-to-Image** | Generate images from a text prompt (no `--input-images`) |
| **Image-to-Image** | Edit/generate with reference images (pass `--input-images`) |

## Subcommands

| Subcommand | When to use |
|------------|-------------|
| `run` | **Default.** Generate image and show result |
| `list-models` | Show available models, resolutions, and proportions |

## Usage

```bash
python {baseDir}/scripts/ai_image.py <subcommand> [options]
```

## Examples

### List Models

```bash
# Show all models with supported parameters (MUST do this first)
python {baseDir}/scripts/ai_image.py list-models
```

### Text-to-Image

```bash
# Nano Banana — pick resolution
python {baseDir}/scripts/ai_image.py run \
  --model nano-banana \
  --prompt "一只橘猫在阳光下睡觉" \
  --proportion 16:9 \
  --resolution 2k

# gpt-image-2 — no --resolution needed
python {baseDir}/scripts/ai_image.py run \
  --model gpt-image-2 \
  --prompt "赛博朋克城市夜景" \
  --proportion 9:16
```

### Image-to-Image (with reference)

```bash
# Nano Banana Pro — edit with reference image
python {baseDir}/scripts/ai_image.py run \
  --model nano-banana-pro \
  --prompt "换成都市场景" \
  --input-images photo.jpg \
  --proportion 16:9 \
  --resolution 4k

# Multiple reference images
python {baseDir}/scripts/ai_image.py run \
  --model nano-banana \
  --prompt "把两张图合成一张" \
  --input-images photo1.jpg photo2.jpg \
  --proportion 1:1 \
  --resolution 4k
```

### Multi-Image Generation (Parallel)

```bash
# Generate 5 images with auto styles (runs in parallel!)
python {baseDir}/scripts/ai_image.py run \
  --model gpt-image-2 \
  --prompt "赛博朋克城市" \
  --count 5 \
  --proportion 16:9

# Generate 3 images with specific styles
python {baseDir}/scripts/ai_image.py run \
  --model nano-banana \
  --prompt "一只猫" \
  --count 3 \
  --styles 写实 卡通 油画 \
  --proportion 1:1 \
  --resolution 4k
```

> ⭐ **Don't run multi-image tasks one by one!** Use `--count N` — the script runs all N tasks in parallel automatically.
> ⚠️ Max `--count` is **14**. Single command at a time — wait for completion before next.

## Options

| Option | Description |
|--------|-------------|
| `--model` | Model key: `nano-banana`, `nano-banana-pro`, `gpt-image-2` (required) |
| `--prompt` | Text prompt describing the image (required) |
| `--proportion` | Aspect ratio, e.g. `16:9`, `1:1`, `9:16` |
| `--resolution` | `1k` / `2k` / `4k` — only for nano-banana/pro, do NOT pass for gpt-image-2 |
| `--input-images` | Local file path(s) for image-to-image (space-separated) |
| `--count` | Number of images to generate (default: 1, max: 14). **When > 1, all tasks run in parallel** |
| `--styles` | Custom styles for multi-image generation, space-separated. E.g. `--styles 写实 卡通 油画` |
| `--json` | Output result as JSON |

## Resolution Rules

| Model | Mode | Options |
|-------|------|---------|
| **Nano Banana** | Manual | `1k` / `2k` / `4k` (default: `1k`) |
| **Nano Banana Pro** | Manual | `1k` / `2k` / `4k` (default: `1k`) |
| **gpt-image-2** | Auto (from proportion) | `1:1` → `4k`, `9:16` → `4k`, `16:9` → `4k` |

## Supported Proportions (per model)

| Model | Supported Proportions |
|-------|----------------------|
| **Nano Banana** | `1:1` `9:16` `16:9` `2:3` `3:2` `3:4` `4:3` `4:5` `5:4` `21:9` (10种) |
| **Nano Banana Pro** | `1:1` `9:16` `16:9` `2:3` `3:2` `3:4` `4:3` `4:5` `5:4` `21:9` (10种) |
| **gpt-image-2** | `1:1` `9:16` `16:9` `2:3` `3:2` `3:4` `4:3` `4:5` `5:4` `21:9` (10种) |

## Model Recommendation

| Use Case | Recommended Model |
|----------|-------------------|
| **Best overall (default)** | Nano Banana |
| **Higher quality** | Nano Banana Pro |
| **Photo-realistic / art style** | gpt-image-2 |
