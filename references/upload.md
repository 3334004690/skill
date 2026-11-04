# Upload Module

Upload local images, videos, audio, or other files to Aimaxhug and return temp URL + metadata for media generation.

## When to Use

User provides local files that need to be used as generation references. The AI handles uploading and fills the returned references into the generation request. This includes image-to-image input, Muse first/last frames, reference images, and continuation videos. Existing usable media URLs are used directly without re-uploading.

For ordinary creative requests, keep intermediate media URLs and upload metadata in the execution flow. Tell the user which supplied materials are being used, without asking them to create URLs or showing technical upload fields. The final generated artwork/video is still presented normally; provide technical details when explicitly requested.

## Subcommands

| Subcommand | When to use |
|------------|-------------|
| `run` | **Default.** Upload file(s) and print result |

## Usage

```bash
python {baseDir}/scripts/upload.py run <file_paths...> [options]
```

## Examples

```bash
# Upload single file
python {baseDir}/scripts/upload.py run photo.jpg

# Upload multiple files
python {baseDir}/scripts/upload.py run photo1.jpg photo2.png

# JSON output for scripting
python {baseDir}/scripts/upload.py run photo.jpg --json

# Video upload (for Muse continuation, check local duration before uploading)
python {baseDir}/scripts/upload.py run source.mp4 --json
```

## Options

| Option | Description |
|--------|-------------|
| `files` | Local file path(s) to upload (required, one or more) |
| `--json` | Output results as JSON |

## Output

With `--json`, the script returns an array with one data object per file, in input order. Each object includes the fields below; a `markedUrl` may also be present. `ai_image.py --input-images` uses the metadata object. Muse takes only each object's `tmp_url` string and fills `input_reference`, `last_frame`, `images`, or `video_url` according to the supplied material's role. See [Muse material handling](muse_video.md#ai-自动处理参考素材).

```json
{
    "tmp_url": "https://static.aimaxhug.com/xxx.jpg",
    "name": "xxx.jpg",
    "type": "image/jpeg",
    "size": 123456
}
```
